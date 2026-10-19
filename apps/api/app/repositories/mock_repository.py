from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from uuid import uuid4

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
from app.repositories.base import (
    CaseVersionConflictError,
    ReportVersionConflictError,
    SessionVersionConflictError,
    TranscriptVersionConflictError,
)
from app.services.audit_safety import validate_audit_event


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:10]}"


def _plain(value):
    return getattr(value, "value", value)


def record_matches(record, where: dict) -> bool:
    """Whether a record's fields equal the wanted values; enums compare by value."""
    for field, wanted in where.items():
        actual = _plain(getattr(record, field))
        if isinstance(wanted, (set, frozenset, list, tuple)):
            if actual not in {_plain(item) for item in wanted}:
                return False
        elif actual != _plain(wanted):
            return False
    return True


_RECORD_KEYS = {
    "cases": "case_id",
    "sessions": "session_id",
    "transcripts": "transcript_id",
    "features": "feature_set_id",
    "ml_results": "result_id",
    "ai_reviews": "ai_review_id",
    "reports": "report_id",
    "therapy_goals": "goal_id",
    "audio_files": "audio_file_id",
    "jobs": "job_id",
    "privacy_operations": "privacy_operation_id",
}


def _record_key(collection: str, record) -> str:
    return getattr(record, _RECORD_KEYS[collection])


_RECORD_TYPES = {
    "cases": ChildCase,
    "sessions": TherapySession,
    "transcripts": Transcript,
    "features": FeatureSet,
    "ml_results": MLResult,
    "ai_reviews": AiReview,
    "reports": Report,
    "therapy_goals": TherapyGoal,
    "audio_files": AudioFileMetadata,
    "jobs": ProcessingJob,
    "privacy_operations": PrivacyOperation,
}


def _fields(collection: str) -> set[str]:
    return set(_RECORD_TYPES[collection].model_fields)


def _deletion_message(removed: dict[str, int], session_id: str | None) -> str:
    """What a case or session deletion removed, in counts only (no clinical content)."""
    what = "Session deleted" if session_id else "Case deleted"
    counts = ", ".join(f"{count} {name}" for name, count in removed.items() if count and name not in {"cases"})
    return f"{what} with its records: {counts}." if counts else f"{what}."


