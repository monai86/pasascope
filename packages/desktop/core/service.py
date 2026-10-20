"""The clinical workflow the desktop UI drives.

Each method does what the matching ``/api/v1`` route does, minus HTTP: the
same consent checks, the same service call, the same audit event. Records
are written to the workspace's SQLite file as they change.

Flow: case → consent → session → recording or transcript → review and
attest → features and review cues → report draft → sign-off → export.
"""

from __future__ import annotations

from typing import Any

from packages.desktop.core.i18n import tr
from packages.desktop.core.workspace import LOCAL_ORGANIZATION_ID, LOCAL_USER_ID, Workspace
from packages.desktop.core.workflow.common import (  # noqa: F401 - imported from here by the UI
    QaOverrideRequired,
    TranscriptionCancelled,
    WorkflowError,
)
from packages.desktop.core.workflow.settings import SettingsMixin
from packages.desktop.core.workflow.clinic_speaker import ClinicSpeakerMixin
from packages.desktop.core.workflow.maintenance import MaintenanceMixin
from packages.desktop.core.workflow.cases import CasesMixin
from packages.desktop.core.workflow.recordings import RecordingsMixin
from packages.desktop.core.workflow.transcripts import TranscriptsMixin
from packages.desktop.core.workflow.findings import FindingsMixin
from packages.desktop.core.workflow.reports import ReportsMixin


class DesktopService(
    SettingsMixin,
    ClinicSpeakerMixin,
    MaintenanceMixin,
    CasesMixin,
    RecordingsMixin,
    TranscriptsMixin,
    FindingsMixin,
    ReportsMixin,
):
    """Every step of the workflow; each mixin holds one area (see ``packages/desktop/core/workflow``)."""

    def __init__(self, workspace: Workspace, *, repository: Any | None = None) -> None:
        self.workspace = workspace
        if repository is None:
            from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

            repository = SqlAlchemyRepository(workspace.database_url, create_schema=True, seed_demo=False)
        self.repo = repository
        from packages.desktop.core.models import use_downloaded_thai_model

        use_downloaded_thai_model()
        self._apply_transcription_mode()
        self._apply_clinic_speaker_model()

    def close(self) -> None:
        """Release the database file, e.g. before a restore replaces it."""
        engine = getattr(self.repo, "engine", None)
        if engine is not None:
            engine.dispose()

    @property
    def user(self):
        from app.core.security import CurrentUser

        return CurrentUser(
            user_id=LOCAL_USER_ID,
            role="therapist",
            display_name=self.therapist_name or "Therapist",
            organization_id=LOCAL_ORGANIZATION_ID,
        )

    def _require_signer(self) -> str:
        name = self.therapist_name
        if not name:
            raise WorkflowError(tr("ตั้งชื่อนักบำบัดก่อน (เมนู ตั้งค่า) เพราะชื่อนี้จะอยู่ในการรับรองและการลงนาม", "Set the therapist name first (Settings); it appears on attestations and signatures."))
        return name

    def _save(self) -> None:
        if hasattr(self.repo, "save"):
            self.repo.save()

    def audit_events(self, limit: int = 200) -> list[dict]:
        if hasattr(self.repo, "audit_events"):
            events = self.repo.audit_events()
        else:
            events = list(self.repo.audit_log)
        return events[-limit:]
