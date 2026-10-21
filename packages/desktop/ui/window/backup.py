"""Backing up and restoring the data folder, with progress windows.

Part of :class:`packages.desktop.ui.main_window.MainWindow`."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import threading

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QFileDialog, QProgressDialog, QMessageBox

from packages.desktop.core.backup import BackupCancelled, BackupError, read_backup, restore_backup
from packages.desktop.core.i18n import tr


class BackupMixin:
    def backup(self) -> None:
        title = tr("สำรองข้อมูล", "Back up")
        if self.busy or self.runner.busy:
            QMessageBox.information(self, title, tr("รอให้งานที่ทำอยู่เสร็จก่อน แล้วค่อยสำรองข้อมูล", "Wait for the current task to finish, then back up."))
            return
        if not self._confirm_leave():
            return
        last_dir = QSettings().value("backup/folder") or str(Path.home() / "Documents")
        default = Path(last_dir) / f"PasaScope-backup-{datetime.now():%Y-%m-%d-%H%M}.zip"
        path, _ = QFileDialog.getSaveFileName(self, tr("สำรองข้อมูลไปที่", "Back up to"), str(default),
                                              tr("ไฟล์สำรอง PasaScope (*.zip)", "PasaScope backup (*.zip)"))
        if not path:
            return
        target = Path(path) if path.lower().endswith(".zip") else Path(path + ".zip")
        if target.resolve().is_relative_to(self.service.workspace.root):
            QMessageBox.warning(self, title, tr("เลือกที่เก็บนอกโฟลเดอร์ข้อมูลของโปรแกรม เช่น ไดรฟ์ภายนอก",
                                                "Choose a place outside PasaScope's data folder, such as an external drive."))
            return
        QSettings().setValue("backup/folder", str(target.parent))
        self._set_busy(True)
        dialog = self._progress_dialog(title, tr("กำลังเตรียมสำรองข้อมูล…", "Preparing the backup…"), cancellable=True)
        cancel = threading.Event()
        dialog.canceled.connect(cancel.set)

        def progress(fraction: float, stage: str) -> None:
            dialog.setLabelText(stage)
            dialog.setValue(int(fraction * 1000))

        def done(info) -> None:
            self._set_busy(False)
            dialog.close()
            self._update_backup_label()
            counts = info.counts
            QMessageBox.information(
                self, tr("สำรองข้อมูลแล้ว", "Backup saved"),
                tr(
                    f"บันทึกที่ {info.path}\n{counts.get('cases', 0)} เคส, {counts.get('sessions', 0)} session, "
                    f"{counts.get('recordings', 0)} ไฟล์เสียง, {info.total_bytes / 1_048_576:.1f} MB\n\n"
                    "ไฟล์นี้ไม่เข้ารหัส และมีเสียงกับข้อความของเด็ก เก็บไว้ในที่ที่มีแต่นักบำบัดเข้าถึงได้",
                    f"Saved to {info.path}\n{counts.get('cases', 0)} cases, {counts.get('sessions', 0)} sessions, "
                    f"{counts.get('recordings', 0)} recordings, {info.total_bytes / 1_048_576:.1f} MB\n\n"
                    "The file is not encrypted and holds children's recordings and transcripts. Keep it where only therapists can reach it.",
                ),
            )
            self.refresh_home()

        def failed(exc: Exception) -> None:
            self._set_busy(False)
            dialog.close()
            if isinstance(exc, BackupCancelled):
                self.notify(tr("ยกเลิกการสำรองข้อมูลแล้ว ไม่มีไฟล์ถูกบันทึก", "Backup cancelled; no file was saved."))
                return
            QMessageBox.critical(self, tr("สำรองข้อมูลไม่สำเร็จ", "Backup failed"), f"{type(exc).__name__}: {exc}")

        self.runner.run(
            lambda report: self.service.create_backup(target, self.version, progress=report, cancelled=cancel.is_set),
            on_done=done, on_error=failed, on_progress=progress,
        )

    def _progress_dialog(self, title: str, text: str, cancellable: bool) -> QProgressDialog:
        dialog = QProgressDialog(text, tr("ยกเลิก", "Cancel") if cancellable else "", 0, 1000, self)
        if not cancellable:
            dialog.setCancelButton(None)
        dialog.setWindowTitle(title)
        dialog.setWindowModality(Qt.WindowModality.WindowModal)
        dialog.setMinimumDuration(0)
        dialog.setAutoClose(False)
        dialog.setAutoReset(False)
        dialog.setValue(0)
        return dialog

    def restore(self) -> None:
        title = tr("กู้คืนข้อมูล", "Restore")
        if self.busy or self.runner.busy:
            QMessageBox.information(self, title, tr("รอให้งานที่ทำอยู่เสร็จก่อน", "Wait for the current task to finish."))
            return
        if not self._confirm_leave():
            return
        last_dir = QSettings().value("backup/folder") or str(Path.home() / "Documents")
        path, _ = QFileDialog.getOpenFileName(self, tr("เลือกไฟล์สำรอง", "Choose a backup"), str(last_dir),
                                              tr("ไฟล์สำรอง PasaScope (*.zip)", "PasaScope backup (*.zip)"))
        if not path:
            return
        try:
            info = read_backup(Path(path))
        except BackupError as exc:
            QMessageBox.warning(self, title, str(exc))
            return
        counts = info.counts
        when = info.created_at[:16].replace("T", " ")
        demo = tr("\n\nไฟล์นี้สำรองมาจากข้อมูลสาธิต", "\n\nThis backup was made from demonstration data.") if info.demo else ""
        answer = QMessageBox.question(
            self, title,
            tr(
                f"ไฟล์สำรองเมื่อ {when}\n{counts.get('cases', 0)} เคส, {counts.get('sessions', 0)} session, "
                f"{counts.get('recordings', 0)} ไฟล์เสียง{demo}\n\n"
                "ข้อมูลปัจจุบันทั้งหมดจะถูกแทนที่ด้วยไฟล์สำรองนี้ ข้อมูลปัจจุบันไม่ถูกลบ แต่จะย้ายไปไว้ในโฟลเดอร์ \"ก่อนกู้คืน\" ข้าง ๆ กัน\n\n"
                "กู้คืนแล้วโปรแกรมจะปิด ต้องเปิดใหม่ กู้คืนเลยไหม?",
                f"Backup from {when}\n{counts.get('cases', 0)} cases, {counts.get('sessions', 0)} sessions, "
                f"{counts.get('recordings', 0)} recordings{demo}\n\n"
                "Everything now in PasaScope will be replaced by this backup. The current data is not deleted; it is moved "
                "to a \"before restore\" folder next to it.\n\nPasaScope closes after restoring. Restore now?",
            ),
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.service.close()
        root = self.service.workspace.root
        self._set_busy(True)
        dialog = self._progress_dialog(title, tr("กำลังตรวจและแตกไฟล์สำรอง…", "Checking and unpacking the backup…"), cancellable=False)

        def progress(fraction: float, stage: str) -> None:
            dialog.setLabelText(stage)
            dialog.setValue(int(fraction * 1000))

        def done(previous) -> None:
            self._set_busy(False)
            dialog.close()
            QMessageBox.information(
                self, tr("กู้คืนแล้ว", "Restored"),
                tr(f"ข้อมูลเดิมย้ายไปที่ {previous}\nโปรแกรมจะปิดตอนนี้ เปิดใหม่เพื่อใช้ข้อมูลที่กู้คืน",
                   f"The previous data was moved to {previous}\nPasaScope will close now; open it again to use the restored data."),
            )
            self._restored = True
            self.close()

        def failed(exc: Exception) -> None:
            self._set_busy(False)
            dialog.close()
            detail = str(exc) if isinstance(exc, (BackupError, OSError)) else f"{type(exc).__name__}: {exc}"
            QMessageBox.critical(self, tr("กู้คืนไม่สำเร็จ", "Restore failed"),
                                 tr(f"ข้อมูลปัจจุบันยังอยู่ครบ ไม่ได้เปลี่ยนแปลง\n\n{detail}", f"Your current data is unchanged.\n\n{detail}"))

        self.runner.run(lambda report: restore_backup(root, info.path, progress=report),
                        on_done=done, on_error=failed, on_progress=progress)
