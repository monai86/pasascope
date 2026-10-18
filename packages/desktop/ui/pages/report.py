"""Step 4: draft the session report, edit it, sign it, export it."""

from __future__ import annotations

from packages.desktop.core.i18n import report_language, tr

from datetime import datetime
from html import escape
from pathlib import Path
import tempfile

from PySide6.QtCore import Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtPrintSupport import QPrinter, QPrintPreviewWidget
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QLineEdit,
    QScrollArea,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from packages.desktop.ui import theme
from packages.desktop.ui.pages.base import SessionPage
from packages.desktop.ui.pdf import ReportMeta, a4_layout, ensure_fonts, paint_report, write_report_pdf
from packages.desktop.ui.report_form import FIELDS, GOALS, INTERPRETATION, RECOMMENDATIONS, read_field, write_field
from packages.desktop.ui.widgets import EmptyState, button, chip, label, set_chip

REPORT_LANGUAGES = [("en", "English"), ("th", "ไทย")]

EXPORTS = [
    ("pdf", "PDF", "PDF (*.pdf)", ".pdf"),
    ("html", "HTML", "HTML (*.html)", ".html"),
    ("markdown", "Markdown", "Markdown (*.md)", ".md"),
]


def form_text() -> dict[str, tuple[str, str, str]]:
    """(title, hint, example) of each form field, in the interface language."""
    return {
    INTERPRETATION.key: (
        tr("การแปลผลของนักบำบัด", "Therapist's interpretation"),
        tr("สิ่งที่สังเกตได้ในการบำบัดครั้งนี้และความหมายทางคลินิก เขียนเป็นย่อหน้า เว้นบรรทัดเพื่อขึ้นย่อหน้าใหม่",
           "What you observed in this session and what it means clinically. Leave a blank line between paragraphs."),
        tr("เช่น เด็กเล่นของเล่นร่วมกับผู้ปกครองได้ดี ตอบคำถามง่าย ๆ ได้ ...", "e.g. Played well alongside the parent and answered simple questions ..."),
    ),
    GOALS.key: (
        tr("เป้าหมายการบำบัด", "Therapy goals"),
        tr("หนึ่งบรรทัดต่อหนึ่งเป้าหมาย", "One goal per line."),
        tr("เช่น พูดประโยค 2–3 คำเพื่อขอสิ่งของ", "e.g. Uses 2–3 word phrases to request objects"),
    ),
    RECOMMENDATIONS.key: (
        tr("ข้อเสนอแนะ", "Recommendations"),
        tr("หนึ่งบรรทัดต่อหนึ่งข้อ จะเป็นหัวข้อใหม่ในรายงานเมื่อกรอก", "One per line. Adds a section to the report when filled in."),
        tr("เช่น ผู้ปกครองอ่านนิทานร่วมกับเด็กวันละ 10 นาที", "e.g. Caregiver shares a picture book with the child for 10 minutes a day"),
    ),
    }


