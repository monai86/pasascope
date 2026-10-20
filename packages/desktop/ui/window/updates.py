"""Checking for a new version and downloading speech models, with progress windows.

Part of :class:`packages.desktop.ui.main_window.MainWindow`."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QProgressDialog, QMessageBox

from packages.desktop.core.i18n import tr


class UpdatesMixin:
    def check_for_updates(self, quiet: bool = True) -> None:
        """Ask GitHub for a newer release in the background; ``quiet`` says nothing when there is none."""
        if not self.version:
            if not quiet:
                QMessageBox.information(self, tr("ตรวจหาอัปเดต", "Check for updates"),
                                        tr("ไม่ทราบรุ่นของโปรแกรมนี้", "This copy's version is unknown."))
            return

        def done(release) -> None:
            self._available_update = release
            if release is None:
                self.update_label.hide()
                if not quiet:
                    QMessageBox.information(self, tr("ตรวจหาอัปเดต", "Check for updates"),
                                            tr(f"รุ่น {self.version} เป็นรุ่นล่าสุดแล้ว", f"Version {self.version} is the latest."))
                return
            self._show_update(release)
            if not quiet:
                self._offer_update(release)

        def failed(exc: Exception) -> None:
            if not quiet:
                QMessageBox.warning(self, tr("ตรวจหาอัปเดตไม่ได้", "Could not check for updates"),
                                    tr(f"เชื่อมต่อ GitHub ไม่ได้ ลองใหม่เมื่อมีอินเทอร์เน็ต\n\n{exc}",
                                       f"GitHub could not be reached; try again when online.\n\n{exc}"))

        self.runner.run(lambda: self.service.check_for_update(self.version), on_done=done, on_error=failed)

    def _show_update(self, release) -> None:
        self._available_update = release
        self.update_label.setText(f'<a href="update">{tr(f"มีรุ่นใหม่ {release.version}", f"Version {release.version} is available")}</a>')
        self.update_label.show()

    def _offer_update(self, release) -> None:
        if release is None or self.busy or self.runner.busy:
            return
        notes = release.notes[:1200] + ("…" if len(release.notes) > 1200 else "")
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Information)
        box.setWindowTitle(tr("มีรุ่นใหม่", "New version"))
        box.setText(tr(f"PasaScope {release.version} พร้อมให้ติดตั้ง (รุ่นที่ใช้อยู่ {self.version})",
                       f"PasaScope {release.version} is available (this is {self.version})."))
        box.setInformativeText(tr(
            f"ขนาด {release.size / 1_000_000:.0f} MB ระบบจะสำรองข้อมูลก่อน แล้วดาวน์โหลดไปที่โฟลเดอร์ Downloads "
            "และตรวจ SHA-256 ก่อนเปิด ข้อมูลเคสอยู่แยกจากตัวโปรแกรม การอัปเดตจึงไม่ลบข้อมูล",
            f"{release.size / 1_000_000:.0f} MB. PasaScope backs up your data first, downloads to the Downloads folder "
            "and checks the SHA-256 before opening it. Your cases are kept apart from the app, so updating does not remove them.",
        ))
        if notes:
            box.setDetailedText(notes)
        install = box.addButton(tr("สำรองข้อมูลแล้วดาวน์โหลด", "Back up and download"), QMessageBox.ButtonRole.AcceptRole)
        box.addButton(tr("ไว้ทีหลัง", "Later"), QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() is install:
            self._backup_then_download(release)

    def _backup_then_download(self, release) -> None:
        folder = Path.home() / "Documents" / "PasaScope backups"
        target = folder / f"PasaScope-before-{release.version}-{datetime.now():%Y-%m-%d-%H%M}.zip"
        dialog = QProgressDialog(tr("กำลังสำรองข้อมูล…", "Backing up…"), tr("ยกเลิก", "Cancel"), 0, 1000, self)
        dialog.setWindowTitle(tr("อัปเดต PasaScope", "Update PasaScope"))
        dialog.setWindowModality(Qt.WindowModality.WindowModal)
        dialog.setMinimumDuration(0)
        self._set_busy(True)

        def work(report):
            folder.mkdir(parents=True, exist_ok=True)
            report(0.0, tr("กำลังสำรองข้อมูล", "Backing up"))
            backup = self.service.create_backup(target, self.version)
            path = self.service.download_update(release, report, dialog.wasCanceled)
            return backup, path

        def progress(fraction: float, stage: str) -> None:
            dialog.setLabelText(stage)
            dialog.setValue(int(fraction * 1000))

        def done(result) -> None:
            self._set_busy(False)
            dialog.close()
            backup, path = result
            self._update_backup_label()
            checked = tr(f"สำรองข้อมูลไว้ที่ {backup.path}\nดาวน์โหลดและตรวจ {path.name} แล้ว\n\n",
                         f"Backed up to {backup.path}\nDownloaded and checked {path.name}.\n\n")
            if sys.platform == "win32":
                # The installer replaces the program files, so PasaScope closes first.
                QMessageBox.information(self, tr("พร้อมติดตั้ง", "Ready to install"), checked + tr(
                    "เมื่อกด OK โปรแกรมติดตั้งจะเปิดขึ้นและ PasaScope จะปิดเพื่อให้ติดตั้งได้ "
                    "ทำตามขั้นตอนของโปรแกรมติดตั้ง แล้วเปิด PasaScope ใหม่",
                    "When you click OK the installer opens and PasaScope closes so it can be replaced. "
                    "Follow the installer, then open PasaScope again.",
                ))
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
                self.close()
                return
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
            QMessageBox.information(self, tr("พร้อมติดตั้ง", "Ready to install"), checked + tr(
                "ขั้นต่อไป: ปิด PasaScope แล้วลากไอคอน PasaScope ในหน้าต่างที่เปิดขึ้นไปที่ Applications "
                "เลือก 'แทนที่' แล้วเปิดโปรแกรมใหม่",
                "Next: quit PasaScope, drag PasaScope from the window that opened onto Applications, "
                "choose Replace, then open it again.",
            ))

        def failed(exc: Exception) -> None:
            self._set_busy(False)
            dialog.close()
            QMessageBox.warning(self, tr("อัปเดตไม่สำเร็จ", "Update failed"), f"{exc}")

        self.runner.run(work, on_done=done, on_error=failed, on_progress=progress)

    def download_models(self, confirm: bool = True) -> None:
        """Download the speech models with a progress window; the work runs off the UI thread.

        ``confirm=False`` skips the question, when the therapist already chose it at first start.
        """
        if self.busy or self.runner.busy:
            return
        status = self.service.thai_model_status()
        size_gb = status["size"] / 1_000_000_000
        if status["installed"]:
            text = tr("โมเดลภาษาไทยอยู่ในเครื่องแล้ว ตรวจและดาวน์โหลดโมเดลเล็กที่เหลือ?",
                      "The Thai model is already here. Check and fetch the smaller models?")
        else:
            text = tr(f"ดาวน์โหลดโมเดลถอดเสียงภาษาไทย ประมาณ {size_gb:.1f} GB จาก Hugging Face "
                      "ระบบตรวจทุกไฟล์ด้วย SHA-256 ก่อนใช้ ไม่ส่งข้อมูลของเด็กออกจากเครื่อง ดำเนินการต่อ?",
                      f"Download the Thai speech model, about {size_gb:.1f} GB, from Hugging Face? Every file is checked "
                      "against its SHA-256 before use. No children's data leaves this computer.")
        if confirm and QMessageBox.question(self, tr("ดาวน์โหลดโมเดลถอดเสียง", "Download speech models"), text) != QMessageBox.StandardButton.Yes:
            return
        dialog = QProgressDialog(tr("กำลังดาวน์โหลด…", "Downloading…"), tr("ยกเลิก", "Cancel"), 0, 1000, self)
        dialog.setWindowTitle(tr("ดาวน์โหลดโมเดลถอดเสียง", "Download speech models"))
        dialog.setWindowModality(Qt.WindowModality.WindowModal)
        dialog.setMinimumDuration(0)
        dialog.setValue(0)
        self._set_busy(True)

        def progress(fraction: float, stage: str) -> None:
            dialog.setLabelText(stage)
            dialog.setValue(int(fraction * 1000))

        def done(_folder) -> None:
            self._set_busy(False)
            dialog.close()
            self.dashboard.refresh()
            self._update_status_bar()
            QMessageBox.information(self, tr("พร้อมถอดเสียง", "Ready to transcribe"),
                                    tr("ดาวน์โหลดและตรวจโมเดลครบแล้ว", "The models are downloaded and checked."))

        def failed(exc: Exception) -> None:
            self._set_busy(False)
            dialog.close()
            QMessageBox.warning(self, tr("ดาวน์โหลดไม่สำเร็จ", "Download failed"),
                                tr(f"{exc}\n\nลองใหม่ได้ ส่วนที่ดาวน์โหลดครบแล้วจะไม่ต้องโหลดซ้ำ",
                                   f"{exc}\n\nYou can try again; files already downloaded are kept."))

        self.runner.run(lambda report: self.service.download_speech_models(report, dialog.wasCanceled),
                        on_done=done, on_error=failed, on_progress=progress)
