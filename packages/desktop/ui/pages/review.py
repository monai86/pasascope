"""Step 2: correct the draft against the recording, then attest it.

Keys while the table has focus: Space plays the selected utterance,
Ctrl+1 marks it as the child, Ctrl+2 as the adult, Enter edits the text,
Ctrl+S saves.

The words column shows what CLAN's rules count in each utterance, so the
therapist sees the effect of a CHAT code (xxx, [/], &-...) as soon as it is
typed. The code buttons insert those codes around the selected words.
"""

from __future__ import annotations

from packages.desktop.core.i18n import tr

from collections import Counter
from functools import partial
from pathlib import Path
import uuid

from PySide6.QtCore import QModelIndex, Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLineEdit,
    QMessageBox,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from packages.cha.clan_words import MainTierAnalysis, analyze_main_tier, chat_code_problems
from packages.desktop.core import QaOverrideRequired
from packages.desktop.ui import labels, theme
from packages.desktop.ui.audio import SegmentPlayer, waveform_peaks
from packages.desktop.ui.pages.base import SessionPage
from packages.desktop.ui.widgets import EmptyState, WaveformView, button, chip, label, set_chip
from packages.features.language_sample import compute_language_sample_measures

COL_TIME, COL_SPEAKER, COL_TEXT, COL_WORDS, COL_CONF = range(5)
LOW_CONFIDENCE = 0.6
ADULT = "INV"

# (button text, what it does, action) for the CHAT code buttons.
CHAT_CODES = [
    (tr("ฟังไม่ออก xxx", "Unintelligible xxx"), tr("ใส่แทนคำที่ฟังไม่ออก ประโยคนี้จะไม่ถูกนับใน MLU", "Replaces a word you cannot make out; the utterance is left out of MLU"), "xxx"),
    (tr("พูดซ้ำ [/]", "Repetition [/]"), tr("เลือกคำที่พูดซ้ำครั้งแรกก่อน ส่วนที่เลือกจะไม่ถูกนับ", "Select the first saying of the repeated words; they will not be counted"), "[/]"),
    (tr("พูดแก้ [//]", "Retracing [//]"), tr("เลือกคำที่พูดผิดแล้วพูดแก้ ส่วนที่เลือกจะไม่ถูกนับ", "Select the words the child corrected; they will not be counted"), "[//]"),
    (tr("คำเติม &-", "Filler &-"), tr("เช่น อือ เอ่อ ไม่นับเป็นคำ", "Such as um or uh; not counted as a word"), "&-"),
    (tr("ตั้งใจพูดว่า [: ]", "Target [: ]"), tr("เลือกคำที่พูดเพี้ยน แล้วพิมพ์คำที่ตั้งใจพูดในวงเล็บ ระบบนับคำที่ตั้งใจพูด", "Select a mispronounced word, then type the intended word; the intended word is counted"), "[: ]"),
    (tr("คำผิด [*]", "Error [*]"), tr("ทำเครื่องหมายคำที่ใช้ผิด นับใน Word_Errors", "Marks a word used in error; counted in word errors"), "[*]"),
    (tr("ไม่นับประโยค [+ exc]", "Exclude [+ exc]"), tr("ตัดประโยคนี้ออกจากตัวชี้วัดทั้งหมด", "Leaves this utterance out of every measure"), "[+ exc]"),
]


def apply_chat_code(text: str, start: int, length: int, code: str) -> tuple[str, int]:
    """Insert ``code`` at the selection; return the new text and cursor position."""
    before, chosen, after = text[:start], text[start:start + length].strip(), text[start + length:]
    if code == "[+ exc]":
        if "[+ exc]" in text:
            return text, len(text)
        new = f"{text.rstrip()} [+ exc]"
        return new, len(new)
    if code == "xxx":
        insert = "xxx"
    elif code == "&-":
        insert = f"&-{chosen}"
    elif code == "[: ]":
        insert = f"{chosen} [: ]" if chosen else "[: ]"
    else:
        scope = f"<{chosen}>" if " " in chosen else chosen
        insert = f"{scope} {code}" if scope else code
    if before and not before.endswith(" "):
        insert = " " + insert
    if after and not after.startswith(" "):
        insert = insert + " "
    cursor = len(before) + len(insert.rstrip())
    if code == "[: ]":
        cursor -= 1  # inside the brackets, ready to type the target word
    return before + insert + after, cursor


