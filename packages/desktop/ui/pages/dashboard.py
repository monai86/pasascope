"""Home: what is waiting for the therapist, and the state of this computer."""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from packages.desktop.core.i18n import tr
from packages.desktop.ui import labels, theme
from packages.desktop.ui.widgets import button, label


def step_text(step) -> str:
    """What has to happen next for a row of the work queue."""
    return {
        "consent": tr("บันทึกความยินยอม", "Record consent"),
        0: tr("เพิ่มเสียงหรือ transcript", "Add a recording or transcript"),
        1: tr("ตรวจและรับรอง transcript", "Review and attest the transcript"),
        2: tr("วิเคราะห์และตรวจ cue", "Analyse and review cues"),
        3: tr("ลงนามรายงาน", "Sign the report"),
    }[step]


def waiting_text(days: int) -> str:
    if days <= 0:
        return tr("วันนี้", "today")
    if days == 1:
        return tr("เมื่อวาน", "yesterday")
    return tr(f"{days} วัน", f"{days} days")


class Dashboard(QWidget):
    open_case = Signal(str, object)  # case_id, session_id or None
    new_case = Signal()
    backup = Signal()
    speaker_settings = Signal()
    download_models = Signal()

    def __init__(self, service, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.service = service
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 26, 32, 18)
        layout.setSpacing(14)

        head = QHBoxLayout()
        self.title = label(tr("งานวันนี้", "Today"), "CaseTitle")
        head.addWidget(self.title)
        head.addStretch(1)
        add = button(tr("เพิ่มเคส", "New case"), "primary")
        add.clicked.connect(self.new_case.emit)
        head.addWidget(add)
        layout.addLayout(head)
        self.date_line = label("", "Muted")
        layout.addWidget(self.date_line)

        columns = QHBoxLayout()
        columns.setSpacing(28)
        layout.addLayout(columns, 1)

        main = QVBoxLayout()
        main.setSpacing(8)
        main.addWidget(label(tr("รอดำเนินการ", "Waiting for you"), "SectionTitle"))
        self.queue = QTableWidget(0, 4)
        self.queue.setHorizontalHeaderLabels([tr("เด็ก", "Child"), tr("Session", "Session"), tr("ขั้นถัดไป", "Next step"), tr("ค้างมา", "Waiting")])
        self.queue.verticalHeader().hide()
        self.queue.setShowGrid(False)
        self.queue.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.queue.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.queue.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.queue.verticalHeader().setDefaultSectionSize(36)
        header = self.queue.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.queue.cellActivated.connect(self._open_row)
        self.queue.cellDoubleClicked.connect(self._open_row)
        main.addWidget(self.queue, 1)
        self.queue_empty = label(tr("ไม่มีงานค้าง", "Nothing waiting."), "Muted")
        main.addWidget(self.queue_empty)
        # Takes the free height when the table is hidden, so the heading and the
        # empty line stay at the top instead of spreading down the page.
        main.addStretch(0)
        self._main = main
        columns.addLayout(main, 3)

        side = QVBoxLayout()
        side.setSpacing(6)
        side.addWidget(label(tr("เคสล่าสุด", "Recent cases"), "SectionTitle"))
        self.recent = QVBoxLayout()
        self.recent.setSpacing(0)
        side.addLayout(self.recent)
        side.addSpacing(18)
        side.addWidget(label(tr("เครื่องนี้", "This computer"), "SectionTitle"))
        self.facts = QVBoxLayout()
        self.facts.setSpacing(6)
        side.addLayout(self.facts)
        side.addStretch(1)
        side_box = QWidget()
        side_box.setLayout(side)
        side_box.setFixedWidth(320)
        columns.addWidget(side_box)

    def refresh(self) -> None:
        today = date.today()
        self.date_line.setText(today.strftime("%d/%m/%Y"))
        rows = self.service.work_queue()
        self.queue.setRowCount(len(rows))
        for index, row in enumerate(rows):
            case, session = row["case"], row["session"]
            name = case.child_code + (f"  {case.nickname}" if case.nickname else "")
            cells = [name, str(session.session_date) if session else "—", step_text(row["step"]), waiting_text(row["waiting_days"])]
            for column, text in enumerate(cells):
                item = QTableWidgetItem(text)
                item.setData(Qt.ItemDataRole.UserRole, (case.case_id, session.session_id if session else None))
                if column == 3 and row["waiting_days"] >= 7:
                    item.setForeground(QBrush(QColor(theme.ATTENTION)))
                if column == 2 and row["step"] == "consent":
                    item.setForeground(QBrush(QColor(theme.ATTENTION)))
                self.queue.setItem(index, column, item)
        self.queue.setVisible(bool(rows))
        self.queue_empty.setVisible(not rows)
        self._main.setStretch(self._main.count() - 1, 0 if rows else 1)
        self._fill_recent()
        self._fill_facts()

    def _clear(self, layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _fill_recent(self) -> None:
        self._clear(self.recent)
        cases = self.service.list_cases()[:6]
        if not cases:
            self.recent.addWidget(label(tr("ยังไม่มีเคส", "No cases yet."), "Muted"))
        for case in cases:
            consent, _ = labels.CONSENT.get(case.consent_status, (case.consent_status, ""))
            text = f"{case.child_code}" + (f"  {case.nickname}" if case.nickname else "") + f"   ·   {labels.age_text(case.age_months)}"
            link = button(text, "ghost", tooltip=consent)
            link.clicked.connect(lambda _=False, cid=case.case_id: self.open_case.emit(cid, None))
            self.recent.addWidget(link)

    def _fill_facts(self) -> None:
        self._clear(self.facts)
        last = self.service.last_backup_at
        backup_line = tr(f"สำรองล่าสุด {last:%d/%m/%Y}", f"Last backup {last:%d/%m/%Y}") if last else tr("ยังไม่เคยสำรองข้อมูล", "Never backed up")
        due = self.service.backup_due()
        row = QHBoxLayout()
        text = label(backup_line, "AttentionText" if due else "Muted")
        row.addWidget(text)
        row.addStretch(1)
        backup = button(tr("สำรองตอนนี้", "Back up"))
        backup.clicked.connect(self.backup.emit)
        row.addWidget(backup)
        holder = QWidget()
        holder.setLayout(row)
        self.facts.addWidget(holder)

        if not self.service.thai_model_status()["installed"]:
            size = self.service.thai_model_status()["size"] / 1_000_000_000
            models = label(
                tr(f"ยังไม่มีโมเดลถอดเสียงภาษาไทยในเครื่อง  <a href=\"download\">ดาวน์โหลด ({size:.1f} GB)</a>",
                   f"The Thai speech model is not on this computer.  <a href=\"download\">Download ({size:.1f} GB)</a>"),
                wrap=True,
            )
            models.setTextFormat(Qt.TextFormat.RichText)
            models.setObjectName("AttentionText")
            models.linkActivated.connect(lambda _: self.download_models.emit())
            self.facts.addWidget(models)
        available, reason = self.service.transcription_availability()
        mode = tr("แม่นยำ", "accurate") if self.service.transcription_mode == "accurate" else tr("เร็ว", "fast")
        self.facts.addWidget(label(
            tr(f"ถอดเสียงบนเครื่อง: พร้อม (โหมด{mode})", f"Transcription ready ({mode} mode)") if available
            else tr(f"ถอดเสียงบนเครื่องไม่ได้: {reason}", f"Transcription unavailable: {reason}"),
            "Muted", wrap=True,
        ))
        status = self.service.clinic_speaker_status()
        if status["in_use"]:
            speaker = tr("แยกเสียงเด็ก/ผู้ใหญ่: ใช้โมเดลประจำคลินิก", "Child/adult voices: clinic model in use")
        elif status["sessions_needed"] or status["children_needed"]:
            speaker = tr(f"แยกเสียงเด็ก/ผู้ใหญ่: โมเดลพื้นฐาน (อีก {status['sessions_needed']} session จึงเรียนได้)",
                         f"Child/adult voices: base model ({status['sessions_needed']} more sessions to train)")
        else:
            speaker = tr("แยกเสียงเด็ก/ผู้ใหญ่: โมเดลพื้นฐาน", "Child/adult voices: base model")
        voices = label(f'{speaker}  <a href="settings">{tr("ตั้งค่า", "Settings")}</a>', "Muted", wrap=True)
        voices.setTextFormat(Qt.TextFormat.RichText)
        voices.linkActivated.connect(lambda _: self.speaker_settings.emit())
        self.facts.addWidget(voices)

    def _open_row(self, row: int, _column: int) -> None:
        item = self.queue.item(row, 0)
        if item is not None:
            case_id, session_id = item.data(Qt.ItemDataRole.UserRole)
            self.open_case.emit(case_id, session_id)
