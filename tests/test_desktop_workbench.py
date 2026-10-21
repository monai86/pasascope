"""The workbench: several session tabs, unsaved marks, closing, and the command palette (offscreen)."""

from __future__ import annotations

from datetime import date
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from PySide6.QtWidgets import QMessageBox  # noqa: E402

from packages.desktop.ui import main_window, theme  # noqa: E402
from packages.desktop.ui.editors import SessionEditor  # noqa: E402
from packages.desktop.ui.workbench import match_score  # noqa: E402
from tests.test_desktop_service import CHAT  # noqa: E402
from tests.test_desktop_ui import _case_with_session, window  # noqa: E402,F401 - the window fixture


def _two_sessions(window):
    case, first = _case_with_session(window)
    second = window.service.create_session(case.case_id, date(2026, 10, 20))
    window.service.import_transcript_text(first.session_id, CHAT)
    window.service.import_transcript_text(second.session_id, CHAT)
    return case, first, second


def test_each_session_has_its_own_tab_and_keeps_its_step(window):
    case, first, second = _two_sessions(window)
    one = window.open_session(first.session_id)
    one.tabs.setCurrentIndex(1)
    two = window.open_session(second.session_id)
    two.tabs.setCurrentIndex(0)
    assert one is not two and one.pages[1] is not two.pages[1]
    assert window.session.session_id == second.session_id

    window.open_session(first.session_id)  # back to the first tab
    assert window.session_editor is one and one.tabs.currentIndex() == 1
    assert window.editor_area.bar.tabText(window.editor_area.index_of(f"session:{first.session_id}")) == "TH-010 · 16/10/2026"


def test_unsaved_edits_mark_the_tab_and_are_asked_about_on_close(window, monkeypatch):
    _, first, _ = _two_sessions(window)
    editor = window.open_session(first.session_id)
    key = f"session:{first.session_id}"
    editor.pages[1].dirty = True
    window._poll_dirty()
    assert window.editor_area.bar.tabText(window.editor_area.index_of(key)).startswith("● ")

    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Cancel)
    assert not window.close_tab(key)
    assert key in window.editor_area.keys()

    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Discard)
    assert window.close_tab(key)
    assert key not in window.editor_area.keys()


def test_a_busy_session_tab_stays_open(window):
    _, first, _ = _two_sessions(window)
    editor = window.open_session(first.session_id)
    editor._on_busy(True)
    assert window.busy
    assert not window.close_tab(f"session:{first.session_id}")
    editor._on_busy(False)
    assert not window.busy
    assert window.close_tab(f"session:{first.session_id}")


def test_closing_every_tab_shows_the_shortcuts(window):
    _two_sessions(window)
    for key in list(window.editor_area.keys()):
        window.close_tab(key)
    assert window.editor_area.keys() == []
    assert window.editor_area.stack.currentWidget() is window.editor_area.watermark
    window.show_home()
    assert window.current_editor is window.dashboard


def test_quick_open_finds_a_session_by_typing(window, qtbot):
    _, first, second = _two_sessions(window)
    window.show_home()
    window.show_command_palette(quick_open=True)
    palette = window.command_palette
    assert palette.isVisible()
    palette.input.setText("th-010 20/10")
    assert palette.list.count() >= 1
    palette._run_item(palette.list.item(0))
    assert not palette.isVisible()
    assert window.session.session_id == second.session_id


def test_command_palette_runs_commands(window, monkeypatch):
    window.show_command_palette()
    palette = window.command_palette
    from packages.desktop.core.i18n import tr

    palette.input.setText(f"{tr('ความรู้', 'Knowledge')} MLU")
    labels = [palette.list.item(i).text() for i in range(palette.list.count())]
    assert labels, "a Knowledge topic should match"
    palette._run_item(palette.list.item(0))
    assert window.editor_area.current_key() == "knowledge"


def test_match_score_needs_every_word():
    assert match_score("demo 16", "Open: DEMO-001 · 16/10/2026") is not None
    assert match_score("demo xyz", "Open: DEMO-001") is None
    assert match_score("dm", "DEMO") is not None  # letters in order
    assert match_score("demo", "DEMO-001") > match_score("dmo", "DEMO-001")


def test_tree_lists_sessions_under_their_case(window):
    case, first, second = _two_sessions(window)
    window.reload_cases(case.case_id)
    top = window.case_list.topLevelItem(0)
    assert top.childCount() == 2
    window._on_tree_item(top.child(1))
    assert isinstance(window.current_editor, SessionEditor)
    assert window.case_list.currentItem() is top.child(1)  # the tree is not rebuilt by switching tabs
    window._on_tree_item(top)
    assert window.case_editor is not None and window.case_editor.case.case_id == case.case_id


def test_theme_change_reopens_every_tab(window, qtbot, monkeypatch):
    _, first, second = _two_sessions(window)
    window.open_session(first.session_id).tabs.setCurrentIndex(1)
    window.open_session(second.session_id)
    keys = window.editor_area.keys()
    monkeypatch.setattr(theme, "saved_mode", lambda: "dark")
    try:
        window.restyle(ask=False)
        successor = main_window._LIVE[0]
        qtbot.addWidget(successor)
        assert successor.editor_area.keys() == keys
        assert successor.session.session_id == second.session_id
        assert successor.editor_area.editors[f"session:{first.session_id}"].tabs.currentIndex() == 1
    finally:
        theme.apply_theme(qtbot_app(), "light")
        main_window._LIVE.clear()


def qtbot_app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance()


def test_a_new_case_appears_in_the_tree_and_opens(window, monkeypatch):
    from packages.desktop.ui import dialogs

    def fill(dialog):
        dialog.code.setText("TH-099")
        return True

    monkeypatch.setattr(dialogs.NewCaseDialog, "exec", fill)
    monkeypatch.setattr(dialogs.ConsentDialog, "exec", lambda dialog: False)
    window.new_case()
    assert window.case_editor is not None and window.case.child_code == "TH-099"
    assert window.case_list.currentItem().text(0).startswith("TH-099")


def test_the_tab_in_front_is_the_page_shown(window):
    assert window.editor_area.stack.currentWidget() is window.dashboard
    case, first, second = _two_sessions(window)
    editor = window.open_session(second.session_id)
    assert window.editor_area.stack.currentWidget() is editor
    window.close_tab(f"session:{second.session_id}")
    assert window.editor_area.stack.currentWidget() is window.current_editor


def test_the_tab_row_keeps_its_height_with_one_tab(window):
    assert window.editor_area.bar.count() == 1
    assert window.editor_area.bar.height() == 36
