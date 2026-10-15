"""Forms that open over the main window."""

from __future__ import annotations

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
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from packages.desktop.ui import theme
from packages.desktop.ui.widgets import label

SESSION_TYPES = [
    ("therapy_session", "บำบัดตามนัด"),
    ("assessment", "ประเมิน"),
    ("follow_up", "ติดตามผล"),
]


def _qdate(value: date) -> QDate:
    return QDate(value.year, value.month, value.day)


def _pydate(value: QDate) -> date:
    return date(value.year(), value.month(), value.day())


class _Form(QDialog):
    def __init__(self, title: str, parent: QWidget | None = None, ok_text: str = "บันทึก") -> None:
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
        ok.setText(ok_text)
        ok.setProperty("role", "primary")
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("ยกเลิก")
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
        super().__init__("เพิ่มเคสใหม่", parent)
        self.code = QLineEdit()
        self.code.setPlaceholderText("เช่น TH-2026-014 (ห้ามใช้ชื่อจริง)")
        self.code.setMaxLength(64)
        self.nickname = QLineEdit()
        self.nickname.setPlaceholderText("ไม่บังคับ")
        self.nickname.setMaxLength(120)
        age = QHBoxLayout()
        self.years = QSpinBox()
        self.years.setRange(0, 20)
        self.years.setValue(4)
        self.years.setSuffix(" ปี")
        self.months = QSpinBox()
        self.months.setRange(0, 11)
        self.months.setSuffix(" เดือน")
        age.addWidget(self.years)
        age.addWidget(self.months)
        age.addStretch(1)
        self.language = QComboBox()
        self.language.addItems(["Thai", "English", "Thai + English"])
        self.notes = QPlainTextEdit()
        self.notes.setPlaceholderText("ไม่บังคับ")
        self.notes.setFixedHeight(70)
        self.form.addRow("รหัสเด็ก", self.code)
        self.form.addRow("ชื่อเล่น", self.nickname)
        self.form.addRow("อายุ", age)
        self.form.addRow("ภาษาที่ใช้", self.language)
        self.form.addRow("หมายเหตุ", self.notes)
        hint = label("ระบบเก็บเฉพาะรหัสและชื่อเล่น ข้อมูลทั้งหมดอยู่ในเครื่องนี้เท่านั้น", "Muted", wrap=True)
        self.outer.insertWidget(2, hint)

    @property
    def age_months(self) -> int:
        return self.years.value() * 12 + self.months.value()

    def validate(self) -> str | None:
        if not self.code.text().strip():
            return "กรุณาใส่รหัสเด็ก"
        return None


class ConsentDialog(_Form):
    def __init__(self, child_code: str, parent: QWidget | None = None) -> None:
        super().__init__(f"บันทึกความยินยอม · {child_code}", parent, ok_text="บันทึกความยินยอม")
        self.signer = QLineEdit()
        self.signer.setPlaceholderText("เช่น มารดา / บิดา / ผู้ปกครองตามกฎหมาย")
        self.signer.setMaxLength(120)
        self.when = QDateEdit(_qdate(date.today()))
        self.when.setCalendarPopup(True)
        self.when.setMaximumDate(_qdate(date.today()))
        self.notes = QPlainTextEdit()
        self.notes.setPlaceholderText("เช่น เลขที่เอกสารความยินยอม (ไม่บังคับ)")
        self.notes.setFixedHeight(60)
        self.confirm = QCheckBox("ผู้ปกครองลงนามในเอกสารยินยอมให้บันทึกเสียงและวิเคราะห์ภาษาแล้ว")
        self.form.addRow("ผู้ให้ความยินยอม", self.signer)
        self.form.addRow("วันที่ลงนาม", self.when)
        self.form.addRow("หมายเหตุ", self.notes)
        self.outer.insertWidget(3, self.confirm)

    @property
    def consent_date(self) -> date:
        return _pydate(self.when.date())

    def validate(self) -> str | None:
        if not self.signer.text().strip():
            return "กรุณาระบุผู้ให้ความยินยอม"
        if not self.confirm.isChecked():
            return "ยืนยันว่าได้รับเอกสารยินยอมที่ลงนามแล้ว"
        return None


class WithdrawConsentDialog(_Form):
    def __init__(self, child_code: str, parent: QWidget | None = None) -> None:
        super().__init__(f"ถอนความยินยอม · {child_code}", parent, ok_text="ถอนความยินยอม")
        warning = label(
            "หลังถอนความยินยอม จะเพิ่ม session บันทึกเสียง แก้ transcript หรือ export รายงานของเคสนี้ไม่ได้อีก "
            "และหมายเหตุของเคสจะถูกลบ การถอนย้อนกลับไม่ได้",
            wrap=True,
        )
        warning.setStyleSheet(f"color: {theme.DANGER};")
        self.outer.insertWidget(1, warning)
        self.reason = QPlainTextEdit()
        self.reason.setFixedHeight(70)
        self.form.addRow("เหตุผล", self.reason)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setProperty("role", "danger")

    def validate(self) -> str | None:
        if not self.reason.toPlainText().strip():
            return "กรุณาระบุเหตุผล"
        return None


class NewSessionDialog(_Form):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("เพิ่ม session", parent, ok_text="สร้าง session")
        self.when = QDateEdit(_qdate(date.today()))
        self.when.setCalendarPopup(True)
        self.kind = QComboBox()
        for code, text in SESSION_TYPES:
            self.kind.addItem(text, code)
        self.notes = QPlainTextEdit()
        self.notes.setPlaceholderText("กิจกรรมใน session เช่น เล่นรถ อ่านนิทาน (ไม่บังคับ)")
        self.notes.setFixedHeight(70)
        self.form.addRow("วันที่", self.when)
        self.form.addRow("ประเภท", self.kind)
        self.form.addRow("บันทึก", self.notes)

    @property
    def session_date(self) -> date:
        return _pydate(self.when.date())

    @property
    def session_type(self) -> str:
        return str(self.kind.currentData())


class TherapistDialog(_Form):
    def __init__(self, current: str, parent: QWidget | None = None, first_run: bool = False) -> None:
        super().__init__("ชื่อนักบำบัด", parent)
        text = (
            "ใส่ชื่อของคุณ ชื่อนี้จะอยู่ในการรับรอง transcript การตรวจ cue และการลงนามรายงาน"
            if first_run
            else "ชื่อที่ใช้รับรองและลงนามในเครื่องนี้"
        )
        self.outer.insertWidget(1, label(text, "Muted", wrap=True))
        self.name = QLineEdit(current)
        self.name.setMaxLength(120)
        self.name.setPlaceholderText("เช่น นางสาวกานดา ใจดี (นักแก้ไขการพูด)")
        self.form.addRow("ชื่อ", self.name)

    def validate(self) -> str | None:
        if not self.name.text().strip():
            return "กรุณาใส่ชื่อ"
        return None


class AuditLogDialog(QDialog):
    def __init__(self, events: list[dict], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("ประวัติการทำงาน")
        self.resize(820, 520)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.addWidget(label("ประวัติการทำงาน (audit log)", "SectionTitle"))
        layout.addWidget(label("ทุกการเปลี่ยนข้อมูลในเครื่องนี้ถูกบันทึกไว้ ลบหรือแก้ไม่ได้", "Muted"))
        table = QTableWidget(len(events), 3)
        table.setHorizontalHeaderLabels(["เวลา", "การกระทำ", "รายละเอียด"])
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
        close.button(QDialogButtonBox.StandardButton.Close).setText("ปิด")
        close.rejected.connect(self.reject)
        layout.addWidget(close)
