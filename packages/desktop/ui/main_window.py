"""The main window: navigation on the left; Home, a case, or Knowledge on the right."""

from __future__ import annotations

from html import escape

from PySide6.QtCore import QSettings, Qt, QUrl
from PySide6.QtGui import QAction, QActionGroup, QDesktopServices, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from packages.desktop.core import DesktopService
from packages.desktop.core.i18n import LANGUAGES, language, tr
from packages.desktop.ui import motion, theme
from packages.desktop.ui.pages.capture import CapturePage
from packages.desktop.ui.pages.dashboard import Dashboard
from packages.desktop.ui.pages.findings import FindingsPage
from packages.desktop.ui.pages.knowledge import KnowledgePage
from packages.desktop.ui.pages.overview import CaseOverview
from packages.desktop.ui.pages.report import ReportPage
from packages.desktop.ui.pages.review import ReviewPage
from packages.desktop.ui.tasks import TaskRunner
from packages.desktop.ui.widgets import EmptyState, button, chip, label, repolish
from packages.desktop.ui.window.common import (  # noqa: F401 - tests and the theme change use these from here
    LOGO,
    OVERVIEW,
    NO_SESSION_PAGE,
    SESSION_PAGE,
    OVERVIEW_PAGE,
    HOME_PAGE,
    CASE_PAGE,
    KNOWLEDGE_PAGE,
    _LIVE,
    step_titles,
)
from packages.desktop.ui.window.case_view import CaseViewMixin
from packages.desktop.ui.window.case_actions import CaseActionsMixin
from packages.desktop.ui.window.settings_actions import SettingsActionsMixin
from packages.desktop.ui.window.updates import UpdatesMixin
from packages.desktop.ui.window.appearance import AppearanceMixin
from packages.desktop.ui.window.backup import BackupMixin


