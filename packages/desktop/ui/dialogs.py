"""Forms that open over the main window."""

from __future__ import annotations

from packages.desktop.core.i18n import tr

from datetime import date

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from packages.desktop.ui import theme
from packages.desktop.ui.widgets import label

SESSION_TYPES = [
    ("therapy_session", tr("บำบัดตามนัด", "Therapy session")),
    ("assessment", tr("ประเมิน", "Assessment")),
    ("follow_up", tr("ติดตามผล", "Follow-up")),
]


def _qdate(value: date) -> QDate:
    return QDate(value.year, value.month, value.day)


def _pydate(value: QDate) -> date:
    return date(value.year(), value.month(), value.day())


class _Form(QDialog):
    def __init__(self, title: str, parent: QWidget | None = None, ok_text: str | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(460)
        self.outer = QVBoxLayout(self)
        self.outer.setContentsMargins(22, 20, 22, 18)
        self.outer.setSpacing(14)
        heading = label(title, "SectionTitle")
        self.outer.addWidget(heading)
        self.form = QFormLayout()
        self.form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.form.setHorizontalSpacing(14)
        self.form.setVerticalSpacing(10)
        self.outer.addLayout(self.form)
        self.error = QLabel("")
        self.error.setStyleSheet(f"color: {theme.DANGER};")
        self.error.setWordWrap(True)
        self.error.hide()
        self.outer.addWidget(self.error)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        ok = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        ok.setText(ok_text or tr("บันทึก", "Save"))
        ok.setProperty("role", "primary")
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("ยกเลิก", "Cancel"))
        self.buttons.accepted.connect(self._try_accept)
        self.buttons.rejected.connect(self.reject)
        self.outer.addWidget(self.buttons)

    def show_error(self, message: str) -> None:
        self.error.setText(message)
        self.error.show()

    def validate(self) -> str | None:
        return None

    def _try_accept(self) -> None:
        problem = self.validate()
        if problem:
            self.show_error(problem)
            return
        self.accept()


class NewCaseDialog(_Form):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(tr("เพิ่มเคสใหม่", "New case"), parent)
        self.code = QLineEdit()
        self.code.setPlaceholderText(tr("เช่น TH-2026-014 (ห้ามใช้ชื่อจริง)", "For example TH-2026-014 (never a real name)"))
        self.code.setMaxLength(64)
        self.nickname = QLineEdit()
        self.nickname.setPlaceholderText(tr("ไม่บังคับ", "Optional"))
        self.nickname.setMaxLength(120)
        age = QHBoxLayout()
        self.years = QSpinBox()
        self.years.setRange(0, 20)
        self.years.setValue(4)
        self.years.setSuffix(tr(" ปี", " years"))
        self.months = QSpinBox()
        self.months.setRange(0, 11)
        self.months.setSuffix(tr(" เดือน", " months"))
        age.addWidget(self.years)
        age.addWidget(self.months)
        age.addStretch(1)
        self.language = QComboBox()
        self.language.addItems(["Thai", "English", "Thai + English"])
        self.notes = QPlainTextEdit()
        self.notes.setPlaceholderText(tr("ไม่บังคับ", "Optional"))
        self.notes.setFixedHeight(70)
        self.form.addRow(tr("รหัสเด็ก", "Child code"), self.code)
        self.form.addRow(tr("ชื่อเล่น", "Nickname"), self.nickname)
        self.form.addRow(tr("อายุ", "Age"), age)
        self.form.addRow(tr("ภาษาที่ใช้", "Language"), self.language)
        self.form.addRow(tr("หมายเหตุ", "Notes"), self.notes)
        hint = label(tr("ระบบเก็บเฉพาะรหัสและชื่อเล่น ข้อมูลทั้งหมดอยู่ในเครื่องนี้เท่านั้น", "Only a code and a nickname are stored, and only on this computer."), "Muted", wrap=True)
        self.outer.insertWidget(2, hint)

    @property
    def age_months(self) -> int:
        return self.years.value() * 12 + self.months.value()

    def validate(self) -> str | None:
        if not self.code.text().strip():
            return tr("กรุณาใส่รหัสเด็ก", "Enter a child code.")
        return None


