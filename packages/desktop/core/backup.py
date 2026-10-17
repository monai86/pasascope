"""Back up a workspace to one zip file, and restore it.

A backup holds a consistent copy of the database (SQLite's backup API, so it
is safe while the app is open), the recordings, exports and profile, and a
manifest with the date, record counts and a SHA-256 for every file. Restore
checks the manifest and every hash before touching anything, then moves the
current workspace aside instead of deleting it.

The zip is not encrypted: it contains children's recordings and transcripts
and must be kept somewhere only the therapist can reach.
"""

from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import sqlite3
import tempfile
import zipfile

from packages.desktop.core.workspace import Workspace

MANIFEST = "pasascope-backup.json"
BACKUP_FORMAT = 1
DATABASE = "pasascope.db"
# Already-compressed media gains nothing from deflate.
_STORED_SUFFIXES = {".mp3", ".m4a", ".mp4", ".webm", ".ogg", ".zip", ".pdf"}


class BackupError(Exception):
    """The file is not a usable PasaScope backup."""


@dataclass(frozen=True)
class BackupInfo:
    path: Path
    created_at: str
    app_version: str
    counts: dict
    file_count: int
    total_bytes: int
    demo: bool


def create_backup(workspace: Workspace, destination: Path, *, counts: dict, app_version: str = "") -> BackupInfo:
    """Write the workspace to ``destination`` (a .zip); return what was written."""
    destination = Path(destination)
    partial = destination.with_name(destination.name + ".partial")
    files: dict[str, dict] = {}
    with tempfile.TemporaryDirectory() as tmp:
        snapshot = Path(tmp) / DATABASE
        _snapshot_database(workspace.database_path, snapshot)
        sources = [(DATABASE, snapshot)] + [
            (path.relative_to(workspace.root).as_posix(), path)
            for path in sorted(workspace.root.rglob("*"))
            if path.is_file() and path.name != DATABASE
            and not any(part.startswith(".") for part in path.relative_to(workspace.root).parts)
            and not path.name.endswith((".db-journal", ".db-wal", ".db-shm"))
        ]
        with zipfile.ZipFile(partial, "w") as archive:
            for name, path in sources:
                compression = zipfile.ZIP_STORED if path.suffix.lower() in _STORED_SUFFIXES else zipfile.ZIP_DEFLATED
                archive.write(path, name, compress_type=compression)
                files[name] = {"sha256": _sha256(path), "bytes": path.stat().st_size}
            manifest = {
                "format": BACKUP_FORMAT,
                "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                "app_version": app_version,
                "counts": counts,
                "demo": (workspace.root / "pasascope-demo.json").exists(),
                "files": files,
            }
            archive.writestr(MANIFEST, json.dumps(manifest, ensure_ascii=False, indent=2))
    partial.replace(destination)
    return _info(destination, manifest)


def read_backup(path: Path) -> BackupInfo:
    """Check that ``path`` is a complete backup and describe it, without extracting."""
    manifest = _manifest(Path(path))
    return _info(Path(path), manifest)


def restore_backup(workspace_root: Path, path: Path) -> Path:
    """Replace the workspace with the backup; return where the old workspace was moved.

    Every file is extracted and checked against the manifest in a sibling
    folder first, so a damaged backup leaves the current workspace untouched.
    """
    workspace_root = Path(workspace_root)
    manifest = _manifest(Path(path))
    staging = workspace_root.with_name(f".{workspace_root.name}-restore")
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    try:
        with zipfile.ZipFile(path) as archive:
            for name, expected in manifest["files"].items():
                target = staging / name
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(name) as source, target.open("wb") as sink:
                    shutil.copyfileobj(source, sink)
                if _sha256(target) != expected["sha256"]:
                    raise BackupError(f"ไฟล์ {name} ในไฟล์สำรองเสียหาย (checksum ไม่ตรง)")
        _check_database(staging / DATABASE)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    previous = workspace_root.with_name(f"{workspace_root.name} ก่อนกู้คืน {stamp}")
    if workspace_root.exists():
        workspace_root.rename(previous)
    staging.rename(workspace_root)
    for folder in ("storage", "exports"):
        (workspace_root / folder).mkdir(exist_ok=True)
    return previous


def _snapshot_database(source: Path, target: Path) -> None:
    if not source.exists():
        raise BackupError("ยังไม่มีฐานข้อมูลให้สำรอง")
    with closing(sqlite3.connect(f"file:{source}?mode=ro", uri=True)) as src, closing(sqlite3.connect(target)) as dst:
        src.backup(dst)
    _check_database(target)


def _check_database(path: Path) -> None:
    try:
        with closing(sqlite3.connect(f"file:{path}?mode=ro", uri=True)) as connection:
            result = connection.execute("PRAGMA integrity_check").fetchone()
    except sqlite3.Error as exc:
        raise BackupError(f"ฐานข้อมูลในไฟล์สำรองเปิดไม่ได้: {exc}") from exc
    if not result or result[0] != "ok":
        raise BackupError("ฐานข้อมูลในไฟล์สำรองไม่สมบูรณ์")


def _manifest(path: Path) -> dict:
    try:
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            if MANIFEST not in names:
                raise BackupError("ไฟล์นี้ไม่ใช่ไฟล์สำรองของ PasaScope")
            manifest = json.loads(archive.read(MANIFEST).decode("utf-8"))
    except (zipfile.BadZipFile, OSError, ValueError) as exc:
        raise BackupError(f"เปิดไฟล์สำรองไม่ได้: {exc}") from exc
    if manifest.get("format") != BACKUP_FORMAT:
        raise BackupError("ไฟล์สำรองนี้มาจากโปรแกรมรุ่นที่ไม่รองรับ")
    files = manifest.get("files")
    if not isinstance(files, dict) or DATABASE not in files:
        raise BackupError("ไฟล์สำรองไม่มีฐานข้อมูล")
    for name in files:
        if not _safe_member(name) or name not in names:
            raise BackupError(f"ไฟล์สำรองไม่สมบูรณ์หรือมีชื่อไฟล์ผิดปกติ: {name}")
    return manifest


def _safe_member(name: str) -> bool:
    """Only plain relative paths: no absolute paths, drive letters or '..'."""
    member = PurePosixPath(name)
    return bool(name) and not member.is_absolute() and ".." not in member.parts and ":" not in name and "\\" not in name


def _info(path: Path, manifest: dict) -> BackupInfo:
    files = manifest.get("files", {})
    return BackupInfo(
        path=path,
        created_at=str(manifest.get("created_at", "")),
        app_version=str(manifest.get("app_version", "")),
        counts=dict(manifest.get("counts") or {}),
        file_count=len(files),
        total_bytes=sum(int(item.get("bytes", 0)) for item in files.values()),
        demo=bool(manifest.get("demo")),
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
