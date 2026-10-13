from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def isolated_desktop_records(tmp_path, monkeypatch):
    """Keep the desktop app's local records file out of the home directory during tests."""
    path = tmp_path / "desktop-records.json"
    monkeypatch.setenv("PASASCOPE_DESKTOP_RECORDS_PATH", str(path))
    return path

