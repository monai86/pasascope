"""Backups, app updates and speech-model downloads.

Part of :class:`packages.desktop.core.service.DesktopService`."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from packages.desktop.core.i18n import tr
from packages.desktop.core.workspace import LOCAL_USER_ID


class MaintenanceMixin:
    BACKUP_REMINDER_DAYS = 7

    @property
    def last_backup_at(self):
        """When this workspace was last backed up, or None."""
        value = self.workspace.read_profile().get("last_backup_at")
        try:
            return datetime.fromisoformat(value) if value else None
        except ValueError:
            return None

    def backup_due(self) -> bool:
        """True when there is real data and no backup in the last week."""
        if (self.workspace.root / "pasascope-demo.json").exists() or not self.list_cases():
            return False
        last = self.last_backup_at
        return last is None or (datetime.now(last.tzinfo) - last).days >= self.BACKUP_REMINDER_DAYS

    def create_backup(self, destination, app_version: str = "", progress=None, cancelled=None):
        from packages.desktop.core.backup import create_backup

        self._save()
        cases = self.list_cases()
        counts = {
            "cases": len(cases),
            "sessions": sum(len(self.list_sessions(case.case_id)) for case in cases),
            "recordings": sum(1 for path in self.workspace.storage_root.rglob("*") if path.is_file()),
        }
        info = create_backup(self.workspace, Path(destination), counts=counts, app_version=app_version,
                             progress=progress, cancelled=cancelled)
        profile = self.workspace.read_profile()
        profile["last_backup_at"] = info.created_at
        profile["last_backup_path"] = str(info.path)
        self.workspace.write_profile(profile)
        return info

    @property
    def auto_update_check(self) -> bool:
        return bool(self.workspace.read_profile().get("auto_update_check", True))

    def set_auto_update_check(self, enabled: bool) -> None:
        profile = self.workspace.read_profile()
        profile["auto_update_check"] = bool(enabled)
        self.workspace.write_profile(profile)

    def update_check_due(self, now: datetime | None = None) -> bool:
        """Automatic checks run at most once a day, and only when switched on."""
        if not self.auto_update_check:
            return False
        last = self.workspace.read_profile().get("last_update_check")
        if not last:
            return True
        try:
            then = datetime.fromisoformat(str(last))
        except ValueError:
            return True
        now = now or datetime.now(timezone.utc)
        return (now - then).total_seconds() >= 24 * 3600

    def check_for_update(self, current_version: str):
        """The newer release on GitHub, or None; remembers when it last looked."""
        from packages.desktop.core.updates import check_for_update

        release = check_for_update(current_version)
        profile = self.workspace.read_profile()
        profile["last_update_check"] = datetime.now(timezone.utc).isoformat()
        self.workspace.write_profile(profile)
        return release

    def download_update(self, release, progress=None, cancelled=None) -> Path:
        """Download and check the release's installer for this platform into the Downloads folder."""
        from packages.desktop.core.updates import download_release

        def report(done: int, total: int) -> None:
            if progress:
                progress(done / total if total else 0.0, tr("ดาวน์โหลดรุ่นใหม่", "Downloading the new version"))

        path = download_release(release, Path.home() / "Downloads", report, cancelled=cancelled)
        self.repo.add_audit("app.update_downloaded", release.version, f"Downloaded {path.name} (SHA-256 checked).",
                            actor_id=LOCAL_USER_ID)
        self._save()
        return path

    def thai_model_status(self) -> dict:
        """Whether the Thai Whisper model is on this computer, where, and its download size."""
        from packages.desktop.core.models import THAI_WHISPER, use_downloaded_thai_model

        folder = use_downloaded_thai_model()
        return {"installed": folder is not None, "path": folder, "size": THAI_WHISPER.size}

    def download_speech_models(self, progress=None, cancelled=None) -> Path:
        """Download and check the Thai Whisper model, then fetch the smaller models used on first transcription."""
        from packages.desktop.core.models import THAI_WHISPER, download, prefetch_others, use_downloaded_thai_model

        def report(done: int, total: int) -> None:
            if progress:
                progress(done / total * 0.95, tr("ดาวน์โหลดโมเดลภาษาไทย", "Downloading the Thai model"))

        if not self.thai_model_status()["installed"]:
            download(THAI_WHISPER, report, cancelled=cancelled)
        if progress:
            progress(0.96, tr("ดาวน์โหลดโมเดลแยกเสียงและภาษา", "Downloading the voice and language models"))
        prefetch_others()
        folder = use_downloaded_thai_model()
        self.repo.add_audit("models.download", "speech_models", f"Speech models ready at {folder}.", actor_id=LOCAL_USER_ID)
        self._save()
        return folder
