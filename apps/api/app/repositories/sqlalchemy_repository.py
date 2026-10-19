from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import threading

from app.db.models import (
    AiReviewRecord,
    AudioFileRecord,
    AuditLogRecord,
    CaseCareTeamAssignmentRecord,
    Base,
    ChildCaseRecord,
    FeatureSetRecord,
    MLResultRecord,
    OrganizationRecord,
    OrganizationSettingsRecord,
    PrivacyOperationRecord,
    ProcessingJobRecord,
    ReportRecord,
    SessionRecord,
    TherapyGoalRecord,
    TranscriptRecord,
)
from app.repositories.lazy_table import LazyTable
from app.repositories.base import (
    CaseVersionConflictError,
    ReportVersionConflictError,
    SessionVersionConflictError,
    TranscriptVersionConflictError,
)
from app.repositories.mock_repository import MockRepository, _plain, new_id, record_matches
from app.schemas.clinical import (
    AiReview,
    AudioFileMetadata,
    ChildCase,
    ChildCaseCreate,
    ChildCaseUpdate,
    FeatureSet,
    MLResult,
    PrivacyOperation,
    ProcessingJob,
    Report,
    ReviewStatus,
    TherapyGoal,
    TherapySession,
    TherapySessionCreate,
    TherapySessionUpdate,
    Transcript,
    utc_now,
)
from app.services.audit_safety import validate_audit_event


