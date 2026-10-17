"""The main window: cases on the left, the selected session's steps on the right."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QSettings, Qt, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QKeySequence
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from packages.desktop.core import DesktopService
from packages.desktop.core.backup import BackupError, read_backup, restore_backup
from packages.desktop.ui import dialogs, labels, theme
from packages.desktop.ui.pages.capture import CapturePage
from packages.desktop.ui.pages.findings import FindingsPage
from packages.desktop.ui.pages.overview import CaseOverview
from packages.desktop.ui.pages.report import ReportPage
from packages.desktop.ui.pages.review import ReviewPage
from packages.desktop.ui.tasks import TaskRunner
from packages.desktop.ui.widgets import EmptyState, button, chip, label, set_chip

STEPS = ["1 · เสียง", "2 · ตรวจ transcript", "3 · ตัวชี้วัดและ cue", "4 · รายงาน"]
OVERVIEW = "__overview__"  # session picker entry for the case overview
NO_SESSION_PAGE, SESSION_PAGE, OVERVIEW_PAGE = range(3)


class MainWindow(QMainWindow):
    def __init__(self, service: DesktopService, version: str = "") -> None:
        super().__init__()
        self.service = service
        self.version = version
        self.runner = TaskRunner(self)
        self.case = None
        self.session = None
        self.busy = False
        self._switching = False
        self.setWindowTitle("PasaScope")
        self.resize(1280, 820)
        self.setMinimumSize(980, 640)

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_sidebar())

        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)
        self.no_case = EmptyState("เลือกเคสทางซ้าย หรือเพิ่มเคสใหม่", "ข้อมูลทั้งหมดเก็บอยู่ในเครื่องนี้")
        new_btn = button("+ เพิ่มเคสใหม่", "primary")
        new_btn.clicked.connect(self.new_case)
        self.no_case.actions.addWidget(new_btn)
        self.stack.addWidget(self.no_case)
        self.stack.addWidget(self._build_case_view())

        self._build_menus()
        self.asr_label = QLabel("")
        self.name_label = QLabel("")
        self.backup_label = QLabel("")
        self.backup_label.setTextFormat(Qt.TextFormat.RichText)
        self.backup_label.linkActivated.connect(lambda _: self.backup())
        self.statusBar().setContentsMargins(12, 0, 12, 0)
        self.statusBar().addWidget(self.name_label)
        self.statusBar().addWidget(self.backup_label)
        self.statusBar().addPermanentWidget(self.asr_label)
        self._update_status_bar()

        settings = QSettings()
        geometry = settings.value("main/geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)
        self.reload_cases()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def _build_sidebar(self) -> QWidget:
        side = QFrame()
        side.setObjectName("Sidebar")
        side.setFixedWidth(280)
        layout = QVBoxLayout(side)
        layout.setContentsMargins(16, 18, 12, 12)
        layout.setSpacing(10)
        layout.addWidget(label("PasaScope", "Brand"))
        layout.addWidget(label("ช่วยถอดเสียงและวิเคราะห์ตัวอย่างภาษาเด็ก", "BrandSub", wrap=True))
        self.search = QLineEdit()
        self.search.setPlaceholderText("ค้นหารหัสหรือชื่อเล่น")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(lambda _: self.reload_cases())
        layout.addWidget(self.search)
        self.case_list = QListWidget()
        self.case_list.currentItemChanged.connect(self._on_case_item)
        layout.addWidget(self.case_list, 1)
        self.case_count = label("", "Muted")
        layout.addWidget(self.case_count)
        add = button("+ เพิ่มเคสใหม่", "primary")
        add.clicked.connect(self.new_case)
        layout.addWidget(add)
        return side

    def _build_case_view(self) -> QWidget:
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(24, 18, 24, 10)
        layout.setSpacing(10)

        head = QHBoxLayout()
        title_box = QVBoxLayout()
        self.case_title = label("", "CaseTitle")
        self.case_meta = label("", "Hint")
        title_box.addWidget(self.case_title)
        title_box.addWidget(self.case_meta)
        head.addLayout(title_box)
        head.addStretch(1)
        self.consent_chip = chip("")
        head.addWidget(self.consent_chip, 0, Qt.AlignmentFlag.AlignVCenter)
        self.consent_btn = button("")
        self.consent_btn.clicked.connect(self._consent_action)
        head.addWidget(self.consent_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addLayout(head)

        session_row = QHBoxLayout()
        session_row.addWidget(label("Session", "SectionTitle"))
        self.session_pick = QComboBox()
        self.session_pick.setMinimumWidth(320)
        self.session_pick.currentIndexChanged.connect(self._on_session_pick)
        session_row.addWidget(self.session_pick)
        self.new_session_btn = button("+ session ใหม่")
        self.new_session_btn.clicked.connect(self.new_session)
        session_row.addWidget(self.new_session_btn)
        session_row.addStretch(1)
        layout.addLayout(session_row)

        self.session_stack = QStackedWidget()
        self.no_session = EmptyState("", "")
        self.no_session_btn = button("", "primary")
        self.no_session_btn.clicked.connect(self._no_session_action)
        self.no_session.actions.addWidget(self.no_session_btn)
        self.session_stack.addWidget(self.no_session)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.pages = [
            CapturePage(self.service, self.runner),
            ReviewPage(self.service, self.runner),
            FindingsPage(self.service, self.runner),
            ReportPage(self.service, self.runner),
        ]
        for page, title in zip(self.pages, STEPS):
            self.tabs.addTab(page, title)
            page.changed.connect(self.refresh_session)
            page.navigate.connect(self.tabs.setCurrentIndex)
            page.busy_changed.connect(self._set_busy)
        self.pages[1].attested.connect(self.learn_speakers_in_background)
        self.session_stack.addWidget(self.tabs)
        self.overview = CaseOverview(self.service)
        self.overview.open_session.connect(self._pick_session)
        self.session_stack.addWidget(self.overview)
        layout.addWidget(self.session_stack, 1)
        return view

    def _build_menus(self) -> None:
        bar = self.menuBar()
        file_menu = bar.addMenu("ไฟล์")
        new_case = QAction("เพิ่มเคสใหม่…", self)
        new_case.setShortcut(QKeySequence("Ctrl+N"))
        new_case.triggered.connect(self.new_case)
        file_menu.addAction(new_case)
        open_folder = QAction("เปิดโฟลเดอร์ข้อมูล", self)
        open_folder.triggered.connect(
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.service.workspace.root)))
        )
        file_menu.addAction(open_folder)
        file_menu.addSeparator()
        backup_action = QAction("สำรองข้อมูล…", self)
        backup_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        backup_action.triggered.connect(self.backup)
        file_menu.addAction(backup_action)
        restore_action = QAction("กู้คืนจากไฟล์สำรอง…", self)
        restore_action.triggered.connect(self.restore)
        file_menu.addAction(restore_action)
        file_menu.addSeparator()
        quit_action = QAction("ออก", self)
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        settings_menu = bar.addMenu("ตั้งค่า")
        name_action = QAction("ชื่อนักบำบัด…", self)
        name_action.triggered.connect(lambda: self.ask_therapist_name(first_run=False))
        settings_menu.addAction(name_action)
        settings_menu.addSeparator()
        mode_menu = settings_menu.addMenu("โหมดถอดเสียง")
        self.mode_actions = {}
        for mode, text in (
            ("accurate", "แม่นยำ: โมเดลภาษาไทย (ช้ากว่า ราว 5 เท่าของความยาวเสียง)"),
            ("fast", "เร็ว: โมเดลหลายภาษา (ราวเท่าความยาวเสียง แต่ผิดมากกว่า)"),
        ):
            action = QAction(text, self, checkable=True)
            action.setChecked(self.service.transcription_mode == mode)
            action.triggered.connect(lambda _=False, m=mode: self._set_mode(m))
            mode_menu.addAction(action)
            self.mode_actions[mode] = action
        speaker_action = QAction("การแยกเสียงเด็ก/ผู้ใหญ่ของคลินิก…", self)
        speaker_action.triggered.connect(self.show_speaker_model)
        settings_menu.addAction(speaker_action)

        help_menu = bar.addMenu("ช่วยเหลือ")
        audit = QAction("ประวัติการทำงาน (audit log)", self)
        audit.triggered.connect(self.show_audit_log)
        help_menu.addAction(audit)
        about = QAction("เกี่ยวกับ PasaScope", self)
        about.triggered.connect(self.show_about)
        help_menu.addAction(about)

    # ------------------------------------------------------------------
    # Cases
    # ------------------------------------------------------------------
    def reload_cases(self, select_id: str | None = None) -> None:
        select_id = select_id or (self.case.case_id if self.case else None)
        cases = self.service.list_cases(self.search.text())
        self._switching = True
        self.case_list.clear()
        for case in cases:
            consent_text, _ = labels.CONSENT.get(case.consent_status, (case.consent_status, ""))
            name = f"{case.child_code}" + (f" · {case.nickname}" if case.nickname else "")
            item = QListWidgetItem(f"{name}\n{labels.age_text(case.age_months)} · {consent_text}")
            item.setData(Qt.ItemDataRole.UserRole, case.case_id)
            if case.consent_status == "withdrawn":
                item.setForeground(Qt.GlobalColor.gray)
            self.case_list.addItem(item)
            if case.case_id == select_id:
                self.case_list.setCurrentItem(item)
        self._switching = False
        total = len(self.service.list_cases())
        self.case_count.setText(f"{len(cases)} จาก {total} เคส" if self.search.text() else f"{total} เคส")
        if self.case_list.currentItem() is None:
            self.case = None
            self.session = None
            self.stack.setCurrentIndex(0)

    def _confirm_leave(self) -> bool:
        dirty = [p for p in self.pages if p.has_unsaved_changes()]
        if not dirty:
            return True
        answer = QMessageBox.question(
            self, "มีการแก้ไขที่ยังไม่บันทึก",
            "บันทึกการแก้ไขก่อนเปลี่ยนหน้า?",
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
        if self.case and case_id == self.case.case_id:
            return
        if not self._confirm_leave():
            self._switching = True
            self.case_list.setCurrentItem(previous)
            self._switching = False
            return
        self.open_case(case_id)

    def open_case(self, case_id: str, session_id: str | None = None) -> None:
        self.case = self.service.get_case(case_id)
        self.stack.setCurrentIndex(1)
        self._fill_case_header()
        self._fill_sessions(session_id)

    def _fill_case_header(self) -> None:
        case = self.case
        self.case_title.setText(case.child_code + (f"  ·  {case.nickname}" if case.nickname else ""))
        meta = [f"อายุ {labels.age_text(case.age_months)} (ตอนเปิดเคส)", f"ภาษา {case.language}"]
        self.case_meta.setText(" · ".join(meta))
        text, kind = labels.CONSENT.get(case.consent_status, (case.consent_status, "neutral"))
        set_chip(self.consent_chip, text, kind)
        if case.consent_status == "granted":
            self.consent_btn.setText("ถอนความยินยอม…")
            self.consent_btn.setProperty("role", "danger")
            self.consent_btn.setVisible(True)
        elif case.consent_status == "pending":
            self.consent_btn.setText("บันทึกความยินยอม…")
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
                self.no_session.set_text("ยังไม่มี session", "สร้าง session แรกเพื่อบันทึกหรือนำเข้าเสียง")
                self.no_session_btn.setText("+ สร้าง session แรก")
                self.no_session_btn.setVisible(True)
            elif self.case.consent_status == "pending":
                self.no_session.set_text("บันทึกความยินยอมก่อน", "ต้องมีเอกสารยินยอมของผู้ปกครองก่อนบันทึกเสียงหรือเพิ่มข้อมูลของเด็ก")
                self.no_session_btn.setText("บันทึกความยินยอม…")
                self.no_session_btn.setVisible(True)
            else:
                self.no_session.set_text("ถอนความยินยอมแล้ว", "เคสนี้เพิ่มข้อมูลใหม่ไม่ได้")
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
            self.session_pick.addItem(f"ภาพรวมเคส · {len(sessions)} session", OVERVIEW)
        for session in sessions:
            self.session_pick.addItem(f"{session.session_date} · {labels.status_text(session.status)}", session.session_id)
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
        if self.session is None:
            return
        transcript = self.service.get_transcript(self.session.session_id)
        features = self.service.get_features(self.session.session_id)
        report = self.service.get_report(self.session.session_id)
        marks = [
            transcript is not None,
            bool(transcript and transcript.therapist_attested),
            features is not None and not self.session.findings_stale,
            bool(report and (report.status.value if hasattr(report.status, "value") else report.status) == "Signed Off"),
        ]
        for index, (title, done) in enumerate(zip(STEPS, marks)):
            self.tabs.setTabText(index, f"{title}  ✓" if done else title)

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

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
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
            QMessageBox.information(self, "รอสักครู่", "รอให้การถอดเสียงหรือการบันทึกเสียงเสร็จก่อน")
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

    def _set_mode(self, mode: str) -> None:
        try:
            self.service.set_transcription_mode(mode)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "ตั้งค่าไม่สำเร็จ", str(exc))
        for key, action in self.mode_actions.items():
            action.setChecked(key == self.service.transcription_mode)
        self._update_status_bar()

    # ------------------------------------------------------------------
    # The clinic's own child/adult model
    # ------------------------------------------------------------------
    def show_speaker_model(self) -> None:
        dialog = dialogs.ClinicSpeakerDialog(self.service.clinic_speaker_status(), self)
        dialog.exec()
        if dialog.enabled.isChecked() != self.service.clinic_speaker_enabled:
            self.service.set_clinic_speaker_enabled(dialog.enabled.isChecked())
        if dialog.choice == "train":
            self.learn_speakers_in_background(force=True)
        elif dialog.choice == "reset":
            answer = QMessageBox.question(
                self, "ล้างโมเดลประจำคลินิก",
                "ล้างสิ่งที่โปรแกรมเรียนไว้ แล้วกลับไปใช้โมเดลพื้นฐาน? โปรแกรมจะเริ่มเรียนใหม่เมื่อรับรอง transcript ครั้งต่อไป",
            )
            if answer == QMessageBox.StandardButton.Yes:
                self.service.reset_clinic_speaker_model()
                self.statusBar().showMessage("ล้างโมเดลประจำคลินิกแล้ว", 8000)

    def learn_speakers_in_background(self, force: bool = False) -> None:
        """After an attestation, retrain the clinic's child/adult model without blocking the window."""
        from packages.desktop.ui import labels as wording

        if getattr(self, "_learning_speakers", False) or not (force or self.service.clinic_speaker_enabled):
            return
        sessions = self.service.clinic_speaker_training_sessions()
        status = self.service.clinic_speaker_status()
        if status["sessions_needed"] or status["children_needed"]:
            return
        self._learning_speakers = True
        self.statusBar().showMessage("กำลังเรียนเสียงจาก session ที่รับรองแล้ว (ทำงานเบื้องหลัง)…")

        def done(result) -> None:
            self._learning_speakers = False
            self.statusBar().showMessage(
                "การแยกเสียงเด็ก/ผู้ใหญ่: " + wording.clinic_speaker_text(self.service.save_clinic_speaker_result(result)), 15000
            )

        def failed(exc: Exception) -> None:
            self._learning_speakers = False
            self.statusBar().showMessage(f"เรียนเสียงไม่สำเร็จ ({type(exc).__name__}) ยังใช้โมเดลเดิม", 15000)

        self.runner.run(lambda: self.service.train_clinic_speaker_model(sessions), on_done=done, on_error=failed)

    def show_audit_log(self) -> None:
        dialogs.AuditLogDialog(self.service.audit_events(500), self).exec()

    def show_about(self) -> None:
        QMessageBox.about(
            self,
            "เกี่ยวกับ PasaScope",
            f"<b>PasaScope</b> {self.version}<br><br>"
            "โปรแกรมช่วยนักบำบัดถอดเสียงและวิเคราะห์ตัวอย่างภาษาของเด็ก<br>"
            "ถอดเสียงด้วย Whisper บนเครื่องนี้ ข้อมูลไม่ออกจากเครื่อง<br><br>"
            "เป็นเครื่องมือสนับสนุนการตัดสินใจทางคลินิก ไม่ใช่เครื่องมือวินิจฉัย "
            "และยังไม่ได้ตรวจสอบความถูกต้องทางคลินิกกับเด็กไทย<br><br>"
            f"โฟลเดอร์ข้อมูล: {self.service.workspace.root}",
        )

    # ------------------------------------------------------------------
    # Window state
    # ------------------------------------------------------------------
    def _set_busy(self, busy: bool) -> None:
        self.busy = busy
        self.case_list.setEnabled(not busy)
        self.session_pick.setEnabled(not busy)
        self.new_session_btn.setEnabled(not busy and bool(self.case) and self.case.consent_status == "granted")

    def _update_status_bar(self) -> None:
        name = self.service.therapist_name
        self.name_label.setText(f"นักบำบัด: {name}" if name else "ยังไม่ได้ตั้งชื่อนักบำบัด (เมนู ตั้งค่า)")
        available, reason = self.service.transcription_availability()
        mode = "แม่นยำ" if self.service.transcription_mode == "accurate" else "เร็ว"
        self.asr_label.setText(f"ถอดเสียงบนเครื่อง: พร้อม · โหมด{mode}" if available else f"ถอดเสียงบนเครื่อง: ไม่พร้อม ({reason})")
        self.asr_label.setStyleSheet(f"color: {theme.OK if available else theme.ATTENTION};")
        self._update_backup_label()

    def _update_backup_label(self) -> None:
        last = self.service.last_backup_at
        when = f"สำรองล่าสุด {last:%d/%m/%Y %H:%M}" if last else "ยังไม่เคยสำรองข้อมูล"
        if self.service.backup_due():
            self.backup_label.setText(f'· <span style="color:{theme.ATTENTION}">{when}</span> <a href="backup">สำรองตอนนี้</a>')
        else:
            self.backup_label.setText(f'· <span style="color:{theme.MUTED}">{when}</span>')

    # ------------------------------------------------------------------
    # Backup and restore
    # ------------------------------------------------------------------
    def backup(self) -> None:
        if self.busy or self.runner.busy:
            QMessageBox.information(self, "สำรองข้อมูล", "รอให้งานที่ทำอยู่เสร็จก่อน แล้วค่อยสำรองข้อมูล")
            return
        if not self._confirm_leave():
            return
        last_dir = QSettings().value("backup/folder") or str(Path.home() / "Documents")
        default = Path(last_dir) / f"PasaScope-สำรอง-{datetime.now():%Y-%m-%d-%H%M}.zip"
        path, _ = QFileDialog.getSaveFileName(self, "สำรองข้อมูลไปที่", str(default), "ไฟล์สำรอง PasaScope (*.zip)")
        if not path:
            return
        target = Path(path) if path.lower().endswith(".zip") else Path(path + ".zip")
        if target.resolve().is_relative_to(self.service.workspace.root):
            QMessageBox.warning(self, "สำรองข้อมูล", "เลือกที่เก็บนอกโฟลเดอร์ข้อมูลของโปรแกรม เช่น ไดรฟ์ภายนอก")
            return
        QSettings().setValue("backup/folder", str(target.parent))
        self._set_busy(True)
        self.statusBar().showMessage("กำลังสำรองข้อมูล…")

        def done(info) -> None:
            self._set_busy(False)
            self.statusBar().clearMessage()
            self._update_backup_label()
            counts = info.counts
            QMessageBox.information(
                self, "สำรองข้อมูลแล้ว",
                f"บันทึกที่ {info.path}\n"
                f"{counts.get('cases', 0)} เคส · {counts.get('sessions', 0)} session · "
                f"{counts.get('recordings', 0)} ไฟล์เสียง · {info.total_bytes / 1_048_576:.1f} MB\n\n"
                "ไฟล์นี้ไม่เข้ารหัส และมีเสียงกับข้อความของเด็ก เก็บไว้ในที่ที่มีแต่นักบำบัดเข้าถึงได้",
            )

        def failed(exc: Exception) -> None:
            self._set_busy(False)
            self.statusBar().clearMessage()
            QMessageBox.critical(self, "สำรองข้อมูลไม่สำเร็จ", f"{type(exc).__name__}: {exc}")

        self.runner.run(lambda: self.service.create_backup(target, self.version), on_done=done, on_error=failed)

    def restore(self) -> None:
        if self.busy or self.runner.busy:
            QMessageBox.information(self, "กู้คืนข้อมูล", "รอให้งานที่ทำอยู่เสร็จก่อน")
            return
        if not self._confirm_leave():
            return
        last_dir = QSettings().value("backup/folder") or str(Path.home() / "Documents")
        path, _ = QFileDialog.getOpenFileName(self, "เลือกไฟล์สำรอง", str(last_dir), "ไฟล์สำรอง PasaScope (*.zip)")
        if not path:
            return
        try:
            info = read_backup(Path(path))
        except BackupError as exc:
            QMessageBox.warning(self, "กู้คืนข้อมูล", str(exc))
            return
        counts = info.counts
        demo = "\n\nไฟล์นี้สำรองมาจากข้อมูลสาธิต (Demo)" if info.demo else ""
        answer = QMessageBox.question(
            self, "กู้คืนข้อมูล",
            f"ไฟล์สำรองเมื่อ {info.created_at[:16].replace('T', ' ')}\n"
            f"{counts.get('cases', 0)} เคส · {counts.get('sessions', 0)} session · {counts.get('recordings', 0)} ไฟล์เสียง{demo}\n\n"
            "ข้อมูลปัจจุบันทั้งหมดจะถูกแทนที่ด้วยไฟล์สำรองนี้ ข้อมูลปัจจุบันไม่ถูกลบ "
            "แต่จะย้ายไปไว้ในโฟลเดอร์ \"ก่อนกู้คืน\" ข้าง ๆ กัน\n\nกู้คืนแล้วโปรแกรมจะปิด ต้องเปิดใหม่ กู้คืนเลยไหม?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.service.close()
        try:
            previous = restore_backup(self.service.workspace.root, info.path)
        except (BackupError, OSError) as exc:
            QMessageBox.critical(self, "กู้คืนไม่สำเร็จ", f"ข้อมูลปัจจุบันยังอยู่ครบ ไม่ได้เปลี่ยนแปลง\n\n{exc}")
            return
        QMessageBox.information(
            self, "กู้คืนแล้ว",
            f"ข้อมูลเดิมย้ายไปที่ {previous}\nโปรแกรมจะปิดตอนนี้ เปิดใหม่เพื่อใช้ข้อมูลที่กู้คืน",
        )
        self._restored = True
        self.close()

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt override
        if getattr(self, "_restored", False):
            event.accept()
            return
        if self.busy or self.runner.busy:
            answer = QMessageBox.question(
                self, "กำลังทำงานอยู่", "ยังถอดเสียงหรือบันทึกเสียงอยู่ ปิดโปรแกรมแล้วงานนี้จะหยุด ปิดเลยไหม?"
            )
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
        if not self._confirm_leave():
            event.ignore()
            return
        for page in self.pages:
            if hasattr(page, "shutdown"):
                page.shutdown()
        QSettings().setValue("main/geometry", self.saveGeometry())
        self.runner.wait(3000)
        event.accept()
