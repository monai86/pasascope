"""Names the main window and its mixins share: page indexes, the logo, step titles."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QMainWindow

from packages.desktop.core.i18n import tr

LOGO = Path(__file__).resolve().parents[1] / "assets" / "logo.png"
OVERVIEW = "__overview__"  # session picker entry for the case overview
NO_SESSION_PAGE, SESSION_PAGE, OVERVIEW_PAGE = range(3)
HOME_PAGE, CASE_PAGE, KNOWLEDGE_PAGE = range(3)
_LIVE: list[QMainWindow] = []  # the window in use after a theme change replaced the first one


def step_titles() -> list[str]:
    return [tr("1  เสียง", "1  Recording"), tr("2  Transcript", "2  Transcript"),
            tr("3  ตัวชี้วัด", "3  Findings"), tr("4  รายงาน", "4  Report")]
