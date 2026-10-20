"""Report drafts, sign-off and export.

Part of :class:`packages.desktop.core.service.DesktopService`."""

from __future__ import annotations

from pathlib import Path

from packages.desktop.core.i18n import language as current_language, report_language, tr
from packages.desktop.core.workspace import LOCAL_USER_ID
from packages.desktop.core.workflow.common import WorkflowError, _status_value, REPORT_PROVIDERS


class ReportsMixin:
    def get_report(self, session_id: str):
        session = self.get_session(session_id)
        return self.repo.reports.get(session.report_id) if session.report_id else None

    def report_language(self, report) -> str:
        """"th" or "en": the language a report was drafted in, read from its headings."""
        return report_language(report.markdown if report is not None else "")

    def draft_report(self, session_id: str, *, therapist_notes: str = "", language: str | None = None):
        """Draft (or redraft) the session report in ``language``.

        Without a language, a redraft keeps the current report's language and a
        first draft uses the interface language in use.
        """
        from app.schemas.clinical import ReportGenerationRequest
        from app.services.consent_service import ensure_session_consent_active
        from app.services.report_service import draft_report

        self.get_session(session_id)
        self._ensure(ensure_session_consent_active, session_id)
        existing = self.get_report(session_id)
        if language is None:
            language = self.report_language(existing) if existing is not None else current_language()
        if language not in REPORT_PROVIDERS:
            raise WorkflowError(f"Unknown report language {language}")
        try:
            report = draft_report(
                self.repo,
                session_id,
                ReportGenerationRequest(
                    provider_id=REPORT_PROVIDERS[language],
                    therapist_notes=therapist_notes or None,
                    replace_existing=existing is not None,
                ),
                actor_id=LOCAL_USER_ID,
            )
        except ValueError as exc:
            raise WorkflowError(str(exc)) from exc
        self._save()
        return report

    def update_report(self, report_id: str, markdown: str):
        from app.schemas.clinical import ReportPatch
        from app.services.consent_service import ensure_report_consent_active
        from app.services.report_service import patch_report, revise_finalized_report

        self._ensure(ensure_report_consent_active, report_id)
        report = self.repo.reports[report_id]
        try:
            if _status_value(report.status) == "Signed Off":
                updated = revise_finalized_report(self.repo, report_id, ReportPatch(markdown=markdown), actor_id=LOCAL_USER_ID)
            else:
                updated = patch_report(self.repo, report_id, ReportPatch(markdown=markdown), actor_id=LOCAL_USER_ID)
        except ValueError as exc:
            raise WorkflowError(str(exc)) from exc
        self._save()
        return updated

    def sign_off(self, report_id: str):
        from app.services.consent_service import ensure_report_consent_active
        from app.services.report_service import sign_off_report

        signer = self._require_signer()
        self._ensure(ensure_report_consent_active, report_id)
        try:
            report = sign_off_report(self.repo, report_id, signer, signed_by_user_id=LOCAL_USER_ID)
        except ValueError as exc:
            raise WorkflowError(str(exc)) from exc
        self._save()
        return report

    def report_for_export(self, report_id: str):
        """The report, when it may be exported now (consent active, not stale)."""
        from app.services.consent_service import ensure_report_consent_active

        self._ensure(ensure_report_consent_active, report_id)
        report = self.repo.reports.get(report_id)
        if report is None:
            raise WorkflowError(tr("ไม่พบรายงานนี้", "Report not found."))
        if _status_value(report.status) == "stale":
            raise WorkflowError(tr("transcript หรือตัวชี้วัดเปลี่ยนหลังทำรายงานนี้ สร้างร่างใหม่ก่อน export", "The transcript or findings changed after this report; redraft it before exporting."))
        return report

    def record_export(self, report_id: str, export_format: str) -> None:
        self.repo.add_audit(
            "report.export", report_id, f"Report exported as {export_format} from the desktop app.", actor_id=LOCAL_USER_ID
        )
        self._save()

    def export_report(self, report_id: str, export_format: str, destination: Path) -> Path:
        """Write the report as markdown or html. PDF is drawn by the UI, which has the fonts."""
        from packages.desktop.core.rendering import report_html

        report = self.report_for_export(report_id)
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if export_format == "html":
            destination.write_text(report_html(report.markdown, report.title), encoding="utf-8")
        elif export_format == "markdown":
            destination.write_text(report.markdown, encoding="utf-8")
        else:
            raise WorkflowError(tr(f"ไม่รองรับรูปแบบ {export_format}", f"Unsupported format {export_format}"))
        self.record_export(report_id, export_format)
        return destination