class MockRepository:
    """In-memory repository for local demo and contract tests."""

    def __init__(self, *, seed_demo: bool = True) -> None:
        self.cases: dict[str, ChildCase] = {}
        self.sessions: dict[str, TherapySession] = {}
        self.transcripts: dict[str, Transcript] = {}
        self.features: dict[str, FeatureSet] = {}
        self.ml_results: dict[str, MLResult] = {}
        self.ai_reviews: dict[str, AiReview] = {}
        self.reports: dict[str, Report] = {}
        self.therapy_goals: dict[str, TherapyGoal] = {}
        self.audio_files: dict[str, AudioFileMetadata] = {}
        self.jobs: dict[str, ProcessingJob] = {}
        self.privacy_operations: dict[str, PrivacyOperation] = {}
        self.organization_settings: dict[str, dict[str, object]] = {}
        self.audit_log: list[dict] = []
        if seed_demo:
            self.seed()

    def seed(self) -> None:
        if self.cases:
            return
        case = ChildCase(
            case_id="case_demo_001",
            organization_id="pilot_org_001",
            care_team_user_ids=["therapist-demo"],
            primary_therapist_user_id="therapist-demo",
            child_code="C-1024",
            nickname="Demo child",
            age_months=62,
            language="English",
            consent_status="granted",
            review_priority="moderate",
        )
        session = TherapySession(
            session_id="session_demo_001",
            case_id=case.case_id,
            session_date="2026-06-12",
            session_type="therapy_session",
            status=ReviewStatus.needs_review,
        )
        case.latest_session_date = session.session_date
        case.latest_session_status = session.status
        self.cases[case.case_id] = case
        self.sessions[session.session_id] = session
        self.organization_settings.setdefault(case.organization_id, {"ai_review_enabled": True})

    def clone(self, value):
        return deepcopy(value)

    def delete_feature_set(self, feature_set_id: str) -> None:
        self.features.pop(feature_set_id, None)

    def delete_ml_result(self, result_id: str) -> None:
        self.ml_results.pop(result_id, None)

    def is_ai_review_enabled(self, organization_id: str) -> bool:
        settings = self.organization_settings.get(organization_id, {})
        return bool(settings.get("ai_review_enabled", False))

    def set_ai_review_enabled(self, organization_id: str, enabled: bool) -> None:
        settings = dict(self.organization_settings.get(organization_id, {}))
        settings["ai_review_enabled"] = enabled
        self.organization_settings[organization_id] = settings

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
        event = validate_audit_event(
            actor_id=actor_id,
            action=action,
            target_id=target_id,
            outcome=outcome,
            correlation_id=correlation_id,
            message=message,
        )
        event_data = event.as_dict()
        event_data["organization_id"] = organization_id or self._organization_for_target(target_id)
        self.audit_log.append(event_data)

    def _organization_for_target(self, target_id: str) -> str:
        if target_id in self.cases:
            return self.cases[target_id].organization_id
        if target_id in self.sessions:
            return self.sessions[target_id].organization_id
        if target_id in self.transcripts:
            return self.transcripts[target_id].organization_id
        if target_id in self.features:
            return self.features[target_id].organization_id
        if target_id in self.ml_results:
            return self.ml_results[target_id].organization_id
        if target_id in self.ai_reviews:
            return self.ai_reviews[target_id].organization_id
        if target_id in self.reports:
            return self.reports[target_id].organization_id
        if target_id in self.therapy_goals:
            return self.therapy_goals[target_id].organization_id
        if target_id in self.audio_files:
            return self.audio_files[target_id].organization_id
        if target_id in self.jobs:
            return self.jobs[target_id].organization_id
        if target_id in self.privacy_operations:
            return self.privacy_operations[target_id].organization_id
        return "pilot_org_001"

    def find(self, collection: str, **where) -> list:
        """Records of one collection whose fields equal the given values.

        A set, list or tuple matches any of its members. This is how callers
        ask for a subset, so a database-backed repository can answer with a
        query on those fields instead of reading the whole collection.
        """
        return [
            record
            for record in getattr(self, collection).values()
            if record_matches(record, where)
        ]

    def audit_events(self, **where) -> list[dict]:
        """Recorded audit events whose fields equal the given values, oldest first."""
        return [dict(event) for event in self.audit_log if all(event.get(k) == v for k, v in where.items())]

    def case_deletion_blocker(self, case_id: str) -> str | None:
        """Why a case may not be deleted, or ``None`` when nothing has been recorded for it.

        Only a case that holds no clinical record can go: one made by mistake.
        A case with a session, a goal, a privacy operation or withdrawn consent
        carries records that have to be kept, so it stays.
        """
        case = self.cases[case_id]
        if case.consent_status == "withdrawn":
            return "consent_withdrawn"
        if self.find("sessions", case_id=case_id):
            return "has_sessions"
        if self.find("therapy_goals", case_id=case_id):
            return "has_goals"
        if self.find("privacy_operations", case_id=case_id):
            return "has_privacy_operations"
        return None

    def delete_case(self, case_id: str, *, actor_id: str) -> None:
        """Remove an empty case. The audit event is kept."""
        case = self.cases.pop(case_id)
        self.add_audit(
            "case.delete",
            case_id,
            "Empty case deleted.",
            actor_id=actor_id,
            organization_id=case.organization_id,
        )

    # Every collection that holds a workspace's records, children before parents.
    _WORKSPACE_COLLECTIONS = (
        "ml_results",
        "features",
        "ai_reviews",
        "reports",
        "audio_files",
        "transcripts",
        "jobs",
        "privacy_operations",
        "therapy_goals",
        "sessions",
        "cases",
    )

    def workspace_records(self, organization_id: str) -> dict[str, list]:
        """Every record of one workspace, by collection.

        A record counts when it carries the workspace's id or hangs off one of
        its cases or sessions, so a record written with a wrong organization
        id is still found through what it belongs to.
        """
        cases = self.find("cases", organization_id=organization_id)
        case_ids = {case.case_id for case in cases}
        sessions = self.find("sessions", organization_id=organization_id)
        if case_ids:
            sessions += self.find("sessions", case_id=case_ids)
        session_ids = {session.session_id for session in sessions}
        records: dict[str, list] = {}
        for collection in self._WORKSPACE_COLLECTIONS:
            found = {}
            for record in self.find(collection, organization_id=organization_id):
                found[id(record)] = record
            if collection != "cases" and case_ids and "case_id" in _fields(collection):
                for record in self.find(collection, case_id=case_ids):
                    found[id(record)] = record
            if collection not in {"cases", "sessions"} and session_ids and "session_id" in _fields(collection):
                for record in self.find(collection, session_id=session_ids):
                    found[id(record)] = record
            records[collection] = list(found.values())
        return records

    def case_records(self, case_id: str, *, session_id: str | None = None) -> dict[str, list]:
        """Every record of one case (or only of one of its sessions), by collection.

        With ``session_id`` the case itself, its goals and its privacy
        operations are left out: they belong to the case, not the session.
        """
        sessions = [
            session for session in self.find("sessions", case_id=case_id)
            if session_id is None or session.session_id == session_id
        ]
        session_ids = {session.session_id for session in sessions}
        records: dict[str, list] = {}
        for collection in self._WORKSPACE_COLLECTIONS:
            found = {}
            if collection == "sessions":
                found = {id(session): session for session in sessions}
            elif collection == "cases":
                if session_id is None and case_id in self.cases:
                    found[id(self.cases[case_id])] = self.cases[case_id]
            else:
                fields = _fields(collection)
                if session_id is None and "case_id" in fields:
                    for record in self.find(collection, case_id=case_id):
                        found[id(record)] = record
                if session_ids and "session_id" in fields:
                    for record in self.find(collection, session_id=session_ids):
                        found[id(record)] = record
            records[collection] = list(found.values())
        return records

    def delete_case_records(self, case_id: str, *, actor_id: str, session_id: str | None = None) -> dict[str, int]:
        """Remove a case with everything recorded for it, or one of its sessions.

        Stored recordings are the caller's to remove; this drops their
        metadata. The audit log is kept and gains one event with counts only.
        """
        organization_id = self.cases[case_id].organization_id
        removed = {}
        for collection, records in self.case_records(case_id, session_id=session_id).items():
            table = getattr(self, collection)
            for record in records:
                table.pop(_record_key(collection, record), None)
            removed[collection] = len(records)
        self.add_audit(
            "session.delete" if session_id else "case.delete",
            session_id or case_id,
            _deletion_message(removed, session_id),
            actor_id=actor_id,
            organization_id=organization_id,
        )
        return removed

    def delete_workspace(self, organization_id: str, *, user_id: str) -> dict[str, int]:
        """Remove a workspace's records, settings and audit events.

        Stored recordings are the caller's to remove first; this only drops
        their metadata. One audit event, with no content, records the deletion.
        """
        removed = {}
        for collection, records in self.workspace_records(organization_id).items():
            table = getattr(self, collection)
            for record in records:
                table.pop(_record_key(collection, record), None)
            removed[collection] = len(records)
        self.organization_settings.pop(organization_id, None)
        self.audit_log[:] = [event for event in self.audit_log if event.get("organization_id") != organization_id]
        self.add_audit(
            "account.delete",
            organization_id,
            "Account deleted with its records.",
            actor_id=user_id,
            organization_id=organization_id,
        )
        return removed

    def create_case(
        self,
        payload: ChildCaseCreate,
        *,
        actor_id: str,
        audit_actor_id: str | None = None,
    ) -> ChildCase:
        """``actor_id`` drives care-team defaults; ``audit_actor_id`` is who made the request."""
        case = ChildCase(case_id=new_id("case"), **payload.model_dump())
        if actor_id not in case.care_team_user_ids and actor_id != "system":
            case.care_team_user_ids = [*case.care_team_user_ids, actor_id]
        if case.primary_therapist_user_id is None and actor_id != "system":
            case.primary_therapist_user_id = actor_id
        if case.primary_therapist_user_id and case.primary_therapist_user_id not in case.care_team_user_ids:
            case.care_team_user_ids = [*case.care_team_user_ids, case.primary_therapist_user_id]
        self.cases[case.case_id] = case
        self.add_audit("case.create", case.case_id, "Case created.", actor_id=audit_actor_id or actor_id)
        return self.clone(case)

    def update_case(
        self,
        case_id: str,
        patch: ChildCaseUpdate,
        *,
        expected_version: int | None,
        actor_id: str,
    ) -> ChildCase:
        case = self.cases[case_id]
        if expected_version is not None and case.version != expected_version:
            raise CaseVersionConflictError(
                f"Case {case_id} expected version {expected_version}, found {case.version}."
            )
        for key, value in patch.model_dump(exclude_unset=True).items():
            setattr(case, key, value)
        case.version += 1
        self.add_audit("case.update", case_id, "Case updated.", actor_id=actor_id)
        return self.clone(case)

    def create_session(self, case_id: str, payload: TherapySessionCreate, *, actor_id: str) -> TherapySession:
        case = self.cases[case_id]
        session = TherapySession(
            session_id=new_id("session"),
            case_id=case_id,
            organization_id=case.organization_id,
            **payload.model_dump(),
        )
        self.sessions[session.session_id] = session
        case.latest_session_date = session.session_date
        case.latest_session_status = session.status
        self.add_audit("session.create", session.session_id, "Session created.", actor_id=actor_id)
        return self.clone(session)

    def update_session(
        self,
        session_id: str,
        patch: TherapySessionUpdate,
        *,
        expected_version: int | None,
        actor_id: str,
    ) -> TherapySession:
        session = self.sessions[session_id]
        if expected_version is not None and session.version != expected_version:
            raise SessionVersionConflictError(
                f"Session {session_id} expected version {expected_version}, found {session.version}."
            )
        for key, value in patch.model_dump(exclude_unset=True).items():
            setattr(session, key, value)
        session.version += 1
        self.add_audit("session.patch", session_id, "Session updated.", actor_id=actor_id)
        return self.clone(session)

    def create_transcript(
        self,
        transcript: Transcript,
        *,
        session_status: ReviewStatus,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> Transcript:
        session = self.sessions[transcript.session_id]
        invalidated = self._mark_downstream_outputs_stale(session)
        transcript.organization_id = session.organization_id
        self.transcripts[transcript.transcript_id] = transcript
        session.transcript_id = transcript.transcript_id
        session.status = session_status
        self.add_audit(audit_action, transcript.transcript_id, audit_message, actor_id=actor_id)
        if invalidated:
            self.add_audit(
                "workflow.invalidate_downstream",
                transcript.transcript_id,
                "Derived workflow outputs marked stale after transcript change.",
                actor_id=actor_id,
            )
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
        current = self.transcripts[transcript.transcript_id]
        if expected_version is not None:
            if current is transcript:
                if transcript.version not in {expected_version, expected_version + 1}:
                    raise TranscriptVersionConflictError(
                        f"Transcript {transcript.transcript_id} expected version {expected_version}."
                    )
            elif current.version != expected_version:
                raise TranscriptVersionConflictError(
                    f"Transcript {transcript.transcript_id} expected version {expected_version}, found {current.version}."
                )
        session = self.sessions[transcript.session_id]
        invalidated = self._mark_downstream_outputs_stale(session) if invalidate_downstream else False
        session.status = session_status
        transcript.organization_id = session.organization_id
        self.transcripts[transcript.transcript_id] = transcript
        self.add_audit(audit_action, transcript.transcript_id, audit_message, actor_id=actor_id)
        if invalidated:
            self.add_audit(
                "workflow.invalidate_downstream",
                transcript.transcript_id,
                "Derived workflow outputs marked stale after transcript change.",
                actor_id=actor_id,
            )
        return self.clone(transcript)

    def _mark_downstream_outputs_stale(self, session: TherapySession) -> bool:
        invalidated = False
        feature_set = self.features.get(session.feature_set_id or "")
        if feature_set is not None and feature_set.review_status != ReviewStatus.stale:
            feature_set.review_status = ReviewStatus.stale
            invalidated = True
        ml_result = self.ml_results.get(session.ml_result_id or "")
        if ml_result is not None and ml_result.is_current:
            ml_result.is_current = False
            invalidated = True
        ai_review = self.ai_reviews.get(session.ai_review_id or "")
        if ai_review is not None and ai_review.therapist_review_status != ReviewStatus.stale:
            ai_review.therapist_review_status = ReviewStatus.stale
            invalidated = True
        report = self.reports.get(session.report_id or "")
        if report is not None and report.status not in {ReviewStatus.signed_off, ReviewStatus.stale}:
            report.status = ReviewStatus.stale
            report.version += 1
            report.updated_at = utc_now()
            self.cases[session.case_id].latest_report_status = ReviewStatus.stale
            invalidated = True
        return invalidated

    def create_report(
        self,
        report: Report,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> Report:
        session = self.sessions[report.session_id]
        transcript = self.transcripts.get(report.transcript_id or "")
        expected_transcript_version = report.generated_from_versions.get("transcript_version")
        if report.transcript_id and (
            transcript is None
            or session.transcript_id != report.transcript_id
            or expected_transcript_version != str(transcript.version)
        ):
            raise ValueError("Transcript changed during report generation; discard the stale draft and retry.")
        if report.feature_result_id and (
            session.feature_set_id != report.feature_result_id
            or report.feature_result_id not in self.features
            or self.features[report.feature_result_id].review_status == ReviewStatus.stale
            or transcript is None
            or self.features[report.feature_result_id].transcript_version != transcript.version
        ):
            raise ValueError("Findings changed during report generation; discard the stale draft and retry.")
        report.organization_id = self.cases[report.case_id].organization_id
        self.reports[report.report_id] = report
        self.sessions[report.session_id].report_id = report.report_id
        self.cases[report.case_id].latest_report_status = report.status
        self.add_audit(audit_action, report.report_id, audit_message, actor_id=actor_id)
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
        current = self.reports[report.report_id]
        if expected_version is not None:
            if current is report:
                if report.version not in {expected_version, expected_version + 1}:
                    raise ReportVersionConflictError(f"Report {report.report_id} expected version {expected_version}.")
            elif current.version != expected_version:
                raise ReportVersionConflictError(
                    f"Report {report.report_id} expected version {expected_version}, found {current.version}."
                )
        report.organization_id = self.cases[report.case_id].organization_id
        self.reports[report.report_id] = report
        self.cases[report.case_id].latest_report_status = report.status
        self.add_audit(audit_action, report.report_id, audit_message, actor_id=actor_id)
        return self.clone(report)

    def create_therapy_goal(
        self,
        goal: TherapyGoal,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> TherapyGoal:
        goal.organization_id = self.cases[goal.case_id].organization_id
        self.therapy_goals[goal.goal_id] = goal
        self.add_audit(audit_action, goal.goal_id, audit_message, actor_id=actor_id)
        return self.clone(goal)

    def update_therapy_goal(
        self,
        goal: TherapyGoal,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> TherapyGoal:
        goal.organization_id = self.cases[goal.case_id].organization_id
        self.therapy_goals[goal.goal_id] = goal
        self.add_audit(audit_action, goal.goal_id, audit_message, actor_id=actor_id)
        return self.clone(goal)

    def create_privacy_operation(
        self,
        operation: PrivacyOperation,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> PrivacyOperation:
        operation.organization_id = self.cases[operation.case_id].organization_id
        self.privacy_operations[operation.privacy_operation_id] = operation
        self.add_audit(audit_action, operation.privacy_operation_id, audit_message, actor_id=actor_id)
        return self.clone(operation)

    def update_privacy_operation(
        self,
        operation: PrivacyOperation,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> PrivacyOperation:
        operation.organization_id = self.cases[operation.case_id].organization_id
        self.privacy_operations[operation.privacy_operation_id] = operation
        self.add_audit(audit_action, operation.privacy_operation_id, audit_message, actor_id=actor_id)
        return self.clone(operation)

    def create_feature_set(
        self,
        feature_set: FeatureSet,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> FeatureSet:
        session = self.sessions[feature_set.session_id]
        transcript = self.transcripts.get(feature_set.transcript_id)
        if (
            transcript is None
            or session.transcript_id != feature_set.transcript_id
            or transcript.version != feature_set.transcript_version
        ):
            raise ValueError("Transcript changed during feature extraction; discard the stale result and retry.")
        feature_set.organization_id = session.organization_id
        self.features[feature_set.feature_set_id] = feature_set
        session.feature_set_id = feature_set.feature_set_id
        session.ml_result_id = None
        self.add_audit(audit_action, feature_set.feature_set_id, audit_message, actor_id=actor_id)
        return self.clone(feature_set)

    def create_ai_review(
        self,
        review: AiReview,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> AiReview:
        session = self.sessions[review.session_id]
        transcript = self.transcripts.get(session.transcript_id or "")
        feature_set = self.features.get(review.feature_set_id or "")
        if transcript is None or transcript.version != review.input_transcript_version:
            raise ValueError("Transcript changed during AI-assisted review generation; discard the stale result and retry.")
        if review.feature_set_id and (
            session.feature_set_id != review.feature_set_id
            or feature_set is None
            or feature_set.review_status == ReviewStatus.stale
            or feature_set.transcript_version != transcript.version
        ):
            raise ValueError("Findings changed during AI-assisted review generation; discard the stale result and retry.")
        review.organization_id = session.organization_id
        self.ai_reviews[review.ai_review_id] = review
        self.sessions[review.session_id].ai_review_id = review.ai_review_id
        self.cases[self.sessions[review.session_id].case_id].review_priority = review.review_priority
        self.add_audit(audit_action, review.ai_review_id, audit_message, actor_id=actor_id)
        return self.clone(review)

    def update_ai_review(
        self,
        review: AiReview,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> AiReview:
        review.organization_id = self.sessions[review.session_id].organization_id
        self.ai_reviews[review.ai_review_id] = review
        self.add_audit(audit_action, review.ai_review_id, audit_message, actor_id=actor_id)
        return self.clone(review)

    def create_ml_result(
        self,
        result: MLResult,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> MLResult:
        session = self.sessions[result.session_id]
        transcript = self.transcripts.get(result.transcript_id)
        feature_set = self.features.get(result.feature_result_id)
        if (
            transcript is None
            or session.transcript_id != result.transcript_id
            or session.feature_set_id != result.feature_result_id
            or feature_set is None
            or feature_set.review_status == ReviewStatus.stale
            or feature_set.transcript_id != transcript.transcript_id
            or feature_set.transcript_version != transcript.version
        ):
            raise ValueError("Transcript or findings changed during ML review generation; discard the stale result and retry.")
        result.organization_id = session.organization_id
        self.ml_results[result.result_id] = result
        self.sessions[result.session_id].ml_result_id = result.result_id
        self.add_audit(audit_action, result.result_id, audit_message, actor_id=actor_id)
        return self.clone(result)

    def update_ml_result(
        self,
        result: MLResult,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> MLResult:
        result.organization_id = self.sessions[result.session_id].organization_id
        self.ml_results[result.result_id] = result
        self.add_audit(audit_action, result.result_id, audit_message, actor_id=actor_id)
        return self.clone(result)

    def snapshot(self) -> dict:
        return {
            "cases": {key: value.model_dump(mode="json") for key, value in self.cases.items()},
            "sessions": {key: value.model_dump(mode="json") for key, value in self.sessions.items()},
            "transcripts": {key: value.model_dump(mode="json") for key, value in self.transcripts.items()},
            "features": {key: value.model_dump(mode="json") for key, value in self.features.items()},
            "ml_results": {key: value.model_dump(mode="json") for key, value in self.ml_results.items()},
            "ai_reviews": {key: value.model_dump(mode="json") for key, value in self.ai_reviews.items()},
            "reports": {key: value.model_dump(mode="json") for key, value in self.reports.items()},
            "therapy_goals": {key: value.model_dump(mode="json") for key, value in self.therapy_goals.items()},
            "audio_files": {key: value.model_dump(mode="json") for key, value in self.audio_files.items()},
            "jobs": {key: value.model_dump(mode="json") for key, value in self.jobs.items()},
            "privacy_operations": {key: value.model_dump(mode="json") for key, value in self.privacy_operations.items()},
            "organization_settings": self.organization_settings,
            "audit_log": self.audit_log,
        }


class JsonFileRepository(MockRepository):
    """Durable local demo repository stored as JSON outside browser storage."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        super().__init__()
        self.load()

    def load(self) -> None:
        if not self.path.exists() or self.path.stat().st_size == 0:
            self.save()
            return
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.cases = {key: ChildCase.model_validate(value) for key, value in data.get("cases", {}).items()}
        self.sessions = {key: TherapySession.model_validate(value) for key, value in data.get("sessions", {}).items()}
        self.transcripts = {key: Transcript.model_validate(value) for key, value in data.get("transcripts", {}).items()}
        self.features = {key: FeatureSet.model_validate(value) for key, value in data.get("features", {}).items()}
        self.ml_results = {key: MLResult.model_validate(value) for key, value in data.get("ml_results", {}).items()}
        self.ai_reviews = {key: AiReview.model_validate(value) for key, value in data.get("ai_reviews", {}).items()}
        self.reports = {key: Report.model_validate(value) for key, value in data.get("reports", {}).items()}
        self.therapy_goals = {key: TherapyGoal.model_validate(value) for key, value in data.get("therapy_goals", {}).items()}
        self.audio_files = {key: AudioFileMetadata.model_validate(value) for key, value in data.get("audio_files", {}).items()}
        self.jobs = {key: ProcessingJob.model_validate(value) for key, value in data.get("jobs", {}).items()}
        self.privacy_operations = {key: PrivacyOperation.model_validate(value) for key, value in data.get("privacy_operations", {}).items()}
        self.organization_settings = {
            key: dict(value) for key, value in data.get("organization_settings", {}).items()
        }
        self.organization_settings.setdefault("pilot_org_001", {"ai_review_enabled": True})
        self.audit_log = list(data.get("audit_log", []))

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.snapshot(), indent=2), encoding="utf-8")

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