def word_cell(utt) -> tuple[str, str, bool]:
    """(text, tooltip, counts for the child) for the words column."""
    problems = chat_code_problems(utt.text)
    if problems:
        return tr("⚠ ตรวจรหัส", "⚠ Check codes"), tr("รหัส CHAT อาจเขียนผิด ระบบจะนับคำผิด:\n", "A CHAT code may be malformed, so words will be miscounted:\n") + "\n".join(f"• {p}" for p in problems), False
    if str(utt.speaker) != "CHI":
        return "", tr("ผู้ใหญ่: ไม่ใช้คิดตัวชี้วัดของเด็ก", "Adult line: not used in the child's measures"), False
    analysis = analyze_main_tier(utt.text)
    lines = [tr(f"นับ {len(analysis.words)} คำ: {' '.join(analysis.words) or '—'}", f"{len(analysis.words)} counted: {' '.join(analysis.words) or '—'}")]
    if analysis.excluded:
        lines.append(tr("ประโยคนี้ไม่ถูกนับในตัวชี้วัดใด ([+ exc] หรือ www)", "Not counted in any measure ([+ exc] or www)"))
        return tr("ไม่นับ", "Excluded"), "\n".join(lines), False
    dropped = Counter(analysis.spoken_words) - Counter(analysis.words)
    if dropped:
        lines.append(tr("ไม่นับส่วนที่พูดซ้ำหรือพูดแก้: ", "Not counted (repeated or retraced): ") + " ".join(dropped.elements()))
    if "&-" in utt.text or "&+" in utt.text:
        lines.append(tr("ไม่นับคำเติมและคำที่พูดไม่จบ (&-, &+)", "Fillers and fragments are not counted (&-, &+)"))
    if analysis.mlu_excluded:
        lines.append(tr("มีคำที่ฟังไม่ออก จึงไม่ใช้คิด MLU แต่ยังนับคำอื่นในจำนวนคำ", "Has an unintelligible word, so it is left out of MLU; its other words still count"))
        return tr(f"{len(analysis.words)} · ไม่คิด MLU", f"{len(analysis.words)}, not in MLU"), "\n".join(lines), True
    return str(len(analysis.words)), "\n".join(lines), True


# How the pipeline's explanations begin, in either language (utterance_boundaries, clinic_speaker_model).
BOUNDARY_MARKS = ("ขึ้นประโยคใหม่", "New utterance")
SPEAKER_MARKS = ("โมเดลประจำคลินิก", "Clinic model")


def _from_mark(notes: str, marks: tuple[str, ...]) -> str:
    found = [notes.index(mark) for mark in marks if mark in notes]
    return notes[min(found):].strip() if found else ""


def note_parts(notes: str | None) -> tuple[str, str]:
    """(why the utterance starts here, why the clinic model chose the speaker), from the draft's notes."""
    notes = notes or ""
    speaker = _from_mark(notes, SPEAKER_MARKS)
    boundary = _from_mark(notes, BOUNDARY_MARKS).replace(speaker, "").strip()
    return boundary, speaker


def explain_utterance(utt) -> list[tuple[str, str]]:
    """What the inspector shows for one utterance: (heading, text) pairs a therapist can check."""
    boundary, speaker_note = note_parts(utt.notes)
    speaker = labels.SPEAKER_LABELS.get(str(utt.speaker), str(utt.speaker))
    if getattr(utt, "review_status", "") == "reviewed" and not utt.speaker_uncertain:
        speaker_why = tr("นักบำบัดยืนยันแล้ว", "Confirmed by the therapist")
    elif utt.speaker_uncertain:
        speaker_why = (tr("ระบบไม่แน่ใจ: เสียงสั้น ระดับเสียงก้ำกึ่ง หรืออายุเด็กอยู่นอกช่วงที่ระบบตรวจแล้ว (2;6–6;11 ปี)"
                       " ฟังแล้วยืนยันก่อน", "Uncertain: the line is short, the voice is borderline, or the child is outside the checked ages (2;6 to 6;11). Listen and confirm."))
    elif str(utt.source) == "asr":
        speaker_why = tr("ระบบมั่นใจจากโมเดลแยกเสียงเด็ก/ผู้ใหญ่", "Labelled with confidence by the child/adult voice model")
    else:
        speaker_why = tr("มาจาก transcript ที่นำเข้าหรือพิมพ์เอง", "From an imported or typed transcript")
    rows = [(tr("ผู้พูด", "Speaker"), f"{speaker} · {speaker_why}")]
    if speaker_note:
        rows.append((tr("เหตุผลของโมเดลประจำคลินิก", "Clinic model"), speaker_note))
    if boundary:
        rows.append((tr("ทำไมขึ้นประโยคใหม่ตรงนี้", "Why a new utterance starts here"), boundary))
    elif str(utt.source) == "asr":
        rows.append((tr("ทำไมขึ้นประโยคใหม่ตรงนี้", "Why a new utterance starts here"), tr("ผู้พูดเปลี่ยน หรือหยุดพูดนานกว่า 0.6 วินาที (ร่างภาษาไทยใช้กฎช่วงหยุด)", "The speaker changed, or paused for more than 0.6 s (Thai drafts use this pause rule)")))
    words, words_why, _ = word_cell(utt)
    rows.append((tr("คำที่นับ", "Counted"), words_why if words_why else "—"))
    if utt.confidence is not None:
        sure = tr("ต่ำ ฟังทวนคำในประโยคนี้", "low; listen to this line again") if utt.confidence < LOW_CONFIDENCE else tr("ปกติ", "normal")
        rows.append((tr("ความมั่นใจของการถอดเสียง", "Transcription confidence"), f"{utt.confidence * 100:.0f}% · {sure}"))
    return rows


