"""Backups hold the whole workspace, and a restore never loses the current data."""

from __future__ import annotations

from datetime import date, datetime, timedelta
import zipfile

import pytest

from packages.desktop.core import DesktopService, open_workspace
from packages.desktop.core.backup import MANIFEST, BackupCancelled, BackupError, read_backup, restore_backup
from tests.test_desktop_service import CHAT


@pytest.fixture
def service(tmp_path):
    svc = DesktopService(open_workspace(tmp_path / "ws"))
    svc.set_therapist_name("นักบำบัด ทดสอบ")
    case = svc.create_case("TH-001", 50, nickname="ภูมิ")
    svc.grant_consent(case.case_id, "แม่", date(2026, 10, 1))
    session = svc.create_session(case.case_id, date(2026, 10, 16))
    svc.import_transcript_text(session.session_id, CHAT)
    audio = svc.workspace.storage_root / "audio" / "rec.wav"
    audio.parent.mkdir(parents=True, exist_ok=True)
    audio.write_bytes(b"RIFF" + bytes(2000))
    return svc


def test_backup_holds_database_recordings_and_manifest(service, tmp_path):
    cache = service.workspace.root / ".cache" / "speaker_features" / "x.npy"  # rebuilt from the recordings when needed
    cache.parent.mkdir(parents=True)
    cache.write_bytes(b"x")
    info = service.create_backup(tmp_path / "backup.zip", "1.0")
    assert info.counts == {"cases": 1, "sessions": 1, "recordings": 1}
    with zipfile.ZipFile(info.path) as archive:
        names = set(archive.namelist())
    assert {"pasascope.db", "profile.json", "storage/audio/rec.wav", MANIFEST} <= names
    assert not any(name.startswith(".cache/") for name in names)
    assert read_backup(info.path).counts == info.counts
    assert service.last_backup_at is not None
    assert not (tmp_path / "backup.zip.partial").exists()


def test_restore_replaces_data_and_keeps_the_old_folder(service, tmp_path):
    root = service.workspace.root
    backup = service.create_backup(tmp_path / "backup.zip").path
    service.create_case("TH-002", 40)
    service.close()

    previous = restore_backup(root, backup)

    restored = DesktopService(open_workspace(root))
    assert [case.child_code for case in restored.list_cases()] == ["TH-001"]
    assert (root / "storage" / "audio" / "rec.wav").exists()
    kept = DesktopService(open_workspace(previous))
    assert {case.child_code for case in kept.list_cases()} == {"TH-001", "TH-002"}


def test_damaged_backup_leaves_the_workspace_untouched(service, tmp_path):
    root = service.workspace.root
    good = service.create_backup(tmp_path / "good.zip").path
    bad = tmp_path / "bad.zip"
    with zipfile.ZipFile(good) as source, zipfile.ZipFile(bad, "w") as target:
        for item in source.infolist():
            data = source.read(item.filename)
            if item.filename == "storage/audio/rec.wav":
                data = data[:-1] + b"X"
            target.writestr(item, data)

    with pytest.raises(BackupError, match="checksum"):
        restore_backup(root, bad)
    assert [case.child_code for case in service.list_cases()] == ["TH-001"]
    assert not any(path.name.startswith(".ws-restore") for path in root.parent.iterdir())


def test_unsafe_or_foreign_files_are_rejected(tmp_path):
    foreign = tmp_path / "other.zip"
    with zipfile.ZipFile(foreign, "w") as archive:
        archive.writestr("notes.txt", "hello")
    with pytest.raises(BackupError, match="ไม่ใช่ไฟล์สำรอง"):
        read_backup(foreign)

    sneaky = tmp_path / "sneaky.zip"
    with zipfile.ZipFile(sneaky, "w") as archive:
        archive.writestr("pasascope.db", b"")
        archive.writestr("../escape.txt", b"x")
        archive.writestr(MANIFEST, '{"format": 1, "files": {"pasascope.db": {"sha256": "", "bytes": 0}, '
                                   '"../escape.txt": {"sha256": "", "bytes": 1}}}')
    with pytest.raises(BackupError, match="ผิดปกติ"):
        read_backup(sneaky)


def test_backup_reminder_after_a_week(service):
    assert service.backup_due()  # data, never backed up
    profile = service.workspace.read_profile()
    profile["last_backup_at"] = datetime.now().astimezone().isoformat()
    service.workspace.write_profile(profile)
    assert not service.backup_due()
    profile["last_backup_at"] = (datetime.now().astimezone() - timedelta(days=8)).isoformat()
    service.workspace.write_profile(profile)
    assert service.backup_due()


def test_backup_and_restore_report_progress_by_bytes(service, tmp_path):
    seen = []
    info = service.create_backup(tmp_path / "backup.zip", progress=lambda fraction, stage: seen.append((fraction, stage)))
    fractions = [fraction for fraction, _ in seen]
    assert fractions == sorted(fractions) and fractions[-1] == pytest.approx(1.0)
    assert any("rec.wav" in stage for _, stage in seen)

    service.close()
    restored = []
    restore_backup(service.workspace.root, info.path, progress=lambda fraction, stage: restored.append(fraction))
    assert restored == sorted(restored) and restored[-1] == pytest.approx(1.0)


def test_cancelled_backup_leaves_no_file(service, tmp_path):
    target = tmp_path / "backup.zip"
    with pytest.raises(BackupCancelled):
        service.create_backup(target, cancelled=lambda: True)
    assert not target.exists()
    assert not (tmp_path / "backup.zip.partial").exists()
    assert service.last_backup_at is None


def test_a_failed_backup_removes_its_partial_file(service, tmp_path, monkeypatch):
    import packages.desktop.core.backup as backup

    def broken(*_args, **_kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(backup.json, "dumps", broken)
    with pytest.raises(OSError):
        service.create_backup(tmp_path / "backup.zip")
    assert not (tmp_path / "backup.zip.partial").exists()
