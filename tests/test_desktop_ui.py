"""The desktop window drives the workflow end to end (offscreen, no audio)."""

from __future__ import annotations

from datetime import date
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from PySide6.QtCore import Qt  # noqa: E402
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


def test_empty_window_opens_on_home(window):
    assert window.editor_area.current_key() == "home"
    assert window.current_editor is window.dashboard
    assert window.case_list.topLevelItemCount() == 0


def test_window_is_a_workbench_with_activity_bar_side_bar_and_status_bar(window):
    assert window.activity.width() == 48
    assert set(window.activity.views) == {"cases", "knowledge"}
    assert window.activity.views["cases"].isChecked() and window.side_bar.isVisible()
    window._on_activity_view("cases")  # the shown view again hides the side bar
    assert not window.side_bar.isVisible() and not window.activity.views["cases"].isChecked()
    window.toggle_side_bar()
    assert window.side_bar.isVisible()
    assert window.statusBar().maximumHeight() == 22


def test_pending_consent_blocks_sessions(window):
    case = window.service.create_case("TH-011", 40)
    window.reload_cases(case.case_id)
    window.open_case(case.case_id)
    editor = window.case_editor
    assert editor is not None and not editor.new_session_btn.isEnabled()
    assert editor.stack.currentWidget() is editor.no_session
    assert "ความยินยอม" in editor.no_session.title.text()


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
    assert window.steps_done[3]


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
    assert window.case_editor is not None and window.session is None
    assert window.overview.table.rowCount() == 2
    assert window.overview.cards["sessions"].value.text() == "2"
    window.overview.open_session.emit(second.session_id)
    assert window.session.session_id == second.session_id
    # The first session's tab (opened by the helper) stays open beside the second.
    assert {f"session:{first.session_id}", f"session:{second.session_id}", f"case:{case.case_id}"} <= set(window.editor_area.keys())
    window.open_case_editor(case.case_id)
    assert window.session is None and window.case_editor is not None


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


def test_lines_that_may_have_no_speech_are_marked_until_reviewed(window):
    from packages.desktop.ui import theme
    from packages.desktop.ui.pages.review import COL_TEXT

    _case_with_session(window)
    capture = window.pages[0]
    capture.paste.setPlainText(CHAT)
    capture.paste_btn.click()
    review = window.pages[1]
    note = "อาจไม่มีเสียงพูด: โมเดลให้โอกาส 86% ว่าช่วงนี้ไม่มีคนพูด"
    review.utterances[0] = review.utterances[0].model_copy(update={"notes": note, "review_status": "draft"})
    review._fill_table()
    review._update_status()
    item = review.table.item(0, COL_TEXT)
    assert item.toolTip() == note
    assert item.background().color().name().lower() == theme.ATTENTION_SOFT.lower()
    assert "อาจไม่มีคนพูด 1" in review.summary.text()
    assert "ไม่แน่ใจว่ามีคนพูด" in review.notice.text()
    review.table.selectRow(0)
    review.set_speaker("CHI")
    assert "อาจไม่มีคนพูด" not in review.summary.text()
    assert review.table.item(0, COL_TEXT).toolTip() == ""


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
    assert labels.clinic_speaker_text(adopted).startswith("ใช้อยู่ เรียนจาก 6 session (เด็ก 4 คน)")
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
    rows = [empty._steps.layout().itemAt(i).widget() for i in range(empty._steps.layout().count())]
    assert [r.text()[0] for r in rows] == ["1", "2", "3", "4"]
    assert [r.property("state") for r in rows] == ["done", "current", "todo", "todo"]

    chart = TrendChart()
    qtbot.addWidget(chart)
    chart.set_series("MLU-w", [("1", 2.5), ("2", 3.0)], samples=[12, 64], min_sample=50)
    assert chart._short(0) and not chart._short(1)
    assert _nice_ceiling(3.3) == 5 and _nice_ceiling(0.92) == 1 and _nice_ceiling(23) == 25