class MainWindow(
    CaseViewMixin,
    CaseActionsMixin,
    SettingsActionsMixin,
    UpdatesMixin,
    AppearanceMixin,
    BackupMixin,
    QMainWindow,
):
    def __init__(self, service: DesktopService, version: str = "") -> None:
        super().__init__()
        self.service = service
        self.version = version
        self.runner = TaskRunner(self)
        self.case = None
        self.session = None
        self.busy = False
        self._switching = False
        self._restyle_pending = False  # a theme change waits for work or unsaved edits
        self._replaced = False  # a theme change built a new window in place of this one
        self.steps_done = [False] * 4
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
        self.dashboard = Dashboard(self.service)
        self.dashboard.open_case.connect(self._open_from_dashboard)
        self.dashboard.new_case.connect(self.new_case)
        self.dashboard.backup.connect(self.backup)
        self.dashboard.speaker_settings.connect(self.show_speaker_model)
        self.dashboard.download_models.connect(self.download_models)
        self.stack.addWidget(self.dashboard)
        self.stack.addWidget(self._build_case_view())
        self.knowledge = KnowledgePage()
        self.stack.addWidget(self.knowledge)

        self._build_menus()
        self.asr_label = QLabel("")
        self.name_label = QLabel("")
        self.name_label.setTextFormat(Qt.TextFormat.RichText)
        self.name_label.linkActivated.connect(lambda _: self.ask_therapist_name(first_run=False))
        self.backup_label = QLabel("")
        self.backup_label.setTextFormat(Qt.TextFormat.RichText)
        self.backup_label.linkActivated.connect(lambda _: self.backup())
        self.statusBar().setContentsMargins(12, 0, 12, 0)
        self.statusBar().addWidget(self.name_label)
        self.statusBar().addWidget(self.backup_label)
        self.update_label = QLabel("")
        self.update_label.setTextFormat(Qt.TextFormat.RichText)
        self.update_label.linkActivated.connect(lambda _: self._offer_update(self._available_update))
        self.update_label.hide()
        self._available_update = None
        self.statusBar().addPermanentWidget(self.update_label)
        self.statusBar().addPermanentWidget(self.asr_label)
        self._update_status_bar()

        settings = QSettings()
        geometry = settings.value("main/geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)
        self.toast = motion.Toast(self)
        self.stack.currentChanged.connect(lambda _: motion.fade_in(self.stack.currentWidget()))
        self.session_stack.currentChanged.connect(lambda _: motion.fade_in(self.session_stack.currentWidget()))
        self.tabs.currentChanged.connect(lambda _: motion.fade_in(self.tabs.currentWidget()))
        self.reload_cases()
        self.show_home()
        self.runner.idle.connect(self._apply_pending_restyle)
        QApplication.instance().styleHints().colorSchemeChanged.connect(self._on_system_scheme)

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def _build_sidebar(self) -> QWidget:
        side = QFrame()
        side.setObjectName("Sidebar")
        side.setFixedWidth(260)
        layout = QVBoxLayout(side)
        layout.setContentsMargins(12, 16, 12, 12)
        layout.setSpacing(2)
        brand_row = QHBoxLayout()
        brand_row.setContentsMargins(8, 0, 0, 10)
        brand_row.setSpacing(8)
        mark = QLabel()
        logo = QPixmap(str(LOGO))
        if not logo.isNull():
            ratio = self.devicePixelRatioF() or 1.0
            logo = logo.scaled(int(22 * ratio), int(22 * ratio), Qt.AspectRatioMode.KeepAspectRatio,
                               Qt.TransformationMode.SmoothTransformation)
            logo.setDevicePixelRatio(ratio)
            mark.setPixmap(logo)
        brand_row.addWidget(mark)
        brand_row.addWidget(label("PasaScope", "Brand"))
        brand_row.addStretch(1)
        layout.addLayout(brand_row)
        self.home_btn = button(tr("หน้าแรก", "Home"), "nav")
        self.home_btn.clicked.connect(self.show_home)
        self.knowledge_btn = button(tr("ความรู้", "Knowledge"), "nav")
        self.knowledge_btn.clicked.connect(self.show_knowledge)
        for nav in (self.home_btn, self.knowledge_btn):
            nav.setCheckable(True)
            layout.addWidget(nav)
        layout.addSpacing(14)
        cases_title = label(tr("เคส", "Cases"), "SidebarHeading")
        cases_title.setContentsMargins(8, 0, 0, 4)
        layout.addWidget(cases_title)
        self.search = QLineEdit()
        self.search.setPlaceholderText(tr("ค้นหารหัสหรือชื่อเล่น", "Search code or nickname"))
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(lambda _: self.reload_cases())
        layout.addWidget(self.search)
        layout.addSpacing(4)
        self.case_list = QListWidget()
        self.case_list.currentItemChanged.connect(self._on_case_item)
        self.case_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.case_list.customContextMenuRequested.connect(self._case_list_menu)
        # Delete (and the Mac's delete key, Backspace) on a selected case asks to delete it.
        for key in (QKeySequence.StandardKey.Delete, QKeySequence(Qt.Key.Key_Backspace)):
            shortcut = QShortcut(key, self.case_list)
            shortcut.setContext(Qt.ShortcutContext.WidgetShortcut)
            shortcut.activated.connect(self._delete_selected_case)
        layout.addWidget(self.case_list, 1)
        self.case_count = label("", "Muted")
        self.case_count.setContentsMargins(8, 4, 0, 4)
        layout.addWidget(self.case_count)
        add = button(tr("+ เพิ่มเคส", "+ New case"), "nav")
        add.clicked.connect(self.new_case)
        layout.addWidget(add)
        layout.addSpacing(10)
        line = QFrame()
        line.setObjectName("SidebarRule")
        line.setFixedHeight(1)
        layout.addWidget(line)
        layout.addSpacing(8)
        therapist_title = label(tr("นักบำบัดในเครื่องนี้", "Therapist on this computer"), "SidebarHeading")
        therapist_title.setContentsMargins(8, 0, 0, 2)
        layout.addWidget(therapist_title)
        # The name signs attestations and reports, so it is one click away.
        therapist_row = QHBoxLayout()
        therapist_row.setContentsMargins(8, 0, 0, 0)
        therapist_row.setSpacing(6)
        self.therapist_label = label("", "TherapistName")
        therapist_row.addWidget(self.therapist_label, 1)
        self.therapist_btn = button(tr("เปลี่ยน", "Change"), "ghost", tr("เปลี่ยนชื่อนักบำบัด", "Change the therapist name"))
        self.therapist_btn.clicked.connect(lambda: self.ask_therapist_name(first_run=False))
        therapist_row.addWidget(self.therapist_btn)
        layout.addLayout(therapist_row)
        return side

    def _build_case_view(self) -> QWidget:
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(32, 22, 32, 10)
        layout.setSpacing(8)

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
        self.consent_btn.clicked.connect(self._consent_action)
        head.addWidget(self.consent_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        self.case_more_btn = button("⋯", tooltip=tr("แก้ไขหรือลบเคส", "Edit or delete the case"))
        self.case_more_btn.setFixedWidth(40)
        self.case_more_btn.clicked.connect(
            lambda: self._case_menu(self.case.case_id).exec(self.case_more_btn.mapToGlobal(self.case_more_btn.rect().bottomLeft()))
        )
        head.addWidget(self.case_more_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addLayout(head)

        session_row = QHBoxLayout()
        self.session_pick = QComboBox()
        self.session_pick.setMinimumWidth(300)
        self.session_pick.currentIndexChanged.connect(self._on_session_pick)
        session_row.addWidget(self.session_pick)
        self.new_session_btn = button(tr("+ Session ใหม่", "+ New session"))
        self.new_session_btn.clicked.connect(self.new_session)
        session_row.addWidget(self.new_session_btn)
        session_row.addStretch(1)
        layout.addSpacing(6)
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
        for page, title in zip(self.pages, step_titles()):
            self.tabs.addTab(page, title)
            page.changed.connect(self.refresh_session)
            page.navigate.connect(self.tabs.setCurrentIndex)
            page.busy_changed.connect(self._set_busy)
            page.ask_name.connect(lambda: self.ask_therapist_name(first_run=False))
            page.notify.connect(self.notify)
        self.pages[1].attested.connect(self.learn_speakers_in_background)
        self.pages[2].open_guide.connect(self.show_feature_guide)
        self.session_stack.addWidget(self.tabs)
        self.overview = CaseOverview(self.service)
        self.overview.open_session.connect(self._pick_session)
        self.overview.delete_session.connect(self.delete_session)
        self.session_stack.addWidget(self.overview)
        layout.addWidget(self.session_stack, 1)
        return view

    def _build_menus(self) -> None:
        bar = self.menuBar()
        file_menu = bar.addMenu(tr("ไฟล์", "File"))
        new_case = QAction(tr("เพิ่มเคส…", "New case…"), self)
        new_case.setShortcut(QKeySequence("Ctrl+N"))
        new_case.triggered.connect(self.new_case)
        file_menu.addAction(new_case)
        open_folder = QAction(tr("เปิดโฟลเดอร์ข้อมูล", "Open data folder"), self)
        open_folder.triggered.connect(
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.service.workspace.root)))
        )
        file_menu.addAction(open_folder)
        file_menu.addSeparator()
        backup_action = QAction(tr("สำรองข้อมูล…", "Back up…"), self)
        backup_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        backup_action.triggered.connect(self.backup)
        file_menu.addAction(backup_action)
        restore_action = QAction(tr("กู้คืนจากไฟล์สำรอง…", "Restore from backup…"), self)
        restore_action.triggered.connect(self.restore)
        file_menu.addAction(restore_action)
        file_menu.addSeparator()
        quit_action = QAction(tr("ออก", "Quit"), self)
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        self.case_bar_menu = bar.addMenu(tr("เคส", "Case"))
        self.case_bar_menu.aboutToShow.connect(self._fill_case_bar_menu)

        settings_menu = bar.addMenu(tr("ตั้งค่า", "Settings"))
        name_action = QAction(tr("ชื่อนักบำบัด…", "Therapist name…"), self)
        name_action.triggered.connect(lambda: self.ask_therapist_name(first_run=False))
        settings_menu.addAction(name_action)
        models_action = QAction(tr("ดาวน์โหลดโมเดลถอดเสียง…", "Download speech models…"), self)
        models_action.triggered.connect(self.download_models)
        settings_menu.addAction(models_action)
        organization_action = QAction(tr("ชื่อหน่วยงานบนรายงาน…", "Clinic name on reports…"), self)
        organization_action.triggered.connect(self.ask_organization)
        settings_menu.addAction(organization_action)
        settings_menu.addSeparator()
        mode_menu = settings_menu.addMenu(tr("โหมดถอดเสียง", "Transcription"))
        self.mode_actions = {}
        for mode, text in (
            ("accurate", tr("แม่นยำ: โมเดลภาษาไทย (ราว 5 เท่าของความยาวเสียง)", "Accurate: Thai model (about 5x the recording length)")),
            ("fast", tr("เร็ว: โมเดลหลายภาษา (ราวเท่าความยาวเสียง ผิดมากกว่า)", "Fast: multilingual model (about 1x, more errors)")),
        ):
            action = QAction(text, self, checkable=True)
            action.setChecked(self.service.transcription_mode == mode)
            action.triggered.connect(lambda _=False, m=mode: self._set_mode(m))
            mode_menu.addAction(action)
            self.mode_actions[mode] = action
        speaker_action = QAction(tr("แยกเสียงเด็ก/ผู้ใหญ่ของคลินิก…", "Child/adult voices…"), self)
        speaker_action.triggered.connect(self.show_speaker_model)
        settings_menu.addAction(speaker_action)
        language_menu = settings_menu.addMenu(tr("ภาษา / Language", "Language / ภาษา"))
        group = QActionGroup(self)
        for code, name in LANGUAGES.items():
            action = QAction(name, self, checkable=True)
            action.setChecked(code == language())
            action.triggered.connect(lambda _=False, c=code: self._set_language(c))
            group.addAction(action)
            language_menu.addAction(action)
        appearance_menu = settings_menu.addMenu(tr("ธีม", "Appearance"))
        appearance_group = QActionGroup(self)
        self.appearance_actions = {}
        for mode, text in (
            ("system", tr("ตามเครื่อง", "Match the computer")),
            ("light", tr("สว่าง", "Light")),
            ("dark", tr("มืด", "Dark")),
        ):
            action = QAction(text, self, checkable=True)
            action.setChecked(mode == theme.saved_mode())
            action.triggered.connect(lambda _=False, m=mode: self._set_appearance(m))
            appearance_group.addAction(action)
            appearance_menu.addAction(action)
            self.appearance_actions[mode] = action
        motion_menu = settings_menu.addMenu(tr("การเคลื่อนไหว", "Motion"))
        motion_group = QActionGroup(self)
        self.motion_actions = {}
        for mode, text in (
            ("system", tr("ตามเครื่อง (ลดการเคลื่อนไหวในการตั้งค่าระบบ)", "Match the computer (Reduce motion in system settings)")),
            ("reduce", tr("ลดการเคลื่อนไหว", "Reduce motion")),
            ("full", tr("เปิดภาพเคลื่อนไหว", "Animate")),
        ):
            action = QAction(text, self, checkable=True)
            action.setChecked(mode == motion.saved_mode())
            action.triggered.connect(lambda _=False, m=mode: motion.save_mode(m))
            motion_group.addAction(action)
            motion_menu.addAction(action)
            self.motion_actions[mode] = action

        help_menu = bar.addMenu(tr("ช่วยเหลือ", "Help"))
        knowledge = QAction(tr("ความรู้", "Knowledge"), self)
        knowledge.setShortcut(QKeySequence("F1"))
        knowledge.triggered.connect(self.show_knowledge)
        help_menu.addAction(knowledge)
        audit = QAction(tr("ประวัติการทำงาน (audit log)", "Audit log"), self)
        audit.triggered.connect(self.show_audit_log)
        help_menu.addAction(audit)
        update = QAction(tr("ตรวจหาอัปเดต…", "Check for updates…"), self)
        update.triggered.connect(lambda: self.check_for_updates(quiet=False))
        help_menu.addAction(update)
        auto_update = QAction(tr("ตรวจหาอัปเดตอัตโนมัติวันละครั้ง", "Check for updates once a day"), self, checkable=True)
        auto_update.setChecked(self.service.auto_update_check)
        auto_update.toggled.connect(self.service.set_auto_update_check)
        help_menu.addAction(auto_update)
        about = QAction(tr("เกี่ยวกับ PasaScope", "About PasaScope"), self)
        about.triggered.connect(self.show_about)
        help_menu.addAction(about)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------
    def _mark_nav(self, page: int) -> None:
        self.home_btn.setChecked(page == HOME_PAGE)
        self.knowledge_btn.setChecked(page == KNOWLEDGE_PAGE)

    def show_home(self) -> None:
        if self.stack.currentIndex() == CASE_PAGE and not self._confirm_leave():
            self._mark_nav(CASE_PAGE)
            return
        self.stop_pages()
        self.case = None
        self.session = None
        self._switching = True
        self.case_list.setCurrentItem(None)
        self.case_list.clearSelection()
        self._switching = False
        self.dashboard.refresh()
        self.stack.setCurrentIndex(HOME_PAGE)
        self._mark_nav(HOME_PAGE)

    def show_knowledge(self, topic: str | None = None) -> None:
        if isinstance(topic, str):
            self.knowledge.open_topic(topic)
        self.stack.setCurrentIndex(KNOWLEDGE_PAGE)
        self._mark_nav(KNOWLEDGE_PAGE)

    def show_feature_guide(self, name: str = "") -> None:
        """The Knowledge page's measure guide, at one measure when given."""
        self.stack.setCurrentIndex(KNOWLEDGE_PAGE)
        self._mark_nav(KNOWLEDGE_PAGE)
        self.knowledge.open_feature(name)

    def _open_from_dashboard(self, case_id: str, session_id) -> None:
        self.reload_cases(case_id)
        self.open_case(case_id, session_id)

    # ------------------------------------------------------------------
    # Window state
    # ------------------------------------------------------------------
    def notify(self, text: str, msecs: int = 5000) -> None:
        """A short message that fades away by itself (see ``motion.Toast``)."""
        self.toast.show_message(text, msecs)

    def _set_busy(self, busy: bool) -> None:
        self.busy = busy
        self.case_list.setEnabled(not busy)
        self.session_pick.setEnabled(not busy)
        self.home_btn.setEnabled(not busy)
        self.new_session_btn.setEnabled(not busy and bool(self.case) and self.case.consent_status == "granted")
        if not busy:
            self._apply_pending_restyle()

    def _update_status_bar(self) -> None:
        name = self.service.therapist_name
        self.name_label.setText(
            f"{escape(name)} · <a href='name'>{tr('เปลี่ยนชื่อ', 'Change')}</a>" if name
            else f"<a href='name'>{tr('ตั้งชื่อนักบำบัด', 'Set the therapist name')}</a>"
        )
        self.therapist_label.setText(
            self.therapist_label.fontMetrics().elidedText(name, Qt.TextElideMode.ElideRight, 170) if name
            else tr("ยังไม่ได้ตั้งชื่อ", "No name yet")
        )
        self.therapist_label.setToolTip(name)
        self.therapist_btn.setText(tr("เปลี่ยน", "Change") if name else tr("ตั้งชื่อ", "Set name"))
        available, reason = self.service.transcription_availability()
        mode = tr("แม่นยำ", "accurate") if self.service.transcription_mode == "accurate" else tr("เร็ว", "fast")
        self.asr_label.setText(
            tr(f"ถอดเสียง: พร้อม (โหมด{mode})", f"Transcription ready ({mode})") if available
            else tr(f"ถอดเสียงไม่ได้: {reason}", f"Transcription unavailable: {reason}")
        )
        self.asr_label.setObjectName("Muted" if available else "AttentionText")
        repolish(self.asr_label)
        self._update_backup_label()

    def _update_backup_label(self) -> None:
        last = self.service.last_backup_at
        when = tr(f"สำรองล่าสุด {last:%d/%m/%Y %H:%M}", f"Backed up {last:%d/%m/%Y %H:%M}") if last else tr("ยังไม่เคยสำรองข้อมูล", "Never backed up")
        if self.service.backup_due():
            self.backup_label.setText(
                f'   <span style="color:{theme.ATTENTION}">{when}</span>   <a href="backup">{tr("สำรองตอนนี้", "Back up now")}</a>'
            )
        else:
            self.backup_label.setText(f'   <span style="color:{theme.MUTED}">{when}</span>')

    # ------------------------------------------------------------------
    # Backup and restore
    # ------------------------------------------------------------------
    def closeEvent(self, event) -> None:  # noqa: N802 - Qt override
        if getattr(self, "_restored", False):
            event.accept()
            return
        if self._replaced:  # a theme change: the new window carries on, nothing to ask
            for page in self.pages:
                if hasattr(page, "shutdown"):
                    page.shutdown()
            event.accept()
            return
        if self.busy or self.runner.busy:
            answer = QMessageBox.question(
                self, tr("กำลังทำงานอยู่", "Still working"),
                tr("ยังถอดเสียงหรือบันทึกเสียงอยู่ ปิดโปรแกรมแล้วงานนี้จะหยุด ปิดเลยไหม?",
                   "A transcription or recording is still running and will stop if you quit. Quit anyway?"),
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
