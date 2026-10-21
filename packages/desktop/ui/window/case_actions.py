"""Creating, editing and deleting cases and sessions, and recording or withdrawing consent.

Part of :class:`packages.desktop.ui.main_window.MainWindow`. The actions work
on the case of the tab in front (``self.case``); the tree's right-click menu
opens that case first.
"""

from __future__ import annotations

from PySide6.QtWidgets import QMenu, QMessageBox

from packages.desktop.core.i18n import tr
from packages.desktop.ui import dialogs, labels
from packages.desktop.ui.window.case_view import ROLE


class CaseActionsMixin:
    def new_case(self) -> None:
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
            self.open_case_editor(case.case_id)
            self.record_consent()
            self.refresh_home()
            return

    def _consent_action(self) -> None:
        if self.case is None:
            return
        if self.case.consent_status == "granted":
            self.withdraw_consent()
        else:
            self.record_consent()

    def record_consent(self) -> None:
        case = self.case
        if case is None:
            return
        dialog = dialogs.ConsentDialog(case.child_code, self)
        while dialog.exec():
            try:
                self.service.grant_consent(case.case_id, dialog.signer.text(), dialog.consent_date, dialog.notes.toPlainText())
            except Exception as exc:  # noqa: BLE001
                dialog.show_error(str(exc))
                continue
            self._refresh_case_views(case.case_id)
            for editor in self.session_editors(case.case_id):
                editor.load()
            return

    def withdraw_consent(self) -> None:
        case = self.case
        if case is None:
            return
        if self.busy:
            QMessageBox.information(self, tr("รอสักครู่", "Please wait"),
                                    tr("รอให้การถอดเสียงหรือการบันทึกเสียงเสร็จก่อน", "Wait for the transcription or recording to finish."))
            return
        if not self._confirm_leave(self.session_editors(case.case_id)):
            return
        dialog = dialogs.WithdrawConsentDialog(case.child_code, self)
        while dialog.exec():
            try:
                self.service.withdraw_consent(case.case_id, dialog.reason.toPlainText())
            except Exception as exc:  # noqa: BLE001
                dialog.show_error(str(exc))
                continue
            for editor in self.session_editors(case.case_id):
                editor.load()
            self._refresh_case_views(case.case_id)
            return

    def new_session(self) -> None:
        case = self.case
        if case is None:
            return
        dialog = dialogs.NewSessionDialog(self)
        while dialog.exec():
            try:
                session = self.service.create_session(
                    case.case_id, dialog.session_date,
                    session_type=dialog.session_type, notes=dialog.notes.toPlainText(),
                )
            except Exception as exc:  # noqa: BLE001
                dialog.show_error(str(exc))
                continue
            self._refresh_case_views(case.case_id)
            self.open_session(session.session_id)
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
            session_id, day = self.session.session_id, labels.day_text(self.session.session_date)
            menu.addSeparator()
            menu.addAction(tr(f"ลบ session {day}…", f"Delete session {day}…"), lambda: self.delete_session(session_id))
        menu.addSeparator()
        menu.addAction(tr("ลบเคส…", "Delete case…"), lambda: self.delete_case(case_id))
        return menu

    def _session_menu(self, session_id: str) -> QMenu:
        session = self.service.get_session(session_id)
        menu = QMenu(self)
        menu.addAction(tr("เปิด session", "Open session"), lambda: self.open_session(session_id))
        menu.addAction(tr("เปิดเคส", "Open case"), lambda: self.open_case_editor(session.case_id))
        menu.addSeparator()
        day = labels.day_text(session.session_date)
        menu.addAction(tr(f"ลบ session {day}…", f"Delete session {day}…"),
                       lambda: self.delete_session(session_id))
        return menu

    def _case_list_menu(self, position) -> None:
        item = self.case_list.itemAt(position)
        if item is None:
            return
        kind, identifier = item.data(0, ROLE)
        menu = self._session_menu(identifier) if kind == "session" else self._case_menu(identifier)
        menu.exec(self.case_list.viewport().mapToGlobal(position))

    def _fill_case_bar_menu(self) -> None:
        self.case_bar_menu.clear()
        self.case_bar_menu.addAction(tr("เพิ่มเคส…", "New case…"), self.new_case)
        if self.case is not None:
            self.case_bar_menu.addSeparator()
            self._case_menu(self.case.case_id, self.case_bar_menu)

    def _select_case(self, case_id: str) -> bool:
        """Bring ``case_id`` to the front (its session tab stays in front if one is)."""
        if self.case and self.case.case_id == case_id:
            return True
        self.open_case_editor(case_id)
        return True

    def _delete_selected_case(self) -> None:
        item = self.case_list.currentItem()
        if item is None:
            return
        kind, identifier = item.data(0, ROLE)
        if kind == "session":
            self.delete_session(identifier)
        else:
            self.delete_case(identifier)

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
            self._refresh_case_views(case_id)
            return

    def delete_case(self, case_id: str) -> None:
        if self._wait_for_work():
            return
        case = self.service.get_case(case_id)
        dialog = dialogs.DeleteCaseDialog(case.child_code, self.service.deletion_summary(case_id), self, on_backup=self.backup)
        while dialog.exec():
            if self._wait_for_work():
                return
            for editor in self.session_editors(case_id):
                editor.stop_playback()
            try:
                self.service.delete_case(case_id, dialog.typed.text())
            except Exception as exc:  # noqa: BLE001
                dialog.show_error(str(exc))
                continue
            self.close_case_tabs(case_id)
            if not self.editor_area.keys():
                self.show_home()
            self.reload_cases()
            self.refresh_home()
            self.notify(tr(f"ลบเคส {case.child_code} แล้ว", f"Deleted case {case.child_code}."), 6000)
            return

    def delete_session(self, session_id: str) -> None:
        if self._wait_for_work():
            return
        session = self.service.get_session(session_id)
        summary = self.service.deletion_summary(session.case_id, session_id)
        day = labels.day_text(session.session_date)
        signed = tr(" รวมรายงานที่ลงนามแล้ว", ", including a signed report") if summary["signed_reports"] else ""
        answer = QMessageBox.warning(
            self, tr("ลบ session", "Delete session"),
            tr(f"ลบ session วันที่ {day} พร้อมไฟล์เสียง {summary['recordings']} ไฟล์ "
               f"transcript ตัวชี้วัด และรายงาน{signed}? ย้อนกลับไม่ได้",
               f"Delete the session of {day} with its {summary['recordings']} recording(s), "
               f"transcript, findings and report{signed}? This cannot be undone."),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.close_case_tabs(session.case_id, session_id)
        self.service.delete_session(session_id)
        self._refresh_case_views(session.case_id)
        if not self.editor_area.keys():
            self.open_case_editor(session.case_id)
        self.notify(tr(f"ลบ session {day} แล้ว", f"Deleted the session of {day}."), 6000)
