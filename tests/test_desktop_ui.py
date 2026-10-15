"""The desktop window drives the workflow end to end (offscreen, no audio)."""

from __future__ import annotations

from datetime import date
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from PySide6.QtWidgets import QMessageBox  # noqa: E402

from packages.desktop.core import DesktopService, open_workspace  # noqa: E402
from packages.desktop.ui.main_window import MainWindow  # noqa: E402
from tests.test_desktop_service import CHAT  # noqa: E402


@pytest.fixture
def window(qtbot, tmp_path, monkeypatch):
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    service = DesktopService(open_workspace(tmp_path / "ws"))
    service.set_therapist_name("นักบำบัด ทดสอบ")
    win = MainWindow(service)
    qtbot.addWidget(win)
    win.show()
    return win


def _case_with_session(win: MainWindow):
    case = win.service.create_case("TH-010", 50, nickname="ภูมิ")
    win.service.grant_consent(case.case_id, "แม่", date(2026, 10, 1))
    session = win.service.create_session(case.case_id, date(2026, 10, 16))
    win.reload_cases(case.case_id)
    win.open_case(case.case_id, session.session_id)
    return case, session


def test_empty_window_shows_case_prompt(window):
    assert window.stack.currentIndex() == 0
    assert window.case_list.count() == 0


def test_pending_consent_blocks_sessions(window):
    case = window.service.create_case("TH-011", 40)
    window.reload_cases(case.case_id)
    window.open_case(case.case_id)
    assert not window.new_session_btn.isEnabled()
    assert window.session_stack.currentIndex() == 0
    assert "ความยินยอม" in window.no_session.title.text()


def test_text_import_to_signed_report(window, qtbot):
    case, session = _case_with_session(window)
    assert window.tabs.currentIndex() == 0

    capture = window.pages[0]
    capture.paste.setPlainText(CHAT)
    capture.paste_btn.click()
    assert window.tabs.currentIndex() == 1

    review = window.pages[1]
    assert review.table.rowCount() == 8
    review.table.item(1, 2).setText("ชอบกินขนมครับ")
    assert review.dirty and review.save_btn.isEnabled()
    review.attest_btn.click()
    assert window.service.get_transcript(session.session_id).therapist_attested
    assert window.service.get_transcript(session.session_id).utterances[1].text == "ชอบกินขนมครับ"
    assert window.tabs.currentIndex() == 2

    findings = window.pages[2]
    findings.empty_btn.click()
    qtbot.waitUntil(lambda: window.service.get_features(session.session_id) is not None, timeout=10000)
    qtbot.waitUntil(lambda: findings.body.isVisible(), timeout=10000)
    assert findings.table.rowCount() > 5

    window.tabs.setCurrentIndex(3)
    report = window.pages[3]
    report.empty_btn.click()
    assert report.body.isVisible()
    report.editor.appendPlainText("\nหมายเหตุนักบำบัด: เด็กตอบคำถามได้ดีขึ้น")
    assert report.dirty
    report.sign_btn.click()
    signed = window.service.get_report(session.session_id)
    assert signed.signed_by == "นักบำบัด ทดสอบ"
    assert "เด็กตอบคำถามได้ดีขึ้น" in signed.markdown
    assert "✓" in window.tabs.tabText(3)


def test_editing_after_attest_marks_findings_stale(window, qtbot):
    case, session = _case_with_session(window)
    window.service.import_transcript_text(session.session_id, CHAT)
    transcript = window.service.get_transcript(session.session_id)
    window.service.attest(transcript.transcript_id, override_reason="ตรวจแล้ว")
    window.service.analyze(session.session_id)
    window.refresh_session()

    window.tabs.setCurrentIndex(1)
    review = window.pages[1]
    review.table.item(3, 2).setText("ขนมอะไร")
    assert "ยกเลิกการรับรอง" in review.notice.text()
    review.save()
    assert window.service.get_session(session.session_id).findings_stale
    window.tabs.setCurrentIndex(2)
    assert window.pages[2].empty.isVisible()
