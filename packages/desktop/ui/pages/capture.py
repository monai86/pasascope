"""Step 1: get the session's language sample in — record, import a file, or paste a transcript."""

from __future__ import annotations

from packages.desktop.core.i18n import tr

from pathlib import Path
import tempfile
import threading
import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from packages.desktop.ui import labels
from packages.desktop.ui.audio import Recorder
from packages.desktop.ui.pages.base import SessionPage
from packages.desktop.ui.widgets import button, card, chip, label, set_chip

AUDIO_FILTER = tr("ไฟล์เสียง (*.wav *.mp3 *.m4a *.mp4 *.webm *.ogg)", "Audio (*.wav *.mp3 *.m4a *.mp4 *.webm *.ogg)")
TEXT_FILTER = "Transcript (*.cha *.txt)"

STAGES = [
    ("Loading", tr("กำลังโหลดโมเดลถอดเสียง (ครั้งแรกใช้เวลานานกว่า)", "Loading the speech model (slower the first time)")),
    ("Running Whisper", tr("กำลังถอดเสียง", "Transcribing")),
    ("ASR Transcribing", tr("กำลังถอดเสียง", "Transcribing")),
    ("diarization", tr("กำลังแยกเสียงเด็กกับผู้ใหญ่", "Telling child from adult voices")),
    ("Formatting", tr("กำลังจัดรูปแบบ transcript", "Formatting the transcript")),
    ("acoustic", tr("กำลังวิเคราะห์ลักษณะเสียง", "Measuring the recording")),
    ("complete", tr("เสร็จแล้ว", "Done")),
]


def stage_text(stage: str) -> str:
    for key, text in STAGES:
        if key.lower() in stage.lower():
            return text
    return stage


