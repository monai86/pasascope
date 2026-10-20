"""Cases, consent and sessions.

Part of :class:`packages.desktop.core.service.DesktopService`."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any

from packages.desktop.core.i18n import tr
from packages.desktop.core.workspace import LOCAL_ORGANIZATION_ID, LOCAL_USER_ID
from packages.desktop.core.workflow.common import WorkflowError, _utc, _validation_message


class CasesMixin:
    def list_cases(self, search: str = "") -> list:
        cases = self.repo.find("cases", organization_id=LOCAL_ORGANIZATION_ID)
        needle = search.strip().lower()
        if needle:
            cases = [
                c for c in cases
                if needle in c.child_code.lower() or needle in (c.nickname or "").lower()
            ]
        return sorted(cases, key=lambda c: _utc(c.updated_at), reverse=True)

    def get_case(self, case_id: str):
        case = self.repo.cases.get(case_id)
        if case is None or case.organization_id != LOCAL_ORGANIZATION_ID:
            raise WorkflowError(tr("ไม่พบเคสนี้", "Case not found."))
        return case

    def create_case(
        self,
        child_code: str,
        age_months: int,
        *,
        nickname: str = "",
        language: str = "Thai",
        notes: str = "",
    ):
        from pydantic import ValidationError

        from app.schemas.clinical import ChildCaseCreate

        child_code = child_code.strip()
        if any(c.child_code == child_code for c in self.list_cases()):
            raise WorkflowError(tr(f"มีเคสรหัส {child_code} อยู่แล้ว", f"A case with code {child_code} already exists."))
        try:
            payload = ChildCaseCreate(
                child_code=child_code,
                nickname=nickname.strip() or None,
                age_months=age_months,
                language=language,
                notes=notes,
                organization_id=LOCAL_ORGANIZATION_ID,
                care_team_user_ids=[LOCAL_USER_ID],
                primary_therapist_user_id=LOCAL_USER_ID,
                consent_status="pending",
            )
        except ValidationError as exc:
            raise WorkflowError(_validation_message(exc)) from exc
        case = self.repo.create_case(payload, actor_id="system", audit_actor_id=LOCAL_USER_ID)
        self._save()
        return case

    def grant_consent(self, case_id: str, signer: str, consent_date: date, notes: str = ""):
        from pydantic import ValidationError

        from app.schemas.clinical import ConsentGrantRequest
        from app.services.consent_service import grant_consent

        self.get_case(case_id)
        try:
            payload = ConsentGrantRequest(
                signer=signer, consent_date=consent_date, notes=notes, confirmation_checked=True
            )
            case = grant_consent(self.repo, case_id, payload, actor_id=LOCAL_USER_ID)
        except ValidationError as exc:
            raise WorkflowError(_validation_message(exc)) from exc
        except ValueError as exc:
            raise WorkflowError(str(exc)) from exc
        self._save()
        return case

    def withdraw_consent(self, case_id: str, reason: str):
        from app.services.consent_service import withdraw_consent

        self.get_case(case_id)
        if not reason.strip():
            raise WorkflowError(tr("กรุณาระบุเหตุผลที่ถอนความยินยอม", "Enter the reason for withdrawing consent."))
        result = withdraw_consent(
            self.repo, case_id, reason.strip(), True, actor_id=LOCAL_USER_ID, requester_role="therapist"
        )
        self._save()
        return result

    def update_case(self, case_id: str, *, nickname: str, age_months: int, language: str, notes: str):
        """Change a case's nickname, age at intake, language and notes; the code stays (it is on every record)."""
        from pydantic import ValidationError

        from app.schemas.clinical import ChildCaseUpdate

        case = self.get_case(case_id)
        try:
            patch = ChildCaseUpdate(
                nickname=nickname.strip() or None, age_months=age_months,
                language=language.strip() or case.language, notes=notes.strip(),
            )
            updated = self.repo.update_case(case_id, patch, expected_version=None, actor_id=LOCAL_USER_ID)
        except ValidationError as exc:
            raise WorkflowError(_validation_message(exc)) from exc
        self._save()
        return updated

    def deletion_summary(self, case_id: str, session_id: str | None = None) -> dict[str, int]:
        """What deleting a case (or one of its sessions) would remove, for the confirmation dialog."""
        self.get_case(case_id)
        if session_id is not None and self.get_session(session_id).case_id != case_id:
            raise WorkflowError(tr("ไม่พบ session นี้", "Session not found."))
        records = self.repo.case_records(case_id, session_id=session_id)
        return {
            "sessions": len(records["sessions"]),
            "recordings": len(records["audio_files"]),
            "transcripts": len(records["transcripts"]),
            "reports": len(records["reports"]),
            "signed_reports": sum(1 for report in records["reports"] if report.status == "Signed Off"),
        }

    def delete_case(self, case_id: str, typed_code: str) -> dict[str, int]:
        """Delete a case with its sessions, recordings, transcripts, findings and reports.

        The therapist types the child's code to confirm. The audit log keeps
        one event with counts only, and exported files and backups outside the
        data folder are not touched.
        """
        case = self.get_case(case_id)
        if typed_code.strip() != case.child_code:
            raise WorkflowError(tr(f"พิมพ์รหัส {case.child_code} ให้ตรงเพื่อยืนยันการลบ", f"Type {case.child_code} exactly to confirm."))
        return self._delete_records(case_id, None)

    def delete_session(self, session_id: str) -> dict[str, int]:
        """Delete one session with its recording, transcript, findings and report."""
        session = self.get_session(session_id)
        return self._delete_records(session.case_id, session_id)

    def _delete_records(self, case_id: str, session_id: str | None) -> dict[str, int]:
        root = self.workspace.storage_root.resolve()
        audio = self.repo.case_records(case_id, session_id=session_id)["audio_files"]
        removed = self.repo.delete_case_records(case_id, actor_id=LOCAL_USER_ID, session_id=session_id)
        # Files go after the records: a failure here leaves a file without a record, never the reverse.
        for audio_file in audio:
            for path in (
                root / str(audio_file.object_key or ""),
                root / "playback" / f"{audio_file.audio_file_id}.wav",
                root / "playback" / f"{audio_file.audio_file_id}.full.wav",
            ):
                path = path.resolve()
                if root in path.parents and path.is_file():
                    path.unlink(missing_ok=True)
        self._save()
        return removed

    def consent_active(self, case_id: str) -> bool:
        return self.get_case(case_id).consent_status == "granted"

    def _ensure(self, check: Callable[..., None], *args: Any) -> None:
        """The API's consent gate: nothing changes on a case whose consent was withdrawn."""
        try:
            check(self.repo, *args)
        except ValueError as exc:
            raise WorkflowError(tr("ผู้ปกครองถอนความยินยอมของเคสนี้แล้ว จึงเพิ่มหรือแก้ข้อมูลไม่ได้", "Consent for this case was withdrawn, so its data cannot be added to or changed.")) from exc

    def _require_granted(self, case_id: str) -> None:
        """New sessions and recordings need consent that was actually recorded, not just pending."""
        status = self.get_case(case_id).consent_status
        if status == "withdrawn":
            raise WorkflowError(tr("ผู้ปกครองถอนความยินยอมของเคสนี้แล้ว จึงเพิ่มหรือแก้ข้อมูลไม่ได้", "Consent for this case was withdrawn, so its data cannot be added to or changed."))
        if status != "granted":
            raise WorkflowError(tr("บันทึกความยินยอมของผู้ปกครองก่อน แล้วจึงเริ่ม session หรือบันทึกเสียง", "Record the parent's consent before starting a session or recording."))

    def list_sessions(self, case_id: str) -> list:
        self.get_case(case_id)
        sessions = self.repo.find("sessions", case_id=case_id)
        return sorted(sessions, key=lambda s: (s.session_date, _utc(s.created_at)), reverse=True)

    def get_session(self, session_id: str):
        session = self.repo.sessions.get(session_id)
        if session is None or session.organization_id != LOCAL_ORGANIZATION_ID:
            raise WorkflowError(tr("ไม่พบ session นี้", "Session not found."))
        return session

    def create_session(self, case_id: str, session_date: date, *, session_type: str = "therapy_session", notes: str = ""):
        from app.schemas.clinical import TherapySessionCreate
        from app.services.consent_service import ensure_case_consent_active

        self._require_granted(case_id)
        self._ensure(ensure_case_consent_active, case_id)
        session = self.repo.create_session(
            case_id,
            TherapySessionCreate(session_date=session_date.isoformat(), session_type=session_type, notes=notes),
            actor_id=LOCAL_USER_ID,
        )
        self._save()
        return session
