"""Light and dark themes, and changing theme without losing the place (offscreen)."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from PySide6.QtWidgets import QApplication  # noqa: E402

from packages.desktop.ui import main_window, theme  # noqa: E402
from tests.test_desktop_ui import _case_with_session, window  # noqa: E402,F401 - the window fixture


def _contrast(foreground: str, background: str) -> float:
    def luminance(colour: str) -> float:
        channels = [int(colour.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    high, low = sorted((luminance(foreground), luminance(background)), reverse=True)
    return (high + 0.05) / (low + 0.05)


@pytest.fixture(autouse=True)
def back_to_light(qapp):
    yield
    theme.apply_theme(qapp, "light")
    main_window._LIVE.clear()


def test_both_themes_name_the_same_colours():
    assert set(theme.LIGHT) == set(theme.DARK)


def test_dark_text_is_readable_on_its_pages():
    dark = theme.DARK
    for text in ("INK", "INK_SOFT", "MUTED", "PRIMARY_TEXT", "LINK", "ATTENTION", "DANGER", "OK", "ADULT"):
        for page in ("CANVAS", "SIDEBAR", "HOVER"):
            assert _contrast(dark[text], dark[page]) >= 4.5, (text, page)
    for text, tint in (("ATTENTION", "ATTENTION_SOFT"), ("DANGER", "DANGER_SOFT"), ("OK", "OK_SOFT"),
                       ("PRIMARY_TEXT", "PRIMARY_SOFT"), ("INK", "PRIMARY_SOFT")):
        assert _contrast(dark[text], dark[tint]) >= 4.5, (text, tint)


def test_apply_theme_switches_every_colour_and_the_style_sheet(qapp):
    assert theme.apply_theme(qapp, "dark") is True
    assert theme.is_dark()
    assert theme.INK == theme.DARK["INK"]
    assert theme.SPEAKER_COLORS["CHI"] == theme.DARK["PRIMARY_TEXT"]
    assert theme.DARK["SURFACE"] in qapp.styleSheet()
    assert f'#Chip[kind="primary"] {{ color: {theme.DARK["PRIMARY_TEXT"]}' in qapp.styleSheet()
    assert theme.apply_theme(qapp, "light") is False
    assert theme.INK == theme.LIGHT["INK"]
    assert theme.LIGHT["SURFACE"] in qapp.styleSheet()


def test_widget_colours_come_from_the_style_sheet_not_inline_styles(qtbot):
    """Every colour lives in the theme's selectors, so one style sheet repaints the app."""
    import pathlib
    import re

    ui = pathlib.Path(theme.__file__).parent
    inline = [
        f"{path.relative_to(ui)}:{number}"
        for path in ui.rglob("*.py") if path.name != "theme.py"
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if re.search(r"\.setStyleSheet\(", line)
    ]
    assert inline == []


def test_chip_kind_changes_its_colours(qtbot, qapp):
    from packages.desktop.ui.widgets import chip, set_chip

    theme.apply_theme(qapp, "light")
    tag = chip("Draft", "attention")
    qtbot.addWidget(tag)
    tag.show()
    assert tag.palette().color(tag.foregroundRole()).name() == theme.LIGHT["ATTENTION"]
    set_chip(tag, "Signed", "ok")
    assert tag.property("kind") == "ok"
    assert tag.palette().color(tag.foregroundRole()).name() == theme.LIGHT["OK"]


def test_changing_theme_reopens_the_same_case_session_and_step(window, qtbot, monkeypatch):
    case, session = _case_with_session(window)
    window.tabs.setCurrentIndex(1)
    window.search.setText("TH-010")
    monkeypatch.setattr(theme, "saved_mode", lambda: "dark")

    window.restyle(ask=False)

    successor = main_window._LIVE[0]
    qtbot.addWidget(successor)
    assert successor is not window
    assert theme.is_dark()
    assert successor.case.case_id == case.case_id
    assert successor.session.session_id == session.session_id
    assert successor.tabs.currentIndex() == 1
    assert successor.search.text() == "TH-010"
    assert successor.appearance_actions["dark"].isChecked()
    assert theme.DARK["CANVAS"] in QApplication.instance().styleSheet()


def test_knowledge_topic_survives_a_theme_change(window, qtbot, monkeypatch):
    window.show_knowledge("privacy")
    monkeypatch.setattr(theme, "saved_mode", lambda: "dark")

    window.restyle(ask=False)

    successor = main_window._LIVE[0]
    qtbot.addWidget(successor)
    assert successor.editor_area.current_key() == "knowledge"
    assert successor.knowledge.topics.currentItem().data(0x0100) == "privacy"


def test_theme_change_waits_for_work_to_finish(window, qtbot, monkeypatch):
    monkeypatch.setattr(theme, "saved_mode", lambda: "dark")
    monkeypatch.setattr(window, "deleteLater", lambda: None)  # qtbot closes it after the test
    window._set_busy(True)

    window.restyle(ask=False)

    assert not main_window._LIVE
    assert not theme.is_dark()
    assert window._restyle_pending

    window._set_busy(False)
    qtbot.waitUntil(lambda: bool(main_window._LIVE), timeout=2000)
    qtbot.addWidget(main_window._LIVE[0])
    assert theme.is_dark()


def test_unasked_theme_change_keeps_unsaved_edits(window, monkeypatch):
    _case_with_session(window)
    monkeypatch.setattr(theme, "saved_mode", lambda: "dark")
    monkeypatch.setattr(window.pages[1], "has_unsaved_changes", lambda: True)

    window.restyle(ask=False)  # as when the computer switches to dark by itself

    assert not main_window._LIVE
    assert window._restyle_pending
    assert not theme.is_dark()


def test_no_change_needed_does_not_rebuild(window):
    window.restyle(ask=False)  # saved mode follows the computer; offscreen it is light

    assert not main_window._LIVE
    assert not window._restyle_pending