def _fmt(ms: int | None) -> str:
    if ms is None:
        return "—"
    seconds = ms / 1000
    return f"{int(seconds // 60):02d}:{seconds % 60:04.1f}"


class UtteranceInspector(QWidget):
    """Side panel: how the system reached each part of the selected utterance, in plain Thai."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Panel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedWidth(300)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 12, 14, 12)
        outer.setSpacing(4)
        self.title = label(tr("รายละเอียดประโยค", "Line details"), "SectionTitle")
        outer.addWidget(self.title)
        self.when = label(tr("เลือกประโยคในตารางเพื่อดูว่าระบบตัดสินแต่ละส่วนอย่างไร", "Select a line to see how it was labelled, cut and counted."), "Muted", wrap=True)
        outer.addWidget(self.when)
        self.rows = QVBoxLayout()
        self.rows.setSpacing(2)
        outer.addLayout(self.rows)
        outer.addStretch(1)

    def show_utterance(self, utt, number: int | None = None) -> None:
        while self.rows.count():
            item = self.rows.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if utt is None:
            self.title.setText(tr("รายละเอียดประโยค", "Line details"))
            self.when.setText(tr("เลือกประโยคในตารางเพื่อดูว่าระบบตัดสินแต่ละส่วนอย่างไร", "Select a line to see how it was labelled, cut and counted."))
            return
        self.title.setText(tr(f"ประโยคที่ {number}", f"Line {number}"))
        self.when.setText(f"{_fmt(utt.start_ms)} – {_fmt(utt.end_ms)}")
        for heading, text in explain_utterance(utt):
            key = label(heading, "InspectorKey")
            key.setContentsMargins(0, 8, 0, 0)
            value = label(text, "InspectorValue", wrap=True)
            value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            self.rows.addWidget(key)
            self.rows.addWidget(value)


class SpeakerDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):  # noqa: N802 - Qt override
        combo = QComboBox(parent)
        for code, text in labels.SPEAKERS:
            combo.addItem(text, code)
        return combo

    def setEditorData(self, editor, index):  # noqa: N802 - Qt override
        code = index.data(Qt.ItemDataRole.UserRole)
        position = editor.findData(code)
        editor.setCurrentIndex(max(0, position))
        editor.showPopup()

    def setModelData(self, editor, model, index):  # noqa: N802 - Qt override
        model.setData(index, editor.currentData(), Qt.ItemDataRole.UserRole)
        model.setData(index, editor.currentText(), Qt.ItemDataRole.DisplayRole)


class ReviewPage(SessionPage):
    attested = Signal()  # the therapist attested a transcript; the clinic speaker model may learn from it

    def __init__(self, service, runner, parent=None) -> None:
        super().__init__(service, runner, parent)
        self.transcript = None
        self.utterances: list = []
        self.dirty = False
        self.audio_wav: Path | None = None
        self.player = SegmentPlayer()
        self._loading = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 12, 4, 8)
        layout.setSpacing(10)

        self.empty = EmptyState(tr("ยังไม่มี transcript", "No transcript yet"), tr("บันทึกหรือนำเข้าเสียงในขั้นที่ 1 ก่อน", "Record or import audio first."))
        go = button(tr("ไปที่ขั้นเสียง", "Go to Recording"), "primary")
        go.clicked.connect(lambda: self.navigate.emit(0))
        self.empty.actions.addWidget(go)
        layout.addWidget(self.empty)

        self.body = QWidget()
        body = QVBoxLayout(self.body)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(10)
        layout.addWidget(self.body)

        top = QHBoxLayout()
        self.status_chip = chip("")
        top.addWidget(self.status_chip)
        self.summary = label("", "Hint")
        top.addWidget(self.summary)
        top.addStretch(1)
        self.save_btn = button(tr("บันทึกการแก้ไข", "Save"), tooltip="Ctrl+S")
        self.save_btn.clicked.connect(self.save)
        self.attest_btn = button(tr("รับรอง transcript", "Attest"), "primary")
        self.attest_btn.clicked.connect(self._attest)
        top.addWidget(self.save_btn)
        top.addWidget(self.attest_btn)
        body.addLayout(top)

        self.notice = label("", wrap=True)
        self.notice.setStyleSheet(
            f"background: {theme.ATTENTION_SOFT}; color: {theme.ATTENTION}; border-radius: 8px; padding: 8px 12px;"
        )
        self.notice.hide()
        body.addWidget(self.notice)

        self.wave = WaveformView()
        self.wave.setFixedHeight(96)
        self.wave.seek.connect(self._play_from)
        body.addWidget(self.wave)

        controls = QHBoxLayout()
        self.play_btn = button(tr("▶ เล่น", "▶ Play"), tooltip=tr("เล่นประโยคที่เลือก (Space)", "Play the selected line (Space)"))
        self.play_btn.clicked.connect(self.play_selected)
        self.stop_btn = button(tr("■ หยุด", "■ Stop"))
        self.stop_btn.clicked.connect(self.stop_playback)
        self.autoplay = QCheckBox(tr("เล่นเมื่อเลือก", "Play on select"))
        self.autoplay.setToolTip(tr("เล่นเสียงทันทีเมื่อเลือกประโยค", "Play a line as soon as it is selected"))
        self.autoplay.setChecked(True)
        controls.addWidget(self.play_btn)
        controls.addWidget(self.stop_btn)
        controls.addWidget(self.autoplay)
        controls.addStretch(1)
        self.child_btn = button(tr("เป็นเด็ก", "Child"), tooltip="Ctrl+1")
        self.child_btn.clicked.connect(lambda: self.set_speaker("CHI"))
        self.adult_btn = button(tr("เป็นผู้ใหญ่", "Adult"), tooltip="Ctrl+2")
        self.adult_btn.clicked.connect(lambda: self.set_speaker(ADULT))
        self.swap_btn = button(tr("สลับทั้งหมด", "Swap all"), tooltip=tr("สลับเด็กกับผู้ใหญ่ทุกประโยค", "Swap child and adult on every line"))
        self.swap_btn.clicked.connect(self._swap_all)
        self.insert_btn = button(tr("+ แทรก", "Insert"), tooltip=tr("แทรกประโยคใต้แถวที่เลือก", "Insert a line below the selected one"))
        self.insert_btn.clicked.connect(self._insert_row)
        self.delete_btn = button(tr("ลบ", "Delete"), "danger", tooltip=tr("ลบประโยคที่เลือก", "Delete the selected lines"))
        self.delete_btn.clicked.connect(self._delete_rows)
        for widget in (self.child_btn, self.adult_btn, self.swap_btn, self.insert_btn, self.delete_btn):
            controls.addWidget(widget)
        body.addLayout(controls)

        codes = QHBoxLayout()
        codes.setSpacing(6)
        codes.addWidget(label(tr("รหัส CHAT", "CHAT"), "Hint"))
        for text, tip, code in CHAT_CODES:
            code_btn = button(text.replace("&", "&&"), tooltip=tip)  # "&" alone marks a Qt mnemonic
            # Keep focus in the open text editor so the code lands at its cursor.
            code_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            code_btn.clicked.connect(partial(self.insert_code, code))
            codes.addWidget(code_btn)
        codes.addStretch(1)
        body.addLayout(codes)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([tr("เวลา", "Time"), tr("ผู้พูด", "Speaker"), tr("ข้อความ", "Text"), tr("คำที่นับ", "Counted"), tr("ความมั่นใจ", "Confidence")])
        self.table.verticalHeader().setDefaultSectionSize(34)
        self.table.verticalHeader().setVisible(True)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(COL_TIME, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(COL_SPEAKER, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(COL_TEXT, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(COL_WORDS, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(COL_CONF, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setColumnWidth(COL_SPEAKER, 150)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
            | QAbstractItemView.EditTrigger.AnyKeyPressed
        )
        self.table.setItemDelegateForColumn(COL_SPEAKER, SpeakerDelegate(self.table))
        self.table.itemChanged.connect(self._on_item_changed)
        self.table.itemSelectionChanged.connect(self._on_selection)
        table_row = QHBoxLayout()
        table_row.setSpacing(10)
        table_row.addWidget(self.table, 1)
        self.inspector = UtteranceInspector()
        table_row.addWidget(self.inspector)
        body.addLayout(table_row, 1)

        hint = label(
            tr("Space เล่น    Enter แก้ข้อความ    Ctrl+1 เด็ก    Ctrl+2 ผู้ใหญ่    Ctrl+S บันทึก", "Space play    Enter edit    Ctrl+1 child    Ctrl+2 adult    Ctrl+S save"),
            "Muted", wrap=True,
        )
        body.addWidget(hint)

        for keys, slot in (
            ("Ctrl+S", self.save),
            ("Ctrl+1", lambda: self.set_speaker("CHI")),
            ("Ctrl+2", lambda: self.set_speaker(ADULT)),
        ):
            shortcut = QShortcut(QKeySequence(keys), self)
            shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            shortcut.activated.connect(slot)
        space = QShortcut(QKeySequence(Qt.Key.Key_Space), self.table)
        space.setContext(Qt.ShortcutContext.WidgetShortcut)
        space.activated.connect(self.play_selected)

        self.timer = QTimer(self)
        self.timer.setInterval(60)
        self.timer.timeout.connect(self._update_playhead)

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------
    def refresh(self) -> None:
        self.stop_playback()
        self.transcript = self.service.get_transcript(self.session.session_id) if self.session else None
        has = self.transcript is not None
        self.empty.setVisible(not has)
        if not has and self.session is not None:
            self.empty.set_steps(0)
        self.body.setVisible(has)
        if not has:
            self.utterances = []
            self.dirty = False
            return
        self.utterances = [u.model_copy(deep=True) for u in self.transcript.utterances]
        self.dirty = False
        self._fill_table()
        self._update_status()
        self._load_audio()

    def _fill_table(self) -> None:
        self._loading = True
        self.table.setRowCount(len(self.utterances))
        for row, utt in enumerate(self.utterances):
            self._fill_row(row, utt)
        self._loading = False

    def _fill_row(self, row: int, utt) -> None:
        time_item = QTableWidgetItem(_fmt(utt.start_ms))
        time_item.setFlags(time_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        time_item.setForeground(QBrush(QColor(theme.MUTED)))
        boundary_note, speaker_note = note_parts(utt.notes)
        if boundary_note:  # why the draft started a new utterance here (boundary model)
            time_item.setToolTip(boundary_note)
        speaker = str(utt.speaker)
        uncertain = bool(getattr(utt, "speaker_uncertain", False))
        speaker_item = QTableWidgetItem(labels.SPEAKER_LABELS.get(speaker, speaker) + ("  ?" if uncertain else ""))
        speaker_item.setData(Qt.ItemDataRole.UserRole, speaker)
        speaker_item.setForeground(QBrush(QColor(theme.ATTENTION if uncertain else theme.SPEAKER_COLORS.get(speaker, theme.INK))))
        speaker_tip = []
        if uncertain:
            speaker_tip.append(tr("ระบบไม่แน่ใจผู้พูด ฟังแล้วยืนยันก่อน", "Speaker uncertain; listen and confirm"))
        if speaker_note:  # the clinic model's reasons: its probability and similar attested utterances
            speaker_tip.append(speaker_note)
        if speaker_tip:
            speaker_item.setToolTip("\n".join(speaker_tip))
        text_item = QTableWidgetItem(utt.text)
        conf = utt.confidence
        conf_item = QTableWidgetItem("—" if conf is None else f"{conf * 100:.0f}%")
        conf_item.setFlags(conf_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        low = conf is not None and conf < LOW_CONFIDENCE
        for item in (time_item, speaker_item, text_item, conf_item):
            if low or utt.unintelligible:
                item.setBackground(QBrush(QColor(theme.ATTENTION_SOFT)))
        self.table.setItem(row, COL_TIME, time_item)
        self.table.setItem(row, COL_SPEAKER, speaker_item)
        self.table.setItem(row, COL_TEXT, text_item)
        self.table.setItem(row, COL_CONF, conf_item)
        self._fill_word_cell(row, utt)

    def _fill_word_cell(self, row: int, utt) -> None:
        text, tooltip, counted = word_cell(utt)
        item = QTableWidgetItem(text)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        item.setToolTip(tooltip)
        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        if text.startswith("⚠"):
            item.setForeground(QBrush(QColor(theme.DANGER)))
        elif not counted or text.endswith("MLU"):
            item.setForeground(QBrush(QColor(theme.ATTENTION if text else theme.MUTED)))
        loading, self._loading = self._loading, True
        self.table.setItem(row, COL_WORDS, item)
        self._loading = loading

    def _load_audio(self) -> None:
        self.audio_wav = None
        audio = self.service.session_audio(self.session.session_id)
        has_times = any(u.start_ms is not None for u in self.utterances)
        for widget in (self.play_btn, self.stop_btn, self.autoplay):
            widget.setEnabled(audio is not None and has_times)
        if audio is None:
            self.wave.set_message(tr("session นี้ไม่มีไฟล์เสียง (transcript นำเข้าจากข้อความ)", "No recording for this session (imported transcript)"))
            return
        self.wave.set_message(tr("กำลังโหลดคลื่นเสียง…", "Loading waveform…"))
        session_id = self.session.session_id

        def load():
            path = self.service.playback_path(audio)
            peaks, duration = waveform_peaks(path)
            return path, peaks, duration

        def loaded(result) -> None:
            if self.session is None or self.session.session_id != session_id:
                return
            path, peaks, duration = result
            self.audio_wav = path
            self.wave.set_audio(peaks, duration)
            self._update_regions()

        def failed(exc: Exception) -> None:
            self.wave.set_message(tr(f"เปิดไฟล์เสียงไม่ได้: {exc}", f"Could not open the recording: {exc}"))

        self.runner.run(load, on_done=loaded, on_error=failed)

    def _update_regions(self) -> None:
        self.wave.set_regions([
            (u.start_ms / 1000, u.end_ms / 1000, str(u.speaker))
            for u in self.utterances
            if u.start_ms is not None and u.end_ms is not None
        ])

    def _update_status(self) -> None:
        attested = bool(self.transcript and self.transcript.therapist_attested) and not self.dirty
        n_child = sum(1 for u in self.utterances if str(u.speaker) == "CHI")
        n_unknown = sum(1 for u in self.utterances if str(u.speaker) == "UNK")
        n_low = sum(1 for u in self.utterances if u.confidence is not None and u.confidence < LOW_CONFIDENCE)
        n_guessed = sum(1 for u in self.utterances if getattr(u, "speaker_uncertain", False))
        parts = [tr(f"{len(self.utterances)} ประโยค", f"{len(self.utterances)} lines"), tr(f"เด็ก {n_child}", f"child {n_child}")]
        analyses: list[MainTierAnalysis] = [
            analyze_main_tier(u.text) for u in self.utterances if str(u.speaker) == "CHI"
        ]
        if analyses:
            live = compute_language_sample_measures(analyses, include_vocd=False)
            parts.append(tr(f"คำของเด็ก {live.freq_tokens}", f"child words {live.freq_tokens}"))
            if live.mlu_words is not None:
                parts.append(f"MLU {live.mlu_words:.2f}")
        if n_unknown:
            parts.append(tr(f"ยังไม่ระบุผู้พูด {n_unknown}", f"no speaker {n_unknown}"))
        if n_low:
            parts.append(tr(f"ไม่มั่นใจ {n_low}", f"low confidence {n_low}"))
        if n_guessed:
            parts.append(tr(f"ผู้พูดที่ควรเช็ก {n_guessed}", f"speakers to check {n_guessed}"))
        self.summary.setText(" · ".join(parts))
        if self.dirty:
            set_chip(self.status_chip, tr("มีการแก้ไขที่ยังไม่บันทึก", "Unsaved changes"), "attention")
        elif attested:
            set_chip(self.status_chip, tr("รับรองแล้ว", "Attested"), "ok")
        else:
            set_chip(self.status_chip, tr("รอตรวจและรับรอง", "To review"), "attention")
        self.save_btn.setEnabled(self.dirty)
        self.attest_btn.setEnabled(not attested)
        self.attest_btn.setText(tr("บันทึกและรับรอง", "Save and attest") if self.dirty else tr("รับรอง transcript", "Attest"))
        notes = []
        n_bad_codes = sum(1 for u in self.utterances if chat_code_problems(u.text))
        if n_bad_codes:
            notes.append(tr(f"มี {n_bad_codes} ประโยคที่รหัส CHAT อาจเขียนผิด (ดูช่อง \"คำที่นับ\" ที่ขึ้น ⚠) ระบบจะนับคำของประโยคนั้นผิด", f"{n_bad_codes} lines may have malformed CHAT codes (marked ⚠ under Counted); their words will be miscounted."))
        if n_unknown:
            notes.append(tr(f"มี {n_unknown} ประโยคที่ยังไม่ระบุผู้พูด ระบุให้ครบก่อนรับรอง", f"{n_unknown} lines have no speaker. Set them before attesting."))
        if self.transcript and self.transcript.therapist_attested and self.dirty:
            notes.append(tr("การแก้ไขหลังรับรองจะยกเลิกการรับรอง และตัวชี้วัดกับร่างรายงานเดิมต้องทำใหม่", "Editing withdraws the attestation; the findings and report draft will need redoing."))
        self.notice.setText("\n".join(notes))
        self.notice.setVisible(bool(notes))

    def has_unsaved_changes(self) -> bool:
        return self.dirty

    # ------------------------------------------------------------------
    # Editing
    # ------------------------------------------------------------------
    def _mark_dirty(self) -> None:
        self.dirty = True
        self._update_status()
        self._refresh_inspector()

    def _refresh_inspector(self) -> None:
        """Show the selected utterance again after an edit, without playing it."""
        rows = self._selected_rows()
        if len(rows) == 1 and rows[0] < len(self.utterances):
            self.inspector.show_utterance(self.utterances[rows[0]], rows[0] + 1)

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._loading:
            return
        row = item.row()
        if row >= len(self.utterances):
            return
        utt = self.utterances[row]
        if item.column() == COL_TEXT:
            text = item.text().strip()
            if text != utt.text:
                self.utterances[row] = utt.model_copy(update={"text": text, "review_status": "reviewed"})
                self._fill_word_cell(row, self.utterances[row])
                self._mark_dirty()
        elif item.column() == COL_SPEAKER:
            code = item.data(Qt.ItemDataRole.UserRole)
            if code and code != str(utt.speaker):
                self.utterances[row] = utt.model_copy(update={"speaker": code, "review_status": "reviewed", "speaker_uncertain": False})
                item.setForeground(QBrush(QColor(theme.SPEAKER_COLORS.get(code, theme.INK))))
                self._fill_word_cell(row, self.utterances[row])
                self._update_regions()
                self._mark_dirty()

    def insert_code(self, code: str) -> None:
        """Put a CHAT code around the words selected in the open text editor."""
        editor = self._text_editor()
        if editor is None:
            rows = self._selected_rows()
            if not rows:
                return
            item = self.table.item(rows[0], COL_TEXT)
            self.table.setCurrentItem(item)
            self.table.editItem(item)
            editor = self._text_editor()
            if editor is None:
                return
            editor.end(False)
        start = editor.selectionStart() if editor.hasSelectedText() else editor.cursorPosition()
        length = len(editor.selectedText()) if editor.hasSelectedText() else 0
        text, cursor = apply_chat_code(editor.text(), start, length, code)
        editor.setText(text)
        editor.setCursorPosition(cursor)
        editor.setFocus()

    def _text_editor(self) -> QLineEdit | None:
        widget = QApplication.focusWidget()
        if isinstance(widget, QLineEdit) and self.table.isAncestorOf(widget):
            return widget
        return None

    def _selected_rows(self) -> list[int]:
        return sorted({index.row() for index in self.table.selectionModel().selectedRows()})

    def set_speaker(self, code: str) -> None:
        rows = self._selected_rows()
        if not rows:
            return
        self._loading = True
        for row in rows:
            utt = self.utterances[row]
            self.utterances[row] = utt.model_copy(update={"speaker": code, "review_status": "reviewed", "speaker_uncertain": False})
            self._fill_row(row, self.utterances[row])
        self._loading = False
        self._update_regions()
        self._mark_dirty()
        nxt = rows[-1] + 1
        if len(rows) == 1 and nxt < self.table.rowCount():
            self.table.selectRow(nxt)

    def _swap_all(self) -> None:
        swapped = []
        for utt in self.utterances:
            speaker = str(utt.speaker)
            if speaker == "CHI":
                swapped.append(utt.model_copy(update={"speaker": ADULT}))
            elif speaker in ("INV", "MOT", "FAT", "THER"):
                swapped.append(utt.model_copy(update={"speaker": "CHI"}))
            else:
                swapped.append(utt)
        self.utterances = swapped
        self._fill_table()
        self._update_regions()
        self._mark_dirty()

    def _insert_row(self) -> None:
        from app.schemas.clinical import Utterance

        rows = self._selected_rows()
        at = rows[-1] + 1 if rows else len(self.utterances)
        before = self.utterances[at - 1] if at > 0 else None
        new = Utterance(
            utterance_id=f"utt_{uuid.uuid4().hex[:10]}",
            speaker="CHI",
            text="",
            start_ms=before.end_ms if before else None,
            end_ms=before.end_ms if before else None,
            source="manual",
            review_status="reviewed",
        )
        self.utterances.insert(at, new)
        self._fill_table()
        self._mark_dirty()
        self.table.selectRow(at)
        self.table.editItem(self.table.item(at, COL_TEXT))

    def _delete_rows(self) -> None:
        rows = self._selected_rows()
        if not rows:
            return
        answer = QMessageBox.question(self, tr("ลบประโยค", "Delete lines"), tr(f"ลบ {len(rows)} ประโยคที่เลือก?", f"Delete {len(rows)} selected lines?"))
        if answer != QMessageBox.StandardButton.Yes:
            return
        for row in reversed(rows):
            del self.utterances[row]
        self._fill_table()
        self._update_regions()
        self._mark_dirty()

    def save(self) -> bool:
        if not self.dirty or self.transcript is None:
            return True
        empty = [i + 1 for i, u in enumerate(self.utterances) if not u.text.strip()]
        if empty:
            QMessageBox.warning(self, tr("มีประโยคว่าง", "Empty lines"), tr(f"ใส่ข้อความหรือลบแถวที่ {', '.join(map(str, empty[:10]))} ก่อนบันทึก", f"Fill in or delete line {', '.join(map(str, empty[:10]))} before saving."))
            return False
        saved = self.attempt(self.service.save_utterances, self.transcript.transcript_id, self.utterances, title=tr("บันทึกไม่สำเร็จ", "Not saved"))
        if saved is None:
            return False
        selected = self._selected_rows()
        self.dirty = False
        self.changed.emit()
        if selected and selected[0] < self.table.rowCount():
            self.table.selectRow(selected[0])
        return True

    def _attest(self) -> None:
        if not self.save():
            return
        if any(str(u.speaker) == "UNK" for u in self.utterances):
            QMessageBox.warning(self, tr("ยังรับรองไม่ได้", "Cannot attest yet"), tr("ระบุผู้พูดให้ครบทุกประโยคก่อน (แถวที่เป็น ‘ยังไม่ระบุ’)", "Set a speaker on every line first (lines marked Not set)."))
            return
        if not self.service.therapist_name:
            self.ask_name.emit()
            if not self.service.therapist_name:
                return
        answer = QMessageBox.question(
            self, tr("รับรอง transcript", "Attest"),
            tr(f"ยืนยันว่า {self.service.therapist_name} ตรวจ transcript นี้กับเสียงแล้ว และผู้พูดถูกต้อง?", f"Confirm that {self.service.therapist_name} has checked this transcript against the recording and the speakers are right?"),
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        transcript_id = self.service.get_transcript(self.session.session_id).transcript_id
        try:
            self.service.attest(transcript_id)
        except QaOverrideRequired as exc:
            issues = "\n".join(f"• {i.message}" for i in exc.issues if getattr(i, "blocking", False)) or "\n".join(
                f"• {i.message}" for i in exc.issues[:8]
            )
            reason, ok = QInputDialog.getMultiLineText(
                self, tr("transcript ไม่ผ่านการตรวจรูปแบบ", "Transcript failed the format check"),
                tr(f"{issues}\n\nถ้าตรวจแล้วว่ายังใช้วิเคราะห์ได้ ระบุเหตุผลเพื่อรับรอง (บันทึกใน audit log):", f"{issues}\n\nIf it can still be analysed, give the reason for attesting (kept in the audit log):"),
            )
            if not ok or not reason.strip():
                return
            if self.attempt(self.service.attest, transcript_id, override_reason=reason, title=tr("รับรองไม่สำเร็จ", "Not attested")) is None:
                return
        except Exception as exc:  # noqa: BLE001
            self.report_error(exc, tr("รับรองไม่สำเร็จ", "Not attested"))
            return
        self.attested.emit()
        self.changed.emit()
        self.navigate.emit(2)

    # ------------------------------------------------------------------
    # Playback
    # ------------------------------------------------------------------
    def _on_selection(self) -> None:
        rows = self._selected_rows()
        if len(rows) != 1 or rows[0] >= len(self.utterances):
            self.wave.set_selected(None)
            self.inspector.show_utterance(None)
            return
        utt = self.utterances[rows[0]]
        self.inspector.show_utterance(utt, rows[0] + 1)
        if utt.start_ms is not None and utt.end_ms is not None:
            self.wave.set_selected((utt.start_ms / 1000, utt.end_ms / 1000))
            if self.autoplay.isChecked() and self.audio_wav is not None and not self._loading:
                self.play_selected()
        else:
            self.wave.set_selected(None)

    def play_selected(self) -> None:
        rows = self._selected_rows()
        if not rows or self.audio_wav is None:
            return
        first, last = self.utterances[rows[0]], self.utterances[rows[-1]]
        if first.start_ms is None:
            return
        end = last.end_ms if last.end_ms is not None else first.start_ms + 5000
        self._play(first.start_ms / 1000, end / 1000 + 0.15)

    def _play_from(self, seconds: float) -> None:
        if self.audio_wav is None:
            return
        for row, utt in enumerate(self.utterances):
            if utt.start_ms is not None and utt.end_ms is not None and utt.start_ms / 1000 <= seconds <= utt.end_ms / 1000:
                self._loading = True
                self.table.selectRow(row)
                self._loading = False
                break
        self._play(seconds, None)

    def _play(self, start: float, end: float | None) -> None:
        try:
            self.player.play(self.audio_wav, max(0.0, start - 0.05), end)
        except Exception as exc:  # noqa: BLE001 - no output device
            self.report_error(exc, tr("เล่นเสียงไม่ได้", "Cannot play audio"))
            return
        self.timer.start()

    def stop_playback(self) -> None:
        self.player.stop()
        self.timer.stop()
        self.wave.set_playhead(None)

    def _update_playhead(self) -> None:
        position = self.player.position()
        self.wave.set_playhead(position)
        if position is None:
            self.timer.stop()

    def shutdown(self) -> None:
        self.stop_playback()
