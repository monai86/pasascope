"""Step 3: language-sample features and review cues from the attested transcript.

Every cue is a prompt to look, not a finding: the therapist confirms or
dismisses each one, and each echo pair is shown so it can be judged in context.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QScrollArea,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from packages.desktop.ui import labels, theme
from packages.desktop.ui.pages.base import SessionPage
from packages.desktop.ui.widgets import EmptyState, TrendChart, button, card, chip, label, set_chip


class CueCard(QFrame):
    def __init__(self, page: "FindingsPage", result, cue, utterances: dict) -> None:
        super().__init__()
        self.setObjectName("Card")
        self.page = page
        self.result = result
        self.cue = cue
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        title, explanation, step = labels.CUES.get(
            cue.cue_code, (cue.title, cue.explanation, cue.recommended_next_review_step)
        )
        head = QHBoxLayout()
        head.addWidget(label(title, "SectionTitle"))
        severity_text, severity_kind = labels.CUE_SEVERITY.get(cue.severity, (cue.severity, "neutral"))
        head.addWidget(chip(severity_text, severity_kind))
        head.addStretch(1)
        state = cue.review_state.status if cue.review_state else "unreviewed"
        self.state_chip = chip("")
        set_chip(
            self.state_chip,
            labels.CUE_STATE.get(state, state),
            {"acknowledged": "ok", "dismissed": "neutral"}.get(state, "attention"),
        )
        head.addWidget(self.state_chip)
        layout.addLayout(head)
        layout.addWidget(label(explanation, "Hint", wrap=True))

        for item in cue.evidence[:12]:
            layout.addWidget(self._evidence_row(item, utterances))
        if len(cue.evidence) > 12:
            layout.addWidget(label(f"และอีก {len(cue.evidence) - 12} คู่", "Muted"))

        layout.addWidget(label(f"ขั้นต่อไป: {step}", "Muted", wrap=True))

        reviewed_by = getattr(cue.review_state, "reviewed_by_name", None)
        if state != "unreviewed" and reviewed_by:
            note = cue.review_state.therapist_note
            layout.addWidget(label(f"{labels.CUE_STATE[state]}โดย {reviewed_by}" + (f" · {note}" if note else ""), "Muted", wrap=True))

        actions = QHBoxLayout()
        self.note = QLineEdit()
        self.note.setPlaceholderText("บันทึกของนักบำบัด (ไม่บังคับ)")
        actions.addWidget(self.note, 1)
        confirm = button("ยืนยัน", "primary" if state == "unreviewed" else "")
        confirm.clicked.connect(lambda: self.page.set_cue(self.result, self.cue, "acknowledged", self.note.text()))
        dismiss = button("ปัดตก")
        dismiss.clicked.connect(lambda: self.page.set_cue(self.result, self.cue, "dismissed", self.note.text()))
        actions.addWidget(confirm)
        actions.addWidget(dismiss)
        layout.addLayout(actions)

    def _evidence_row(self, item: dict, utterances: dict) -> QWidget:
        box = QFrame()
        box.setStyleSheet(f"background: {theme.CANVAS}; border-radius: 6px;")
        row = QVBoxLayout(box)
        row.setContentsMargins(10, 6, 10, 6)
        row.setSpacing(2)
        adult = utterances.get(item.get("adult_utterance_id", ""))
        child = utterances.get(item.get("child_utterance_id", "") or item.get("utterance_id", ""))
        if adult is not None:
            row.addWidget(label(f"ผู้ใหญ่: {adult.text}", "Hint", wrap=True))
        if child is not None:
            text = label(f"เด็ก: {child.text}", wrap=True)
            text.setStyleSheet(f"color: {theme.PRIMARY_DARK}; font-weight: 600;")
            row.addWidget(text)
        category = labels.ECHO_CATEGORY.get(item.get("category", ""))
        if category:
            row.addWidget(label(category, "Muted"))
        if adult is None and child is None:
            row.addWidget(label("ไม่พบประโยคนี้ใน transcript ปัจจุบัน", "Muted"))
        return box


class FindingsPage(SessionPage):
    def __init__(self, service, runner, parent=None) -> None:
        super().__init__(service, runner, parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 12, 4, 8)
        layout.setSpacing(10)

        self.empty = EmptyState("", "")
        self.empty_btn = button("", "primary")
        self.empty_btn.clicked.connect(self._empty_action)
        self.empty.actions.addWidget(self.empty_btn)
        layout.addWidget(self.empty)

        self.body = QWidget()
        body = QVBoxLayout(self.body)
        body.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.body)

        top = QHBoxLayout()
        self.status_chip = chip("")
        top.addWidget(self.status_chip)
        self.status_text = label("", "Hint")
        top.addWidget(self.status_text)
        top.addStretch(1)
        self.analyze_btn = button("วิเคราะห์ใหม่")
        self.analyze_btn.clicked.connect(self.analyze)
        self.report_btn = button("ไปทำรายงาน →", "primary")
        self.report_btn.clicked.connect(lambda: self.navigate.emit(3))
        top.addWidget(self.analyze_btn)
        top.addWidget(self.report_btn)
        body.addLayout(top)

        split = QSplitter(Qt.Orientation.Horizontal)
        body.addWidget(split, 1)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 6, 0)
        left_layout.addWidget(label("ตัวชี้วัดจากตัวอย่างภาษา", "SectionTitle"))
        left_layout.addWidget(label("ค่าเชิงบรรยายของ session นี้ ยังไม่มีเกณฑ์อ้างอิงของเด็กไทย จึงไม่แปลว่าปกติหรือผิดปกติ", "Muted", wrap=True))
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["ตัวชี้วัด", "ค่า"])
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setDefaultSectionSize(32)
        left_layout.addWidget(self.table, 1)

        trend_card, trend = card()
        trow = QHBoxLayout()
        trow.addWidget(label("แนวโน้มข้าม session", "SectionTitle"))
        trow.addStretch(1)
        self.trend_pick = QComboBox()
        for name in labels.TREND_FEATURES:
            self.trend_pick.addItem(labels.FEATURES[name][0], name)
        self.trend_pick.currentIndexChanged.connect(self._draw_trend)
        trow.addWidget(self.trend_pick)
        trend.addLayout(trow)
        self.chart = TrendChart()
        trend.addWidget(self.chart)
        left_layout.addWidget(trend_card)
        split.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(6, 0, 0, 0)
        right_layout.addWidget(label("Cue ที่ควรตรวจ", "SectionTitle"))
        right_layout.addWidget(label("ระบบไม่วินิจฉัย cue เป็นเพียงจุดที่ควรกลับไปดูใน transcript ยืนยันหรือปัดตกทีละข้อ", "Muted", wrap=True))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.cue_holder = QWidget()
        self.cue_layout = QVBoxLayout(self.cue_holder)
        self.cue_layout.setContentsMargins(0, 0, 0, 0)
        self.cue_layout.setSpacing(10)
        scroll.setWidget(self.cue_holder)
        right_layout.addWidget(scroll, 1)
        split.addWidget(right)
        split.setSizes([520, 520])

        self._empty_target = 0

    # ------------------------------------------------------------------
    def refresh(self) -> None:
        if self.session is None:
            return
        self.session = self.service.get_session(self.session.session_id)
        transcript = self.service.get_transcript(self.session.session_id)
        features = self.service.get_features(self.session.session_id)
        if transcript is None:
            self._show_empty("ยังไม่มี transcript", "บันทึกหรือนำเข้าเสียงก่อน", "ไปขั้นที่ 1 →", 0)
            return
        if features is None or self.session.findings_stale:
            if not transcript.therapist_attested:
                self._show_empty("รับรอง transcript ก่อน", "ตัวชี้วัดคำนวณจาก transcript ที่นักบำบัดตรวจและรับรองแล้วเท่านั้น", "ไปตรวจ transcript →", 1)
            else:
                body = "transcript ถูกแก้หลังวิเคราะห์ครั้งก่อน ต้องวิเคราะห์ใหม่" if features else "transcript รับรองแล้ว พร้อมคำนวณตัวชี้วัดและ cue"
                self._show_empty("ยังไม่ได้วิเคราะห์", body, "วิเคราะห์ตอนนี้", -1)
            return
        self.empty.hide()
        self.body.show()
        cues = self.service.get_cues(self.session.session_id)
        self._fill_features(features)
        self._fill_cues(cues, transcript)
        pending = sum(1 for c in (cues.cues if cues else []) if (c.review_state.status if c.review_state else "unreviewed") == "unreviewed")
        if pending:
            set_chip(self.status_chip, f"รอตรวจ cue {pending} ข้อ", "attention")
        else:
            set_chip(self.status_chip, "ตรวจ cue ครบแล้ว", "ok")
        self.status_text.setText(f"วิเคราะห์เมื่อ {features.extracted_at:%d/%m/%Y %H:%M}")
        self._draw_trend()

    def _show_empty(self, title: str, body: str, action: str, target: int) -> None:
        self.body.hide()
        self.empty.show()
        self.empty.set_text(title, body)
        self.empty_btn.setText(action)
        self._empty_target = target

    def _empty_action(self) -> None:
        if self._empty_target < 0:
            self.analyze()
        else:
            self.navigate.emit(self._empty_target)

    def _fill_features(self, features) -> None:
        rows = [f for f in features.features if f.name in labels.FEATURES]
        self.table.setRowCount(len(rows))
        for row, feature in enumerate(rows):
            title, _, hint = labels.FEATURES[feature.name]
            name_item = QTableWidgetItem(title)
            name_item.setToolTip(hint)
            value_item = QTableWidgetItem(labels.feature_value_text(feature.name, feature.value, feature.unit))
            value_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if feature.warnings:
                value_item.setToolTip("\n".join(feature.warnings))
            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, value_item)

    def _fill_cues(self, result, transcript) -> None:
        while self.cue_layout.count():
            item = self.cue_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if result is None or not result.cues:
            self.cue_layout.addWidget(label("ไม่มี cue จากกฎใน session นี้", "Muted"))
            self.cue_layout.addStretch(1)
            return
        utterances = {u.utterance_id: u for u in transcript.utterances}
        for cue in result.cues:
            self.cue_layout.addWidget(CueCard(self, result, cue, utterances))
        self.cue_layout.addStretch(1)

    def _draw_trend(self) -> None:
        if self.case is None:
            return
        name = self.trend_pick.currentData()
        series = [(when, values[name]) for when, values in self.service.feature_trend(self.case.case_id, [name]) if name in values]
        kind = labels.FEATURES[name][1]
        fmt = "{:.0f}" if kind == "int" else "{:.2f}"
        self.chart.set_series(labels.FEATURES[name][0], series, fmt)

    # ------------------------------------------------------------------
    def analyze(self) -> None:
        session_id = self.session.session_id
        self.analyze_btn.setEnabled(False)
        self.empty_btn.setEnabled(False)

        def done(_result) -> None:
            self.analyze_btn.setEnabled(True)
            self.empty_btn.setEnabled(True)
            self.changed.emit()

        def failed(exc: Exception) -> None:
            self.analyze_btn.setEnabled(True)
            self.empty_btn.setEnabled(True)
            self.report_error(exc, "วิเคราะห์ไม่สำเร็จ")

        self.runner.run(lambda: self.service.analyze(session_id), on_done=done, on_error=failed)

    def set_cue(self, result, cue, status: str, note: str) -> None:
        if self.attempt(self.service.set_cue_state, result.result_id, cue.cue_code, status, note, title="บันทึกไม่สำเร็จ") is not None:
            self.changed.emit()
