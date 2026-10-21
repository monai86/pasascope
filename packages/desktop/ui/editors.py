"""What an editor tab holds: one session's four steps, or one case and its sessions.

Each open session has its own :class:`SessionEditor` with its own pages, so
several sessions stay open side by side, each keeping its place and its
unsaved edits. The main window wires the pages' requests (refresh, ask for
the therapist's name, show a toast) and closes an editor only when it is not
busy and its edits are saved or discarded.
"""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QHBoxLayout, QStackedWidget, QTabWidget, QVBoxLayout, QWidget

from packages.desktop.core.i18n import tr
from packages.desktop.ui import labels, motion, theme
from packages.desktop.ui.pages.capture import CapturePage
from packages.desktop.ui.pages.findings import FindingsPage
from packages.desktop.ui.pages.overview import CaseOverview
from packages.desktop.ui.pages.report import ReportPage
from packages.desktop.ui.pages.review import ReviewPage
from packages.desktop.ui.widgets import EmptyState, button, chip, label, set_chip
from packages.desktop.ui.window.common import step_titles
from packages.desktop.ui.workbench import Breadcrumbs


def case_name(case) -> str:
    return case.child_code + (f"  {case.nickname}" if case.nickname else "")


def session_day(session) -> str:
    """The session date as 16/10/2026, whether it is stored as a date or as ISO text."""
    value = session.session_date
    if isinstance(value, str):
        try:
            value = date.fromisoformat(value[:10])
        except ValueError:
            return value
    return value.strftime("%d/%m/%Y") if hasattr(value, "strftime") else str(value)


def session_key(session_id: str) -> str:
    return f"session:{session_id}"


def case_key(case_id: str) -> str:
    return f"case:{case_id}"