class CapturePage(SessionPage):
    def __init__(self, service, runner, parent=None) -> None:
        super().__init__(service, runner, parent)
        self.recorder = Recorder()
        self.cancel_event: threading.Event | None = None
        self.started_at = 0.0
        self.working = False

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
        body = QWidget()
        scroll.setWidget(body)
        layout = QVBoxLayout(body)
        layout.setContentsMargins(4, 12, 4, 12)
        layout.setSpacing(14)

        # Current state of the session
        self.state_card, state = card()
        row = QHBoxLayout()
        self.state_title = label("", "SectionTitle")
        self.state_chip = chip("")
        row.addWidget(self.state_title)
        row.addStretch(1)
        row.addWidget(self.state_chip)
        state.addLayout(row)
        self.state_body = label("", "Hint", wrap=True)
        state.addWidget(self.state_body)
        self.retranscribe_btn = button(tr("ถอดเสียงไฟล์นี้อีกครั้ง", "Transcribe again"))
        self.retranscribe_btn.clicked.connect(self._retranscribe)
        self.open_review_btn = button(tr("เปิด transcript", "Open transcript"), "primary")
        self.open_review_btn.clicked.connect(lambda: self.navigate.emit(1))
        actions = QHBoxLayout()
        actions.addWidget(self.retranscribe_btn)
        actions.addStretch(1)
        actions.addWidget(self.open_review_btn)
        state.addLayout(actions)
        layout.addWidget(self.state_card)

        # Progress while transcribing
        self.progress_card, progress = card()
        self.progress_title = label(tr("กำลังถอดเสียง", "Transcribing"), "SectionTitle")
        progress.addWidget(self.progress_title)
        self.progress_stage = label("", "Hint")
        progress.addWidget(self.progress_stage)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 1000)
        self.progress_bar.setTextVisible(False)
        progress.addWidget(self.progress_bar)
        prow = QHBoxLayout()
        self.progress_time = label("", "Muted")
        prow.addWidget(self.progress_time)
        prow.addStretch(1)
        self.cancel_btn = button(tr("ยกเลิก", "Cancel"), "danger")
        self.cancel_btn.clicked.connect(self._cancel)
        prow.addWidget(self.cancel_btn)
        progress.addLayout(prow)
        progress.addWidget(label(tr("ถอดเสียงบนเครื่องนี้ทั้งหมด เสียงไม่ถูกส่งออกไปที่ใด ใช้งานส่วนอื่นของโปรแกรมระหว่างรอได้", "Runs on this computer; the recording is not sent anywhere. You can keep working meanwhile."), "Muted", wrap=True))
        self.progress_card.hide()
        layout.addWidget(self.progress_card)

        # Three ways in
        grid = QGridLayout()
        grid.setSpacing(14)

        rec_card, rec = card()
        rec.addWidget(label(tr("บันทึกเสียงจากไมโครโฟน", "Record"), "SectionTitle"))
        rec.addWidget(label(tr("วางไมโครโฟนให้ใกล้เด็ก ลดเสียงรบกวน แล้วกดเริ่ม", "Place the microphone near the child and keep background noise down."), "Muted", wrap=True))
        self.rec_time = label("00:00", "RecordTime")
        rec.addWidget(self.rec_time)
        self.level = QProgressBar()
        self.level.setRange(0, 100)
        self.level.setTextVisible(False)
        rec.addWidget(self.level)
        rrow = QHBoxLayout()
        self.rec_btn = button(tr("● เริ่มบันทึก", "● Record"), "primary")
        self.rec_btn.clicked.connect(self._toggle_recording)
        self.rec_discard = button(tr("ทิ้ง", "Discard"))
        self.rec_discard.clicked.connect(self._discard_recording)
        self.rec_discard.hide()
        rrow.addWidget(self.rec_btn)
        rrow.addWidget(self.rec_discard)
        rrow.addStretch(1)
        rec.addLayout(rrow)
        rec.addStretch(1)
        grid.addWidget(rec_card, 0, 0)

        file_card, files = card()
        files.addWidget(label(tr("นำเข้าไฟล์เสียง", "Import audio"), "SectionTitle"))
        files.addWidget(label(tr("wav, mp3, m4a, mp4, webm หรือ ogg ไม่เกิน 250 MB ระบบเก็บสำเนาไว้ในโฟลเดอร์ข้อมูลของโปรแกรม", "wav, mp3, m4a, mp4, webm or ogg, up to 250 MB. A copy is kept in PasaScope's data folder."), "Muted", wrap=True))
        files.addStretch(1)
        self.file_btn = button(tr("เลือกไฟล์เสียง…", "Choose file…"), "primary")
        self.file_btn.clicked.connect(self._choose_audio)
        files.addWidget(self.file_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        grid.addWidget(file_card, 0, 1)

        text_card, text = card()
        text.addWidget(label(tr("นำเข้า transcript ที่มีอยู่แล้ว", "Import a transcript"), "SectionTitle"))
        text.addWidget(label(tr("ไฟล์ CHAT (.cha) หรือวางข้อความทีละบรรทัด เช่น  CHI: เล่นรถ", "A CHAT file (.cha), or paste one line per utterance, such as  CHI: car go"), "Muted", wrap=True))
        self.paste = QPlainTextEdit()
        self.paste.setPlaceholderText(tr("INV: วันนี้เล่นอะไรดี\nCHI: เล่นรถ\nINV: รถสีอะไร\nCHI: สีแดง", "INV: what shall we play\nCHI: car\nINV: what colour is it\nCHI: red"))
        self.paste.setFixedHeight(110)
        text.addWidget(self.paste)
        trow = QHBoxLayout()
        self.text_file_btn = button(tr("เปิดไฟล์…", "Open file…"))
        self.text_file_btn.clicked.connect(self._choose_text)
        self.paste_btn = button(tr("นำเข้าข้อความ", "Import text"), "primary")
        self.paste_btn.clicked.connect(self._import_pasted)
        trow.addWidget(self.text_file_btn)
        trow.addStretch(1)
        trow.addWidget(self.paste_btn)
        text.addLayout(trow)
        grid.addWidget(text_card, 1, 0, 1, 2)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        layout.addLayout(grid)

        self.asr_note = label("", "Muted", wrap=True)
        layout.addWidget(self.asr_note)
        layout.addStretch(1)

        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self._tick)

    # ------------------------------------------------------------------
    def refresh(self) -> None:
        if self.session is None:
            return
        transcript = self.service.get_transcript(self.session.session_id)
        audio = self.service.session_audio(self.session.session_id)
        available, reason = self.service.transcription_availability()
        self.asr_note.setText(
            tr("ถอดเสียงด้วย Whisper บนเครื่องนี้ (โมเดลภาษาไทย)", "Transcribed with Whisper on this computer (Thai model)") if available
            else tr(f"ถอดเสียงบนเครื่องยังไม่พร้อม: {reason} ยังนำเข้า transcript ได้", f"Transcription unavailable: {reason}. Transcripts can still be imported.")
        )
        self.retranscribe_btn.setVisible(audio is not None and available)
        self.open_review_btn.setVisible(transcript is not None)
        if transcript is not None:
            n = len(transcript.utterances)
            self.state_title.setText(tr("session นี้มี transcript แล้ว", "Transcript added"))
            source = tr("ร่างจากการถอดเสียง", "Draft from the recording") if str(transcript.source).startswith("asr") else tr("นำเข้า", "Imported")
            self.state_body.setText(
                tr(f"{source} {n} ประโยค", f"{source}, {n} lines")
                + (tr(f" · ไฟล์เสียง {audio.original_filename}", f", recording {audio.original_filename}") if audio else "")
                + tr("\nบันทึกหรือนำเข้าใหม่จะแทนที่ transcript เดิม", "\nRecording or importing again replaces it.")
            )
            if transcript.therapist_attested:
                set_chip(self.state_chip, tr("รับรองแล้ว", "Attested"), "ok")
            else:
                set_chip(self.state_chip, tr("รอตรวจ", "To review"), "attention")
        elif audio is not None:
            self.state_title.setText(tr("มีไฟล์เสียงแล้ว แต่ยังไม่มี transcript", "Recording without a transcript"))
            self.state_body.setText(tr(f"{audio.original_filename} · กด ‘ถอดเสียงไฟล์นี้อีกครั้ง’ หรือนำเข้า transcript", f"{audio.original_filename}. Transcribe it again or import a transcript."))
            set_chip(self.state_chip, tr("ยังไม่ถอดเสียง", "Not transcribed"), "attention")
        else:
            self.state_title.setText(tr("เริ่มจากเก็บตัวอย่างภาษาของ session นี้", "Add this session's language sample"))
            self.state_body.setText(tr("บันทึกเสียง นำเข้าไฟล์เสียง หรือนำเข้า transcript ที่ถอดไว้แล้ว", "Record, import audio, or import a transcript you already have."))
            set_chip(self.state_chip, tr("ยังไม่มีข้อมูล", "Empty"), "neutral")
        self._set_inputs_enabled(not self.working)

    def _set_inputs_enabled(self, enabled: bool) -> None:
        for widget in (self.file_btn, self.text_file_btn, self.paste_btn, self.retranscribe_btn):
            widget.setEnabled(enabled)
        self.rec_btn.setEnabled(enabled or self.recorder.recording)

    def _confirm_replace(self) -> bool:
        if self.service.get_transcript(self.session.session_id) is None:
            return True
        answer = QMessageBox.question(
            self, tr("แทนที่ transcript เดิม?", "Replace the transcript?"),
            tr("session นี้มี transcript อยู่แล้ว ข้อมูลใหม่จะแทนที่ transcript, ตัวชี้วัด และร่างรายงานเดิม ดำเนินการต่อ?", "This session already has a transcript. The new one replaces it, its findings and the report draft. Continue?"),
        )
        return answer == QMessageBox.StandardButton.Yes

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------
    def _toggle_recording(self) -> None:
        if self.recorder.recording:
            self._finish_recording()
            return
        if not self._confirm_replace():
            return
        try:
            self.recorder.start()
        except Exception as exc:  # noqa: BLE001 - no microphone or no permission
            self.report_error(exc, tr("เปิดไมโครโฟนไม่ได้ (ตรวจสิทธิ์ไมโครโฟนใน System Settings)", "Could not open the microphone (check microphone access in System Settings)"))
            return
        self.rec_btn.setText(tr("■ หยุดและถอดเสียง", "■ Stop and transcribe"))
        self.rec_discard.show()
        self.timer.start()
        self.busy_changed.emit(True)

    def _discard_recording(self) -> None:
        self.recorder.discard()
        self._reset_recorder_ui()

    def _reset_recorder_ui(self) -> None:
        self.timer.stop()
        self.rec_btn.setText(tr("● เริ่มบันทึก", "● Record"))
        self.rec_discard.hide()
        self.rec_time.setText("00:00")
        self.level.setValue(0)
        self.busy_changed.emit(False)

    def _finish_recording(self) -> None:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        target = Path(tempfile.gettempdir()) / f"pasascope-recording-{stamp}.wav"
        path = self.recorder.stop(target)
        self._reset_recorder_ui()
        if path is None:
            QMessageBox.information(self, tr("ไม่มีเสียง", "No audio"), tr("ไม่ได้รับเสียงจากไมโครโฟน", "Nothing was heard from the microphone."))
            return
        self._store_and_transcribe(path, delete_after=True)

    # ------------------------------------------------------------------
    # Importing
    # ------------------------------------------------------------------
    def _choose_audio(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, tr("เลือกไฟล์เสียง", "Choose a recording"), str(Path.home()), AUDIO_FILTER)
        if path and self._confirm_replace():
            self._store_and_transcribe(Path(path))

    def _choose_text(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, tr("เลือก transcript", "Choose a transcript"), str(Path.home()), TEXT_FILTER)
        if not path:
            return
        try:
            text = Path(path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            self.report_error(exc, tr("อ่านไฟล์ไม่ได้ (ต้องเป็น UTF-8)", "Could not read the file (it must be UTF-8)"))
            return
        self._import_text(text, Path(path).name)

    def _import_pasted(self) -> None:
        self._import_text(self.paste.toPlainText(), "pasted.cha")

    def _import_text(self, text: str, filename: str) -> None:
        if not text.strip():
            QMessageBox.information(self, tr("ไม่มีข้อความ", "No text"), tr("วางหรือเปิด transcript ก่อน", "Paste or open a transcript first."))
            return
        if not self._confirm_replace():
            return
        result = self.attempt(self.service.import_transcript_text, self.session.session_id, text, filename=filename)
        if result is not None:
            self.paste.clear()
            self.notify.emit(tr("นำเข้า transcript แล้ว", "Transcript imported"))
            self.changed.emit()
            self.navigate.emit(1)

    def _store_and_transcribe(self, path: Path, delete_after: bool = False) -> None:
        session_id = self.session.session_id
        self._begin_work(tr("กำลังเก็บไฟล์เสียง", "Saving the recording"))

        def store():
            try:
                return self.service.store_recording(session_id, path)
            finally:
                if delete_after:
                    path.unlink(missing_ok=True)

        def stored(audio) -> None:
            self.changed.emit()
            self._transcribe(audio.audio_file_id)

        self.runner.run(store, on_done=stored, on_error=self._work_failed)

    def _retranscribe(self) -> None:
        audio = self.service.session_audio(self.session.session_id)
        if audio is not None and self._confirm_replace():
            self._begin_work(tr("กำลังเตรียมถอดเสียง", "Preparing to transcribe"))
            self._transcribe(audio.audio_file_id)

    def _transcribe(self, audio_file_id: str) -> None:
        available, reason = self.service.transcription_availability()
        if not available:
            self._end_work()
            QMessageBox.warning(self, tr("ถอดเสียงไม่ได้", "Cannot transcribe"), tr(f"เก็บไฟล์เสียงแล้ว แต่ถอดเสียงบนเครื่องยังไม่พร้อม: {reason}", f"The recording was saved, but transcription is unavailable: {reason}"))
            self.refresh()
            return
        session_id = self.session.session_id
        day = labels.day_text(self.session.session_date)
        finished_text = tr(f"ถอดเสียง {self.case.child_code} session {day} เสร็จแล้ว",
                           f"Transcribed {self.case.child_code}, session {day}")
        self.cancel_event = threading.Event()
        cancel = self.cancel_event
        self.progress_title.setText(tr(f"กำลังถอดเสียง · {self.case.child_code} · session {day}", f"Transcribing {self.case.child_code}, session {day}"))
        self.cancel_btn.setEnabled(True)

        def work(progress):
            return self.service.transcribe(session_id, audio_file_id, progress=progress, cancel=cancel)

        def done(_transcript) -> None:
            self._end_work()
            self.notify.emit(finished_text)
            self.changed.emit()
            if self.session is not None and self.session.session_id == session_id:
                self.navigate.emit(1)

        self.runner.run(work, on_done=done, on_error=self._work_failed, on_progress=self._on_progress)

    # ------------------------------------------------------------------
    # Progress
    # ------------------------------------------------------------------
    def _begin_work(self, stage: str) -> None:
        self.working = True
        self.started_at = time.monotonic()
        self.progress_stage.setText(stage)
        self.progress_bar.setValue(0)
        self.progress_card.show()
        self.timer.start()
        self._set_inputs_enabled(False)
        self.busy_changed.emit(True)

    def _end_work(self) -> None:
        self.working = False
        self.cancel_event = None
        self.progress_card.hide()
        if not self.recorder.recording:
            self.timer.stop()
        self._set_inputs_enabled(True)
        self.busy_changed.emit(False)

    def _work_failed(self, exc: Exception) -> None:
        self._end_work()
        self.refresh()
        self.report_error(exc, tr("ถอดเสียงไม่สำเร็จ", "Transcription failed"))

    def _on_progress(self, fraction: float, stage: str) -> None:
        self.progress_bar.setValue(int(max(0.0, min(1.0, fraction)) * 1000))
        self.progress_stage.setText(stage_text(stage))

    def _cancel(self) -> None:
        if self.cancel_event is not None:
            self.cancel_event.set()
            self.cancel_btn.setEnabled(False)
            self.progress_stage.setText(tr("กำลังหยุด… (รอให้ขั้นตอนปัจจุบันจบ)", "Stopping after the current step…"))

    def _tick(self) -> None:
        if self.recorder.recording:
            secs = int(self.recorder.elapsed())
            self.rec_time.setText(f"{secs // 60:02d}:{secs % 60:02d}")
            self.level.setValue(min(100, int(self.recorder.level * 400)))
        if self.working:
            secs = int(time.monotonic() - self.started_at)
            self.progress_time.setText(tr(f"ผ่านไป {secs // 60}:{secs % 60:02d} นาที", f"{secs // 60}:{secs % 60:02d} elapsed"))

    def shutdown(self) -> None:
        if self.recorder.recording:
            self.recorder.discard()
        if self.cancel_event is not None:
            self.cancel_event.set()