class ReportForm(QScrollArea):
    """The parts of the report the therapist writes, as plain fields."""

    field_changed = Signal(object, str)  # Field, text
    organization_changed = Signal(str)
    organization_done = Signal(str)
    change_signer = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.Shape.NoFrame)
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(2, 10, 10, 10)
        layout.setSpacing(6)
        self._loading = False

        layout.addWidget(label(tr("ชื่อหน่วยงาน (หัวกระดาษ)", "Clinic name (letterhead)"), "SectionTitle"))
        self.organization = QLineEdit()
        self.organization.setPlaceholderText(tr("เช่น คลินิกแก้ไขการพูด โรงพยาบาล...", "e.g. Speech Clinic, ... Hospital"))
        self.organization.textChanged.connect(lambda text: None if self._loading else self.organization_changed.emit(text))
        self.organization.editingFinished.connect(lambda: self.organization_done.emit(self.organization.text()))
        layout.addWidget(self.organization)
        self.signer = label("", "Hint", wrap=True)
        self.signer.setTextFormat(Qt.TextFormat.RichText)
        self.signer.linkActivated.connect(lambda _: self.change_signer.emit())
        layout.addWidget(self.signer)

        self.boxes: dict[str, QPlainTextEdit] = {}
        for field in FIELDS:
            title, hint, example = form_text()[field.key]
            layout.addSpacing(10)
            layout.addWidget(label(title, "SectionTitle"))
            layout.addWidget(label(hint, "Hint", wrap=True))
            box = QPlainTextEdit()
            box.setPlaceholderText(example)
            box.setMinimumHeight(120 if field.kind == "text" else 90)
            box.setStyleSheet("font-family: 'Sarabun'; font-size: 15px;")
            box.textChanged.connect(lambda f=field, b=box: None if self._loading else self.field_changed.emit(f, b.toPlainText()))
            layout.addWidget(box)
            self.boxes[field.key] = box
        layout.addSpacing(8)
        layout.addWidget(label(tr("ตัวชี้วัด cue และข้อจำกัด ระบบเติมจากข้อมูลของ session แก้เพิ่มได้ในแท็บ ‘ทั้งฉบับ’",
                                  "Measures, cues and limitations come from the session's data; edit them in the ‘Whole report’ tab."),
                               "Hint", wrap=True))
        layout.addStretch(1)
        self.setWidget(inner)

    def load(self, markdown: str, organization: str, signer: str) -> None:
        """Show the report's current text without sending change signals."""
        self._loading = True
        if self.organization.text() != organization:
            self.organization.setText(organization)
        for field in FIELDS:
            text = read_field(markdown, field)
            box = self.boxes[field.key]
            if box.toPlainText() != text:
                box.setPlainText(text)
        self.set_signer(signer)
        self._loading = False

    def set_signer(self, signer: str) -> None:
        if signer:
            self.signer.setText(tr(f"ผู้ลงนาม: {escape(signer)} · <a href='name'>เปลี่ยนชื่อ</a>",
                                   f"Signed by: {escape(signer)} · <a href='name'>Change</a>"))
        else:
            self.signer.setText(tr("ยังไม่ได้ตั้งชื่อผู้ลงนาม · <a href='name'>ตั้งชื่อ</a>",
                                   "No signer name yet · <a href='name'>Set the name</a>"))