class SessionEditor(QWidget):
    """One session: breadcrumbs, then the Recording, Transcript, Findings and Report steps."""

    changed = Signal()  # a page changed a record
    busy_changed = Signal(bool)
    open_case = Signal(str)  # the case part of the breadcrumbs

    def __init__(self, service, runner, case, session, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.service = service
        self.case = case
        self.session = session
        self.busy = False
        self.steps_done = [False] * 4
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        head = QWidget()
        head.setObjectName("EditorHeader")
        head_layout = QHBoxLayout(head)
        head_layout.setContentsMargins(0, 2, 20, 0)
        self.crumbs = Breadcrumbs()
        head_layout.addWidget(self.crumbs, 1)
        self.consent_chip = chip("")
        head_layout.addWidget(self.consent_chip, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(head)
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(24, 4, 24, 8)
        self.tabs = QTabWidget()
        self.tabs.setObjectName("StepTabs")
        self.tabs.setDocumentMode(True)
        self.pages = [
            CapturePage(service, runner),
            ReviewPage(service, runner),
            FindingsPage(service, runner),
            ReportPage(service, runner),
        ]
        for page, title in zip(self.pages, step_titles()):
            self.tabs.addTab(page, title)
            page.changed.connect(self.changed.emit)
            page.navigate.connect(self.tabs.setCurrentIndex)
            page.busy_changed.connect(self._on_busy)
        self.tabs.currentChanged.connect(self._on_step)
        body_layout.addWidget(self.tabs)
        layout.addWidget(body, 1)
        self._loaded = False

    # ------------------------------------------------------------------
    def load(self) -> None:
        """Read the session again and fill every page; the first load opens the step still to do."""
        self.case = self.service.get_case(self.case.case_id)
        self.session = self.service.get_session(self.session.session_id)
        current = self.tabs.currentIndex()
        for page in self.pages:
            page.load(self.case, self.session)
        if not self._loaded:
            # A signed session (step 4) opens on its report.
            self.tabs.setCurrentIndex(min(self.service.session_step(self.session), 3))
            self._loaded = True
        else:
            self.tabs.setCurrentIndex(current)
        self.update_header()
        self.update_steps()

    def update_header(self, case=None) -> None:
        if case is not None:
            self.case = case
        text, kind = labels.CONSENT.get(self.case.consent_status, (self.case.consent_status, "neutral"))
        set_chip(self.consent_chip, text, kind)
        self.crumbs.set_parts([
            (case_name(self.case), lambda: self.open_case.emit(self.case.case_id)),
            (f"{session_day(self.session)} · {labels.status_text(self.session.status)}", None),
            (step_titles()[self.tabs.currentIndex()].split("  ", 1)[-1], None),
        ])

    def update_steps(self) -> None:
        """Finished steps are shown quieter, so the step still to do stands out."""
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

    def title(self) -> str:
        return f"{self.case.child_code} · {session_day(self.session)}"

    def tooltip(self) -> str:
        return f"{case_name(self.case)} · {session_day(self.session)} · {labels.status_text(self.session.status)}"

    def has_unsaved_changes(self) -> bool:
        return any(page.has_unsaved_changes() for page in self.pages)

    def dirty_pages(self) -> list:
        return [page for page in self.pages if page.has_unsaved_changes()]

    def stop_playback(self) -> None:
        review = self.pages[1]
        if hasattr(review, "stop_playback"):
            review.stop_playback()

    def shutdown(self) -> None:
        for page in self.pages:
            if hasattr(page, "shutdown"):
                page.shutdown()

    def _on_busy(self, busy: bool) -> None:
        self.busy = busy
        self.busy_changed.emit(busy)

    def _on_step(self, index: int) -> None:
        if index >= 0 and self._loaded:
            self.update_header()
            motion.fade_in(self.tabs.currentWidget())


class CaseEditor(QWidget):
    """One case: its details and consent, a button for a new session, and its sessions."""

    def __init__(self, service, case, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.service = service
        self.case = case
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.crumbs = Breadcrumbs()
        layout.addWidget(self.crumbs)
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(32, 10, 32, 10)
        body_layout.setSpacing(8)
        head = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        self.case_title = label("", "CaseTitle")
        self.case_meta = label("", "Muted")
        title_box.addWidget(self.case_title)
        title_box.addWidget(self.case_meta)
        head.addLayout(title_box)
        head.addStretch(1)
        self.consent_chip = chip("")
        head.addWidget(self.consent_chip, 0, Qt.AlignmentFlag.AlignVCenter)
        self.consent_btn = button("")
        head.addWidget(self.consent_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        self.new_session_btn = button(tr("+ Session ใหม่", "+ New session"), "primary")
        head.addWidget(self.new_session_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        self.more_btn = button("⋯", tooltip=tr("แก้ไขหรือลบเคส", "Edit or delete the case"))
        self.more_btn.setFixedWidth(40)
        head.addWidget(self.more_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        body_layout.addLayout(head)
        body_layout.addSpacing(6)
        self.stack = QStackedWidget()
        self.no_session = EmptyState("", "")
        self.no_session_btn = button("", "primary")
        self.no_session.actions.addWidget(self.no_session_btn)
        self.stack.addWidget(self.no_session)
        self.overview = CaseOverview(service)
        self.stack.addWidget(self.overview)
        body_layout.addWidget(self.stack, 1)
        layout.addWidget(body, 1)

    def load(self) -> None:
        case = self.case = self.service.get_case(self.case.case_id)
        self.crumbs.set_parts([(tr("เคส", "Cases"), None), (case_name(case), None)])
        self.case_title.setText(case_name(case))
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
        sessions = self.service.list_sessions(case.case_id)
        if sessions:
            self.overview.load(case)
            self.stack.setCurrentWidget(self.overview)
            return
        self.stack.setCurrentWidget(self.no_session)
        if case.consent_status == "granted":
            self.no_session.set_text(tr("ยังไม่มี session", "No sessions yet"),
                                     tr("เพิ่ม session เพื่อบันทึกหรือนำเข้าเสียง", "Add a session to record or import audio."))
            self.no_session_btn.setText(tr("เพิ่ม session", "Add session"))
            self.no_session_btn.setVisible(True)
        elif case.consent_status == "pending":
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

    def title(self) -> str:
        return self.case.child_code

    def tooltip(self) -> str:
        return f"{case_name(self.case)} · {labels.age_text(self.case.age_months)}"

    def has_unsaved_changes(self) -> bool:
        return False