class EditCaseDialog(_Form):
    """Nickname, age at intake, language and notes of an existing case; the code cannot change."""

    def __init__(self, case, parent: QWidget | None = None) -> None:
        super().__init__(tr(f"แก้ไขข้อมูลเคส · {case.child_code}", f"Edit case: {case.child_code}"), parent)
        code = QLineEdit(case.child_code)
        code.setEnabled(False)
        code.setToolTip(tr("รหัสเด็กเปลี่ยนไม่ได้ เพราะอยู่ในทุกบันทึกและรายงาน", "The code cannot change: it is on every record and report."))
        self.nickname = QLineEdit(case.nickname or "")
        self.nickname.setPlaceholderText(tr("ไม่บังคับ", "Optional"))
        self.nickname.setMaxLength(120)
        age = QHBoxLayout()
        self.years = QSpinBox()
        self.years.setRange(0, 20)
        self.years.setValue(case.age_months // 12)
        self.years.setSuffix(tr(" ปี", " years"))
        self.months = QSpinBox()
        self.months.setRange(0, 11)
        self.months.setValue(case.age_months % 12)
        self.months.setSuffix(tr(" เดือน", " months"))
        age.addWidget(self.years)
        age.addWidget(self.months)
        age.addStretch(1)
        self.language = QComboBox()
        self.language.setEditable(True)
        self.language.addItems(["Thai", "English", "Thai + English"])
        self.language.setCurrentText(case.language or "Thai")
        self.notes = QPlainTextEdit(case.notes or "")
        self.notes.setFixedHeight(70)
        self.form.addRow(tr("รหัสเด็ก", "Child code"), code)
        self.form.addRow(tr("ชื่อเล่น", "Nickname"), self.nickname)
        self.form.addRow(tr("อายุเมื่อเปิดเคส", "Age at intake"), age)
        self.form.addRow(tr("ภาษาที่ใช้", "Language"), self.language)
        self.form.addRow(tr("หมายเหตุ", "Notes"), self.notes)

    @property
    def age_months(self) -> int:
        return self.years.value() * 12 + self.months.value()


class DeleteCaseDialog(_Form):
    """Says what deleting a case removes and asks for the child's code before it can go ahead."""

    def __init__(self, child_code: str, summary: dict, parent: QWidget | None = None, on_backup=None) -> None:
        super().__init__(tr(f"ลบเคส {child_code}", f"Delete case {child_code}"), parent,
                         ok_text=tr("ลบเคสถาวร", "Delete permanently"))
        self.child_code = child_code
        parts = [
            tr(f"{summary['sessions']} session", f"{summary['sessions']} session(s)"),
            tr(f"ไฟล์เสียง {summary['recordings']} ไฟล์", f"{summary['recordings']} recording(s)"),
            tr(f"transcript {summary['transcripts']} ชุด", f"{summary['transcripts']} transcript(s)"),
            tr(f"รายงาน {summary['reports']} ฉบับ", f"{summary['reports']} report(s)"),
        ]
        text = tr(
            "จะลบเคสนี้ออกจากเครื่องพร้อม " + ", ".join(parts) + " ตัวชี้วัด และ cue ทั้งหมด ย้อนกลับไม่ได้ "
            "ประวัติการทำงาน (audit log) จะบันทึกว่ามีการลบ โดยไม่เก็บเนื้อหา "
            "ไฟล์ที่ export ไว้และไฟล์สำรองข้อมูลจะไม่ถูกลบ",
            "This removes the case from this computer with " + ", ".join(parts) + ", and all its findings and cues. "
            "It cannot be undone. The audit log records the deletion, without its content. "
            "Files you exported and backups are not touched.",
        )
        self.outer.insertWidget(1, label(text, "", wrap=True))
        if summary.get("signed_reports"):
            warning = label(tr(
                f"มีรายงานที่ลงนามแล้ว {summary['signed_reports']} ฉบับ ถ้าต้องเก็บเป็นเวชระเบียน ให้ export หรือสำรองข้อมูลก่อน",
                f"{summary['signed_reports']} signed report(s) will be deleted. If they are part of the clinical record, export or back up first.",
            ), "Notice", wrap=True)
            self.outer.insertWidget(2, warning)
        if on_backup is not None:
            backup = QHBoxLayout()
            button = QPushButton(tr("สำรองข้อมูลก่อน…", "Back up first…"))
            button.clicked.connect(on_backup)
            backup.addWidget(button)
            backup.addStretch(1)
            self.outer.insertLayout(self.outer.count() - 3, backup)
        self.typed = QLineEdit()
        self.typed.setPlaceholderText(child_code)
        self.form.addRow(tr(f"พิมพ์ {child_code} เพื่อยืนยัน", f"Type {child_code} to confirm"), self.typed)
        ok = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        ok.setProperty("role", "danger")
        ok.style().unpolish(ok)
        ok.style().polish(ok)
        ok.setEnabled(False)
        self.typed.textChanged.connect(lambda text: ok.setEnabled(text.strip() == child_code))
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)
        # Size the dialog to its wrapped paragraphs; otherwise their last lines are cut off.
        self.outer.setSizeConstraint(QVBoxLayout.SizeConstraint.SetFixedSize)

    def validate(self) -> str | None:
        if self.typed.text().strip() != self.child_code:
            return tr(f"พิมพ์ {self.child_code} ให้ตรง", f"Type {self.child_code} exactly.")
        return None