class PagePreview(QWidget):
    """The report as printed A4 pages, drawn by the same code that writes the PDF."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.markdown = ""
        self.meta = ReportMeta()
        self.pages = 0
        self.outline: dict[str, int] = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        bar = QHBoxLayout()
        bar.addWidget(label(tr("ตัวอย่างก่อนพิมพ์ (A4)", "Print preview (A4)"), "Muted"))
        self.page_count = label("", "Hint")
        bar.addWidget(self.page_count)
        bar.addStretch(1)
        self.fit_width_btn = button(tr("พอดีความกว้าง", "Fit width"), "ghost")
        self.fit_page_btn = button(tr("ทั้งหน้า", "Whole page"), "ghost")
        self.zoom_out_btn = button("−", "ghost", tooltip=tr("ย่อ", "Zoom out"))
        self.zoom_in_btn = button("+", "ghost", tooltip=tr("ขยาย", "Zoom in"))
        self.open_btn = button(tr("เปิดเป็น PDF", "Open as PDF"), tooltip=tr("เปิดในโปรแกรมดู PDF ของเครื่อง", "Open in this computer's PDF viewer"))
        for widget in (self.fit_width_btn, self.fit_page_btn, self.zoom_out_btn, self.zoom_in_btn, self.open_btn):
            bar.addWidget(widget)
        layout.addLayout(bar)

        self.printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        self.printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        self.printer.setFullPage(True)
        self.printer.setPageLayout(a4_layout())
        self.view = QPrintPreviewWidget(self.printer, self)
        self.view.setViewMode(QPrintPreviewWidget.ViewMode.SinglePageView)
        self.view.paintRequested.connect(self._paint)
        layout.addWidget(self.view, 1)

        self.fit_width_btn.clicked.connect(self.view.fitToWidth)
        self.fit_page_btn.clicked.connect(self.view.fitInView)
        self.zoom_out_btn.clicked.connect(lambda: self.view.zoomOut())
        self.zoom_in_btn.clicked.connect(lambda: self.view.zoomIn())
        self.view.setZoomMode(QPrintPreviewWidget.ZoomMode.FitToWidth)
        self.view.setStyleSheet(f"background: {theme.SIDEBAR};")

    def show_report(self, markdown: str, meta: ReportMeta, focus: str | None = None) -> None:
        """Redraw the pages; with ``focus`` (a section heading), show the page that section starts on."""
        self.markdown, self.meta = markdown, meta
        self.view.updatePreview()
        if focus and focus in self.outline:
            self.view.setCurrentPage(self.outline[focus])

    def _paint(self, printer: QPrinter) -> None:
        if not self.markdown:
            return
        self.outline = {}
        self.pages = paint_report(printer, self.markdown, self.meta, outline=self.outline)
        self.page_count.setText(tr(f"{self.pages} หน้า", f"{self.pages} page{'s' if self.pages != 1 else ''}"))


class ReportPage(SessionPage):
    def __init__(self, service, runner, parent=None) -> None:
        super().__init__(service, runner, parent)
        self.report = None
        self.dirty = False
        self._loading = False
        self._syncing = False
        self._focus_field = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 12, 4, 8)
        layout.setSpacing(10)

        self.empty = EmptyState("", "")
        self.empty_btn = button("", "primary")
        self.empty_btn.clicked.connect(self._empty_action)
        self.empty.actions.addWidget(self.empty_btn)
        layout.addWidget(self.empty)
        self._empty_target = 0

        self.body = QWidget()
        body = QVBoxLayout(self.body)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(10)
        layout.addWidget(self.body)

        top = QHBoxLayout()
        self.status_chip = chip("")
        top.addWidget(self.status_chip)
        self.status_text = label("", "Hint")
        top.addWidget(self.status_text)
        top.addStretch(1)
        top.addWidget(label(tr("ภาษาของรายงาน", "Report language"), "Muted"))
        self.language_box = QComboBox()
        for code, name in REPORT_LANGUAGES:
            self.language_box.addItem(name, code)
        self.language_box.setToolTip(tr("เปลี่ยนภาษาจะสร้างร่างใหม่ในภาษานั้น", "Changing the language redrafts the report in that language."))
        self.language_box.activated.connect(self._change_language)
        top.addWidget(self.language_box)
        self.redraft_btn = button(tr("สร้างร่างใหม่", "Redraft"))
        self.redraft_btn.clicked.connect(self._redraft)
        self.save_btn = button(tr("บันทึกการแก้ไข", "Save"), tooltip="Ctrl+S")
        self.save_btn.clicked.connect(self.save)
        self.sign_btn = button(tr("ลงนามรายงาน", "Sign report"), "primary")
        self.sign_btn.clicked.connect(self._sign)
        self.export_btn = button("Export ▾")
        menu = QMenu(self.export_btn)
        for fmt, text, _, _ in EXPORTS:
            menu.addAction(tr(f"รายงานเป็น {text}", f"Report as {text}"), lambda f=fmt: self._export(f))
        menu.addSeparator()
        menu.addAction(tr("Transcript เป็น CHAT (.cha)", "Transcript as CHAT (.cha)"), self._export_cha)
        self.export_btn.setMenu(menu)
        for widget in (self.redraft_btn, self.save_btn, self.sign_btn, self.export_btn):
            top.addWidget(widget)
        body.addLayout(top)

        self.notice = label("", wrap=True)
        self.notice.setStyleSheet(
            f"background: {theme.ATTENTION_SOFT}; color: {theme.ATTENTION}; border-radius: 8px; padding: 8px 12px;"
        )
        self.notice.hide()
        body.addWidget(self.notice)

        split = QSplitter(Qt.Orientation.Horizontal)
        self.edit_tabs = QTabWidget()
        self.edit_tabs.setDocumentMode(True)
        self.form = ReportForm()
        self.form.field_changed.connect(self._form_changed)
        self.form.organization_changed.connect(lambda _: self.preview_timer.start())
        self.form.organization_done.connect(self._save_organization)
        self.form.change_signer.connect(self.ask_name.emit)
        self.edit_tabs.addTab(self.form, tr("กรอกข้อมูล", "Fill in"))
        self.editor = QPlainTextEdit()
        # Sarabun for Thai and Latin alike: a monospace font has no Thai, and the
        # fallback set Thai smaller than the Latin around it.
        ensure_fonts()
        self.editor.setStyleSheet("font-family: 'Sarabun'; font-size: 15px;")
        self.editor.textChanged.connect(self._on_edit)
        self.edit_tabs.addTab(self.editor, tr("ทั้งฉบับ (Markdown)", "Whole report (Markdown)"))
        self.edit_tabs.currentChanged.connect(self._edit_tab_changed)
        editor_box = QWidget()
        editor_layout = QVBoxLayout(editor_box)
        editor_layout.setContentsMargins(0, 0, 6, 0)
        editor_layout.addWidget(self.edit_tabs)
        split.addWidget(editor_box)
        self.preview = PagePreview()
        self.preview.layout().setContentsMargins(6, 0, 0, 0)
        self.preview.open_btn.clicked.connect(self._open_pdf)
        split.addWidget(self.preview)
        split.setSizes([440, 620])
        body.addWidget(split, 1)

        # Laying out the pages takes a moment, so redraw after a short pause in typing.
        self.preview_timer = QTimer(self)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.setInterval(350)
        self.preview_timer.timeout.connect(self._update_preview)

    # ------------------------------------------------------------------
    def refresh(self) -> None:
        if self.session is None:
            return
        self.session = self.service.get_session(self.session.session_id)
        self.report = self.service.get_report(self.session.session_id)
        features = self.service.get_features(self.session.session_id)
        if self.report is None:
            if features is None or self.session.findings_stale:
                self._show_empty(tr("ยังไม่มีตัวชี้วัด", "No findings yet"), tr("วิเคราะห์ transcript ที่รับรองแล้วก่อนทำรายงาน", "Analyse the attested transcript first."), tr("ไปที่ตัวชี้วัด", "Go to Findings"), 2)
            else:
                self._show_empty(tr("ยังไม่มีร่างรายงาน", "No report yet"), tr("ระบบร่างรายงานจากตัวชี้วัดและ cue ของ session นี้ แล้วให้คุณแก้และลงนาม", "Draft a report from this session's findings, then edit and sign it."), tr("สร้างร่างรายงาน", "Draft report"), -1)
            return
        self.empty.hide()
        self.body.show()
        self._loading = True
        self.editor.setPlainText(self.report.markdown)
        self._loading = False
        self.dirty = False
        self.form.load(self.report.markdown, self.service.organization, self.service.therapist_name)
        index = self.language_box.findData(self.service.report_language(self.report))
        self.language_box.setCurrentIndex(max(index, 0))
        self._update_status()
        self._update_preview()

    def _status(self) -> str:
        status = self.report.status
        return status.value if hasattr(status, "value") else str(status)

    def _update_status(self) -> None:
        status = self._status()
        signed = status == "Signed Off"
        stale = status == "stale" or bool(self.session and self.session.report_stale)
        if self.dirty:
            set_chip(self.status_chip, tr("มีการแก้ไขที่ยังไม่บันทึก", "Unsaved changes"), "attention")
        elif stale:
            set_chip(self.status_chip, tr("ต้องสร้างใหม่", "Out of date"), "danger")
        elif signed:
            set_chip(self.status_chip, tr("ลงนามแล้ว", "Signed"), "ok")
        else:
            set_chip(self.status_chip, tr("ร่าง", "Draft"), "attention")
        if signed and self.report.signed_at:
            self.status_text.setText(tr(f"ลงนามโดย {self.report.signed_by} · {self.report.signed_at:%d/%m/%Y %H:%M}", f"Signed by {self.report.signed_by}, {self.report.signed_at:%d/%m/%Y %H:%M}"))
        else:
            self.status_text.setText(tr(f"ฉบับที่ {self.report.revision_number}", f"Revision {self.report.revision_number}"))
        self.save_btn.setEnabled(self.dirty)
        self.sign_btn.setEnabled(not signed and not stale)
        self.export_btn.setEnabled(not stale and not self.dirty)
        notes = []
        if stale:
            notes.append(tr("transcript หรือตัวชี้วัดเปลี่ยนหลังทำรายงานนี้ กด ‘สร้างร่างใหม่’ ก่อนลงนามหรือ export", "The transcript or findings changed after this draft. Redraft before signing or exporting."))
        if self.report.finalization_blocked and self.report.safety_validation_result is not None:
            notes.append(tr("ข้อความบางส่วนไม่ผ่านการตรวจความปลอดภัยของรายงาน (เช่น ถ้อยคำเชิงวินิจฉัย) แก้ก่อนลงนาม", "Some wording failed the report check (diagnostic language, for example). Fix it before signing."))
        if signed and self.dirty:
            notes.append(tr("การแก้รายงานที่ลงนามแล้วจะสร้างฉบับแก้ไขใหม่ที่ต้องลงนามอีกครั้ง", "Editing a signed report creates a new revision to sign."))
        if not signed and not stale:
            notes.append(tr("รายงานยังเป็นร่าง export ได้แต่จะไม่มีลายเซ็น", "Draft: exports will not carry a signature."))
        self.notice.setText("\n".join(notes))
        self.notice.setVisible(bool(notes))

    def report_meta(self, report=None) -> ReportMeta:
        """Page furniture for ``report`` (the page's report): clinic, child, session, signature."""
        report = report or self.report
        signed = report is not None and self._status_of(report) == "Signed Off" and not (report is self.report and self.dirty)
        signed_at = report.signed_at if signed else None
        if isinstance(signed_at, str):
            signed_at = datetime.fromisoformat(signed_at)
        return ReportMeta(
            organization=self.form.organization.text().strip(),
            child_code=self.case.child_code if self.case else "",
            session_date=str(self.session.session_date) if self.session else "",
            signed_by=(report.signed_by or "") if signed else "",
            signed_at=signed_at,
        )

    @staticmethod
    def _status_of(report) -> str:
        status = report.status
        return status.value if hasattr(status, "value") else str(status)

    def _update_preview(self) -> None:
        if self.report is None:
            return
        markdown = self.editor.toPlainText()
        focus = self._focus_field.headings[report_language(markdown)] if self._focus_field else None
        self._focus_field = None
        self.preview.show_report(markdown, self.report_meta(), focus)

    def _form_changed(self, field, value: str) -> None:
        """A form field changed: rewrite its section in the report text (the preview follows)."""
        if self.report is None:
            return
        self._focus_field = field
        markdown = write_field(self.editor.toPlainText(), field, value)
        if markdown != self.editor.toPlainText():
            self._syncing = True
            self.editor.setPlainText(markdown)
            self._syncing = False

    def _edit_tab_changed(self, index: int) -> None:
        if self.edit_tabs.widget(index) is self.form and self.report is not None:
            self.form.load(self.editor.toPlainText(), self.form.organization.text(), self.service.therapist_name)

    def _save_organization(self, name: str) -> None:
        if name.strip() != self.service.organization:
            self.attempt(self.service.set_organization, name, title=tr("ตั้งค่าไม่สำเร็จ", "Setting not saved"))

    def _open_pdf(self) -> None:
        if self.report is None:
            return
        folder = Path(tempfile.mkdtemp(prefix="pasascope-report-"))
        name = f"{self.case.child_code}_{self.session.session_date}.pdf" if self.case else "report.pdf"
        try:
            path = write_report_pdf(self.editor.toPlainText(), folder / name, self.report_meta())
        except OSError as exc:
            self.report_error(exc, tr("สร้างไฟล์ไม่ได้", "Could not create the file"))
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def _change_language(self, _index: int) -> None:
        code = self.language_box.currentData()
        if self.report is None or code == self.service.report_language(self.report):
            return
        answer = QMessageBox.question(
            self, tr("เปลี่ยนภาษาของรายงาน", "Change report language"),
            tr("ระบบจะสร้างร่างใหม่ในภาษาที่เลือก ข้อความที่แก้ไว้ในรายงานนี้จะถูกแทนที่ ดำเนินการต่อ?",
               "The report will be redrafted in the chosen language, replacing your edits. Continue?"),
        )
        if answer != QMessageBox.StandardButton.Yes:
            index = self.language_box.findData(self.service.report_language(self.report))
            self.language_box.setCurrentIndex(max(index, 0))
            return
        self.dirty = False
        if self.attempt(self.service.draft_report, self.session.session_id, language=code,
                        title=tr("สร้างรายงานไม่สำเร็จ", "Report not drafted")) is not None:
            self.changed.emit()

    def has_unsaved_changes(self) -> bool:
        return self.dirty

    def _show_empty(self, title: str, body: str, action: str, target: int) -> None:
        self.body.hide()
        self.empty.show()
        self.empty.set_text(title, body)
        if self.session is not None:
            self.empty.set_steps(self.service.session_step(self.session))
        self.empty_btn.setText(action)
        self._empty_target = target

    def _empty_action(self) -> None:
        if self._empty_target < 0:
            self._draft()
        else:
            self.navigate.emit(self._empty_target)

    def _on_edit(self) -> None:
        if self._loading or self.report is None:
            return
        self.dirty = self.editor.toPlainText() != self.report.markdown
        self.preview_timer.start()
        self._update_status()

    # ------------------------------------------------------------------
    def _draft(self) -> None:
        if self.attempt(self.service.draft_report, self.session.session_id, title=tr("สร้างรายงานไม่สำเร็จ", "Report not drafted")) is not None:
            self.changed.emit()

    def _redraft(self) -> None:
        answer = QMessageBox.question(
            self, tr("สร้างร่างใหม่", "Redraft"), tr("ร่างใหม่จะแทนที่ข้อความที่แก้ไว้ในรายงานนี้ ดำเนินการต่อ?", "Redrafting replaces your edits to this report. Continue?")
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.dirty = False
            self._draft()

    def save(self) -> bool:
        if not self.dirty or self.report is None:
            return True
        updated = self.attempt(self.service.update_report, self.report.report_id, self.editor.toPlainText(), title=tr("บันทึกไม่สำเร็จ", "Not saved"))
        if updated is None:
            return False
        self.dirty = False
        self.changed.emit()
        return True

    def _sign(self) -> None:
        if not self.save():
            return
        if not self.service.therapist_name:
            self.ask_name.emit()
            if not self.service.therapist_name:
                return
        answer = QMessageBox.question(
            self, tr("ลงนามรายงาน", "Sign report"),
            tr(f"ลงนามในชื่อ {self.service.therapist_name}\n\n"
            "ยืนยันว่าได้อ่านและแก้ไขรายงานแล้ว ข้อความเป็นการบรรยายสิ่งที่สังเกต ไม่ใช่การวินิจฉัย "
            "และตัวเลขทั้งหมดมาจาก transcript ที่รับรองแล้ว", f"Sign as {self.service.therapist_name}\n\nI have read and edited this report. It describes what was observed, not a diagnosis, and every number comes from the attested transcript."),
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        report = self.service.get_report(self.session.session_id)
        if self.attempt(self.service.sign_off, report.report_id, title=tr("ลงนามไม่สำเร็จ", "Not signed")) is not None:
            self.changed.emit()

    def _default_path(self, suffix: str) -> str:
        name = f"{self.case.child_code}_{self.session.session_date}{suffix}"
        return str(self.service.workspace.exports_dir / name)

    def _export(self, fmt: str) -> None:
        _, text, file_filter, suffix = next(e for e in EXPORTS if e[0] == fmt)
        path, _ = QFileDialog.getSaveFileName(self, tr(f"Export รายงานเป็น {text}", f"Export report as {text}"), self._default_path(suffix), file_filter)
        if not path:
            return
        report_id = self.report.report_id
        if fmt == "pdf":
            # Qt draws text on the UI thread; a report takes well under a second.
            report = self.attempt(self.service.report_for_export, report_id, title=tr("Export ไม่สำเร็จ", "Export failed"))
            if report is None:
                return
            try:
                written = write_report_pdf(report.markdown, Path(path), self.report_meta(report))
            except OSError as exc:
                self.report_error(exc, tr("บันทึกไฟล์ไม่ได้", "Could not save the file"))
                return
            self.service.record_export(report_id, "pdf")
            self._exported(written)
            return
        written = self.attempt(self.service.export_report, report_id, fmt, Path(path), title=tr("Export ไม่สำเร็จ", "Export failed"))
        if written is not None:
            self._exported(written)

    def _export_cha(self) -> None:
        transcript = self.service.get_transcript(self.session.session_id)
        if transcript is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, tr("Export transcript เป็น CHAT", "Export transcript as CHAT"), self._default_path(".cha"), "CHAT (*.cha)")
        if not path:
            return
        text = self.attempt(self.service.export_cha, transcript.transcript_id, title=tr("Export ไม่สำเร็จ", "Export failed"))
        if text is None:
            return
        Path(path).write_text(text, encoding="utf-8")
        self._exported(Path(path))

    def _exported(self, path: Path) -> None:
        box = QMessageBox(QMessageBox.Icon.Information, tr("Export แล้ว", "Exported"), tr(f"บันทึกไฟล์ที่\n{path}", f"Saved to\n{path}"), parent=self)
        open_btn = box.addButton(tr("เปิดไฟล์", "Open"), QMessageBox.ButtonRole.AcceptRole)
        box.addButton(tr("ปิด", "Close"), QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() is open_btn:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
