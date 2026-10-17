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


def test_report_is_thai_and_exports_to_pdf_and_html(window, tmp_path):
    from packages.desktop.ui.pdf import write_report_pdf

    case, session = _case_with_session(window)
    svc = window.service
    svc.import_transcript_text(session.session_id, CHAT)
    svc.attest(svc.get_transcript(session.session_id).transcript_id, override_reason="ตรวจแล้ว")
    svc.analyze(session.session_id)
    report = svc.draft_report(session.session_id)
    assert report.markdown.startswith("# รายงานการทบทวนตัวอย่างภาษา")
    signed = svc.sign_off(report.report_id)
    assert "- ลงนามโดย: นักบำบัด ทดสอบ" in signed.markdown

    pdf = write_report_pdf(signed.markdown, tmp_path / "r.pdf")
    assert pdf.read_bytes().startswith(b"%PDF") and pdf.stat().st_size > 5000
    html_path = svc.export_report(signed.report_id, "html", tmp_path / "r.html")
    page = html_path.read_text(encoding="utf-8")
    assert '<meta charset="utf-8">' in page and "<table>" in page and "ความยาวประโยคเฉลี่ย" in page


def test_chat_codes_change_the_counted_words(window):
    from packages.desktop.ui.pages.review import COL_TEXT, COL_WORDS, apply_chat_code

    assert apply_chat_code("หนู อยาก หนู อยาก กิน", 0, 8, "[/]")[0] == "<หนู อยาก> [/] หนู อยาก กิน"
    assert apply_chat_code("หนู อยาก กิน", 4, 4, "[: ]") == ("หนู อยาก [: ] กิน", 12)
    assert apply_chat_code("อือ หนู กิน", 0, 3, "&-")[0] == "&-อือ หนู กิน"

    case, session = _case_with_session(window)
    capture = window.pages[0]
    capture.paste.setPlainText(CHAT)
    capture.paste_btn.click()
    review = window.pages[1]
    row = next(i for i, u in enumerate(review.utterances) if str(u.speaker) == "CHI")
    review.table.item(row, COL_TEXT).setText("&-อือ <หนู อยาก> [/] หนู อยาก กิน")
    assert review.table.item(row, COL_WORDS).text() == "3"
    assert "หนู อยาก" in review.table.item(row, COL_WORDS).toolTip()
    review.table.item(row, COL_TEXT).setText("xxx กิน")
    assert review.table.item(row, COL_WORDS).text().endswith("MLU")
    assert "MLU" in review.summary.text()


def test_findings_lead_with_headline_values_and_sample_warning(window, qtbot):
    case, session = _case_with_session(window)
    capture = window.pages[0]
    capture.paste.setPlainText(CHAT)
    capture.paste_btn.click()
    window.pages[1].attest_btn.click()
    findings = window.pages[2]
    findings.empty_btn.click()
    qtbot.waitUntil(lambda: findings.body.isVisible(), timeout=10000)
    mlu = findings.metric_cards["mean_length_of_utterance_words"]
    assert mlu.value.text() not in {"", "—"}
    assert "ประโยค" in mlu.detail.text()
    assert not findings.sample_notice.isHidden()  # the sample has far fewer than 50 utterances
    assert findings.schema_notice.isHidden()


def test_case_with_several_sessions_opens_on_the_overview(window, qtbot):
    case, first = _case_with_session(window)
    second = window.service.create_session(case.case_id, date(2026, 10, 20))
    window.open_case(case.case_id)
    assert window.session_pick.currentData() == "__overview__"
    assert window.session_stack.currentWidget() is window.overview
    assert window.overview.table.rowCount() == 2
    assert window.overview.cards["sessions"].value.text() == "2"
    window.overview.open_session.emit(second.session_id)
    assert window.session.session_id == second.session_id
    assert window.session_stack.currentWidget() is window.tabs
    window.session_pick.setCurrentIndex(0)
    assert window.session is None and window.session_stack.currentWidget() is window.overview


def test_backup_from_the_menu_updates_the_reminder(window, qtbot, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QFileDialog

    _case_with_session(window)
    window._update_backup_label()
    assert "สำรองตอนนี้" in window.backup_label.text()
    target = tmp_path / "out" / "backup.zip"
    target.parent.mkdir()
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (str(target), ""))
    window.backup()
    qtbot.waitUntil(lambda: not window.busy, timeout=10000)
    assert target.exists()
    assert "สำรองล่าสุด" in window.backup_label.text() and "สำรองตอนนี้" not in window.backup_label.text()