class SqlAlchemyRepository(MockRepository):
    """The repository over a SQL database.

    Services look records up by id in the collections below, change the
    objects they get, and call ``save``. Each collection reads a record from
    the database when it is first asked for and keeps the recently used ones;
    nothing is read at start-up. A subset is asked for with ``find``, which
    queries on the given columns.
    """

    def __init__(
        self,
        database_url: str,
        *,
        create_schema: bool = True,
        seed_demo: bool = True,
    ) -> None:
        try:
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError("SQLAlchemy repository mode requires sqlalchemy to be installed.") from exc

        self.database_url = database_url
        self.engine = create_engine(database_url)
        if create_schema:
            Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self._saved_audit_ids: set[str] = set()
        self._save_lock = threading.RLock()
        super().__init__(seed_demo=seed_demo)
        seeded = {name: dict(getattr(self, name)) for name in self._RECORD_TABLES}
        seeded_settings = dict(self.organization_settings)
        self._sources = self._record_sources()
        for name in self._RECORD_TABLES:
            setattr(self, name, self._lazy_table(name))
        self.organization_settings = LazyTable(
            "organization_settings",
            load_one=self._load_organization_settings,
            load_all=self._load_all_organization_settings,
            fingerprint=_settings_fingerprint,
            max_cached=None,
        )
        # Audit events are written as they happen; only the recent ones stay here.
        self.audit_log = []
        self.load(seeded, seeded_settings)

    def get_case(self, case_id: str) -> ChildCase | None:
        with self.SessionLocal() as db:
            row = db.get(ChildCaseRecord, case_id)
            return self._case_from_record(row) if row is not None else None

    def create_case(
        self,
        payload: ChildCaseCreate,
        *,
        actor_id: str,
        audit_actor_id: str | None = None,
    ) -> ChildCase:
        now = _utc_now()
        case = ChildCase(
            case_id=new_id("case"),
            **payload.model_dump(),
            created_at=now,
            updated_at=now,
        )
        if actor_id != "system" and actor_id not in case.care_team_user_ids:
            case.care_team_user_ids = [*case.care_team_user_ids, actor_id]
        if case.primary_therapist_user_id is None and actor_id != "system":
            case.primary_therapist_user_id = actor_id
        if case.primary_therapist_user_id and case.primary_therapist_user_id not in case.care_team_user_ids:
            case.care_team_user_ids = [*case.care_team_user_ids, case.primary_therapist_user_id]
        audit = validate_audit_event(
            actor_id=audit_actor_id or actor_id,
            action="case.create",
            target_id=case.case_id,
            outcome="success",
            correlation_id=f"case-create-{case.version}",
            message="Case created.",
        )
        with self.SessionLocal() as db:
            db.add(self._case_to_record(case))
            db.add(self._audit_to_record(audit.as_dict()))
            db.commit()
        self.cases[case.case_id] = case
        self.audit_log.append(audit.as_dict())
        return self.clone(case)

    def delete_case(self, case_id: str, *, actor_id: str) -> None:
        case = self.cases[case_id]
        audit = validate_audit_event(
            actor_id=actor_id,
            action="case.delete",
            target_id=case_id,
            outcome="success",
            correlation_id=f"case-delete-{case_id}",
            message="Empty case deleted.",
        ).as_dict()
        audit["organization_id"] = case.organization_id
        # One transaction: a row that still refers to the case stops all of it.
        with self.SessionLocal() as db:
            # Rows left by the retired care-team feature still point at the case.
            db.query(CaseCareTeamAssignmentRecord).filter_by(case_id=case_id).delete()
            db.query(ChildCaseRecord).filter_by(case_id=case_id).delete()
            db.add(self._audit_to_record(audit))
            db.commit()
        del self.cases[case_id]
        self.audit_log.append(audit)

    def update_case(
        self,
        case_id: str,
        patch: ChildCaseUpdate,
        *,
        expected_version: int | None,
        actor_id: str,
    ) -> ChildCase:
        now = _utc_now()
        patch_values = patch.model_dump(exclude_unset=True)
        with self.SessionLocal() as db:
            row = db.get(ChildCaseRecord, case_id)
            if row is None:
                raise KeyError(case_id)
            if expected_version is not None and row.version != expected_version:
                raise CaseVersionConflictError(
                    f"Case {case_id} expected version {expected_version}, found {row.version}."
                )
            for field, value in patch_values.items():
                setattr(row, field, value)
            row.version += 1
            row.updated_at = now
            audit = validate_audit_event(
                actor_id=actor_id,
                action="case.update",
                target_id=case_id,
                outcome="success",
                correlation_id=f"case-update-{row.version}",
                message="Case updated.",
            )
            db.add(self._audit_to_record(audit.as_dict()))
            db.commit()
            db.refresh(row)
            updated = self._case_from_record(row)
        self.cases[case_id] = updated
        self.audit_log.append(audit.as_dict())
        return self.clone(updated)

    def list_cases_for_user(self, user_id: str, organization_id: str) -> list[ChildCase]:
        return [self.clone(case) for case in self.find("cases", organization_id=organization_id)]

    def create_session(self, case_id: str, payload: TherapySessionCreate, *, actor_id: str) -> TherapySession:
        now = _utc_now()
        case = self.cases[case_id]
        session = TherapySession(
            session_id=new_id("session"),
            case_id=case_id,
            organization_id=case.organization_id,
            **payload.model_dump(),
            created_at=now,
            updated_at=now,
        )
        audit = validate_audit_event(
            actor_id=actor_id,
            action="session.create",
            target_id=session.session_id,
            outcome="success",
            correlation_id=f"session-create-{session.version}",
            message="Session created.",
        )
        with self.SessionLocal() as db:
            case_row = db.get(ChildCaseRecord, case_id)
            if case_row is None:
                raise KeyError(case_id)
            case_row.latest_session_date = session.session_date
            case_row.latest_session_status = session.status.value if hasattr(session.status, "value") else str(session.status)
            case_row.updated_at = now
            db.add(self._session_to_record(session))
            db.add(self._audit_to_record(audit.as_dict()))
            db.commit()
            db.refresh(case_row)
            updated_case = self._case_from_record(case_row)
        self.sessions[session.session_id] = session
        self.cases[case_id] = updated_case
        self.audit_log.append(audit.as_dict())
        return self.clone(session)

    def update_session(
        self,
        session_id: str,
        patch: TherapySessionUpdate,
        *,
        expected_version: int | None,
        actor_id: str,
    ) -> TherapySession:
        now = _utc_now()
        patch_values = patch.model_dump(exclude_unset=True)
        with self.SessionLocal() as db:
            row = db.get(SessionRecord, session_id)
            if row is None:
                raise KeyError(session_id)
            if expected_version is not None and row.version != expected_version:
                raise SessionVersionConflictError(
                    f"Session {session_id} expected version {expected_version}, found {row.version}."
                )
            for field, value in patch_values.items():
                setattr(row, field, value.value if hasattr(value, "value") else value)
            row.version += 1
            row.updated_at = now
            audit = validate_audit_event(
                actor_id=actor_id,
                action="session.patch",
                target_id=session_id,
                outcome="success",
                correlation_id=f"session-update-{row.version}",
                message="Session updated.",
            )
            db.add(self._audit_to_record(audit.as_dict()))
            db.commit()
            db.refresh(row)
            updated = self._session_from_record(row)
        self.sessions[session_id] = updated
        self.audit_log.append(audit.as_dict())
        return self.clone(updated)

    def create_transcript(
        self,
        transcript: Transcript,
        *,
        session_status: ReviewStatus,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> Transcript:
        transcript.organization_id = self.sessions[transcript.session_id].organization_id
        audit = validate_audit_event(
            actor_id=actor_id,
            action=audit_action,
            target_id=transcript.transcript_id,
            outcome="success",
            correlation_id=f"transcript-create-{transcript.version}",
            message=audit_message,
        )
        with self.SessionLocal() as db:
            session_row = db.get(SessionRecord, transcript.session_id)
            if session_row is None:
                raise KeyError(transcript.session_id)
            invalidated = self._mark_downstream_rows_stale(db, session_row)
            session_row.transcript_id = transcript.transcript_id
            session_row.status = session_status.value if hasattr(session_status, "value") else str(session_status)
            session_row.updated_at = _utc_now()
            db.add(self._transcript_to_record(transcript))
            db.add(self._audit_to_record(audit.as_dict()))
            invalidation_audit = self._downstream_invalidation_audit(actor_id, transcript.transcript_id, transcript.version) if invalidated else None
            if invalidation_audit is not None:
                db.add(self._audit_to_record(invalidation_audit.as_dict()))
            db.commit()
            db.refresh(session_row)
            updated_session = self._session_from_record(session_row)
        self.sessions[transcript.session_id] = updated_session
        self._mark_downstream_outputs_stale(self.sessions[transcript.session_id])
        self.transcripts[transcript.transcript_id] = transcript
        self.audit_log.append(audit.as_dict())
        if invalidation_audit is not None:
            self.audit_log.append(invalidation_audit.as_dict())
        return self.clone(transcript)

    def update_transcript(
        self,
        transcript: Transcript,
        *,
        session_status: ReviewStatus,
        expected_version: int | None,
        actor_id: str,
        audit_action: str,
        audit_message: str,
        invalidate_downstream: bool = True,
    ) -> Transcript:
        transcript.organization_id = self.sessions[transcript.session_id].organization_id
        audit = validate_audit_event(
            actor_id=actor_id,
            action=audit_action,
            target_id=transcript.transcript_id,
            outcome="success",
            correlation_id=f"transcript-update-{transcript.version}",
            message=audit_message,
        )
        with self.SessionLocal() as db:
            row = db.get(TranscriptRecord, transcript.transcript_id)
            if row is None:
                raise KeyError(transcript.transcript_id)
            if expected_version is not None and row.version != expected_version:
                raise TranscriptVersionConflictError(
                    f"Transcript {transcript.transcript_id} expected version {expected_version}, found {row.version}."
                )
            row.source = transcript.source
            row.raw_text = transcript.raw_text
            row.utterances = [item.model_dump(mode="json") for item in transcript.utterances]
            row.qa_status = transcript.qa_status.value if hasattr(transcript.qa_status, "value") else str(transcript.qa_status)
            row.qa_issues = [item.model_dump(mode="json") for item in transcript.qa_issues]
            row.review_status = transcript.review_status.value if hasattr(transcript.review_status, "value") else str(transcript.review_status)
            row.therapist_attested = transcript.therapist_attested
            row.attestation_reason = transcript.attestation_reason
            row.version = transcript.version
            row.updated_at = transcript.updated_at
            session_row = db.get(SessionRecord, transcript.session_id)
            if session_row is None:
                raise KeyError(transcript.session_id)
            invalidated = self._mark_downstream_rows_stale(db, session_row) if invalidate_downstream else False
            session_row.status = session_status.value if hasattr(session_status, "value") else str(session_status)
            session_row.updated_at = _utc_now()
            db.add(self._audit_to_record(audit.as_dict()))
            invalidation_audit = self._downstream_invalidation_audit(actor_id, transcript.transcript_id, transcript.version) if invalidated else None
            if invalidation_audit is not None:
                db.add(self._audit_to_record(invalidation_audit.as_dict()))
            db.commit()
            db.refresh(row)
            db.refresh(session_row)
            updated = self._transcript_from_record(row)
            updated_session = self._session_from_record(session_row)
        self.transcripts[transcript.transcript_id] = updated
        self.sessions[transcript.session_id] = updated_session
        if invalidate_downstream:
            self._mark_downstream_outputs_stale(self.sessions[transcript.session_id])
        self.audit_log.append(audit.as_dict())
        if invalidation_audit is not None:
            self.audit_log.append(invalidation_audit.as_dict())
        return self.clone(updated)

    @staticmethod
    def _mark_downstream_rows_stale(db, session_row: SessionRecord) -> bool:
        invalidated = False
        feature_row = db.get(FeatureSetRecord, session_row.feature_set_id) if session_row.feature_set_id else None
        if feature_row is not None and feature_row.review_status != ReviewStatus.stale.value:
            feature_row.review_status = ReviewStatus.stale.value
            invalidated = True

        ml_row = db.get(MLResultRecord, session_row.ml_result_id) if session_row.ml_result_id else None
        if ml_row is not None and (ml_row.payload or {}).get("is_current", True):
            payload = dict(ml_row.payload or {})
            payload["is_current"] = False
            ml_row.payload = payload
            invalidated = True

        ai_row = db.get(AiReviewRecord, session_row.ai_review_id) if session_row.ai_review_id else None
        if ai_row is not None and ai_row.therapist_review_status != ReviewStatus.stale.value:
            payload = dict(ai_row.payload or {})
            payload["therapist_review_status"] = ReviewStatus.stale.value
            ai_row.payload = payload
            ai_row.therapist_review_status = ReviewStatus.stale.value
            invalidated = True

        report_row = db.get(ReportRecord, session_row.report_id) if session_row.report_id else None
        if report_row is not None and report_row.status not in {ReviewStatus.signed_off.value, ReviewStatus.stale.value}:
            report_row.status = ReviewStatus.stale.value
            report_row.version += 1
            report_row.updated_at = _utc_now()
            case_row = db.get(ChildCaseRecord, session_row.case_id)
            if case_row is not None:
                case_row.latest_report_status = ReviewStatus.stale.value
            invalidated = True
        if invalidated:
            session_row.findings_stale = True
            session_row.report_stale = True
        return invalidated

    @staticmethod
    def _downstream_invalidation_audit(actor_id: str, transcript_id: str, version: int):
        return validate_audit_event(
            actor_id=actor_id,
            action="workflow.invalidate_downstream",
            target_id=transcript_id,
            outcome="success",
            correlation_id=f"workflow-invalidate-{version}",
            message="Derived workflow outputs marked stale after transcript change.",
        )

    def create_report(
        self,
        report: Report,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> Report:
        report.organization_id = self.cases[report.case_id].organization_id
        audit = validate_audit_event(
            actor_id=actor_id,
            action=audit_action,
            target_id=report.report_id,
            outcome="success",
            correlation_id=f"report-create-{report.version}",
            message=audit_message,
        )
        with self.SessionLocal() as db:
            session_row = db.get(SessionRecord, report.session_id)
            if session_row is None:
                raise KeyError(report.session_id)
            case_row = db.get(ChildCaseRecord, report.case_id)
            if case_row is None:
                raise KeyError(report.case_id)
            transcript_row = db.get(TranscriptRecord, report.transcript_id) if report.transcript_id else None
            expected_transcript_version = report.generated_from_versions.get("transcript_version")
            if report.transcript_id and (
                transcript_row is None
                or session_row.transcript_id != report.transcript_id
                or expected_transcript_version != str(transcript_row.version)
            ):
                raise ValueError("Transcript changed during report generation; discard the stale draft and retry.")
            feature_row = db.get(FeatureSetRecord, report.feature_result_id) if report.feature_result_id else None
            if report.feature_result_id and (
                session_row.feature_set_id != report.feature_result_id
                or feature_row is None
                or feature_row.review_status == ReviewStatus.stale.value
                or transcript_row is None
                or feature_row.transcript_version != transcript_row.version
            ):
                raise ValueError("Findings changed during report generation; discard the stale draft and retry.")
            session_row.report_id = report.report_id
            session_row.updated_at = _utc_now()
            case_row.latest_report_status = report.status.value if hasattr(report.status, "value") else str(report.status)
            case_row.updated_at = _utc_now()
            db.add(self._report_to_record(report))
            db.add(self._audit_to_record(audit.as_dict()))
            db.commit()
            db.refresh(session_row)
            db.refresh(case_row)
            updated_session = self._session_from_record(session_row)
            updated_case = self._case_from_record(case_row)
        self.reports[report.report_id] = report
        self.sessions[report.session_id] = updated_session
        self.cases[report.case_id] = updated_case
        self.audit_log.append(audit.as_dict())
        return self.clone(report)

    def update_report(
        self,
        report: Report,
        *,
        expected_version: int | None,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> Report:
        report.organization_id = self.cases[report.case_id].organization_id
        audit = validate_audit_event(
            actor_id=actor_id,
            action=audit_action,
            target_id=report.report_id,
            outcome="success",
            correlation_id=f"report-update-{report.version}",
            message=audit_message,
        )
        with self.SessionLocal() as db:
            row = db.get(ReportRecord, report.report_id)
            if row is None:
                raise KeyError(report.report_id)
            if expected_version is not None and row.version != expected_version:
                raise ReportVersionConflictError(
                    f"Report {report.report_id} expected version {expected_version}, found {row.version}."
                )
            record = self._report_to_record(report)
            for column in ReportRecord.__table__.columns:
                if column.name != "report_id":
                    setattr(row, column.name, getattr(record, column.name))
            case_row = db.get(ChildCaseRecord, report.case_id)
            if case_row is None:
                raise KeyError(report.case_id)
            case_row.latest_report_status = report.status.value if hasattr(report.status, "value") else str(report.status)
            case_row.updated_at = _utc_now()
            db.add(self._audit_to_record(audit.as_dict()))
            db.commit()
            db.refresh(row)
            db.refresh(case_row)
            updated = self._report_from_record(row)
            updated_case = self._case_from_record(case_row)
        self.reports[report.report_id] = updated
        self.cases[report.case_id] = updated_case
        self.audit_log.append(audit.as_dict())
        return self.clone(updated)

    def create_therapy_goal(
        self,
        goal: TherapyGoal,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> TherapyGoal:
        audit = validate_audit_event(
            actor_id=actor_id,
            action=audit_action,
            target_id=goal.goal_id,
            outcome="success",
            correlation_id=f"therapy-goal-create-{goal.goal_id}",
            message=audit_message,
        )
        with self.SessionLocal() as db:
            if db.get(ChildCaseRecord, goal.case_id) is None:
                raise KeyError(goal.case_id)
            db.add(self._goal_to_record(goal))
            db.add(self._audit_to_record(audit.as_dict()))
            db.commit()
        self.therapy_goals[goal.goal_id] = goal
        self.audit_log.append(audit.as_dict())
        return self.clone(goal)

    def update_therapy_goal(
        self,
        goal: TherapyGoal,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> TherapyGoal:
        audit = validate_audit_event(
            actor_id=actor_id,
            action=audit_action,
            target_id=goal.goal_id,
            outcome="success",
            correlation_id=f"therapy-goal-update-{goal.goal_id}",
            message=audit_message,
        )
        with self.SessionLocal() as db:
            row = db.get(TherapyGoalRecord, goal.goal_id)
            if row is None:
                raise KeyError(goal.goal_id)
            row.case_id = goal.case_id
            row.title = goal.title
            row.target = goal.target
            row.status = goal.status
            row.notes = goal.notes
            row.retained = goal.retained
            row.created_at = goal.created_at
            row.updated_at = goal.updated_at
            db.add(self._audit_to_record(audit.as_dict()))
            db.commit()
            db.refresh(row)
            updated = self._goal_from_record(row)
        self.therapy_goals[goal.goal_id] = updated
        self.audit_log.append(audit.as_dict())
        return self.clone(updated)

    def create_privacy_operation(
        self,
        operation: PrivacyOperation,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> PrivacyOperation:
        audit = validate_audit_event(
            actor_id=actor_id,
            action=audit_action,
            target_id=operation.privacy_operation_id,
            outcome="success",
            correlation_id=f"privacy-operation-create-{operation.privacy_operation_id}",
            message=audit_message,
        )
        with self.SessionLocal() as db:
            if db.get(ChildCaseRecord, operation.case_id) is None:
                raise KeyError(operation.case_id)
            db.add(self._privacy_operation_to_record(operation))
            db.add(self._audit_to_record(audit.as_dict()))
            db.commit()
        self.privacy_operations[operation.privacy_operation_id] = operation
        self.audit_log.append(audit.as_dict())
        return self.clone(operation)

    def update_privacy_operation(
        self,
        operation: PrivacyOperation,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> PrivacyOperation:
        audit = validate_audit_event(
            actor_id=actor_id,
            action=audit_action,
            target_id=operation.privacy_operation_id,
            outcome="success",
            correlation_id=f"privacy-operation-update-{operation.privacy_operation_id}",
            message=audit_message,
        )
        with self.SessionLocal() as db:
            row = db.get(PrivacyOperationRecord, operation.privacy_operation_id)
            if row is None:
                raise KeyError(operation.privacy_operation_id)
            record = self._privacy_operation_to_record(operation)
            for column in PrivacyOperationRecord.__table__.columns:
                if column.name != "privacy_operation_id":
                    setattr(row, column.name, getattr(record, column.name))
            db.add(self._audit_to_record(audit.as_dict()))
            db.commit()
            db.refresh(row)
            updated = self._privacy_operation_from_record(row)
        self.privacy_operations[operation.privacy_operation_id] = updated
        self.audit_log.append(audit.as_dict())
        return self.clone(updated)

    def create_feature_set(
        self,
        feature_set: FeatureSet,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> FeatureSet:
        audit = validate_audit_event(
            actor_id=actor_id,
            action=audit_action,
            target_id=feature_set.feature_set_id,
            outcome="success",
            correlation_id=f"feature-set-create-{feature_set.feature_set_id}",
            message=audit_message,
        )
        with self.SessionLocal() as db:
            session_row = db.get(SessionRecord, feature_set.session_id)
            if session_row is None:
                raise KeyError(feature_set.session_id)
            transcript_row = db.get(TranscriptRecord, feature_set.transcript_id)
            if (
                transcript_row is None
                or session_row.transcript_id != feature_set.transcript_id
                or transcript_row.version != feature_set.transcript_version
            ):
                raise ValueError("Transcript changed during feature extraction; discard the stale result and retry.")
            session_row.feature_set_id = feature_set.feature_set_id
            session_row.ml_result_id = None
            session_row.updated_at = _utc_now()
            db.add(self._feature_to_record(feature_set))
            db.add(self._audit_to_record(audit.as_dict()))
            db.commit()
            db.refresh(session_row)
            updated_session = self._session_from_record(session_row)
        self.features[feature_set.feature_set_id] = feature_set
        self.sessions[feature_set.session_id] = updated_session
        self.audit_log.append(audit.as_dict())
        return self.clone(feature_set)

    def create_ai_review(
        self,
        review: AiReview,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> AiReview:
        audit = validate_audit_event(
            actor_id=actor_id,
            action=audit_action,
            target_id=review.ai_review_id,
            outcome="success",
            correlation_id=f"ai-review-create-{review.ai_review_id}",
            message=audit_message,
        )
        with self.SessionLocal() as db:
            session_row = db.get(SessionRecord, review.session_id)
            if session_row is None:
                raise KeyError(review.session_id)
            case_row = db.get(ChildCaseRecord, session_row.case_id)
            if case_row is None:
                raise KeyError(session_row.case_id)
            transcript_row = db.get(TranscriptRecord, session_row.transcript_id) if session_row.transcript_id else None
            feature_row = db.get(FeatureSetRecord, review.feature_set_id) if review.feature_set_id else None
            if transcript_row is None or transcript_row.version != review.input_transcript_version:
                raise ValueError("Transcript changed during AI-assisted review generation; discard the stale result and retry.")
            if review.feature_set_id and (
                session_row.feature_set_id != review.feature_set_id
                or feature_row is None
                or feature_row.review_status == ReviewStatus.stale.value
                or feature_row.transcript_version != transcript_row.version
            ):
                raise ValueError("Findings changed during AI-assisted review generation; discard the stale result and retry.")
            session_row.ai_review_id = review.ai_review_id
            session_row.updated_at = _utc_now()
            case_row.review_priority = review.review_priority
            case_row.updated_at = _utc_now()
            db.add(self._ai_review_to_record(review))
            db.add(self._audit_to_record(audit.as_dict()))
            db.commit()
            db.refresh(session_row)
            db.refresh(case_row)
            updated_session = self._session_from_record(session_row)
            updated_case = self._case_from_record(case_row)
        self.ai_reviews[review.ai_review_id] = review
        self.sessions[review.session_id] = updated_session
        self.cases[updated_case.case_id] = updated_case
        self.audit_log.append(audit.as_dict())
        return self.clone(review)

    def update_ai_review(
        self,
        review: AiReview,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> AiReview:
        audit = validate_audit_event(
            actor_id=actor_id,
            action=audit_action,
            target_id=review.ai_review_id,
            outcome="success",
            correlation_id=f"ai-review-update-{review.ai_review_id}",
            message=audit_message,
        )
        with self.SessionLocal() as db:
            row = db.get(AiReviewRecord, review.ai_review_id)
            if row is None:
                raise KeyError(review.ai_review_id)
            record = self._ai_review_to_record(review)
            row.session_id = record.session_id
            row.payload = record.payload
            row.review_priority = record.review_priority
            row.therapist_review_status = record.therapist_review_status
            row.created_at = record.created_at
            db.add(self._audit_to_record(audit.as_dict()))
            db.commit()
            db.refresh(row)
            updated = AiReview.model_validate(row.payload)
        self.ai_reviews[review.ai_review_id] = updated
        self.audit_log.append(audit.as_dict())
        return self.clone(updated)

    def create_ml_result(
        self,
        result: MLResult,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> MLResult:
        audit = validate_audit_event(
            actor_id=actor_id,
            action=audit_action,
            target_id=result.result_id,
            outcome="success",
            correlation_id=f"ml-result-create-{result.result_id}",
            message=audit_message,
        )
        with self.SessionLocal() as db:
            session_row = db.get(SessionRecord, result.session_id)
            if session_row is None:
                raise KeyError(result.session_id)
            transcript_row = db.get(TranscriptRecord, result.transcript_id)
            feature_row = db.get(FeatureSetRecord, result.feature_result_id)
            if (
                transcript_row is None
                or session_row.transcript_id != result.transcript_id
                or session_row.feature_set_id != result.feature_result_id
                or feature_row is None
                or feature_row.review_status == ReviewStatus.stale.value
                or feature_row.transcript_id != transcript_row.transcript_id
                or feature_row.transcript_version != transcript_row.version
            ):
                raise ValueError("Transcript or findings changed during ML review generation; discard the stale result and retry.")
            session_row.ml_result_id = result.result_id
            session_row.updated_at = _utc_now()
            db.add(self._ml_result_to_record(result))
            db.add(self._audit_to_record(audit.as_dict()))
            db.commit()
            db.refresh(session_row)
            updated_session = self._session_from_record(session_row)
        self.ml_results[result.result_id] = result
        self.sessions[result.session_id] = updated_session
        self.audit_log.append(audit.as_dict())
        return self.clone(result)

    def update_ml_result(
        self,
        result: MLResult,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> MLResult:
        audit = validate_audit_event(
            actor_id=actor_id,
            action=audit_action,
            target_id=result.result_id,
            outcome="success",
            correlation_id=f"ml-result-update-{result.result_id}",
            message=audit_message,
        )
        with self.SessionLocal() as db:
            row = db.get(MLResultRecord, result.result_id)
            if row is None:
                raise KeyError(result.result_id)
            record = self._ml_result_to_record(result)
            row.session_id = record.session_id
            row.transcript_id = record.transcript_id
            row.payload = record.payload
            row.created_at = record.created_at
            db.add(self._audit_to_record(audit.as_dict()))
            db.commit()
            db.refresh(row)
            updated = MLResult.model_validate(row.payload)
        self.ml_results[result.result_id] = updated
        self.audit_log.append(audit.as_dict())
        return self.clone(updated)

    # In the order rows have to be written: a record after the ones it refers to.
    _RECORD_TABLES = (
        "cases",
        "sessions",
        "transcripts",
        "features",
        "ml_results",
        "audio_files",
        "ai_reviews",
        "reports",
        "therapy_goals",
        "jobs",
        "privacy_operations",
    )
    # How many audit events stay in memory after they are stored.
    _AUDIT_TAIL = 200

    def _record_sources(self) -> dict:
        """For each collection: its table, its key column, and how a row becomes a record and back."""
        return {
            "cases": (ChildCaseRecord, "case_id", self._case_from_record, self._case_to_record),
            "sessions": (SessionRecord, "session_id", self._session_from_record, self._session_to_record),
            "transcripts": (TranscriptRecord, "transcript_id", self._transcript_from_record, self._transcript_to_record),
            "features": (FeatureSetRecord, "feature_set_id", self._feature_from_record, self._feature_to_record),
            "ml_results": (
                MLResultRecord,
                "result_id",
                lambda row: MLResult.model_validate(row.payload),
                lambda result: MLResultRecord(
                    result_id=result.result_id,
                    session_id=result.session_id,
                    transcript_id=result.transcript_id,
                    payload=result.model_dump(mode="json"),
                    created_at=result.generated_at,
                ),
            ),
            "audio_files": (AudioFileRecord, "audio_file_id", self._audio_from_record, self._audio_to_record),
            "ai_reviews": (
                AiReviewRecord,
                "ai_review_id",
                lambda row: AiReview.model_validate(row.payload),
                lambda review: AiReviewRecord(
                    ai_review_id=review.ai_review_id,
                    session_id=review.session_id,
                    payload=review.model_dump(mode="json"),
                    review_priority=review.review_priority,
                    therapist_review_status=review.therapist_review_status.value,
                    created_at=review.created_at,
                ),
            ),
            "reports": (ReportRecord, "report_id", self._report_from_record, self._report_to_record),
            "therapy_goals": (TherapyGoalRecord, "goal_id", self._goal_from_record, self._goal_to_record),
            "jobs": (ProcessingJobRecord, "job_id", self._job_from_record, self._job_to_record),
            "privacy_operations": (
                PrivacyOperationRecord,
                "privacy_operation_id",
                self._privacy_operation_from_record,
                self._privacy_operation_to_record,
            ),
        }

    def _lazy_table(self, name: str) -> LazyTable:
        record, key_column, from_record, _ = self._sources[name]

        def load_one(key: str):
            with self.SessionLocal() as db:
                row = db.get(record, key)
                return from_record(row) if row is not None else None

        def load_all():
            with self.SessionLocal() as db:
                return [(getattr(row, key_column), from_record(row)) for row in db.query(record)]

        return LazyTable(name, load_one=load_one, load_all=load_all, fingerprint=_fingerprint)

    def _load_organization_settings(self, organization_id: str) -> dict | None:
        with self.SessionLocal() as db:
            row = db.get(OrganizationSettingsRecord, organization_id)
            return dict(row.settings or {}) if row is not None else None

    def _load_all_organization_settings(self) -> list[tuple[str, dict]]:
        with self.SessionLocal() as db:
            return [(row.organization_id, dict(row.settings or {})) for row in db.query(OrganizationSettingsRecord)]

    def find(self, collection: str, **where) -> list:
        """Records whose fields equal the given values, read with one query on those columns.

        Records already held are returned as the objects everyone else has,
        and what is in memory decides the answer: a record changed or created
        here and not saved yet is judged by its current fields.
        """
        record, key_column, from_record, _ = self._sources[collection]
        table: LazyTable = getattr(self, collection)
        with self.SessionLocal() as db:
            query = db.query(record)
            for field, wanted in where.items():
                column = getattr(record, field)
                if isinstance(wanted, (set, frozenset, list, tuple)):
                    query = query.filter(column.in_([_plain(item) for item in wanted]))
                else:
                    query = query.filter(column == _plain(wanted))
            rows = [(getattr(row, key_column), from_record(row)) for row in query]
        table.admit(rows)
        matches = [(key, value) for key, value in table.loaded() if record_matches(value, where)]
        matches.sort(key=lambda item: (_created_order(item[1]), item[0]))
        return [value for _, value in matches]

    def audit_events(self, **where) -> list[dict]:
        """Stored audit events whose fields equal the given values, oldest first.

        The list in memory holds recent events only; this reads the table.
        """
        self.save()
        with self.SessionLocal() as db:
            query = db.query(AuditLogRecord)
            for field, wanted in where.items():
                query = query.filter(getattr(AuditLogRecord, field) == wanted)
            return [
                {
                    "audit_id": row.audit_id,
                    "organization_id": row.organization_id,
                    "actor_id": row.actor_id,
                    "action": row.action,
                    "target_id": row.target_id,
                    "outcome": row.outcome,
                    "correlation_id": row.correlation_id,
                    "message": row.message,
                    "timestamp": row.timestamp.isoformat() if hasattr(row.timestamp, "isoformat") else str(row.timestamp),
                }
                for row in query.order_by(AuditLogRecord.timestamp)
            ]

    def load(self, seeded: dict | None = None, seeded_settings: dict | None = None) -> None:
        """Prepare an empty cache. Nothing is read until a record is asked for.

        In demo mode an empty database receives the sample records.
        """
        with self._save_lock:
            self.organization_settings.setdefault("pilot_org_001", {"ai_review_enabled": True})
            if not seeded or not seeded.get("cases"):
                return
            with self.SessionLocal() as db:
                has_cases = db.query(ChildCaseRecord.case_id).first() is not None
            if has_cases:
                return
            for name, records in seeded.items():
                table = getattr(self, name)
                for key, value in records.items():
                    table[key] = value
            for organization_id, settings in (seeded_settings or {}).items():
                self.organization_settings.setdefault(organization_id, settings)
            self._save_changes()

    def save(self) -> None:
        """Persist the records held in memory that changed, without deleting any row.

        Service paths change the objects the repository hands out and rely on
        this write. It upserts by primary key the held records that differ
        from what was last read or written, and appends only audit events that
        are not stored yet, so it can never remove records written by another
        repository instance, and its cost follows the size of the change, not
        the size of the database. Row removal goes through the explicit
        ``delete_*`` methods.
        """
        with self._save_lock:
            self._save_changes()

    def _save_changes(self) -> None:
        written: list[tuple[LazyTable, str, bytes]] = []
        with self.SessionLocal() as db:
            for name in self._RECORD_TABLES:
                table: LazyTable = getattr(self, name)
                to_record = self._sources[name][3]
                for key, value, fingerprint in table.changed():
                    db.merge(to_record(value))
                    written.append((table, key, fingerprint))
            for organization_id, settings, fingerprint in self.organization_settings.changed():
                written.append((self.organization_settings, organization_id, fingerprint))
                if db.get(OrganizationRecord, organization_id) is None:
                    db.add(OrganizationRecord(
                        organization_id=organization_id,
                        name=organization_id,
                        pilot_mode=False,
                        created_at=_utc_now(),
                    ))
                existing_settings = db.get(OrganizationSettingsRecord, organization_id)
                if existing_settings is None:
                    db.add(OrganizationSettingsRecord(
                        organization_id=organization_id,
                        ai_drafting_enabled=bool(settings.get("ai_drafting_enabled", False)),
                        default_retention_region=str(settings.get("default_retention_region", "local_pilot")),
                        settings=settings,
                        created_at=_utc_now(),
                        updated_at=_utc_now(),
                    ))
                elif existing_settings.settings != settings:
                    existing_settings.ai_drafting_enabled = bool(settings.get("ai_drafting_enabled", False))
                    existing_settings.default_retention_region = str(
                        settings.get("default_retention_region", "local_pilot")
                    )
                    existing_settings.settings = dict(settings)
                    existing_settings.updated_at = _utc_now()
            # Record-scoped methods store their own audit event before adding it
            # to the list, so ask the database about the unseen ones only.
            unseen = [item for item in list(self.audit_log) if item["audit_id"] not in self._saved_audit_ids]
            unseen_ids = [item["audit_id"] for item in unseen]
            stored_audit_ids = {
                audit_id
                for start in range(0, len(unseen_ids), 500)
                for (audit_id,) in db.query(AuditLogRecord.audit_id).filter(
                    AuditLogRecord.audit_id.in_(unseen_ids[start:start + 500])
                )
            }
            for item in unseen:
                if item["audit_id"] not in stored_audit_ids:
                    db.add(self._audit_to_record(item))
            db.commit()

        for table, key, fingerprint in written:
            table.mark_stored(key, fingerprint)
        for name in self._RECORD_TABLES:
            getattr(self, name).forget_unheld()
        self._saved_audit_ids.update(unseen_ids)
        # Everything in the list is stored now. Removed in place, so an event
        # another thread appends meanwhile is not lost.
        excess = len(self.audit_log) - self._AUDIT_TAIL
        if excess > 0:
            dropped = self.audit_log[:excess]
            if all(item["audit_id"] in self._saved_audit_ids for item in dropped):
                del self.audit_log[:excess]
                self._saved_audit_ids.difference_update(item["audit_id"] for item in dropped)

    def delete_case_records(self, case_id: str, *, actor_id: str, session_id: str | None = None) -> dict[str, int]:
        """Remove a case with every row recorded for it (or one of its sessions) in one transaction.

        Rows go when they are one of the records found, or carry the case's id
        (whole case only), one of the sessions' ids or one of their jobs' ids,
        so tables left by retired features are emptied too. The audit log is
        kept and gains one event with counts only. Stored recordings are the
        caller's to remove.
        """
        from sqlalchemy import inspect, or_

        from app.repositories.mock_repository import _deletion_message

        self.save()
        organization_id = self.cases[case_id].organization_id
        records = self.case_records(case_id, session_id=session_id)
        ids = {
            self._sources[collection][0].__tablename__: {
                getattr(record, self._sources[collection][1]) for record in found
            }
            for collection, found in records.items()
        }
        session_ids = ids.get(SessionRecord.__tablename__, set())
        job_ids = ids.get(ProcessingJobRecord.__tablename__, set())
        removed = {collection: len(found) for collection, found in records.items()}
        audit = validate_audit_event(
            actor_id=actor_id,
            action="session.delete" if session_id else "case.delete",
            target_id=session_id or case_id,
            outcome="success",
            correlation_id=f"{'session' if session_id else 'case'}-delete-{session_id or case_id}",
            message=_deletion_message(removed, session_id),
        ).as_dict()
        audit["organization_id"] = organization_id
        present = set(inspect(self.engine).get_table_names())
        with self.SessionLocal() as db:
            for table in reversed(Base.metadata.sorted_tables):
                if table.name not in present or table.name == AuditLogRecord.__tablename__:
                    continue
                columns = table.columns
                conditions = []
                primary = list(table.primary_key.columns)
                if ids.get(table.name) and len(primary) == 1:
                    conditions.append(primary[0].in_(ids[table.name]))
                if session_id is None and "case_id" in columns:
                    conditions.append(columns["case_id"] == case_id)
                if "session_id" in columns and session_ids:
                    conditions.append(columns["session_id"].in_(session_ids))
                if "job_id" in columns and job_ids and table.name != ProcessingJobRecord.__tablename__:
                    conditions.append(columns["job_id"].in_(job_ids))
                if conditions:
                    db.execute(table.delete().where(or_(*conditions)))
            db.add(self._audit_to_record(audit))
            db.commit()
        for collection, found in records.items():
            table = getattr(self, collection)
            for record in found:
                table.forget(getattr(record, self._sources[collection][1]))
        self.audit_log.append(audit)
        self._saved_audit_ids.add(audit["audit_id"])
        return removed

    def delete_workspace(self, organization_id: str, *, user_id: str) -> dict[str, int]:
        """Remove every row of one workspace and its account in one transaction.

        Tables are emptied children first, in the schema's own dependency
        order. A row goes when it carries the workspace's id, hangs off one
        of its cases, sessions or jobs, or names the account; tables left by
        retired features are included, and a table this database does not
        have is skipped.
        """
        from sqlalchemy import inspect, or_

        self.save()
        records = self.workspace_records(organization_id)
        ids = {
            self._sources[collection][0].__tablename__: {
                getattr(record, self._sources[collection][1]) for record in found
            }
            for collection, found in records.items()
        }
        case_ids = ids.get(ChildCaseRecord.__tablename__, set())
        session_ids = ids.get(SessionRecord.__tablename__, set())
        job_ids = ids.get(ProcessingJobRecord.__tablename__, set())
        audit = validate_audit_event(
            actor_id=user_id,
            action="account.delete",
            target_id=organization_id,
            outcome="success",
            correlation_id=f"account-delete-{organization_id}",
            message="Account deleted with its records.",
        ).as_dict()
        audit["organization_id"] = organization_id
        present = set(inspect(self.engine).get_table_names())
        with self.SessionLocal() as db:
            for table in reversed(Base.metadata.sorted_tables):
                if table.name not in present:
                    continue
                columns = table.columns
                conditions = []
                primary = list(table.primary_key.columns)
                if table.name in ids and ids[table.name] and len(primary) == 1:
                    conditions.append(primary[0].in_(ids[table.name]))
                if "organization_id" in columns:
                    conditions.append(columns["organization_id"] == organization_id)
                if "case_id" in columns and case_ids:
                    conditions.append(columns["case_id"].in_(case_ids))
                if "session_id" in columns and session_ids:
                    conditions.append(columns["session_id"].in_(session_ids))
                if "job_id" in columns and job_ids and table.name != ProcessingJobRecord.__tablename__:
                    conditions.append(columns["job_id"].in_(job_ids))
                for column in ("user_id", "recipient_user_id"):
                    if column in columns:
                        conditions.append(columns[column] == user_id)
                if conditions:
                    db.execute(table.delete().where(or_(*conditions)))
            db.add(self._audit_to_record(audit))
            db.commit()
        for collection, found in records.items():
            table = getattr(self, collection)
            for record in found:
                table.forget(getattr(record, self._sources[collection][1]))
        self.organization_settings.forget(organization_id)
        self.audit_log[:] = [event for event in self.audit_log if event.get("organization_id") != organization_id]
        self.audit_log.append(audit)
        self._saved_audit_ids.add(audit["audit_id"])
        return {collection: len(found) for collection, found in records.items()}

    def delete_feature_set(self, feature_set_id: str) -> None:
        super().delete_feature_set(feature_set_id)
        with self.SessionLocal() as db:
            db.query(FeatureSetRecord).filter_by(feature_set_id=feature_set_id).delete()
            db.commit()

    def delete_ml_result(self, result_id: str) -> None:
        super().delete_ml_result(result_id)
        with self.SessionLocal() as db:
            db.query(MLResultRecord).filter_by(result_id=result_id).delete()
            db.commit()

    def add_audit(
        self,
        action: str,
        target_id: str,
        message: str,
        *,
        actor_id: str = "system",
        outcome: str = "success",
        correlation_id: str = "local",
        organization_id: str | None = None,
    ) -> None:
        super().add_audit(
            action,
            target_id,
            message,
            actor_id=actor_id,
            outcome=outcome,
            correlation_id=correlation_id,
            organization_id=organization_id,
        )
        self.save()

    def _case_to_record(self, case: ChildCase) -> ChildCaseRecord:
        return ChildCaseRecord(
            case_id=case.case_id,
            organization_id=case.organization_id,
            care_team_user_ids=case.care_team_user_ids,
            primary_therapist_user_id=case.primary_therapist_user_id,
            child_code=case.child_code,
            nickname=case.nickname,
            age_months=case.age_months,
            language=case.language,
            consent_status=case.consent_status,
            review_priority=case.review_priority,
            notes=case.notes,
            version=case.version,
            latest_session_date=case.latest_session_date,
            latest_session_status=case.latest_session_status.value
            if hasattr(case.latest_session_status, "value")
            else str(case.latest_session_status),
            latest_report_status=case.latest_report_status.value
            if hasattr(case.latest_report_status, "value")
            else str(case.latest_report_status),
            created_at=case.created_at,
            updated_at=case.updated_at,
        )

    def _privacy_operation_to_record(self, operation: PrivacyOperation) -> PrivacyOperationRecord:
        return PrivacyOperationRecord(
            privacy_operation_id=operation.privacy_operation_id,
            organization_id=operation.organization_id,
            case_id=operation.case_id,
            operation_type=operation.operation_type,
            status=operation.status,
            requested_by=operation.requested_by,
            requester_role=operation.requester_role,
            reason=operation.reason,
            admin_note=operation.admin_note,
            retention_days=operation.retention_days,
            legal_hold=operation.legal_hold,
            deletion_review_required=operation.deletion_review_required,
            preserve_evidence=operation.preserve_evidence,
            eligible_for_deletion_at=operation.eligible_for_deletion_at,
            completed_at=operation.completed_at,
            evidence_retained=operation.evidence_retained,
            created_at=operation.created_at,
            updated_at=operation.updated_at,
        )

    def _privacy_operation_from_record(self, row: PrivacyOperationRecord) -> PrivacyOperation:
        return PrivacyOperation(
            privacy_operation_id=row.privacy_operation_id,
            organization_id=row.organization_id,
            case_id=row.case_id,
            operation_type=row.operation_type,
            status=row.status,
            requested_by=row.requested_by,
            requester_role=row.requester_role,
            reason=row.reason,
            admin_note=row.admin_note,
            retention_days=row.retention_days,
            legal_hold=row.legal_hold,
            deletion_review_required=row.deletion_review_required,
            preserve_evidence=row.preserve_evidence,
            eligible_for_deletion_at=row.eligible_for_deletion_at,
            completed_at=row.completed_at,
            evidence_retained=row.evidence_retained,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _case_from_record(self, row: ChildCaseRecord) -> ChildCase:
        return ChildCase(
            case_id=row.case_id,
            organization_id=row.organization_id,
            care_team_user_ids=list(row.care_team_user_ids or []),
            primary_therapist_user_id=row.primary_therapist_user_id,
            child_code=row.child_code,
            nickname=row.nickname,
            age_months=row.age_months,
            language=row.language,
            consent_status=row.consent_status,
            review_priority=row.review_priority,
            notes=row.notes,
            version=row.version,
            latest_session_date=row.latest_session_date,
            latest_session_status=ReviewStatus(row.latest_session_status),
            latest_report_status=ReviewStatus(row.latest_report_status),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _session_to_record(self, session: TherapySession) -> SessionRecord:
        return SessionRecord(**session.model_dump(mode="python"))

    def _session_from_record(self, row: SessionRecord) -> TherapySession:
        return TherapySession(
            session_id=row.session_id,
            case_id=row.case_id,
            organization_id=row.organization_id,
            version=row.version,
            session_date=row.session_date,
            session_type=row.session_type,
            notes=row.notes,
            status=row.status,
            transcript_id=row.transcript_id,
            feature_set_id=row.feature_set_id,
            ml_result_id=row.ml_result_id,
            ai_review_id=row.ai_review_id,
            report_id=row.report_id,
            findings_stale=getattr(row, "findings_stale", False),
            report_stale=getattr(row, "report_stale", False),
            cues_acknowledged_at=row.cues_acknowledged_at,
            cues_acknowledged_by=row.cues_acknowledged_by,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _transcript_to_record(self, transcript: Transcript) -> TranscriptRecord:
        return TranscriptRecord(
            transcript_id=transcript.transcript_id,
            session_id=transcript.session_id,
            case_id=transcript.case_id,
            organization_id=transcript.organization_id,
            source=transcript.source,
            raw_text=transcript.raw_text,
            utterances=[item.model_dump(mode="json") for item in transcript.utterances],
            qa_status=transcript.qa_status.value,
            qa_issues=[item.model_dump(mode="json") for item in transcript.qa_issues],
            review_status=transcript.review_status.value,
            therapist_attested=transcript.therapist_attested,
            attestation_reason=transcript.attestation_reason,
            version=transcript.version,
            created_at=transcript.created_at,
            updated_at=transcript.updated_at,
        )

    def _transcript_from_record(self, row: TranscriptRecord) -> Transcript:
        return Transcript.model_validate(
            {
                "transcript_id": row.transcript_id,
                "session_id": row.session_id,
                "case_id": row.case_id,
                "organization_id": row.organization_id,
                "source": row.source,
                "raw_text": row.raw_text,
                "utterances": row.utterances,
                "qa_status": row.qa_status,
                "qa_issues": row.qa_issues,
                "review_status": row.review_status,
                "therapist_attested": row.therapist_attested,
                "attestation_reason": row.attestation_reason,
                "version": row.version,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }
        )

    def _feature_to_record(self, feature_set: FeatureSet) -> FeatureSetRecord:
        return FeatureSetRecord(
            feature_set_id=feature_set.feature_set_id,
            organization_id=feature_set.organization_id,
            session_id=feature_set.session_id,
            transcript_id=feature_set.transcript_id,
            transcript_version=feature_set.transcript_version,
            schema_version=feature_set.schema_version,
            therapist_attested=feature_set.therapist_attested,
            warnings=feature_set.warnings,
            features=[item.model_dump(mode="json") for item in feature_set.features],
            review_status=feature_set.review_status.value,
            extracted_at=feature_set.extracted_at,
        )

    def _feature_from_record(self, row: FeatureSetRecord) -> FeatureSet:
        return FeatureSet.model_validate(
            {
                "feature_set_id": row.feature_set_id,
                "organization_id": row.organization_id,
                "session_id": row.session_id,
                "transcript_id": row.transcript_id,
                "transcript_version": row.transcript_version,
                "schema_version": row.schema_version,
                "therapist_attested": row.therapist_attested,
                "warnings": row.warnings,
                "features": row.features,
                "review_status": row.review_status,
                "extracted_at": row.extracted_at,
            }
        )

    def _audio_to_record(self, audio_file: AudioFileMetadata) -> AudioFileRecord:
        return AudioFileRecord(**audio_file.model_dump(mode="python"))

    def _audio_from_record(self, row: AudioFileRecord) -> AudioFileMetadata:
        return AudioFileMetadata(
            audio_file_id=row.audio_file_id,
            organization_id=row.organization_id,
            session_id=row.session_id,
            case_id=row.case_id,
            original_filename=row.original_filename,
            content_type=row.content_type,
            size_bytes=row.size_bytes,
            storage_mode=row.storage_mode,
            object_key=row.object_key,
            upload_status=row.upload_status,
            duration_seconds=row.duration_seconds,
            sample_rate_hz=row.sample_rate_hz,
            channels=row.channels,
            estimated_noise_level=row.estimated_noise_level,
            silence_ratio=row.silence_ratio,
            checksum_sha256=row.checksum_sha256,
            uploaded_at=row.uploaded_at,
            storage_delete_status=row.storage_delete_status,
            retained=row.retained,
            created_at=row.created_at,
        )

    def _ai_review_to_record(self, review: AiReview) -> AiReviewRecord:
        return AiReviewRecord(
            ai_review_id=review.ai_review_id,
            organization_id=review.organization_id,
            session_id=review.session_id,
            payload=review.model_dump(mode="json"),
            review_priority=review.review_priority,
            therapist_review_status=review.therapist_review_status.value,
            created_at=review.created_at,
        )

    def _ml_result_to_record(self, result: MLResult) -> MLResultRecord:
        return MLResultRecord(
            result_id=result.result_id,
            organization_id=result.organization_id,
            session_id=result.session_id,
            transcript_id=result.transcript_id,
            payload=result.model_dump(mode="json"),
            created_at=result.generated_at,
        )

    def _report_to_record(self, report: Report) -> ReportRecord:
        data = report.model_dump(mode="python")
        json_data = report.model_dump(mode="json")
        for field in (
            "safety_validation_result",
            "finalized_safety_result",
            "signed_snapshot",
            "session_goals",
            "generated_from_versions",
            "sections",
        ):
            data[field] = json_data[field]
        return ReportRecord(**data)

    def _report_from_record(self, row: ReportRecord) -> Report:
        return Report(
            report_id=row.report_id,
            session_id=row.session_id,
            case_id=row.case_id,
            organization_id=row.organization_id,
            report_type=row.report_type,
            title=row.title,
            markdown=row.markdown,
            html=row.html,
            status=row.status,
            therapist_signoff_status=row.therapist_signoff_status,
            limitation_text=row.limitation_text,
            export_timestamp=row.export_timestamp,
            created_at=row.created_at,
            updated_at=row.updated_at,
            requested_provider=row.requested_provider,
            actual_provider=row.actual_provider,
            provider_version=row.provider_version,
            fallback_reason=row.fallback_reason,
            rewrite_attempted=row.rewrite_attempted,
            rewrite_succeeded=row.rewrite_succeeded,
            safety_validation_result=row.safety_validation_result,
            finalized_safety_result=row.finalized_safety_result,
            finalization_blocked=row.finalization_blocked,
            validator_version=row.validator_version,
            rule_set_version=row.rule_set_version,
            input_hash=row.input_hash,
            version=row.version,
            signed_by=row.signed_by,
            signed_at=row.signed_at,
            signed_snapshot_version=row.signed_snapshot_version,
            signed_snapshot_hash=row.signed_snapshot_hash,
            signed_snapshot=row.signed_snapshot,
            supersedes_report_id=row.supersedes_report_id,
            revision_number=row.revision_number,
            ai_drafting_requested=row.ai_drafting_requested,
            ai_drafting_enabled=row.ai_drafting_enabled,
            ai_drafting_provider=row.ai_drafting_provider,
            ai_drafting_model=row.ai_drafting_model,
            ai_drafting_region=row.ai_drafting_region,
            ai_drafting_input_hash=row.ai_drafting_input_hash,
            transcript_id=row.transcript_id,
            feature_result_id=row.feature_result_id,
            ml_result_id=row.ml_result_id,
            ml_skipped_reason=row.ml_skipped_reason,
            validation_summary=row.validation_summary,
            feature_schema_version=row.feature_schema_version,
            therapist_notes=row.therapist_notes,
            session_goals=row.session_goals,
            generated_from_versions=row.generated_from_versions,
            sections=row.sections,
        )

    def _goal_to_record(self, goal: TherapyGoal) -> TherapyGoalRecord:
        return TherapyGoalRecord(**goal.model_dump(mode="python"))

    def _goal_from_record(self, row: TherapyGoalRecord) -> TherapyGoal:
        return TherapyGoal(
            goal_id=row.goal_id,
            organization_id=row.organization_id,
            case_id=row.case_id,
            title=row.title,
            target=row.target,
            status=row.status,
            notes=row.notes,
            retained=row.retained,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _job_to_record(self, job: ProcessingJob) -> ProcessingJobRecord:
        return ProcessingJobRecord(**job.model_dump(mode="python"))

    def _job_from_record(self, row: ProcessingJobRecord) -> ProcessingJob:
        return ProcessingJob(
            job_id=row.job_id,
            organization_id=row.organization_id,
            session_id=row.session_id,
            status=row.status,
            message=row.message,
            error_code=row.error_code,
            details=row.details,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _audit_to_record(self, item: dict) -> AuditLogRecord:
        return AuditLogRecord(
            audit_id=item["audit_id"],
            organization_id=item.get("organization_id", "pilot_org_001"),
            actor_id=item.get("actor_id", "system"),
            action=item["action"],
            target_id=item["target_id"],
            outcome=item.get("outcome", "success"),
            correlation_id=item.get("correlation_id", "local"),
            message=item["message"],
            timestamp=_parse_datetime(item["timestamp"]),
        )


def _fingerprint(value) -> bytes:
    return hashlib.blake2b(value.model_dump_json().encode("utf-8"), digest_size=16).digest()


def _created_order(record) -> str:
    """Oldest first, as a plain collection kept them."""
    return str(getattr(record, "created_at", None) or getattr(record, "generated_at", None) or "")


def _settings_fingerprint(settings: dict) -> bytes:
    encoded = json.dumps(settings, sort_keys=True, default=str).encode("utf-8")
    return hashlib.blake2b(encoded, digest_size=16).digest()


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)
