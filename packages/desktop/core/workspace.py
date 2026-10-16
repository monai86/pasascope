"""Where the desktop app keeps its data, and how the shared services are set up.

The app runs the API's service layer (``apps/api/app/services``) in its own
process over a SQLite file, so the web app and the desktop app analyse a
transcript with the same code. Nothing listens on a port.

Layout of a workspace folder::

    pasascope.db     cases, sessions, transcripts, features, cues, reports, audit log
    storage/audio/   recordings, under opaque names
    exports/         default folder for exported reports and transcripts
    profile.json     the therapist who signs on this computer
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
API_ROOT = ROOT / "apps" / "api"

HOME_ENV = "PASASCOPE_DESKTOP_HOME"

# Every record made on this computer belongs to this organization and user.
LOCAL_ORGANIZATION_ID = "local"
LOCAL_USER_ID = "local-therapist"


def default_home() -> Path:
    configured = os.environ.get(HOME_ENV, "").strip()
    if configured:
        return Path(configured).expanduser()
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "PasaScope"
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", Path.home())) / "PasaScope"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "pasascope"


def demo_home() -> Path:
    """The demonstration data folder, next to the real one ("PasaScope Demo")."""
    home = default_home()
    return home.with_name(home.name + " Demo")


@dataclass(frozen=True)
class Workspace:
    root: Path

    @property
    def database_path(self) -> Path:
        return self.root / "pasascope.db"

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.database_path}"

    @property
    def storage_root(self) -> Path:
        return self.root / "storage"

    @property
    def exports_dir(self) -> Path:
        return self.root / "exports"

    @property
    def profile_path(self) -> Path:
        return self.root / "profile.json"

    def read_profile(self) -> dict:
        try:
            data = json.loads(self.profile_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def write_profile(self, profile: dict) -> None:
        self.profile_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")


def _configure_shared_services(workspace: Workspace) -> None:
    """Point the API settings at this workspace before anything reads them.

    ``PASASCOPE_MOCK_MODE`` stays on: in the API it means "local, not the
    production deployment" (no Supabase sign-in, no managed storage). The
    desktop never uses the mock transcription provider or demo records.
    """
    if str(API_ROOT) not in sys.path:
        sys.path.insert(0, str(API_ROOT))
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    os.environ["PASASCOPE_MOCK_MODE"] = "true"
    os.environ["PASASCOPE_AUTH_MODE"] = "mock"
    os.environ["PASASCOPE_REPOSITORY_MODE"] = "sql"
    os.environ["PASASCOPE_DATABASE_URL"] = workspace.database_url
    os.environ["PASASCOPE_STORAGE_MODE"] = "local_private"
    os.environ["PASASCOPE_LOCAL_STORAGE_ROOT"] = str(workspace.storage_root)
    os.environ["PASASCOPE_AUDIO_BACKUP_MODE"] = "none"
    os.environ["PASASCOPE_ASR_HOSTED_ENABLED"] = "false"
    os.environ.setdefault("PASASCOPE_ASR_LOCAL_WHISPER_ENABLED", "true")
    # Child/adult attribution with the USC frame model (downloaded once).
    os.environ.setdefault("PASASCOPE_DIARIZER", "hybrid")

    from app.core.config import get_settings

    get_settings.cache_clear()


def open_workspace(root: Path | None = None) -> Workspace:
    workspace = Workspace((root or default_home()).expanduser().resolve())
    for folder in (workspace.root, workspace.storage_root, workspace.exports_dir):
        folder.mkdir(parents=True, exist_ok=True)
    _configure_shared_services(workspace)
    return workspace
