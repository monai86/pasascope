"""Step 3: language-sample features and review cues from the attested transcript.

Every cue is a prompt to look, not a finding: the therapist confirms or
dismisses each one, and each echo pair is shown so it can be judged in context.
"""

from __future__ import annotations

from packages.desktop.core.i18n import tr

import re

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QScrollArea,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from packages.desktop.ui import labels, theme
from packages.desktop.ui.pages.base import SessionPage
from packages.desktop.ui.widgets import (
    EmptyState,
    MetricCard,
    TrendChart,
    button,
    card,
    chip,
    label,
    notice,
    set_chip,
)

CURRENT_SCHEMA = labels.CURRENT_SCHEMA


_CHAT_TERMINATOR = re.compile(r"\s*[.?!]+$")


def _spoken(text: str) -> str:
    """Utterance text without the CHAT end-of-utterance mark."""
    return _CHAT_TERMINATOR.sub("", text or "")


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
        # Thai titles cannot wrap mid-word, so the chips get their own row.
        layout.addWidget(label(title, "SectionTitle", wrap=True))
        head = QHBoxLayout()
        severity_text, severity_kind = labels.CUE_SEVERITY.get(cue.severity, (cue.severity, "neutral"))
        head.addWidget(chip(severity_text, severity_kind))
        state = cue.review_state.status if cue.review_state else "unreviewed"
        self.state_chip = chip("")
        set_chip(
            self.state_chip,
            labels.CUE_STATE.get(state, state),
            {"acknowledged": "ok", "dismissed": "neutral"}.get(state, "attention"),
        )
        head.addWidget(self.state_chip)
        head.addStretch(1)
        layout.addLayout(head)
        layout.addWidget(label(explanation, "Hint", wrap=True))

        for item in cue.evidence[:12]:
            layout.addWidget(self._evidence_row(item, utterances))
        if len(cue.evidence) > 12:
            layout.addWidget(label(tr(f"และอีก {len(cue.evidence) - 12} คู่", f"and {len(cue.evidence) - 12} more pairs"), "Muted"))

        layout.addWidget(label(tr(f"ขั้นต่อไป: {step}", f"Next: {step}"), "Muted", wrap=True))

        reviewed_by = getattr(cue.review_state, "reviewed_by_name", None)
        if state != "unreviewed" and reviewed_by:
            note = cue.review_state.therapist_note
            layout.addWidget(label(tr(f"{labels.CUE_STATE[state]}โดย {reviewed_by}", f"{labels.CUE_STATE[state]} by {reviewed_by}") + (f" · {note}" if note else ""), "Muted", wrap=True))

        actions = QHBoxLayout()
        self.note = QLineEdit()
        self.note.setPlaceholderText(tr("บันทึกของนักบำบัด (ไม่บังคับ)", "Therapist note (optional)"))
        actions.addWidget(self.note, 1)
        confirm = button(tr("ยืนยัน", "Confirm"), "primary" if state == "unreviewed" else "")
        confirm.clicked.connect(lambda: self.page.set_cue(self.result, self.cue, "acknowledged", self.note.text()))
        dismiss = button(tr("ปัดตก", "Dismiss"))
        dismiss.clicked.connect(lambda: self.page.set_cue(self.result, self.cue, "dismissed", self.note.text()))
        actions.addWidget(confirm)
        actions.addWidget(dismiss)
        layout.addLayout(actions)

    def _evidence_row(self, item: dict, utterances: dict) -> QWidget:
        box = QFrame()
        box.setStyleSheet(f"background: {theme.SIDEBAR}; border-radius: 4px;")
        row = QVBoxLayout(box)
        row.setContentsMargins(10, 6, 10, 6)
        row.setSpacing(2)
        adult = utterances.get(item.get("adult_utterance_id", ""))
        child = utterances.get(item.get("child_utterance_id", "") or item.get("utterance_id", ""))
        if adult is not None:
            row.addWidget(label(tr(f"ผู้ใหญ่: {_spoken(adult.text)}", f"Adult: {_spoken(adult.text)}"), "Hint", wrap=True))
        if child is not None:
            text = label(tr(f"เด็ก: {_spoken(child.text)}", f"Child: {_spoken(child.text)}"), wrap=True)
            text.setStyleSheet(f"color: {theme.PRIMARY_TEXT}; font-weight: 600;")
            row.addWidget(text)
        category = labels.ECHO_CATEGORY.get(item.get("category", ""))
        if category:
            row.addWidget(label(category, "Muted"))
        if adult is None and child is None:
            row.addWidget(label(tr("ไม่พบประโยคนี้ใน transcript ปัจจุบัน", "This line is no longer in the transcript"), "Muted"))
        return box