class ConsentDialog(_Form):
    def __init__(self, child_code: str, parent: QWidget | None = None) -> None:
        super().__init__(tr(f"บันทึกความยินยอม · {child_code}", f"Record consent: {child_code}"), parent, ok_text=tr("บันทึกความยินยอม", "Record consent"))
        self.signer = QLineEdit()
        self.signer.setPlaceholderText(tr("เช่น มารดา / บิดา / ผู้ปกครองตามกฎหมาย", "Mother, father or legal guardian"))
        self.signer.setMaxLength(120)
        self.when = QDateEdit(_qdate(date.today()))
        self.when.setCalendarPopup(True)
        self.when.setMaximumDate(_qdate(date.today()))
        self.notes = QPlainTextEdit()
        self.notes.setPlaceholderText(tr("เช่น เลขที่เอกสารความยินยอม (ไม่บังคับ)", "Consent form number, for example (optional)"))
        self.notes.setFixedHeight(60)
        self.confirm = QCheckBox(tr("ผู้ปกครองลงนามในเอกสารยินยอมให้บันทึกเสียงและวิเคราะห์ภาษาแล้ว", "The parent or guardian has signed consent for recording and language analysis."))
        self.form.addRow(tr("ผู้ให้ความยินยอม", "Given by"), self.signer)
        self.form.addRow(tr("วันที่ลงนาม", "Date signed"), self.when)
        self.form.addRow(tr("หมายเหตุ", "Notes"), self.notes)
        self.outer.insertWidget(3, self.confirm)

    @property
    def consent_date(self) -> date:
        return _pydate(self.when.date())

    def validate(self) -> str | None:
        if not self.signer.text().strip():
            return tr("กรุณาระบุผู้ให้ความยินยอม", "Enter who gave consent.")
        if not self.confirm.isChecked():
            return tr("ยืนยันว่าได้รับเอกสารยินยอมที่ลงนามแล้ว", "Confirm that you hold the signed consent form.")
        return None


class WithdrawConsentDialog(_Form):
    def __init__(self, child_code: str, parent: QWidget | None = None) -> None:
        super().__init__(tr(f"ถอนความยินยอม · {child_code}", f"Withdraw consent: {child_code}"), parent, ok_text=tr("ถอนความยินยอม", "Withdraw consent"))
        warning = label(
            tr("หลังถอนความยินยอม จะเพิ่ม session บันทึกเสียง แก้ transcript หรือ export รายงานของเคสนี้ไม่ได้อีก "
            "และหมายเหตุของเคสจะถูกลบ การถอนย้อนกลับไม่ได้", "After withdrawal, no sessions, recordings, transcript edits or report exports are possible for this case, and its notes are deleted. This cannot be undone."),
            wrap=True,
        )
        warning.setStyleSheet(f"color: {theme.DANGER};")
        self.outer.insertWidget(1, warning)
        self.reason = QPlainTextEdit()
        self.reason.setFixedHeight(70)
        self.form.addRow(tr("เหตุผล", "Reason"), self.reason)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setProperty("role", "danger")

    def validate(self) -> str | None:
        if not self.reason.toPlainText().strip():
            return tr("กรุณาระบุเหตุผล", "Enter a reason.")
        return None


class NewSessionDialog(_Form):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(tr("เพิ่ม session", "Add session"), parent, ok_text=tr("สร้าง session", "Add session"))
        self.when = QDateEdit(_qdate(date.today()))
        self.when.setCalendarPopup(True)
        self.kind = QComboBox()
        for code, text in SESSION_TYPES:
            self.kind.addItem(text, code)
        self.notes = QPlainTextEdit()
        self.notes.setPlaceholderText(tr("กิจกรรมใน session เช่น เล่นรถ อ่านนิทาน (ไม่บังคับ)", "Activity, such as car play or a storybook (optional)"))
        self.notes.setFixedHeight(70)
        self.form.addRow(tr("วันที่", "Date"), self.when)
        self.form.addRow(tr("ประเภท", "Type"), self.kind)
        self.form.addRow(tr("บันทึก", "Notes"), self.notes)

    @property
    def session_date(self) -> date:
        return _pydate(self.when.date())

    @property
    def session_type(self) -> str:
        return str(self.kind.currentData())


class TherapistDialog(_Form):
    def __init__(self, current: str, parent: QWidget | None = None, first_run: bool = False) -> None:
        super().__init__(tr("ชื่อนักบำบัด", "Therapist name"), parent)
        text = (
            tr("ใส่ชื่อของคุณ ชื่อนี้จะอยู่ในการรับรอง transcript การตรวจ cue และการลงนามรายงาน", "Your name appears on transcript attestations, cue reviews and signed reports.")
            if first_run
            else tr("ชื่อที่ใช้รับรองและลงนามในเครื่องนี้", "The name used to attest and sign on this computer.")
        )
        self.outer.insertWidget(1, label(text, "Muted", wrap=True))
        self.name = QLineEdit(current)
        self.name.setMaxLength(120)
        self.name.setPlaceholderText(tr("เช่น นางสาวกานดา ใจดี (นักแก้ไขการพูด)", "For example Kanda Jaidee, speech-language pathologist"))
        self.form.addRow(tr("ชื่อ", "Name"), self.name)

    def validate(self) -> str | None:
        if not self.name.text().strip():
            return tr("กรุณาใส่ชื่อ", "Enter a name.")
        return None


