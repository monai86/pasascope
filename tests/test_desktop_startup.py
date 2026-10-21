"""The splash window, the first-start walkthrough, and the start-up steps (offscreen)."""

from __future__ import annotations

import json
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from PySide6.QtWidgets import QDialog  # noqa: E402

from packages.desktop import app as desktop_app  # noqa: E402
from packages.desktop.core import DesktopService, open_workspace  # noqa: E402
from packages.desktop.core.i18n import language, set_language  # noqa: E402
from packages.desktop.ui import motion  # noqa: E402
from packages.desktop.ui.onboarding import Onboarding  # noqa: E402
from packages.desktop.ui.splash import INTRO_MS, Splash  # noqa: E402


@pytest.fixture(autouse=True)
def keep_language():
    before = language()
    yield
    set_language(before)


@pytest.fixture
def fresh(tmp_path):
    return DesktopService(open_workspace(tmp_path / "ws"))


def test_splash_plays_its_intro_then_closes(qtbot, monkeypatch):
    monkeypatch.setattr(motion, "saved_mode", lambda: "full")
    splash = Splash("1.8.0", demo=True)  # it deletes itself when it closes, so qtbot does not own it
    splash.show()
    assert splash.animated and not splash.minimum_shown()
    splash.set_status("Loading speech recognition…")
    splash.grab()  # paints every layer without error
    qtbot.waitUntil(splash.minimum_shown, timeout=INTRO_MS + 2000)
    splash.finish()
    qtbot.waitUntil(lambda: splash.closed, timeout=2000)


def test_splash_without_motion_is_ready_at_once(qtbot, monkeypatch):
    monkeypatch.setattr(motion, "saved_mode", lambda: "reduce")
    splash = Splash("1.8.0")
    splash.show()
    assert splash.minimum_shown()
    splash.grab()
    splash.finish()
    assert splash.closed


def test_walkthrough_asks_for_understanding_and_a_name(qtbot, fresh, tmp_path):
    set_language("en")
    dialog = Onboarding(fresh, fresh.workspace.root)
    qtbot.addWidget(dialog)
    dialog.show()
    assert dialog.step == 0 and dialog.next_btn.isEnabled()

    dialog.next_btn.click()
    assert dialog.step == 1 and not dialog.next_btn.isEnabled()  # tick the box first
    assert str(fresh.workspace.root) in "".join(w.text() for w in dialog.pages.currentWidget().findChildren(type(dialog.hint)))
    dialog.understood_box.setChecked(True)
    assert dialog.next_btn.isEnabled()

    dialog.next_btn.click()
    assert dialog.step == 2 and not dialog.next_btn.isEnabled()  # a name is needed
    dialog.name.setText("  นักบำบัด ทดสอบ ")
    dialog.clinic.setText("คลินิกทดสอบ")
    assert dialog.next_btn.isEnabled()
    dialog.next_btn.click()

    assert dialog.result() == QDialog.DialogCode.Accepted
    assert fresh.therapist_name == "นักบำบัด ทดสอบ"
    assert fresh.organization == "คลินิกทดสอบ"
    assert fresh.language == "en"


def test_choosing_thai_redraws_the_walkthrough_and_is_saved(qtbot, fresh):
    set_language("en")
    dialog = Onboarding(fresh, fresh.workspace.root)
    qtbot.addWidget(dialog)
    dialog._set_language("th")
    assert language() == "th"
    assert dialog.next_btn.text() == "ถัดไป"
    assert dialog.windowTitle() == "ยินดีต้อนรับสู่ PasaScope"
    dialog._go(2)
    dialog.name.setText("กานดา")
    dialog._next()
    assert fresh.language == "th"


def test_values_survive_a_language_change(qtbot, fresh):
    set_language("en")
    dialog = Onboarding(fresh, fresh.workspace.root)
    qtbot.addWidget(dialog)
    dialog._go(2)
    dialog.name.setText("Kanda")
    dialog._set_language("th")
    assert dialog.step == 2
    assert dialog.name.text() == "Kanda"


def test_start_reads_the_saved_language_without_loading_the_workflow(tmp_path):
    (tmp_path / "profile.json").write_text(json.dumps({"language": "th"}), encoding="utf-8")
    assert desktop_app._profile_language(tmp_path) == "th"
    assert desktop_app._profile_language(tmp_path / "missing") is None


def test_preload_names_each_step_and_finishes():
    state = {"done": False}
    desktop_app._preload(state)
    assert state["done"] and state["stage"]


def test_an_update_keeps_the_name_so_the_walkthrough_does_not_return(tmp_path):
    first = DesktopService(open_workspace(tmp_path / "ws"))
    first.set_therapist_name("Kanda")
    first.close()
    # A new copy of the app opening the same data folder, as after an update.
    again = DesktopService(open_workspace(tmp_path / "ws"))
    assert again.therapist_name == "Kanda"


def test_a_ready_update_starts_only_once_the_window_closes(qtbot, tmp_path, monkeypatch):
    from packages.desktop.ui.main_window import MainWindow
    from packages.desktop.ui.window import updates as window_updates

    service = DesktopService(open_workspace(tmp_path / "ws"))
    window = MainWindow(service)
    qtbot.addWidget(window)
    window.show()
    started = []
    monkeypatch.setattr(window_updates, "start_macos_swap",
                        lambda bundle, staged, pid, relaunch: started.append((bundle, staged, pid, relaunch)))
    window._pending_update = ("macos", tmp_path / "PasaScope.app", tmp_path / ".PasaScope-update.app", True)
    assert not started

    window.close()

    assert started == [(tmp_path / "PasaScope.app", tmp_path / ".PasaScope-update.app", os.getpid(), True)]
    assert window._pending_update is None


def test_log_filter_drops_only_the_accessibility_noise(capsys):
    from PySide6.QtCore import qDebug, qInstallMessageHandler, qWarning

    desktop_app._install_qt_message_filter()
    try:
        qWarning("QTextCursor::setPosition: Position '1' out of range")
        qWarning("something that matters")
        qDebug("Cell requested for row 5 is out of bounds for table with 0 rows! Resizing table model.")
    finally:
        qInstallMessageHandler(None)
    err = capsys.readouterr().err
    assert "something that matters" in err
    assert "setPosition" not in err and "Cell requested" not in err


def test_dates_on_screen_read_day_month_year():
    from datetime import date

    from packages.desktop.ui import labels

    assert labels.day_text("2026-10-16") == "16/10/2026"
    assert labels.day_text(date(2026, 9, 4)) == "04/09/2026"
    assert labels.day_text("not a date") == "not a date"
