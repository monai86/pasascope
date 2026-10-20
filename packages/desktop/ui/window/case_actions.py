"""Creating, editing and deleting cases and sessions, and recording or withdrawing consent.

Part of :class:`packages.desktop.ui.main_window.MainWindow`."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMenu, QMessageBox

from packages.desktop.core.i18n import tr
from packages.desktop.ui import dialogs
from packages.desktop.ui.window.common import HOME_PAGE, CASE_PAGE


class CaseActionsMixin:
    def new_case(self) -> None:
        if not self._confirm_leave():
            return
        dialog = dialogs.NewCaseDialog(self)
        while dialog.exec():
            try:
                case = self.service.create_case(
                    dialog.code.text(),
                    dialog.age_months,
                    nickname=dialog.nickname.text(),
                    language=dialog.language.currentText(),
                    notes=dialog.notes.toPlainText(),
                )
            except Exception as exc:  # noqa: BLE001 - shown in the form
                dialog.show_error(str(exc))
                continue
            self.search.clear()
            self.reload_cases(case.case_id)
            self.open_case(case.case_id)
            self.record_consent()
            return

    def _consent_action(self) -> None:
        if self.case.consent_status == "granted":
            self.withdraw_consent()
        else:
            self.record_consent()

    def record_consent(self) -> None:
        dialog = dialogs.ConsentDialog(self.case.child_code, self)
        while dialog.exec():
            try:
                self.service.grant_consent(
                    self.case.case_id, dialog.signer.text(), dialog.consent_date, dialog.notes.toPlainText()
                )
            except Exception as exc:  # noqa: BLE001
                dialog.show_error(str(exc))
                continue
            self.case = self.service.get_case(self.case.case_id)
            self._fill_case_header()
            self._fill_sessions()
            self.reload_cases(self.case.case_id)
            return

    def withdraw_consent(self) -> None:
        if self.busy:
            QMessageBox.information(self, tr("รอสักครู่", "Please wait"),
                                    tr("รอให้การถอดเสียงหรือการบันทึกเสียงเสร็จก่อน", "Wait for the transcription or recording to finish."))
            return
        dialog = dialogs.WithdrawConsentDialog(self.case.child_code, self)
        while dialog.exec():
            try:
                self.service.withdraw_consent(self.case.case_id, dialog.reason.toPlainText())
            except Exception as exc:  # noqa: BLE001
                dialog.show_error(str(exc))
                continue
            self.refresh_session() if self.session else self.open_case(self.case.case_id)
            self._fill_sessions(self.session.session_id if self.session else None)
            return

    def new_session(self) -> None:
        if not self._confirm_leave():
            return
        dialog = dialogs.NewSessionDialog(self)
        while dialog.exec():
            try:
                session = self.service.create_session(
                    self.case.case_id, dialog.session_date,
                    session_type=dialog.session_type, notes=dialog.notes.toPlainText(),
                )
            except Exception as exc:  # noqa: BLE001
                dialog.show_error(str(exc))
                continue
            self._fill_sessions(session.session_id)
            self.reload_cases(self.case.case_id)
            return

    def _case_menu(self, case_id: str, menu: QMenu | None = None) -> QMenu:
        """The actions on one case, shared by the right-click menu, the ⋯ button and the Case menu."""
        case = self.service.get_case(case_id)
        menu = menu or QMenu(self)
        menu.addAction(tr("เปิดเคส", "Open case"), lambda: self._select_case(case_id))
        new_session = menu.addAction(tr("Session ใหม่…", "New session…"),
                                     lambda: self._select_case(case_id) and self.new_session())
        new_session.setEnabled(case.consent_status == "granted" and not self.busy)
        menu.addAction(tr("แก้ไขข้อมูลเคส…", "Edit case…"), lambda: self.edit_case(case_id))
        if case.consent_status == "pending":
            menu.addAction(tr("บันทึกความยินยอม…", "Record consent…"), lambda: self._select_case(case_id) and self.record_consent())
        elif case.consent_status == "granted":
            menu.addAction(tr("ถอนความยินยอม…", "Withdraw consent…"), lambda: self._select_case(case_id) and self.withdraw_consent())
        if self.case and self.case.case_id == case_id and self.session is not None:
            menu.addSeparator()
            menu.addAction(tr(f"ลบ session {self.session.session_date}…", f"Delete session {self.session.session_date}…"),
                           lambda: self.delete_session(self.session.session_id))
        menu.addSeparator()
        menu.addAction(tr("ลบเคส…", "Delete case…"), lambda: self.delete_case(case_id))
        return menu

    def _case_list_menu(self, position) -> None:
        item = self.case_list.itemAt(position)
        if item is not None:
            self._case_menu(item.data(Qt.ItemDataRole.UserRole)).exec(self.case_list.viewport().mapToGlobal(position))

    def _fill_case_bar_menu(self) -> None:
        self.case_bar_menu.clear()
        self.case_bar_menu.addAction(tr("เพิ่มเคส…", "New case…"), self.new_case)
        if self.case is not None and self.stack.currentIndex() == CASE_PAGE:
            self.case_bar_menu.addSeparator()
            self._case_menu(self.case.case_id, self.case_bar_menu)

    def _select_case(self, case_id: str) -> bool:
        """Open ``case_id`` unless it is already open; False when the therapist stays on unsaved work."""
        if self.case and self.case.case_id == case_id and self.stack.currentIndex() == CASE_PAGE:
            return True
        if not self._confirm_leave():
            return False
        self.stop_pages()
        self.reload_cases(case_id)
        self.open_case(case_id)
        return True

    def _delete_selected_case(self) -> None:
        item = self.case_list.currentItem()
        if item is not None:
            self.delete_case(item.data(Qt.ItemDataRole.UserRole))

    def _wait_for_work(self) -> bool:
        if self.busy or self.runner.busy:
            QMessageBox.information(self, tr("รอสักครู่", "Please wait"),
                                    tr("รอให้งานที่กำลังทำอยู่เสร็จก่อน", "Wait for the work in progress to finish."))
            return True
        return False

    def edit_case(self, case_id: str) -> None:
        case = self.service.get_case(case_id)
        dialog = dialogs.EditCaseDialog(case, self)
        while dialog.exec():
            try:
                self.service.update_case(
                    case_id, nickname=dialog.nickname.text(), age_months=dialog.age_months,
                    language=dialog.language.currentText(), notes=dialog.notes.toPlainText(),
                )
            except Exception as exc:  # noqa: BLE001 - shown in the form
                dialog.show_error(str(exc))
                continue
            if self.case and self.case.case_id == case_id:
                self.case = self.service.get_case(case_id)
                self._fill_case_header()
            self.reload_cases(self.case.case_id if self.case else None)
            self.dashboard.refresh()
            return

    def delete_case(self, case_id: str) -> None:
        if self._wait_for_work():
            return
        case = self.service.get_case(case_id)
        dialog = dialogs.DeleteCaseDialog(case.child_code, self.service.deletion_summary(case_id), self, on_backup=self.backup)
        while dialog.exec():
            if self._wait_for_work():
                return
            open_here = self.case is not None and self.case.case_id == case_id
            if open_here:
                self.stop_pages()
            try:
                self.service.delete_case(case_id, dialog.typed.text())
            except Exception as exc:  # noqa: BLE001
                dialog.show_error(str(exc))
                continue
            if open_here:
                self.case = None
                self.session = None
            self.reload_cases()
            if open_here or self.stack.currentIndex() == HOME_PAGE:
                self.show_home()
            self.dashboard.refresh()
            self.notify(tr(f"ลบเคส {case.child_code} แล้ว", f"Deleted case {case.child_code}."), 6000)
            return

    def delete_session(self, session_id: str) -> None:
        if self._wait_for_work():
            return
        session = self.service.get_session(session_id)
        summary = self.service.deletion_summary(session.case_id, session_id)
        signed = tr(" รวมรายงานที่ลงนามแล้ว", ", including a signed report") if summary["signed_reports"] else ""
        answer = QMessageBox.warning(
            self, tr("ลบ session", "Delete session"),
            tr(f"ลบ session วันที่ {session.session_date} พร้อมไฟล์เสียง {summary['recordings']} ไฟล์ "
               f"transcript ตัวชี้วัด และรายงาน{signed}? ย้อนกลับไม่ได้",
               f"Delete the session of {session.session_date} with its {summary['recordings']} recording(s), "
               f"transcript, findings and report{signed}? This cannot be undone."),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        if self.session is not None and self.session.session_id == session_id:
            self.stop_pages()
            self.session = None
        self.service.delete_session(session_id)
        if self.case is not None and self.case.case_id == session.case_id:
            self._fill_sessions()
        self.reload_cases(self.case.case_id if self.case else None)
        self.dashboard.refresh()
        self.notify(tr(f"ลบ session {session.session_date} แล้ว", f"Deleted the session of {session.session_date}."), 6000)