def test_home_lists_waiting_work_and_opens_it(window):
    case, session = _case_with_session(window)
    window.show_home()
    dashboard = window.dashboard
    assert window.current_editor is dashboard and window.home_btn.isChecked()
    assert dashboard.queue.rowCount() == 1 and "เพิ่มเสียง" in dashboard.queue.item(0, 2).text()
    dashboard._open_row(0, 0)
    assert window.case.case_id == case.case_id and window.session.session_id == session.session_id


def test_knowledge_opens_every_topic_with_its_charts(window):
    from packages.desktop.ui.pages import knowledge

    window.show_knowledge("autism")
    page = window.knowledge
    assert window.current_editor is page and page.topics.currentItem().data(0x0100) == "autism"
    assert window.side_view == "knowledge"
    for row in range(page.topics.count()):
        page.topics.setCurrentRow(row)
        assert page.article.toPlainText().strip()
    assert not knowledge.age_chart("mlu_words", "MLU").isNull()
    assert not knowledge.screening_chart().isNull() and not knowledge.boundary_weights_chart().isNull()


def _analysed_session(window):
    case, session = _case_with_session(window)
    svc = window.service
    svc.import_transcript_text(session.session_id, CHAT)
    svc.attest(svc.get_transcript(session.session_id).transcript_id, override_reason="ตรวจแล้ว")
    svc.analyze(session.session_id)
    return case, session


def test_english_report_has_the_thai_sections_and_signs_once(window):
    _, session = _analysed_session(window)
    svc = window.service
    report = svc.draft_report(session.session_id, language="en")
    assert report.markdown.startswith("# Language Sample Review Report")
    assert svc.report_language(report) == "en"
    assert "## Therapist sign-off" in report.markdown and "Export Timestamp" not in report.markdown
    assert "| Mean length of utterance (MLU-w, words) |" in report.markdown

    signed = svc.sign_off(report.report_id)
    assert "- Signed by: นักบำบัด ทดสอบ" in signed.markdown
    assert "- Status: signed" in signed.markdown and "(Thailand time)" in signed.markdown
    assert "Awaiting therapist review" not in signed.markdown

    # A redraft keeps the report's language unless another is asked for.
    assert svc.report_language(svc.draft_report(session.session_id)) == "en"
    assert svc.report_language(svc.draft_report(session.session_id, language="th")) == "th"


def test_formal_pdf_layout_in_both_languages(window, tmp_path):
    from datetime import datetime, timezone

    from PySide6.QtGui import QPdfWriter

    from packages.desktop.ui.pdf import (
        FALLBACK_SCALE, THAI_IN_LATIN, ZERO_WIDTH_SPACE, ReportMeta, a4_layout, breakable, build_document, formal_date, LAYOUTS,
        write_report_pdf,
    )
    from PySide6.QtCore import QRectF, QUrl
    from PySide6.QtGui import QTextDocument

    assert formal_date("2026-10-02", "th") == "2 ตุลาคม 2569"
    assert formal_date("2026-10-02", "en") == "2 October 2026"
    assert formal_date(datetime(2026, 10, 18, 7, 5, tzinfo=timezone.utc), "th", with_time=True) == "18 ตุลาคม 2569 เวลา 14:05 น."
    assert ZERO_WIDTH_SPACE in breakable("รายงานการทบทวนตัวอย่างภาษา")
    assert breakable("Child words").count(ZERO_WIDTH_SPACE) == 0

    _, session = _analysed_session(window)
    svc = window.service
    for language in ("th", "en"):
        report = svc.sign_off(svc.draft_report(session.session_id, language=language).report_id)
        meta = ReportMeta(organization="Clinic", child_code="TH-010", session_date="2026-10-15",
                          signed_by=report.signed_by, signed_at=report.signed_at)
        pdf = write_report_pdf(report.markdown, tmp_path / f"{language}.pdf", meta)
        assert pdf.read_bytes().startswith(b"%PDF")

        writer = QPdfWriter(str(tmp_path / "probe.pdf"))
        writer.setPageLayout(a4_layout())
        page = QRectF(0, 0, writer.width(), writer.height())
        document, headings, signature = build_document(writer, report.markdown, meta, LAYOUTS[language], page,
                                                       page.adjusted(100, 100, -100, -100), language)
        text = document.toPlainText().replace(ZERO_WIDTH_SPACE, "")
        # Numbered sections, the details as a table, one signature block and no system sign-off lines.
        assert ("1. ข้อมูล session" if language == "th" else "1. Session details") in text
        assert len(headings) == 8 and signature is not None
        assert ("ลงนามโดย:" if language == "th" else "Signed by:") not in text
        assert report.signed_by in text
        assert ("ลงนามอิเล็กทรอนิกส์" if language == "th" else "Signed electronically") in text
        assert document.pageCount() >= 1
        # Only the layout's sizes appear (Thai inside an English report is scaled to match Times).
        layout = LAYOUTS[language]
        allowed = {layout.title_pt, layout.organization_pt, layout.body_pt, layout.small_pt}
        allowed |= {round(size * factor, 3) for size in allowed for factor in (THAI_IN_LATIN, FALLBACK_SCALE)}
        sizes = set()
        block = document.begin()
        while block.isValid():
            it = block.begin()
            while not it.atEnd():
                fragment = it.fragment()
                if fragment.isValid() and fragment.text().strip(ZERO_WIDTH_SPACE + "\ufffc "):
                    sizes.add(round(fragment.charFormat().font().pointSizeF(), 3))
                it += 1
            block = block.next()
        assert sizes <= allowed, sizes
        assert not document.resource(QTextDocument.ResourceType.ImageResource, QUrl("pasascope-logo")) is None
    assert "TimesNewRoman" in (tmp_path / "en.pdf").read_bytes().decode("latin-1")
    assert "THSarabun" in (tmp_path / "th.pdf").read_bytes().decode("latin-1")


