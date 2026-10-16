"""The demo seeder fills its own folder and never touches the real one."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("seed_demo", ROOT / "scripts" / "seed_desktop_demo.py")
seed_demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(seed_demo)


def test_seeds_cases_sessions_and_signed_reports(tmp_path):
    from packages.desktop.core import DesktopService, open_workspace

    home = tmp_path / "demo"
    seed_demo.prepare_folder(home, reset=False)
    seed_demo.seed(home, with_audio=False, log=lambda *_: None)

    service = DesktopService(open_workspace(home))
    codes = {c.child_code: c for c in service.list_cases()}
    assert set(codes) == {"DEMO-001", "DEMO-002"}
    assert codes["DEMO-002"].consent_status == "pending"
    sessions = service.list_sessions(codes["DEMO-001"].case_id)
    assert len(sessions) == 3
    trend = service.feature_trend(codes["DEMO-001"].case_id, ["mean_length_of_utterance_words"])
    assert len(trend) == 3
    signed = [s for s in sessions if (r := service.get_report(s.session_id)) and r.signed_by]
    assert len(signed) == 2


def test_refuses_a_folder_that_is_not_a_demo(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    (real / "pasascope.db").write_bytes(b"")
    with pytest.raises(SystemExit, match="not a demo folder"):
        seed_demo.prepare_folder(real, reset=True)
    assert (real / "pasascope.db").exists()


def test_reset_rebuilds_only_a_marked_demo_folder(tmp_path):
    home = tmp_path / "demo"
    seed_demo.prepare_folder(home, reset=False)
    (home / "old.txt").write_text("x")
    with pytest.raises(SystemExit, match="already exists"):
        seed_demo.prepare_folder(home, reset=False)
    seed_demo.prepare_folder(home, reset=True)
    assert not (home / "old.txt").exists() and (home / seed_demo.MARKER).exists()
