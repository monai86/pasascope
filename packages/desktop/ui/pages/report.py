"""Step 4: draft the session report, edit it, sign it, export it."""

from __future__ import annotations

from packages.desktop.core.i18n import tr

from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QSplitter,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from packages.desktop.ui import theme
from packages.desktop.ui.pages.base import SessionPage
from packages.desktop.ui.pdf import write_report_pdf
from packages.desktop.ui.widgets import EmptyState, button, chip, label, set_chip

EXPORTS = [
    ("pdf", "PDF", "PDF (*.pdf)", ".pdf"),
    ("html", "HTML", "HTML (*.html)", ".html"),
    ("markdown", "Markdown", "Markdown (*.md)", ".md"),
]


class ReportPage(SessionPage):
    def __init__(self, service, runner, parent=None) -> None:
        super().__init__(service, runner, parent)
        self.report = None
        self.dirty = False
        self._loading = False

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
        editor_box = QWidget()
        editor_layout = QVBoxLayout(editor_box)
        editor_layout.setContentsMargins(0, 0, 6, 0)
        editor_layout.addWidget(label(tr("แก้ไข (Markdown)", "Edit (Markdown)"), "Muted"))
        self.editor = QPlainTextEdit()
        self.editor.setStyleSheet("font-family: Menlo, 'SF Mono', monospace; font-size: 13px;")
        self.editor.textChanged.connect(self._on_edit)
        editor_layout.addWidget(self.editor)
        split.addWidget(editor_box)
        preview_box = QWidget()
        preview_layout = QVBoxLayout(preview_box)
        preview_layout.setContentsMargins(6, 0, 0, 0)
        preview_layout.addWidget(label(tr("ตัวอย่าง", "Preview"), "Muted"))
        self.preview = QTextBrowser()
        self.preview.setOpenExternalLinks(False)
        preview_layout.addWidget(self.preview)
        split.addWidget(preview_box)
        split.setSizes([500, 560])
        body.addWidget(split, 1)

        self.preview_timer = QTimer(self)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.setInterval(250)
        self.preview_timer.timeout.connect(lambda: self.preview.setMarkdown(self.editor.toPlainText()))

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
        self.preview.setMarkdown(self.report.markdown)
        self.dirty = False
        self._update_status()

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
            QMessageBox.warning(self, tr("ยังไม่ได้ตั้งชื่อ", "No therapist name"), tr("ตั้งชื่อนักบำบัดก่อน (เมนู ตั้งค่า → ชื่อนักบำบัด)", "Set your name first (Settings, Therapist name)."))
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
                written = write_report_pdf(report.markdown, Path(path), title=f"{self.case.child_code} {self.session.session_date}")
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