def test_report_page_previews_pages_and_switches_language(window, qtbot):
    case, session = _analysed_session(window)
    window.service.set_organization("คลินิกทดสอบ")
    window.service.draft_report(session.session_id)
    window.open_case(case.case_id, session.session_id)
    window.tabs.setCurrentIndex(3)
    page = window.pages[3]
    page.refresh()
    assert page.language_box.currentData() == "th"
    page.preview.view.updatePreview()
    qtbot.waitUntil(lambda: page.preview.pages > 0, timeout=5000)
    assert page.report_meta().organization == "คลินิกทดสอบ"
    assert not page.report_meta().signed

    page.language_box.setCurrentIndex(page.language_box.findData("en"))
    page._change_language(page.language_box.currentIndex())
    page.refresh()
    assert window.service.get_report(session.session_id).markdown.startswith("# Language Sample Review Report")
    assert page.language_box.currentData() == "en"


def test_report_form_fields_round_trip_through_the_markdown():
    from packages.desktop.ui.report_form import GOALS, INTERPRETATION, RECOMMENDATIONS, read_field, write_field

    markdown = (
        "# รายงานการทบทวนตัวอย่างภาษา\n\n## การแปลผลของนักบำบัด\n"
        "- (นักบำบัดเขียนการแปลผลและข้อสังเกตจากการบำบัดที่นี่ ก่อนลงนาม)\n\n"
        "## เป้าหมายการบำบัด\n- ยังไม่ได้บันทึกเป้าหมายการบำบัดของเคสนี้\n\n"
        "## ข้อจำกัด\nข้อความ\n\n## การลงนามของนักบำบัด\nรอนักบำบัดแก้ไขและลงนาม\n"
    )
    assert read_field(markdown, INTERPRETATION) == "" and read_field(markdown, GOALS) == ""
    filled = write_field(markdown, INTERPRETATION, "ย่อหน้าหนึ่ง\n\nย่อหน้าสอง")
    filled = write_field(filled, GOALS, "พูด 2 คำ\nชี้ขอของ")
    filled = write_field(filled, RECOMMENDATIONS, "อ่านนิทานทุกวัน")
    assert read_field(filled, INTERPRETATION) == "ย่อหน้าหนึ่ง\n\nย่อหน้าสอง"
    assert read_field(filled, GOALS) == "พูด 2 คำ\nชี้ขอของ"
    assert "## เป้าหมายการบำบัด\n- พูด 2 คำ\n- ชี้ขอของ" in filled
    # A new section goes before the limitations; emptying it removes it, emptying a template field restores its placeholder.
    assert filled.index("## ข้อเสนอแนะ") < filled.index("## ข้อจำกัด")
    assert "## ข้อเสนอแนะ" not in write_field(filled, RECOMMENDATIONS, "")
    assert "- ยังไม่ได้บันทึกเป้าหมายการบำบัดของเคสนี้" in write_field(filled, GOALS, "")
    assert "\n\n\n" not in filled


