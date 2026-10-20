"""Page fades and toasts, with and without reduced motion (offscreen)."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QLabel  # noqa: E402

from packages.desktop.ui import motion  # noqa: E402
from tests.test_desktop_ui import window  # noqa: E402,F401 - the window fixture


@pytest.fixture
def animate(monkeypatch):
    monkeypatch.setattr(motion, "saved_mode", lambda: "full")


@pytest.fixture
def still(monkeypatch):
    monkeypatch.setattr(motion, "saved_mode", lambda: "reduce")


def test_motion_follows_the_computer_unless_chosen(monkeypatch):
    monkeypatch.setattr(motion, "saved_mode", lambda: "system")
    monkeypatch.setattr(motion, "system_reduces_motion", lambda: True)
    assert not motion.enabled()
    monkeypatch.setattr(motion, "system_reduces_motion", lambda: False)
    assert motion.enabled()
    monkeypatch.setattr(motion, "saved_mode", lambda: "reduce")
    assert not motion.enabled()
    with pytest.raises(ValueError):
        motion.save_mode("fast")


def test_fade_in_removes_its_effect_when_done(qtbot, animate):
    page = QLabel("page")
    qtbot.addWidget(page)
    page.show()

    motion.fade_in(page, duration=40)

    assert page.graphicsEffect() is not None
    qtbot.waitUntil(lambda: page.graphicsEffect() is None, timeout=2000)


def test_reduced_motion_changes_pages_at_once(qtbot, still):
    page = QLabel("page")
    qtbot.addWidget(page)
    page.show()

    motion.fade_in(page)

    assert page.graphicsEffect() is None


def test_toast_shows_plain_text_and_goes_away(window, qtbot, still):
    window.notify("<b>บันทึก</b> แล้ว", msecs=1500)

    toast = window.toast
    assert toast.isVisible()
    assert toast.text() == "<b>บันทึก</b> แล้ว"
    assert toast.textFormat() == Qt.TextFormat.PlainText
    assert window.rect().contains(toast.geometry())
    qtbot.waitUntil(lambda: not toast.isVisible(), timeout=4000)


def test_toast_fades_out_when_motion_is_on(window, qtbot, animate):
    window.notify("Saved")
    assert window.toast.isVisible()

    window.toast.dismiss()

    qtbot.waitUntil(lambda: not window.toast.isVisible(), timeout=2000)


def test_pages_report_through_the_window_toast(window, still):
    for page in window.pages:
        page.notify.emit(f"from {type(page).__name__}")
        assert window.toast.text() == f"from {type(page).__name__}"


def test_motion_menu_shows_the_saved_choice(window):
    assert set(window.motion_actions) == set(motion.MODES)
    assert window.motion_actions[motion.saved_mode()].isChecked()