class FindingsPage(SessionPage):
    open_guide = Signal(str)  # a feature name, or "" for the guide's first page

    def __init__(self, service, runner, parent=None) -> None:
        super().__init__(service, runner, parent)
        self._features = None
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
        self.analyze_btn = button(tr("วิเคราะห์ใหม่", "Analyse again"))
        self.analyze_btn.clicked.connect(self.analyze)
        self.report_btn = button(tr("ไปที่รายงาน", "Open report"), "primary")
        self.report_btn.clicked.connect(lambda: self.navigate.emit(3))
        top.addWidget(self.analyze_btn)
        top.addWidget(self.report_btn)
        body.addLayout(top)

        split = QSplitter(Qt.Orientation.Horizontal)
        body.addWidget(split, 1)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 6, 0)
        left_layout.addWidget(label(tr("ตัวชี้วัดจากตัวอย่างภาษา", "Language measures"), "SectionTitle"))
        left_layout.addWidget(label(tr("ค่าเชิงบรรยายของ session นี้ ยังไม่มีเกณฑ์อ้างอิงของเด็กไทย จึงไม่แปลว่าปกติหรือผิดปกติ", "Descriptive values for this session. There are no Thai norms yet."), "Muted", wrap=True))

        cards = QGridLayout()
        cards.setSpacing(8)
        self.metric_cards: dict[str, MetricCard] = {}
        for column, (name, title) in enumerate(labels.HEADLINE_FEATURES.items()):
            self.metric_cards[name] = MetricCard(title)
            cards.addWidget(self.metric_cards[name], 0, column)
            cards.setColumnStretch(column, 1)
        left_layout.addLayout(cards)
        self.sample_notice = notice()
        left_layout.addWidget(self.sample_notice)
        self.schema_notice = notice(
            tr("คำนวณด้วยวิธีนับแบบเดิม · กด \"วิเคราะห์ใหม่\" เพื่อนับตามกติกา CLAN", "Counted with the earlier method. Analyse again to count with CLAN's rules."),
            "primary",
        )
        left_layout.addWidget(self.schema_notice)

        self.left_tabs = QTabWidget()
        self.left_tabs.setDocumentMode(True)
        left_layout.addWidget(self.left_tabs, 1)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels([tr("ตัวชี้วัด", "Measure"), tr("ค่า", "Value")])
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.setWordWrap(False)
        self.table.verticalHeader().setDefaultSectionSize(32)
        measures_box = QWidget()
        measures_layout = QVBoxLayout(measures_box)
        measures_layout.setContentsMargins(0, 6, 0, 0)
        measures_layout.setSpacing(4)
        measures_bar = QHBoxLayout()
        self.show_all = QCheckBox(tr("แสดงตัวชี้วัดทั้งหมด", "Show all measures"))
        self.show_all.setToolTip(tr("ตัวชี้วัดหลักคือชุดที่ช่วยนักบำบัดมากที่สุด ตัวอื่นเป็นข้อมูลเสริมหรือเบื้องหลัง",
                                    "The main measures help most; the rest are supporting or background figures."))
        self.show_all.toggled.connect(lambda _: self._features and self._fill_features(self._features))
        measures_bar.addWidget(self.show_all)
        measures_bar.addStretch(1)
        guide = label(f'<a href="guide">{tr("แต่ละตัวคืออะไร", "What each one means")}</a>', "Muted")
        guide.setTextFormat(Qt.TextFormat.RichText)
        guide.linkActivated.connect(lambda _: self.open_guide.emit(""))
        measures_bar.addWidget(guide)
        measures_layout.addLayout(measures_bar)
        measures_layout.addWidget(self.table, 1)
        self.table.cellDoubleClicked.connect(self._open_row_guide)
        self.left_tabs.addTab(measures_box, tr("ตัวชี้วัด", "Measures"))

        trend_card, trend = card()
        trow = QHBoxLayout()
        trow.addWidget(label(tr("แนวโน้มข้าม session", "Across sessions"), "SectionTitle"))
        trow.addStretch(1)
        self.trend_pick = QComboBox()
        for name in labels.TREND_FEATURES:
            self.trend_pick.addItem(labels.FEATURES[name][0], name)
        self.trend_pick.currentIndexChanged.connect(self._draw_trend)
        trow.addWidget(self.trend_pick)
        trend.addLayout(trow)
        self.chart = TrendChart()
        trend.addWidget(self.chart, 1)
        self.left_tabs.addTab(trend_card, tr("แนวโน้มข้าม session", "Across sessions"))
        split.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(6, 0, 0, 0)
        right_layout.addWidget(label(tr("Cue ที่ควรตรวจ", "Cues"), "SectionTitle"))
        right_layout.addWidget(label(tr("ระบบไม่วินิจฉัย cue เป็นเพียงจุดที่ควรกลับไปดูใน transcript ยืนยันหรือปัดตกทีละข้อ", "Places worth a second look in the transcript. Confirm or dismiss each."), "Muted", wrap=True))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.cue_holder = QWidget()
        self.cue_layout = QVBoxLayout(self.cue_holder)
        self.cue_layout.setContentsMargins(0, 0, 0, 0)
        self.cue_layout.setSpacing(10)
        scroll.setWidget(self.cue_holder)
        right_layout.addWidget(scroll, 1)
        split.addWidget(right)
        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 2)
        split.setSizes([600, 400])

        self._empty_target = 0

    # ------------------------------------------------------------------
    def refresh(self) -> None:
        if self.session is None:
            return
        self.session = self.service.get_session(self.session.session_id)
        transcript = self.service.get_transcript(self.session.session_id)
        features = self.service.get_features(self.session.session_id)
        if transcript is None:
            self._show_empty(tr("ยังไม่มี transcript", "No transcript yet"), tr("บันทึกหรือนำเข้าเสียงก่อน", "Record or import audio first."), tr("ไปที่ขั้นเสียง", "Go to Recording"), 0)
            return
        if features is None or self.session.findings_stale:
            if not transcript.therapist_attested:
                self._show_empty(tr("รับรอง transcript ก่อน", "Attest the transcript first"), tr("ตัวชี้วัดคำนวณจาก transcript ที่นักบำบัดตรวจและรับรองแล้วเท่านั้น", "Measures are computed only from a transcript you have checked and attested."), tr("เปิด transcript", "Open transcript"), 1)
            else:
                body = tr("transcript ถูกแก้หลังวิเคราะห์ครั้งก่อน ต้องวิเคราะห์ใหม่", "The transcript changed after the last analysis.") if features else tr("transcript รับรองแล้ว พร้อมคำนวณตัวชี้วัดและ cue", "The transcript is attested.")
                self._show_empty(tr("ยังไม่ได้วิเคราะห์", "Not analysed yet"), body, tr("วิเคราะห์ตอนนี้", "Analyse"), -1)
            return
        self.empty.hide()
        self.body.show()
        cues = self.service.get_cues(self.session.session_id)
        self._fill_features(features)
        self._fill_cues(cues, transcript)
        pending = sum(1 for c in (cues.cues if cues else []) if (c.review_state.status if c.review_state else "unreviewed") == "unreviewed")
        if pending:
            set_chip(self.status_chip, tr(f"รอตรวจ cue {pending} ข้อ", f"{pending} cues to review"), "attention")
        else:
            set_chip(self.status_chip, tr("ตรวจ cue ครบแล้ว", "Cues reviewed"), "ok")
        self.status_text.setText(tr(f"วิเคราะห์เมื่อ {features.extracted_at:%d/%m/%Y %H:%M}", f"Analysed {features.extracted_at:%d/%m/%Y %H:%M}"))
        self._draw_trend()

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
            self.analyze()
        else:
            self.navigate.emit(self._empty_target)

    def _fill_features(self, features) -> None:
        self._features = features
        values = {f.name: f.value for f in features.features}
        by_name = {f.name: f for f in features.features}
        self._fill_cards(values)
        self._fill_notices(features, values)

        show_all = self.show_all.isChecked()
        rows: list[tuple[str, object]] = []
        for group, names in labels.FEATURE_GROUPS:
            present = [by_name[name] for name in names
                       if name in by_name and name in labels.FEATURES and (show_all or name in labels.CORE_FEATURES)]
            if not present:
                continue
            rows.append(("group", group))
            if set(names) <= labels.CODED_GROUP_FEATURES and not any(values.get(f.name) for f in present):
                rows.append(("note", tr("ยังไม่มีรหัส [/] [//] [*] ใน transcript นี้", "No [/] [//] [*] codes in this transcript yet")))
                continue
            rows.extend(("feature", feature) for feature in present)

        self.table.clearSpans()
        self.table.setRowCount(len(rows))
        for row, (kind, item) in enumerate(rows):
            if kind == "feature":
                self._feature_row(row, item, values)
            else:
                self._span_row(row, item, heading=kind == "group")

    def _open_row_guide(self, row: int, _column: int) -> None:
        item = self.table.item(row, 0)
        name = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
        if name:
            self.open_guide.emit(name)

    def _feature_row(self, row: int, feature, values: dict) -> None:
        title, _, hint = labels.FEATURES[feature.name]
        name_item = QTableWidgetItem(f"   {title}")
        name_item.setData(Qt.ItemDataRole.UserRole, feature.name)
        hint = f"{hint}\n{tr('ดับเบิลคลิกเพื่ออ่านว่าตัวชี้วัดนี้ช่วยอะไร', 'Double-click to read what this measure tells you')}"
        name_item.setToolTip(hint)
        if feature.value is None or feature.value == "not_available":
            reason = labels.missing_reason(feature.name, values)
            value_item = QTableWidgetItem(f"— {reason}")
            value_item.setForeground(QBrush(QColor(theme.MUTED)))
        else:
            value_item = QTableWidgetItem(labels.feature_value_text(feature.name, feature.value, feature.unit))
        value_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        value_item.setToolTip(hint)
        self.table.setItem(row, 0, name_item)
        self.table.setItem(row, 1, value_item)

    def _span_row(self, row: int, text: str, *, heading: bool) -> None:
        item = QTableWidgetItem(text if heading else f"   {text}")
        if heading:
            font = QFont(self.table.font())
            font.setBold(True)
            item.setFont(font)
            item.setForeground(QBrush(QColor(theme.PRIMARY_TEXT)))
            item.setBackground(QBrush(QColor(theme.SIDEBAR)))
        else:
            item.setForeground(QBrush(QColor(theme.MUTED)))
        self.table.setItem(row, 0, item)
        self.table.setItem(row, 1, QTableWidgetItem(""))
        self.table.setSpan(row, 0, 1, 2)

    def _fill_cards(self, values: dict) -> None:
        details = {
            "mean_length_of_utterance_words": (
                tr(f"จาก {values['mlu_utterance_count']} ประโยค", f"from {values['mlu_utterance_count']} utterances") if "mlu_utterance_count" in values else tr("คำต่อประโยค", "words per utterance")
            ),
            "number_of_different_words": (
                tr(f"จาก {values['total_word_count']} คำ", f"from {values['total_word_count']} words") if values.get("total_word_count") is not None else ""
            ),
            "type_token_ratio": (
                f"MATTR {labels.feature_value_text('mattr_50', values['mattr_50'])}"
                if values.get("mattr_50") is not None else tr("ขึ้นกับความยาวตัวอย่าง", "depends on sample length")
            ),
            "mlu_utterance_count": tr(f"แนะนำ ≥ {labels.RECOMMENDED_MLU_UTTERANCES}", f"{labels.RECOMMENDED_MLU_UTTERANCES}+ recommended"),
        }
        for name, card_widget in self.metric_cards.items():
            value = values.get(name)
            text = labels.feature_value_text(name, value) if name in values else "—"
            card_widget.set_value(text, details.get(name, ""), labels.FEATURES[name][2])

    def _fill_notices(self, features, values: dict) -> None:
        count = values.get("mlu_utterance_count", values.get("child_utterance_count"))
        short = isinstance(count, (int, float)) and count < labels.RECOMMENDED_MLU_UTTERANCES
        self.sample_notice.setVisible(short)
        if short:
            self.sample_notice.setText(
                tr(f"ตัวอย่างสั้น: {int(count)} ประโยค (CLAN แนะนำ ≥ {labels.RECOMMENDED_MLU_UTTERANCES}) "
                "ค่าอาจยังไม่นิ่ง ระวังเมื่อเทียบข้าม session", f"Short sample: {int(count)} utterances ({labels.RECOMMENDED_MLU_UTTERANCES}+ recommended). Values may not be stable across sessions.")
            )
        self.schema_notice.setVisible(features.schema_version != CURRENT_SCHEMA)

    def _fill_cues(self, result, transcript) -> None:
        while self.cue_layout.count():
            item = self.cue_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if result is None or not result.cues:
            self.cue_layout.addWidget(label(tr("ไม่มี cue จากกฎใน session นี้", "No cues in this session"), "Muted"))
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
            self.notify.emit(tr("วิเคราะห์ตัวชี้วัดเสร็จแล้ว", "Measures analysed"))
            self.changed.emit()

        def failed(exc: Exception) -> None:
            self.analyze_btn.setEnabled(True)
            self.empty_btn.setEnabled(True)
            self.report_error(exc, tr("วิเคราะห์ไม่สำเร็จ", "Analysis failed"))

        self.runner.run(lambda: self.service.analyze(session_id), on_done=done, on_error=failed)

    def set_cue(self, result, cue, status: str, note: str) -> None:
        if self.attempt(self.service.set_cue_state, result.result_id, cue.cue_code, status, note, title=tr("บันทึกไม่สำเร็จ", "Not saved")) is not None:
            self.notify.emit(tr("บันทึก cue แล้ว", "Cue saved"))
            self.changed.emit()