def test_report_form_writes_the_report_and_previews_its_page(window, qtbot):
    case, session = _analysed_session(window)
    window.service.draft_report(session.session_id)
    window.open_case(case.case_id, session.session_id)
    window.tabs.setCurrentIndex(3)
    page = window.pages[3]
    page.refresh()
    assert page.edit_tabs.currentWidget() is page.form

    page.form.boxes["interpretation"].setPlainText("เด็กตอบคำถามง่าย ๆ ได้")
    page.form.boxes["recommendations"].setPlainText("อ่านนิทานวันละ 10 นาที")
    assert page.dirty
    text = page.editor.toPlainText()
    assert "## การแปลผลของนักบำบัด\nเด็กตอบคำถามง่าย ๆ ได้" in text and "## ข้อเสนอแนะ\n- อ่านนิทานวันละ 10 นาที" in text
    qtbot.waitUntil(lambda: "ข้อเสนอแนะ" in page.preview.outline, timeout=5000)
    assert page.preview.view.currentPage() == page.preview.outline["ข้อเสนอแนะ"]

    page.form.organization.setText("คลินิกทดสอบ")
    assert page.report_meta().organization == "คลินิกทดสอบ"
    page.form.organization.editingFinished.emit()
    assert window.service.organization == "คลินิกทดสอบ"

    assert page.save()
    saved = window.service.get_report(session.session_id).markdown
    assert "อ่านนิทานวันละ 10 นาที" in saved
    # Editing the whole report shows up in the form when it is opened again.
    page.edit_tabs.setCurrentWidget(page.editor)
    page.editor.setPlainText(page.editor.toPlainText().replace("อ่านนิทานวันละ 10 นาที", "เล่นบทบาทสมมติ"))
    page.edit_tabs.setCurrentWidget(page.form)
    assert page.form.boxes["recommendations"].toPlainText() == "เล่นบทบาทสมมติ"


def test_report_pages_keep_tables_whole_and_the_signature_with_the_text(window, tmp_path):
    from PySide6.QtGui import QPdfWriter

    from packages.desktop.ui.pdf import ReportMeta, a4_layout, paint_report
    from packages.desktop.ui.report_form import INTERPRETATION, RECOMMENDATIONS, write_field

    _, session = _analysed_session(window)
    svc = window.service
    for language in ("th", "en"):
        markdown = svc.draft_report(session.session_id, language=language).markdown
        # Longer therapist text moves the page breaks about; the rules must hold every time.
        for extra in range(0, 12, 3):
            text = write_field(markdown, INTERPRETATION, "\n\n".join(["ข้อสังเกตจากการบำบัด " * 12] * extra) or "สั้น")
            text = write_field(text, RECOMMENDATIONS, "ข้อหนึ่ง\nข้อสอง")
            writer = QPdfWriter(str(tmp_path / f"{language}{extra}.pdf"))
            writer.setPageLayout(a4_layout())
            outline: dict = {}
            pages = paint_report(writer, text, ReportMeta(organization="คลินิก", child_code="TH-010"), outline=outline)
            assert all(first == last for first, last in outline["__tables__"]), (language, extra, outline["__tables__"])
            first, last, before = outline["__signature__"]
            assert first == last == before == pages, (language, extra, outline["__signature__"], pages)


