"""The case at a glance: every session's progress and how the child's measures change.

Double-clicking a session opens it at the step it is waiting on.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from packages.desktop.ui import labels, theme
from packages.desktop.ui.widgets import MetricCard, TrendChart, card, label

# Step → (what the session waits for, colour)
STEP_TEXT = {
    0: ("รอเสียง", theme.MUTED),
    1: ("รอตรวจ", theme.ATTENTION),
    2: ("รอวิเคราะห์", theme.ATTENTION),
    3: ("รอลงนาม", theme.ATTENTION),
    4: ("ลงนามแล้ว", theme.OK),
}
TABLE_FEATURES = [
    "child_utterance_count",
    "mean_length_of_utterance_words",
    "number_of_different_words",
    "type_token_ratio",
]
COLUMNS = ["วันที่", "สถานะ", "ประโยคเด็ก", "MLU-w", "NDW", "TTR", "cue รอตรวจ"]


def _number(name: str, value) -> str:
    """Same precision in every row, so a column reads as one series."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return "—"
    return f"{value:.0f}" if labels.FEATURES[name][1] == "int" else f"{value:.2f}"


class CaseOverview(QWidget):
    open_session = Signal(str)

    def __init__(self, service, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.service = service
        self.case = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 12, 4, 8)
        layout.setSpacing(10)

        cards = QGridLayout()
        cards.setSpacing(8)
        self.cards = {
            "sessions": MetricCard("Session ทั้งหมด"),
            "mlu": MetricCard("MLU-w ล่าสุด"),
            "ndw": MetricCard("NDW ล่าสุด"),
            "open": MetricCard("งานที่ค้าง"),
        }
        for column, widget in enumerate(self.cards.values()):
            cards.addWidget(widget, 0, column)
            cards.setColumnStretch(column, 1)
        layout.addLayout(cards)

        split = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(split, 1)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 6, 0)
        left_layout.addWidget(label("ทุก session", "SectionTitle"))
        left_layout.addWidget(label("ดับเบิลคลิกเพื่อเปิด session ที่ขั้นที่ค้างอยู่", "Muted"))
        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.verticalHeader().setDefaultSectionSize(34)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setStretchLastSection(True)
        self.table.cellDoubleClicked.connect(self._open_row)
        left_layout.addWidget(self.table, 1)
        split.addWidget(left)

        trend_card, trend = card()
        row = QHBoxLayout()
        row.addWidget(label("แนวโน้ม", "SectionTitle"))
        row.addStretch(1)
        self.trend_pick = QComboBox()
        for name in labels.TREND_FEATURES:
            self.trend_pick.addItem(labels.FEATURES[name][0], name)
        self.trend_pick.currentIndexChanged.connect(self._draw_trend)
        row.addWidget(self.trend_pick)
        trend.addLayout(row)
        self.chart = TrendChart()
        trend.addWidget(self.chart, 1)
        trend.addWidget(label(
            "ค่าเชิงบรรยาย ยังไม่มีเกณฑ์อ้างอิงของเด็กไทย ตัวอย่างที่สั้นหรือกิจกรรมต่างกันทำให้ค่าแกว่งได้",
            "Muted", wrap=True,
        ))
        split.addWidget(trend_card)
        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 2)
        split.setSizes([640, 420])

    def load(self, case) -> None:
        self.case = case
        self.refresh()

    def refresh(self) -> None:
        if self.case is None:
            return
        rows = self.service.session_summaries(self.case.case_id, TABLE_FEATURES)
        self._fill_cards(rows)
        self._fill_table(rows)
        self._draw_trend()

    def _fill_cards(self, rows: list[dict]) -> None:
        analysed = [r for r in rows if r["values"]]
        self.cards["sessions"].set_value(str(len(rows)), f"วิเคราะห์แล้ว {len(analysed)}")
        for key, name in (("mlu", "mean_length_of_utterance_words"), ("ndw", "number_of_different_words")):
            series = [r for r in analysed if isinstance(r["values"].get(name), (int, float))]
            if not series:
                self.cards[key].set_value("—", "ยังไม่มี session ที่วิเคราะห์แล้ว")
                continue
            latest = series[0]["values"][name]
            detail = f"{series[0]['session'].session_date}"
            if len(series) > 1:
                previous = series[1]["values"][name]
                change = _number(name, latest - previous)
                detail += f" · ครั้งก่อน {_number(name, previous)} ({'' if change.startswith('-') else '+'}{change})"
            self.cards[key].set_value(_number(name, latest), detail)
        unfinished = sum(1 for r in rows if r["step"] < 4)
        pending = sum(r["pending_cues"] for r in rows)
        self.cards["open"].set_value(
            str(unfinished), f"session ยังไม่ลงนาม · cue รอตรวจ {pending}" if rows else "ยังไม่มี session"
        )

    def _fill_table(self, rows: list[dict]) -> None:
        self.table.setRowCount(len(rows))
        for index, row in enumerate(rows):
            session = row["session"]
            step_text, color = STEP_TEXT[row["step"]]
            if row["values"] and row["schema_version"] != "features-basic-v2":
                step_text += " · วิเคราะห์ใหม่"
            cells = [str(session.session_date), step_text]
            cells.extend(_number(name, row["values"].get(name)) for name in TABLE_FEATURES)
            cells.append(str(row["pending_cues"]) if row["values"] else "—")
            for column, text in enumerate(cells):
                item = QTableWidgetItem(text)
                item.setData(Qt.ItemDataRole.UserRole, session.session_id)
                if column == 1:
                    item.setForeground(QBrush(QColor(color)))
                elif column >= 2:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if column == len(cells) - 1 and row["pending_cues"]:
                    item.setForeground(QBrush(QColor(theme.ATTENTION)))
                self.table.setItem(index, column, item)

    def _open_row(self, row: int, _column: int) -> None:
        item = self.table.item(row, 0)
        if item is not None:
            self.open_session.emit(item.data(Qt.ItemDataRole.UserRole))

    def _draw_trend(self) -> None:
        if self.case is None:
            return
        name = self.trend_pick.currentData()
        series = [(when, values[name]) for when, values in self.service.feature_trend(self.case.case_id, [name]) if name in values]
        kind = labels.FEATURES[name][1]
        self.chart.set_series(labels.FEATURES[name][0], series, "{:.0f}" if kind == "int" else "{:.2f}")
