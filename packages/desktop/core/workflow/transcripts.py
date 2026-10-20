"""Transcripts: import, edit, attest and export as CHAT.

Part of :class:`packages.desktop.core.service.DesktopService`."""

from __future__ import annotations

from packages.desktop.core.i18n import tr
from packages.desktop.core.workspace import LOCAL_USER_ID
from packages.desktop.core.workflow.common import (
    WorkflowError,
    QaOverrideRequired,
    _looks_like_chat,
    _safe_filename,
)


class TranscriptsMixin:
    def get_transcript(self, session_id: str):
        session = self.get_session(session_id)
        if not session.transcript_id:
            return None
        return self.repo.transcripts.get(session.transcript_id)

    def import_transcript_text(self, session_id: str, text: str, *, filename: str = "transcript.cha"):
        """Add a transcript typed or loaded from a file: CHAT when it looks like CHAT, plain lines otherwise."""
        from app.schemas.clinical import TranscriptManualCreate, TranscriptUploadCha
        from app.services import transcript_service
        from app.services.consent_service import ensure_session_consent_active

        self.get_session(session_id)
        self._ensure(ensure_session_consent_active, session_id)
        if not text.strip():
            raise WorkflowError(tr("ไม่มีข้อความให้นำเข้า", "There is no text to import."))
        replace = self.get_transcript(session_id) is not None
        try:
            if _looks_like_chat(text):
                transcript = transcript_service.create_from_cha(
                    self.repo,
                    session_id,
                    TranscriptUploadCha(filename=_safe_filename(filename), cha_text=text, replace_existing=replace),
                    actor_id=LOCAL_USER_ID,
                )
            else:
                transcript = transcript_service.create_from_manual(
                    self.repo,
                    session_id,
                    TranscriptManualCreate(text=text, language="Thai", replace_existing=replace),
                    actor_id=LOCAL_USER_ID,
                )
        except ValueError as exc:
            raise WorkflowError(str(exc)) from exc
        self._save()
        return transcript

    def save_utterances(self, transcript_id: str, utterances: list, *, note: str = ""):
        from app.schemas.clinical import TranscriptPatch
        from app.services import transcript_service
        from app.services.consent_service import ensure_transcript_consent_active

        self._ensure(ensure_transcript_consent_active, transcript_id)
        try:
            transcript = transcript_service.patch_transcript(
                self.repo,
                transcript_id,
                TranscriptPatch(utterances=utterances, reviewer_note=note),
                actor_id=LOCAL_USER_ID,
            )
        except ValueError as exc:
            raise WorkflowError(str(exc)) from exc
        self._save()
        return transcript

    def attest(self, transcript_id: str, *, override_reason: str = ""):
        """Attest the transcript. A transcript that failed QA needs the therapist's reason to override."""
        from app.schemas.clinical import AttestationRequest
        from app.services import transcript_service
        from app.services.consent_service import ensure_transcript_consent_active

        signer = self._require_signer()
        self._ensure(ensure_transcript_consent_active, transcript_id)
        try:
            transcript = transcript_service.attest(
                self.repo,
                transcript_id,
                AttestationRequest(
                    attested_by=signer,
                    reason=override_reason.strip() or "Therapist reviewed the transcript against the recording.",
                    override_qa_failure=bool(override_reason.strip()),
                ),
                actor_id=LOCAL_USER_ID,
                attested_by=signer,
            )
        except ValueError as exc:
            if "failed QA" in str(exc):
                raise QaOverrideRequired(self.repo.transcripts[transcript_id].qa_issues) from exc
            raise WorkflowError(str(exc)) from exc
        self._save()
        return transcript

    def qa_issues(self, transcript_id: str) -> list:
        from app.services import transcript_service

        report = transcript_service.run_qa(self.repo, transcript_id, actor_id=LOCAL_USER_ID)
        self._save()
        return list(report.issues) if hasattr(report, "issues") else []

    def export_cha(self, transcript_id: str) -> str:
        from app.services import transcript_service

        return transcript_service.export_cha(self.repo, transcript_id).cha_text