def test_findings_show_main_measures_and_open_their_guide(window, qtbot):
    from packages.desktop.ui import labels
    from packages.desktop.ui.feature_guide import GUIDE, MAIN, guide_html

    # Every measure the app computes has a guide entry; the main ones match the Findings tab's core set.
    from app.services.providers.basic_provider import BasicFeatureProvider

    computed = {d.feature_name for d in BasicFeatureProvider().get_feature_definitions()} - {"total_utterance_count"}
    assert computed <= set(GUIDE), computed - set(GUIDE)
    assert {name for name, entry in GUIDE.items() if entry[0] == MAIN} == labels.CORE_FEATURES
    assert "feature-child_response_rate" in guide_html()

    case, session = _analysed_session(window)
    window.open_case(case.case_id, session.session_id)
    window.tabs.setCurrentIndex(2)
    page = window.pages[2]
    page.refresh()

    def shown() -> set[str]:
        names = set()
        for row in range(page.table.rowCount()):
            item = page.table.item(row, 0)
            if item is not None and item.data(Qt.ItemDataRole.UserRole):
                names.add(item.data(Qt.ItemDataRole.UserRole))
        return names

    assert shown() <= labels.CORE_FEATURES and "child_response_rate" in shown()
    page.show_all.setChecked(True)
    assert "mlt_ratio" in shown() and "type_token_ratio" in shown()

    row = next(r for r in range(page.table.rowCount())
               if page.table.item(r, 0) and page.table.item(r, 0).data(Qt.ItemDataRole.UserRole) == "child_response_rate")
    page.table.cellDoubleClicked.emit(row, 0)
    assert window.editor_area.current_key() == "knowledge"
    assert window.knowledge.topics.currentItem().data(Qt.ItemDataRole.UserRole) == "measures"


def test_therapist_name_changes_from_the_sidebar_and_the_report(window, qtbot, monkeypatch):
    from packages.desktop.ui import dialogs

    names = iter(["กานดา ใจดี", "Kanda & Co"])

    def answer(dialog):
        dialog.name.setText(next(names))
        return True

    monkeypatch.setattr(dialogs.TherapistDialog, "exec", answer)
    assert window.therapist_label.text() == "นักบำบัด ทดสอบ"
    qtbot.mouseClick(window.therapist_btn, Qt.MouseButton.LeftButton)
    assert window.service.therapist_name == "กานดา ใจดี"
    assert window.therapist_label.text() == "กานดา ใจดี" and "กานดา ใจดี" in window.name_label.text()

    # The report's signer line opens the same dialog and shows the new name.
    _case_with_session(window)
    window.pages[3].form.signer.linkActivated.emit("name")
    assert window.service.therapist_name == "Kanda & Co"
    assert "Kanda &amp; Co" in window.pages[3].form.signer.text()
    assert window.therapist_label.text() == "Kanda & Co"


def test_cases_and_sessions_can_be_edited_and_deleted_from_their_menus(window, qtbot, monkeypatch):
    from packages.desktop.ui import dialogs

    case, session = _case_with_session(window)
    window.service.import_transcript_text(session.session_id, CHAT)

    labels_of = lambda menu: [action.text() for action in menu.actions() if action.text()]  # noqa: E731
    menu = window._case_menu(case.case_id)
    assert labels_of(menu)[:3] == ["เปิดเคส", "Session ใหม่…", "แก้ไขข้อมูลเคส…"]
    assert any("ลบเคส" in text or "Delete case" in text for text in labels_of(menu))

    def edit(dialog):
        dialog.nickname.setText("ภูมิใจ")
        return True
    monkeypatch.setattr(dialogs.EditCaseDialog, "exec", edit)
    window.edit_case(case.case_id)
    assert "ภูมิใจ" in window.session_editor.crumbs.parts[0].text()
    assert "ภูมิใจ" in window.case_list.topLevelItem(0).text(0)

    # Deleting a session asks first; its tab closes.
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: QMessageBox.StandardButton.Yes)
    window.delete_session(session.session_id)
    assert window.session is None and window.service.list_sessions(case.case_id) == []
    assert f"session:{session.session_id}" not in window.editor_area.keys()

    # The delete button stays off until the code is typed.
    def confirm(dialog):
        ok = dialog.buttons.button(dialog.buttons.StandardButton.Ok)
        assert not ok.isEnabled()
        dialog.typed.setText(case.child_code)
        assert ok.isEnabled()
        return True
    monkeypatch.setattr(dialogs.DeleteCaseDialog, "exec", confirm)
    window.delete_case(case.case_id)
    assert window.case is None and window.case_list.topLevelItemCount() == 0
    assert window.editor_area.current_key() == "home"
