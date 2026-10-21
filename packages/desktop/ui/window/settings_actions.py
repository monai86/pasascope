"""The Settings and Help menus: names, transcription mode, language, the clinic's voice model, audit log and About.

Part of :class:`packages.desktop.ui.main_window.MainWindow`."""

from __future__ import annotations

from PySide6.QtWidgets import QInputDialog, QMessageBox

from packages.desktop.core.i18n import tr
from packages.desktop.ui import dialogs, labels


class SettingsActionsMixin:
    def ask_therapist_name(self, first_run: bool) -> None:
        dialog = dialogs.TherapistDialog(self.service.therapist_name, self, first_run=first_run)
        while dialog.exec():
            try:
                self.service.set_therapist_name(dialog.name.text())
            except Exception as exc:  # noqa: BLE001
                dialog.show_error(str(exc))
                continue
            break
        self._update_status_bar()
        for editor in self.session_editors():
            editor.pages[3].form.set_signer(self.service.therapist_name)

    def ask_organization(self) -> None:
        name, ok = QInputDialog.getText(
            self, tr("ชื่อหน่วยงานบนรายงาน", "Clinic name on reports"),
            tr("ชื่อคลินิกหรือหน่วยงาน พิมพ์ที่หัวกระดาษทุกหน้าของรายงาน (เว้นว่างได้)",
               "The clinic or organisation printed at the top of every report page (may be left blank)."),
            text=self.service.organization,
        )
        if not ok:
            return
        try:
            self.service.set_organization(name)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, tr("ตั้งค่าไม่สำเร็จ", "Setting not saved"), str(exc))
            return
        for editor in self.session_editors():
            if not editor.has_unsaved_changes():
                editor.load()  # the report's letterhead shows the new name

    def _set_mode(self, mode: str) -> None:
        try:
            self.service.set_transcription_mode(mode)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, tr("ตั้งค่าไม่สำเร็จ", "Setting not saved"), str(exc))
        for key, action in self.mode_actions.items():
            action.setChecked(key == self.service.transcription_mode)
        self._update_status_bar()

    def _set_language(self, code: str) -> None:
        if code == self.service.language:
            return
        self.service.set_language(code)
        QMessageBox.information(
            self, "PasaScope",
            "Restart PasaScope to switch the language.\nเปิดโปรแกรมใหม่เพื่อเปลี่ยนภาษา",
        )

    def show_speaker_model(self) -> None:
        dialog = dialogs.ClinicSpeakerDialog(self.service.clinic_speaker_status(), self)
        dialog.exec()
        if dialog.enabled.isChecked() != self.service.clinic_speaker_enabled:
            self.service.set_clinic_speaker_enabled(dialog.enabled.isChecked())
        if dialog.choice == "train":
            self.learn_speakers_in_background(force=True)
        elif dialog.choice == "reset":
            answer = QMessageBox.question(
                self, tr("ล้างโมเดลประจำคลินิก", "Clear the clinic model"),
                tr("ล้างสิ่งที่โปรแกรมเรียนไว้ แล้วกลับไปใช้โมเดลพื้นฐาน? โปรแกรมจะเริ่มเรียนใหม่เมื่อรับรอง transcript ครั้งต่อไป",
                   "Clear what PasaScope has learned and go back to the base model? It learns again after the next attested transcript."),
            )
            if answer == QMessageBox.StandardButton.Yes:
                self.service.reset_clinic_speaker_model()
                self.notify(tr("ล้างโมเดลประจำคลินิกแล้ว", "Clinic model cleared"), 6000)
        self.refresh_home()

    def learn_speakers_in_background(self, force: bool = False) -> None:
        """After an attestation, retrain the clinic's child/adult model without blocking the window."""
        if getattr(self, "_learning_speakers", False) or not (force or self.service.clinic_speaker_enabled):
            return
        sessions = self.service.clinic_speaker_training_sessions()
        status = self.service.clinic_speaker_status()
        if status["sessions_needed"] or status["children_needed"]:
            return
        self._learning_speakers = True
        self.statusBar().showMessage(tr("กำลังเรียนเสียงจาก session ที่รับรองแล้ว…", "Learning voices from attested sessions…"))

        def done(result) -> None:
            self._learning_speakers = False
            text = labels.clinic_speaker_text(self.service.save_clinic_speaker_result(result))
            self.statusBar().clearMessage()
            self.notify(tr("แยกเสียงเด็ก/ผู้ใหญ่: ", "Child/adult voices: ") + text, 10000)

        def failed(exc: Exception) -> None:
            self._learning_speakers = False
            self.statusBar().clearMessage()
            self.notify(
                tr(f"เรียนเสียงไม่สำเร็จ ({type(exc).__name__}) ยังใช้โมเดลเดิม", f"Could not learn voices ({type(exc).__name__}); the model in use is unchanged"),
                10000,
            )

        self.runner.run(lambda: self.service.train_clinic_speaker_model(sessions), on_done=done, on_error=failed)

    def show_audit_log(self) -> None:
        dialogs.AuditLogDialog(self.service.audit_events(500), self).exec()

    def show_about(self) -> None:
        QMessageBox.about(
            self,
            tr("เกี่ยวกับ PasaScope", "About PasaScope"),
            f"<b>PasaScope</b> {self.version}<br><br>"
            + tr(
                "ช่วยนักบำบัดถอดเสียงและวิเคราะห์ตัวอย่างภาษาของเด็ก ถอดเสียงด้วย Whisper บนเครื่องนี้ ข้อมูลไม่ออกจากเครื่อง<br><br>"
                "เป็นเครื่องมือสนับสนุนการตัดสินใจทางคลินิก ไม่ใช่เครื่องมือวินิจฉัย และยังไม่ได้ตรวจสอบความถูกต้องทางคลินิกกับเด็กไทย<br><br>",
                "Transcribes and analyses children's language samples for therapists. Whisper runs on this computer; "
                "no data leaves it.<br><br>A clinical decision-support tool, not a diagnostic device. It has not been "
                "clinically validated with Thai children.<br><br>",
            )
            + tr(f"โฟลเดอร์ข้อมูล: {self.service.workspace.root}", f"Data folder: {self.service.workspace.root}"),
        )
