"""Opening a case and its sessions, and keeping the case view in step with the records.

Part of :class:`packages.desktop.ui.main_window.MainWindow`."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QListWidgetItem, QMessageBox

from packages.desktop.core.i18n import tr
from packages.desktop.ui import labels, theme
from packages.desktop.ui.widgets import set_chip
from packages.desktop.ui.window.common import (
    OVERVIEW,
    NO_SESSION_PAGE,
    SESSION_PAGE,
    OVERVIEW_PAGE,
    CASE_PAGE,
)


class CaseViewMixin:
    def reload_cases(self, select_id: str | None = None) -> None:
        select_id = select_id or (self.case.case_id if self.case else None)
        cases = self.service.list_cases(self.search.text())
        self._switching = True
        self.case_list.clear()
        for case in cases:
            name = case.child_code + (f"  {case.nickname}" if case.nickname else "")
            item = QListWidgetItem(name)
            consent, _ = labels.CONSENT.get(case.consent_status, (case.consent_status, ""))
            item.setToolTip(f"{labels.age_text(case.age_months)} · {consent}")
            item.setData(Qt.ItemDataRole.UserRole, case.case_id)
            if case.consent_status != "granted":
                item.setForeground(QColor(theme.ATTENTION if case.consent_status == "pending" else theme.FAINT))
            self.case_list.addItem(item)
            if case.case_id == select_id:
                self.case_list.setCurrentItem(item)
        self._switching = False
        total = len(self.service.list_cases())
        self.case_count.setText(
            tr(f"{len(cases)} จาก {total} เคส", f"{len(cases)} of {total} cases") if self.search.text()
            else tr(f"{total} เคส", f"{total} cases" if total != 1 else "1 case")
        )
        if self.case_list.currentItem() is None and self.stack.currentIndex() == CASE_PAGE:
            self.show_home()

    def _confirm_leave(self) -> bool:
        dirty = [p for p in self.pages if p.has_unsaved_changes()]
        if not dirty:
            return True
        answer = QMessageBox.question(
            self, tr("มีการแก้ไขที่ยังไม่บันทึก", "Unsaved changes"),
            tr("บันทึกการแก้ไขก่อนเปลี่ยนหน้า?", "Save your changes first?"),
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
        )
        if answer == QMessageBox.StandardButton.Cancel:
            return False
        if answer == QMessageBox.StandardButton.Save:
            return all(page.save() for page in dirty)
        return True

    def _on_case_item(self, current: QListWidgetItem | None, previous: QListWidgetItem | None) -> None:
        if self._switching or current is None:
            return
        case_id = current.data(Qt.ItemDataRole.UserRole)
        if self.case and case_id == self.case.case_id and self.stack.currentIndex() == CASE_PAGE:
            return
        if not self._confirm_leave():
            self._switching = True
            self.case_list.setCurrentItem(previous)
            self._switching = False
            return
        self.open_case(case_id)

    def open_case(self, case_id: str, session_id: str | None = None) -> None:
        self.case = self.service.get_case(case_id)
        self.stack.setCurrentIndex(CASE_PAGE)
        self._mark_nav(CASE_PAGE)
        self._fill_case_header()
        self._fill_sessions(session_id)

    def _fill_case_header(self) -> None:
        case = self.case
        self.case_title.setText(case.child_code + (f"  {case.nickname}" if case.nickname else ""))
        self.case_meta.setText(tr(
            f"อายุ {labels.age_text(case.age_months)} ตอนเปิดเคส   ภาษา {case.language}",
            f"{labels.age_text(case.age_months)} at intake   {case.language}",
        ))
        text, kind = labels.CONSENT.get(case.consent_status, (case.consent_status, "neutral"))
        set_chip(self.consent_chip, text, kind)
        if case.consent_status == "granted":
            self.consent_btn.setText(tr("ถอนความยินยอม…", "Withdraw consent…"))
            self.consent_btn.setProperty("role", "danger")
            self.consent_btn.setVisible(True)
        elif case.consent_status == "pending":
            self.consent_btn.setText(tr("บันทึกความยินยอม…", "Record consent…"))
            self.consent_btn.setProperty("role", "primary")
            self.consent_btn.setVisible(True)
        else:
            self.consent_btn.setVisible(False)
        self.consent_btn.style().unpolish(self.consent_btn)
        self.consent_btn.style().polish(self.consent_btn)
        self.new_session_btn.setEnabled(case.consent_status == "granted")

    def _fill_sessions(self, select_id: str | None = None) -> None:
        sessions = self._fill_session_items()
        self._switching = True
        if select_id and self.session_pick.findData(select_id) >= 0:
            index = self.session_pick.findData(select_id)
        elif len(sessions) > 1:
            index = 0  # several sessions: start from the overview
        else:
            index = 1
        self.session_pick.setCurrentIndex(index if sessions else -1)
        self._switching = False
        self.session_pick.setVisible(bool(sessions))
        if sessions and self.session_pick.currentData() == OVERVIEW:
            self._show_overview()
        elif sessions:
            self._open_session(self.session_pick.currentData())
        else:
            self.session = None
            self.session_stack.setCurrentIndex(NO_SESSION_PAGE)
            if self.case.consent_status == "granted":
                self.no_session.set_text(tr("ยังไม่มี session", "No sessions yet"),
                                         tr("เพิ่ม session เพื่อบันทึกหรือนำเข้าเสียง", "Add a session to record or import audio."))
                self.no_session_btn.setText(tr("เพิ่ม session", "Add session"))
                self.no_session_btn.setVisible(True)
            elif self.case.consent_status == "pending":
                self.no_session.set_text(
                    tr("ต้องบันทึกความยินยอมก่อน", "Consent needed"),
                    tr("ต้องมีเอกสารยินยอมของผู้ปกครองก่อนบันทึกเสียงหรือเพิ่มข้อมูลของเด็ก",
                       "Record the parent's or guardian's consent before adding recordings or other data."),
                )
                self.no_session_btn.setText(tr("บันทึกความยินยอม…", "Record consent…"))
                self.no_session_btn.setVisible(True)
            else:
                self.no_session.set_text(tr("ถอนความยินยอมแล้ว", "Consent withdrawn"),
                                         tr("เคสนี้เพิ่มข้อมูลใหม่ไม่ได้", "No new data can be added to this case."))
                self.no_session_btn.setVisible(False)

    def _no_session_action(self) -> None:
        if self.case.consent_status == "granted":
            self.new_session()
        else:
            self.record_consent()

    def _fill_session_items(self) -> list:
        sessions = self.service.list_sessions(self.case.case_id)
        self._switching = True
        self.session_pick.clear()
        if sessions:
            self.session_pick.addItem(tr(f"ภาพรวมเคส ({len(sessions)} session)", f"Case overview ({len(sessions)} sessions)"), OVERVIEW)
        for session in sessions:
            self.session_pick.addItem(f"{session.session_date}   {labels.status_text(session.status)}", session.session_id)
        self._switching = False
        return sessions

    def _pick_session(self, session_id: str) -> None:
        self.session_pick.setCurrentIndex(max(0, self.session_pick.findData(session_id)))

    def _on_session_pick(self, index: int) -> None:
        if self._switching or index < 0:
            return
        session_id = self.session_pick.itemData(index)
        if self.session and session_id == self.session.session_id:
            return
        if session_id == OVERVIEW and self.session is None:
            return
        if not self._confirm_leave():
            self._switching = True
            self.session_pick.setCurrentIndex(self.session_pick.findData(self.session.session_id))
            self._switching = False
            return
        if session_id == OVERVIEW:
            self._show_overview()
        else:
            self._open_session(session_id)

    def _show_overview(self) -> None:
        self.stop_pages()
        self.session = None
        self.overview.load(self.case)
        self.session_stack.setCurrentIndex(OVERVIEW_PAGE)

    def stop_pages(self) -> None:
        """Stop playback before the session pages are hidden."""
        review = self.pages[1]
        if hasattr(review, "stop_playback"):
            review.stop_playback()

    def _open_session(self, session_id: str) -> None:
        self.session = self.service.get_session(session_id)
        self.session_stack.setCurrentIndex(SESSION_PAGE)
        for page in self.pages:
            page.load(self.case, self.session)
        self.tabs.setCurrentIndex(self._suggested_step())
        self._update_tab_state()

    def _suggested_step(self) -> int:
        # A signed session (step 4) opens on its report.
        return min(self.service.session_step(self.session), 3)

    def _update_tab_state(self) -> None:
        """Finished steps are shown quieter, so the step still to do stands out."""
        if self.session is None:
            return
        transcript = self.service.get_transcript(self.session.session_id)
        features = self.service.get_features(self.session.session_id)
        report = self.service.get_report(self.session.session_id)
        self.steps_done = [
            transcript is not None,
            bool(transcript and transcript.therapist_attested),
            features is not None and not self.session.findings_stale,
            bool(report and (report.status.value if hasattr(report.status, "value") else report.status) == "Signed Off"),
        ]
        done_tip = tr("เสร็จแล้ว", "Done")
        for index, done in enumerate(self.steps_done):
            self.tabs.tabBar().setTabTextColor(index, QColor(theme.OK if done else theme.MUTED))
            self.tabs.setTabToolTip(index, done_tip if done else "")

    def refresh_session(self) -> None:
        """Reload everything after a page changed a record."""
        if self.case is None:
            return
        self.case = self.service.get_case(self.case.case_id)
        self._fill_case_header()
        session_id = self.session.session_id if self.session else None
        current_tab = self.tabs.currentIndex()
        self._fill_session_items()
        self._switching = True
        self.session_pick.setCurrentIndex(max(0, self.session_pick.findData(session_id or OVERVIEW)))
        self._switching = False
        if session_id is None and self.session_stack.currentIndex() == OVERVIEW_PAGE:
            self.overview.refresh()
        if session_id:
            self.session = self.service.get_session(session_id)
            for page in self.pages:
                page.load(self.case, self.session)
            self.tabs.setCurrentIndex(current_tab)
            self._update_tab_state()
        self.reload_cases(self.case.case_id)
        self._apply_pending_restyle()  # a save may have cleared the edits a theme change waited for
