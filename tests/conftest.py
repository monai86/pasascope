from __future__ import annotations

import os

import pytest

# Desktop UI tests read Thai wording; English is checked by tests that switch the language.
os.environ.setdefault("PASASCOPE_LANGUAGE", "th")


@pytest.fixture(autouse=True)
def isolated_desktop_records(tmp_path, monkeypatch):
    """Keep the desktop app's local records file out of the home directory during tests."""
    path = tmp_path / "desktop-records.json"
    monkeypatch.setenv("PASASCOPE_DESKTOP_RECORDS_PATH", str(path))
    return path