def test_guessed_speakers_are_marked_until_the_therapist_sets_them(window):
    from packages.desktop.ui.pages.review import COL_SPEAKER

    case, session = _case_with_session(window)
    capture = window.pages[0]
    capture.paste.setPlainText(CHAT)
    capture.paste_btn.click()
    review = window.pages[1]
    review.utterances[0] = review.utterances[0].model_copy(update={"speaker_uncertain": True})
    review._fill_table()
    review._update_status()
    assert review.table.item(0, COL_SPEAKER).text().endswith("?")
    assert "ผู้พูดที่ควรเช็ก 1" in review.summary.text()
    review.table.selectRow(0)
    review.set_speaker("CHI")
    assert review.utterances[0].speaker_uncertain is False
    assert not review.table.item(0, COL_SPEAKER).text().endswith("?")


def test_clinic_speaker_dialog_says_what_is_missing_and_what_is_in_use(window, qtbot):
    from packages.desktop.ui import dialogs, labels

    empty = window.service.clinic_speaker_status()
    assert empty["sessions_needed"] == 4 and not empty["in_use"]
    dialog = dialogs.ClinicSpeakerDialog(empty, window)
    qtbot.addWidget(dialog)
    assert "อีก 4 session" in dialog.status_label.text() and "เด็กอีก 2 คน" in dialog.status_label.text()
    assert not dialog.train_btn.isEnabled() and not dialog.reset_btn.isEnabled()

    adopted = {"trained": True, "adopted": True, "enabled": True, "trained_sessions": 6, "trained_children": 4,
               "model_balanced": 0.93, "frame_balanced": 0.76, "eligible_sessions": 6, "stale": False}
    assert labels.clinic_speaker_text(adopted).startswith("ใช้อยู่ · เรียนจาก 6 session (เด็ก 4 คน)")
    assert "แยกถูกเฉลี่ยเด็กกับผู้ใหญ่ 93% เทียบโมเดลพื้นฐาน 76%" in labels.clinic_speaker_text(adopted)
    kept = dict(adopted, adopted=False, model_balanced=0.85, frame_balanced=0.85, stale=True, eligible_sessions=7)
    assert labels.clinic_speaker_text(kept).startswith("ยังใช้โมเดลพื้นฐาน")
    assert "7 session ยังไม่ได้เรียน" in labels.clinic_speaker_text(kept)


def test_attesting_too_few_sessions_does_not_start_learning(window):
    case, session = _case_with_session(window)
    window.learn_speakers_in_background()
    assert not getattr(window, "_learning_speakers", False) and not window.runner.busy


def test_review_inspector_explains_speaker_boundary_and_counted_words():
    from app.schemas.clinical import Utterance

    from packages.desktop.ui.pages.review import explain_utterance, note_parts

    notes = ("ขึ้นประโยคใหม่ (โอกาส 84%, หยุด 0.9 วินาที): ช่วงหยุด +1.8, คำนี้มักอยู่ท้ายประโยค +0.9 "
             "โมเดลประจำคลินิก: เสียงเด็ก 92% (โมเดลพื้นฐาน 12%)")
    boundary, speaker = note_parts(notes)
    assert boundary.startswith("ขึ้นประโยคใหม่") and "โมเดลประจำคลินิก" not in boundary
    assert speaker.startswith("โมเดลประจำคลินิก")
    utt = Utterance(utterance_id="u1", speaker="CHI", text="<เล่น รถ> [/] เล่น รถ ไหม", start_ms=0, end_ms=900,
                    confidence=0.42, source="asr", notes=notes, speaker_uncertain=True)
    rows = dict(explain_utterance(utt))
    assert "ระบบไม่แน่ใจ" in rows["ผู้พูด"]
    assert rows["ทำไมขึ้นประโยคใหม่ตรงนี้"] == boundary
    assert rows["เหตุผลของโมเดลประจำคลินิก"] == speaker
    assert rows["คำที่นับ"].startswith("นับ 3 คำ")
    assert "ต่ำ" in rows["ความมั่นใจของการถอดเสียง"]


def test_empty_pages_list_the_steps_and_the_chart_marks_short_samples(qtbot):
    from packages.desktop.ui.widgets import EmptyState, TrendChart, _nice_ceiling

    empty = EmptyState("รับรอง transcript ก่อน")
    qtbot.addWidget(empty)
    empty.set_steps(1)
    texts = [empty._steps.layout().itemAt(i).widget().text() for i in range(empty._steps.layout().count())]
    assert len(texts) == 4 and texts[0].startswith("✓") and "ขั้นถัดไป" in texts[1] and texts[3].startswith("○")

    chart = TrendChart()
    qtbot.addWidget(chart)
    chart.set_series("MLU-w", [("1", 2.5), ("2", 3.0)], samples=[12, 64], min_sample=50)
    assert chart._short(0) and not chart._short(1)
    assert _nice_ceiling(3.3) == 5 and _nice_ceiling(0.92) == 1 and _nice_ceiling(23) == 25
