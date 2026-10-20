"""Features, review cues, and the summaries built from them.

Part of :class:`packages.desktop.core.service.DesktopService`."""

from __future__ import annotations

from datetime import datetime, timezone

from packages.desktop.core.i18n import tr
from packages.desktop.core.workspace import LOCAL_USER_ID
from packages.desktop.core.workflow.common import WorkflowError, _utc


class FindingsMixin:
    def analyze(self, session_id: str):
        """Extract features from the attested transcript, then generate review cues."""
        from app.schemas.clinical import FeatureExtractionRequest, MLReviewRequest
        from app.services.consent_service import ensure_transcript_consent_active
        from app.services.feature_service import extract_features
        from app.services.ml_review_service import MLReadinessError, create_ml_review

        transcript = self.get_transcript(session_id)
        if transcript is None:
            raise WorkflowError(tr("session นี้ยังไม่มี transcript", "This session has no transcript yet."))
        if not transcript.therapist_attested:
            raise WorkflowError(tr("รับรอง transcript ก่อน แล้วจึงวิเคราะห์", "Attest the transcript before analysing."))
        self._ensure(ensure_transcript_consent_active, transcript.transcript_id)
        try:
            features = extract_features(
                self.repo, transcript.transcript_id, FeatureExtractionRequest(), actor_id=LOCAL_USER_ID
            )
            cues = create_ml_review(
                self.repo, transcript.transcript_id, MLReviewRequest(force_regenerate=True), actor_id=LOCAL_USER_ID
            )
        except MLReadinessError as exc:
            raise WorkflowError("; ".join(exc.readiness.reasons) or tr("ยังสร้าง cue ไม่ได้", "Cues could not be created yet.")) from exc
        except ValueError as exc:
            raise WorkflowError(str(exc)) from exc
        self._save()
        return features, cues

    def get_features(self, session_id: str):
        session = self.get_session(session_id)
        return self.repo.features.get(session.feature_set_id) if session.feature_set_id else None

    def get_cues(self, session_id: str):
        session = self.get_session(session_id)
        return self.repo.ml_results.get(session.ml_result_id) if session.ml_result_id else None

    def set_cue_state(self, result_id: str, cue_code: str, status: str, note: str = ""):
        from app.schemas.clinical import ReviewCuePatch
        from app.services.consent_service import ensure_session_consent_active
        from app.services.ml_review_service import patch_cue_state

        self._require_signer()
        result = self.repo.ml_results.get(result_id)
        if result is None:
            raise WorkflowError(tr("ไม่พบผลการทบทวนนี้", "Review result not found."))
        self._ensure(ensure_session_consent_active, result.session_id)
        try:
            updated = patch_cue_state(
                self.repo, result_id, cue_code, ReviewCuePatch(status=status, therapist_note=note), self.user
            )
        except (KeyError, PermissionError, ValueError) as exc:
            raise WorkflowError(str(exc)) from exc
        self._save()
        return updated

    def session_step(self, session) -> int:
        """Where a session stands: 0 needs a transcript, 1 review, 2 analysis, 3 sign-off, 4 done."""
        transcript = self.get_transcript(session.session_id)
        if transcript is None:
            return 0
        if not transcript.therapist_attested:
            return 1
        if self.get_features(session.session_id) is None or session.findings_stale:
            return 2
        report = self.get_report(session.session_id)
        status = getattr(getattr(report, "status", None), "value", getattr(report, "status", None))
        return 4 if status == "Signed Off" else 3

    def session_summaries(self, case_id: str, names: list[str]) -> list[dict]:
        """One row per session, newest first: its step, open cues and feature values."""
        rows = []
        for session in self.list_sessions(case_id):
            features = self.get_features(session.session_id)
            cues = self.get_cues(session.session_id)
            values = {}
            if features is not None and not session.findings_stale:
                values = {f.name: f.value for f in features.features if f.name in names}
            pending = sum(
                1 for cue in (cues.cues if cues else [])
                if (cue.review_state.status if cue.review_state else "unreviewed") == "unreviewed"
            )
            rows.append({
                "session": session,
                "step": self.session_step(session),
                "values": values,
                "pending_cues": pending,
                "schema_version": getattr(features, "schema_version", None),
            })
        return rows

    def work_queue(self) -> list[dict]:
        """Everything waiting for the therapist, most urgent first.

        One row per unfinished session of a consented child (``step`` 0-3 as in
        ``session_step``) and one per child still waiting for consent
        (``step`` "consent"). ``waiting_days`` counts from the last change.
        """
        now = datetime.now(timezone.utc)
        rows = []
        for case in self.list_cases():
            if case.consent_status == "pending":
                rows.append({"case": case, "session": None, "step": "consent",
                             "waiting_days": (now - _utc(case.updated_at)).days})
                continue
            if case.consent_status != "granted":
                continue
            for session in self.list_sessions(case.case_id):
                step = self.session_step(session)
                if step < 4:
                    rows.append({"case": case, "session": session, "step": step,
                                 "waiting_days": (now - _utc(session.updated_at)).days})
        order = {"consent": 0, 1: 1, 3: 2, 2: 3, 0: 4}  # review and sign-off first; they block the rest
        return sorted(rows, key=lambda r: (order[r["step"]], -r["waiting_days"]))

    def feature_trend(self, case_id: str, names: list[str]) -> list[tuple[str, dict[str, float]]]:
        """Each session's value for the named features, oldest session first."""
        rows: list[tuple[str, dict[str, float]]] = []
        for session in reversed(self.list_sessions(case_id)):
            features = self.get_features(session.session_id)
            if features is None:
                continue
            values = {
                f.name: float(f.value)
                for f in features.features
                if f.name in names and isinstance(f.value, (int, float)) and not isinstance(f.value, bool)
            }
            if values:
                rows.append((session.session_date, values))
        return rows