class AuditLogDialog(QDialog):
    def __init__(self, events: list[dict], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("ประวัติการทำงาน", "Audit log"))
        self.resize(820, 520)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.addWidget(label(tr("ประวัติการทำงาน (audit log)", "Audit log"), "SectionTitle"))
        layout.addWidget(label(tr("ทุกการเปลี่ยนข้อมูลในเครื่องนี้ถูกบันทึกไว้ ลบหรือแก้ไม่ได้", "Every change on this computer is recorded here and cannot be edited or deleted."), "Muted"))
        table = QTableWidget(len(events), 3)
        table.setHorizontalHeaderLabels([tr("เวลา", "Time"), tr("การกระทำ", "Action"), tr("รายละเอียด", "Details")])
        table.verticalHeader().hide()
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        for row, event in enumerate(reversed(events)):
            when = str(event.get("timestamp") or event.get("created_at") or "")[:19].replace("T", " ")
            table.setItem(row, 0, QTableWidgetItem(when))
            table.setItem(row, 1, QTableWidgetItem(str(event.get("action", ""))))
            table.setItem(row, 2, QTableWidgetItem(str(event.get("message", ""))))
        table.resizeColumnsToContents()
        layout.addWidget(table)
        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.button(QDialogButtonBox.StandardButton.Close).setText(tr("ปิด", "Close"))
        close.rejected.connect(self.reject)
        layout.addWidget(close)


class ClinicSpeakerDialog(QDialog):
    """Status of the clinic's own child/adult model; the caller acts on ``choice``."""

    def __init__(self, status: dict, parent: QWidget | None = None) -> None:
        from packages.desktop.ui import labels
        from packages.desktop.ui.widgets import button

        super().__init__(parent)
        self.choice = ""
        self.setWindowTitle(tr("การแยกเสียงเด็ก/ผู้ใหญ่ของคลินิก", "Child/adult voices"))
        self.resize(560, 300)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.addWidget(label(tr("การแยกเสียงเด็ก/ผู้ใหญ่ของคลินิก", "Child/adult voices"), "SectionTitle"))
        about = label(
            tr("โปรแกรมเรียนเสียงของผู้ใหญ่และเด็กจาก transcript ที่คุณรับรองแล้วในเครื่องนี้ "
            "แล้วใช้แยกผู้พูดในร่างครั้งต่อไป ใช้ก็ต่อเมื่อทดสอบกับ session ของคลินิกแล้วแม่นกว่าโมเดลพื้นฐาน "
            "ข้อมูลไม่ออกจากเครื่อง ประโยคที่ไม่แน่ใจยังติด ? และต้องตรวจร่างทุกครั้ง", "PasaScope learns the adults' and children's voices from transcripts you attested on this computer and uses them to label speakers in later drafts, but only when it beats the base model on this clinic's own sessions. Nothing leaves the computer. Uncertain lines still show a ?, and every draft still needs checking."),
            "Muted",
        )
        about.setWordWrap(True)
        layout.addWidget(about)
        self.status_label = label(labels.clinic_speaker_text(status))
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        self.enabled = QCheckBox(tr("ใช้โมเดลประจำคลินิกเมื่อแม่นกว่า", "Use the clinic model when it is more accurate"))
        self.enabled.setChecked(bool(status.get("enabled")))
        layout.addWidget(self.enabled)
        layout.addStretch(1)
        row = QHBoxLayout()
        self.train_btn = button(tr("เรียนตอนนี้", "Train now"), "secondary")
        self.train_btn.setEnabled(not status.get("sessions_needed") and not status.get("children_needed"))
        self.train_btn.clicked.connect(lambda: self._finish("train"))
        self.reset_btn = button(tr("ล้างและเริ่มเรียนใหม่", "Clear and start over"), "secondary")
        self.reset_btn.setEnabled(bool(status.get("trained")))
        self.reset_btn.clicked.connect(lambda: self._finish("reset"))
        row.addWidget(self.train_btn)
        row.addWidget(self.reset_btn)
        row.addStretch(1)
        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.button(QDialogButtonBox.StandardButton.Close).setText(tr("ปิด", "Close"))
        close.rejected.connect(self.reject)
        row.addWidget(close)
        layout.addLayout(row)

    def _finish(self, choice: str) -> None:
        self.choice = choice
        self.accept()
