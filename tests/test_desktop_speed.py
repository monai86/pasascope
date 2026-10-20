"""The window stays quick with long transcripts (offscreen)."""

from __future__ import annotations

import os
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from PySide6.QtWidgets import QHeaderView, QTableWidget, QTableWidgetItem  # noqa: E402

from packages.desktop.ui.widgets import filling  # noqa: E402
from tests.test_desktop_ui import _analysed_session, _case_with_session, window  # noqa: E402,F401 - the window fixture


def _long_chat(lines: int) -> str:
    adult = ["หนูชอบกินอะไรครับ", "วันนี้ไปโรงเรียนมาไหม", "รถคันนี้สีอะไร"]
    child = ["ชอบกินขนม", "ไปโรงเรียนกับแม่", "สีแดง ไม่เอา สีฟ้า", "แมวกระโดดขึ้นโต๊ะ"]
    body = [
        f"*INV:\t{adult[i % len(adult)]}" if i % 2 == 0 else f"*CHI:\t{child[i % len(child)]}"
        for i in range(lines)
    ]
    return "\n".join(["@Begin", "@Languages:\ttha", "@Participants:\tCHI Target_Child, INV Investigator", *body, "@End", ""])


def test_filling_restores_self_sizing_columns(qtbot):
    table = QTableWidget(0, 3)
    qtbot.addWidget(table)
    header = table.horizontalHeader()
    header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
    header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
    table.show()

    with filling(table):
        assert header.sectionResizeMode(0) == QHeaderView.ResizeMode.Interactive
        table.setRowCount(3)
        for row in range(3):
            table.setItem(row, 0, QTableWidgetItem("a much longer cell than the header" if row == 2 else "x"))

    assert header.sectionResizeMode(0) == QHeaderView.ResizeMode.ResizeToContents
    assert header.sectionResizeMode(1) == QHeaderView.ResizeMode.Stretch
    assert table.updatesEnabled()
    assert header.sectionSize(0) >= table.fontMetrics().horizontalAdvance("a much longer cell than the header")


def test_a_500_line_transcript_opens_and_saves_quickly(window):
    case, session = _case_with_session(window)
    window.service.import_transcript_text(session.session_id, _long_chat(500))
    window.open_case(case.case_id, session.session_id)
    window.tabs.setCurrentIndex(1)
    review = window.pages[1]
    assert review.table.rowCount() == 500

    started = time.perf_counter()
    review.refresh()
    review.dirty = True
    assert review.save()
    elapsed = time.perf_counter() - started

    # Each cell used to re-measure its whole column: about 13 s for these two steps.
    assert elapsed < 2.0, f"refresh and save took {elapsed:.1f} s"


def test_report_preview_waits_until_its_tab_is_shown(window, qtbot):
    case, session = _analysed_session(window)
    window.service.draft_report(session.session_id)
    window.open_case(case.case_id, session.session_id)
    window.tabs.setCurrentIndex(1)
    report = window.pages[3]
    report.refresh()

    assert not report.isVisible()
    assert report._preview_stale
    assert report.preview.pages == 0 or not report.preview.markdown

    window.tabs.setCurrentIndex(3)
    qtbot.waitUntil(lambda: report.preview.pages > 0, timeout=5000)
    assert not report._preview_stale


def test_thai_dictionary_can_load_ahead_of_use():
    from packages.cha.clan_words import _segment_thai, warm_up

    warm_up()
    assert _segment_thai("ชอบกินขนม") == ("ชอบ", "กิน", "ขนม")


def test_the_line_being_played_is_marked_and_kept_in_view(window, qtbot, monkeypatch):
    case, session = _case_with_session(window)
    window.service.import_transcript_text(session.session_id, _long_chat(200))
    window.open_case(case.case_id, session.session_id)
    window.tabs.setCurrentIndex(1)
    review = window.pages[1]
    for row, utt in enumerate(review.utterances):  # imported text has no times; give each line two seconds
        utt.start_ms, utt.end_ms = row * 2000, row * 2000 + 1500
    review.table.selectRow(0)

    monkeypatch.setattr(review.player, "position", lambda: 301.0)  # line 151 (index 150)
    review._update_playhead()

    table = review.table
    assert review.row_at(301.0) == 150
    assert table.playing_row == 150
    assert table.viewport().rect().contains(table.visualItemRect(table.item(150, 2)))
    assert review._selected_rows() == [0]  # playing does not move the selection
    assert table.verticalHeaderItem(150).text() == "▶"

    assert review.row_at(301.8) is None  # the pause after a line marks nothing
    monkeypatch.setattr(review.player, "position", lambda: None)  # playback ended
    review._update_playhead()
    assert table.playing_row is None
    assert table.verticalHeaderItem(150) is None  # its line number is back
