"""The main window, laid out as a workbench: activity bar, side bar, editor tabs, status bar.

The activity bar on the far left picks the side bar's view (Cases or
Knowledge) and opens Home or the command palette; the side bar lists cases
as a tree with their sessions; the editor area holds a tab for Home, each
open case, each open session and Knowledge. See ``ui/workbench.py`` for the
parts and ``ui/window/`` for what the window does.
"""

from __future__ import annotations

from html import escape

from PySide6.QtCore import QSettings, Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QActionGroup, QDesktopServices, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStackedWidget,
    QTreeWidget,
    QVBoxLayout,
    QWidget,
)

from packages.desktop.core import DesktopService
from packages.desktop.core.i18n import LANGUAGES, language, tr
from packages.desktop.ui import motion, theme
from packages.desktop.ui.pages.dashboard import Dashboard
from packages.desktop.ui.pages.knowledge import KnowledgePage
from packages.desktop.ui.tasks import TaskRunner
from packages.desktop.ui.widgets import button, label, repolish
from packages.desktop.ui.window.common import _LIVE  # noqa: F401 - the theme change and its tests use it from here
from packages.desktop.ui.window.case_view import CaseViewMixin
from packages.desktop.ui.window.case_actions import CaseActionsMixin
from packages.desktop.ui.window.commands import CommandsMixin
from packages.desktop.ui.window.settings_actions import SettingsActionsMixin
from packages.desktop.ui.window.updates import UpdatesMixin
from packages.desktop.ui.window.appearance import AppearanceMixin
from packages.desktop.ui.window.backup import BackupMixin
from packages.desktop.ui.workbench import ActivityBar, EditorArea, SideBarHeader

SIDE_WIDTH = 260


class MainWindow(
    CaseViewMixin,
    CaseActionsMixin,
    CommandsMixin,
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
        self.busy = False
        self._switching = False
        self._restyle_pending = False  # a theme change waits for work or unsaved edits
        self._replaced = False  # a theme change built a new window in place of this one
        self.side_view = "cases"
        self.setWindowTitle("PasaScope")
        self.resize(1320, 840)
        self.setMinimumSize(980, 640)

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.dashboard = Dashboard(self.service)
        self.dashboard.open_case.connect(self._open_from_dashboard)
        self.dashboard.new_case.connect(self.new_case)
        self.dashboard.backup.connect(self.backup)
        self.dashboard.speaker_settings.connect(self.show_speaker_model)
        self.dashboard.download_models.connect(self.download_models)
        self.knowledge = KnowledgePage()
        root.addWidget(self._build_activity_bar())
        self.workbench = QSplitter(Qt.Orientation.Horizontal)
        self.workbench.setObjectName("Workbench")
        self.workbench.setHandleWidth(1)
        self.workbench.setChildrenCollapsible(False)
        root.addWidget(self.workbench, 1)
        self.side_bar = self._build_side_bar()
        self.workbench.addWidget(self.side_bar)
        self.editor_area = EditorArea()
        self.editor_area.current_changed.connect(self._on_editor_changed)
        self.editor_area.close_requested.connect(self.close_tab)
        self.workbench.addWidget(self.editor_area)
        self.workbench.setStretchFactor(1, 1)
        self.workbench.setSizes([SIDE_WIDTH, 1000])

        self._build_menus()
        self._build_status_bar()
        self._build_shortcuts()

        settings = QSettings()
        geometry = settings.value("main/geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)
        sizes = settings.value("main/workbench")
        if sizes:
            try:
                self.workbench.setSizes([int(size) for size in sizes])
            except (TypeError, ValueError):
                pass
        self.toast = motion.Toast(self)
        self._dirty_timer = QTimer(self)
        self._dirty_timer.setInterval(500)
        self._dirty_timer.timeout.connect(self._poll_dirty)
        self._dirty_timer.start()
        self.reload_cases()
        self.show_home()
        self.set_side_view("cases")
        self.runner.idle.connect(self._apply_pending_restyle)
        QApplication.instance().styleHints().colorSchemeChanged.connect(self._on_system_scheme)

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def _build_activity_bar(self) -> QWidget:
        self.activity = ActivityBar()
        self.home_btn = self.activity.add_action("home", tr("หน้าแรก", "Home") + f" ({self._keys('Ctrl+Shift+H')})",
                                                 self.show_home, checkable=True)
        self.activity.add_view("cases", "cases", tr("เคส", "Cases"))
        self.knowledge_btn = self.activity.add_view("knowledge", "knowledge", tr("ความรู้", "Knowledge") + " (F1)")
        self.activity.add_action("search", tr("ค้นหาคำสั่ง", "Search commands") + f" ({self._keys('Ctrl+Shift+P')})",
                                 self.show_command_palette)
        self.settings_btn = self.activity.add_action("settings", tr("ตั้งค่า", "Settings"), self._show_settings_menu, bottom=True)
        self.activity.view_selected.connect(self._on_activity_view)
        return self.activity

    def _build_side_bar(self) -> QWidget:
        side = QFrame()
        side.setObjectName("SideBar")
        side.setMinimumWidth(190)
        layout = QVBoxLayout(side)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.side_stack = QStackedWidget()
        layout.addWidget(self.side_stack, 1)

        cases = QWidget()
        cases_layout = QVBoxLayout(cases)
        cases_layout.setContentsMargins(0, 0, 0, 0)
        cases_layout.setSpacing(4)
        header = SideBarHeader(tr("เคส", "Cases"))
        header.add_action("add", tr("เพิ่มเคส", "New case"), self.new_case)
        header.add_action("refresh", tr("โหลดรายการใหม่", "Refresh"), self.reload_cases)
        header.add_action("collapse", tr("ยุบทั้งหมด", "Collapse all"), lambda: self.case_list.collapseAll())
        cases_layout.addWidget(header)
        self.search = QLineEdit()
        self.search.setPlaceholderText(tr("ค้นหารหัสหรือชื่อเล่น", "Search code or nickname"))
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(lambda _: self.reload_cases())
        cases_layout.addWidget(self.search)
        self.case_list = QTreeWidget()
        self.case_list.setObjectName("CaseTree")
        self.case_list.setHeaderHidden(True)
        self.case_list.setIndentation(16)
        self.case_list.setUniformRowHeights(True)
        self.case_list.setAnimated(motion.enabled())
        self.case_list.setExpandsOnDoubleClick(False)
        self.case_list.itemClicked.connect(self._on_tree_item)
        self.case_list.itemActivated.connect(self._on_tree_item)
        self.case_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.case_list.customContextMenuRequested.connect(self._case_list_menu)
        # Delete (and the Mac's delete key, Backspace) on a selected case or session asks to delete it.
        for key in (QKeySequence.StandardKey.Delete, QKeySequence(Qt.Key.Key_Backspace)):
            shortcut = QShortcut(key, self.case_list)
            shortcut.setContext(Qt.ShortcutContext.WidgetShortcut)
            shortcut.activated.connect(self._delete_selected_case)
        cases_layout.addWidget(self.case_list, 1)
        self.case_count = label("", "Hint")
        self.case_count.setContentsMargins(20, 0, 0, 2)
        cases_layout.addWidget(self.case_count)
        footer = QFrame()
        footer.setObjectName("SideBarFooter")
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(0, 6, 8, 8)
        footer_layout.setSpacing(0)
        footer_layout.addWidget(label(tr("นักบำบัดในเครื่องนี้", "THERAPIST ON THIS COMPUTER"), "SideBarSection"))
        # The name signs attestations and reports, so it is one click away.
        therapist_row = QHBoxLayout()
        therapist_row.setContentsMargins(20, 0, 0, 0)
        therapist_row.setSpacing(6)
        self.therapist_label = label("", "TherapistName")
        therapist_row.addWidget(self.therapist_label, 1)
        self.therapist_btn = button(tr("เปลี่ยน", "Change"), "ghost", tr("เปลี่ยนชื่อนักบำบัด", "Change the therapist name"))
        self.therapist_btn.clicked.connect(lambda: self.ask_therapist_name(first_run=False))
        therapist_row.addWidget(self.therapist_btn)
        footer_layout.addLayout(therapist_row)
        cases_layout.addWidget(footer)
        self.side_stack.addWidget(cases)

        topics = QWidget()
        topics_layout = QVBoxLayout(topics)
        topics_layout.setContentsMargins(0, 0, 0, 0)
        topics_layout.setSpacing(0)
        topics_layout.addWidget(SideBarHeader(tr("ความรู้", "Knowledge")))
        list_widget = self.knowledge.topics
        list_widget.setObjectName("TopicList")
        list_widget.setMinimumWidth(0)
        list_widget.setMaximumWidth(16777215)
        topics_layout.addWidget(list_widget, 1)
        self.knowledge.side.hide()  # its list now lives here
        list_widget.itemClicked.connect(lambda _item: self.show_knowledge())
        self.side_stack.addWidget(topics)
        self._side_views = {"cases": cases, "knowledge": topics}
        return side

    def _build_status_bar(self) -> None:
        bar = self.statusBar()
        bar.setSizeGripEnabled(False)
        bar.setFixedHeight(22)
        bar.setContentsMargins(0, 0, 4, 0)
        self.demo_label = QLabel(tr("ข้อมูลสาธิต", "Demo data"))
        self.demo_label.setObjectName("StatusBadge")
        self.demo_label.setVisible((self.service.workspace.root / "pasascope-demo.json").exists())
        bar.addWidget(self.demo_label)
        self.name_label = QLabel("")
        self.name_label.setTextFormat(Qt.TextFormat.RichText)
        self.name_label.linkActivated.connect(lambda _: self.ask_therapist_name(first_run=False))
        self.backup_label = QLabel("")
        self.backup_label.setTextFormat(Qt.TextFormat.RichText)
        self.backup_label.linkActivated.connect(lambda _: self.backup())
        bar.addWidget(self.name_label)
        bar.addWidget(self.backup_label)
        self.update_label = QLabel("")
        self.update_label.setTextFormat(Qt.TextFormat.RichText)
        self.update_label.linkActivated.connect(lambda _: self._offer_update(self._available_update))
        self.update_label.hide()
        self._available_update = None
        self.asr_label = QLabel("")
        self.version_label = QLabel(f"PasaScope {self.version}" if self.version else "PasaScope")
        for widget in (self.update_label, self.asr_label, self.version_label):
            bar.addPermanentWidget(widget)
        self._update_status_bar()

    def _build_shortcuts(self) -> None:
        for keys, slot in (
            ("Ctrl+Shift+P", self.show_command_palette),
            ("Ctrl+P", lambda: self.show_command_palette(quick_open=True)),
            ("Ctrl+W", self.close_tab),
            ("Ctrl+B", self.toggle_side_bar),
            ("Ctrl+Shift+H", self.show_home),
        ):
            QShortcut(QKeySequence(keys), self, activated=slot)
        QShortcut(QKeySequence.StandardKey.NextChild, self, activated=lambda: self._cycle_tabs(1))
        QShortcut(QKeySequence.StandardKey.PreviousChild, self, activated=lambda: self._cycle_tabs(-1))

    @staticmethod
    def _keys(text: str) -> str:
        return QKeySequence(text).toString(QKeySequence.SequenceFormat.NativeText)

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
        close_tab = QAction(tr("ปิดแท็บ", "Close tab"), self)
        close_tab.triggered.connect(lambda: self.close_tab())
        file_menu.addAction(close_tab)
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

        view_menu = bar.addMenu(tr("มุมมอง", "View"))
        palette = QAction(tr("ค้นหาคำสั่ง…", "Command palette…"), self)
        palette.triggered.connect(self.show_command_palette)
        view_menu.addAction(palette)
        quick = QAction(tr("เปิดเคสหรือ session…", "Open case or session…"), self)
        quick.triggered.connect(lambda: self.show_command_palette(quick_open=True))
        view_menu.addAction(quick)
        view_menu.addSeparator()
        home = QAction(tr("หน้าแรก", "Home"), self)
        home.triggered.connect(self.show_home)
        view_menu.addAction(home)
        side = QAction(tr("แสดง/ซ่อน side bar", "Show or hide the side bar"), self)
        side.triggered.connect(self.toggle_side_bar)
        view_menu.addAction(side)

        self.case_bar_menu = bar.addMenu(tr("เคส", "Case"))
        self.case_bar_menu.aboutToShow.connect(self._fill_case_bar_menu)

        self.settings_menu = settings_menu = bar.addMenu(tr("ตั้งค่า", "Settings"))
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
    def _on_activity_view(self, key: str) -> None:
        # Clicking the view already shown hides the side bar, as in code editors.
        if key == self.side_view and self.side_bar.isVisible():
            self.set_side_view(key, visible=False)
        else:
            self.set_side_view(key)
            if key == "knowledge":
                self.show_knowledge()

    def set_side_view(self, key: str, visible: bool = True) -> None:
        self.side_view = key if key in self._side_views else "cases"
        self.side_stack.setCurrentWidget(self._side_views[self.side_view])
        self.side_bar.setVisible(visible)
        self.activity.set_current_view(self.side_view if visible else None)
        if visible:
            motion.fade_in(self.side_stack.currentWidget())

    def toggle_side_bar(self) -> None:
        self.set_side_view(self.side_view, visible=not self.side_bar.isVisible())

    def _show_settings_menu(self) -> None:
        self.settings_menu.exec(self.settings_btn.mapToGlobal(self.settings_btn.rect().topRight()))

    def _cycle_tabs(self, step: int) -> None:
        count = self.editor_area.bar.count()
        if count:
            self.editor_area.bar.setCurrentIndex((self.editor_area.bar.currentIndex() + step) % count)

    def show_home(self) -> None:
        self.dashboard.refresh()
        self.editor_area.open_editor("home", self.dashboard, tr("หน้าแรก", "Home"), tr("งานที่รออยู่และเคสล่าสุด", "Work waiting and recent cases"))
        self.home_btn.setChecked(True)

    def refresh_home(self) -> None:
        if "home" in self.editor_area.editors:
            self.dashboard.refresh()

    def show_knowledge(self, topic: str | None = None) -> None:
        if isinstance(topic, str):
            self.knowledge.open_topic(topic)
        self.editor_area.open_editor("knowledge", self.knowledge, tr("ความรู้", "Knowledge"))
        if self.side_view != "knowledge" and self.side_bar.isVisible():
            self.set_side_view("knowledge")

    def show_feature_guide(self, name: str = "") -> None:
        """The Knowledge page's measure guide, at one measure when given."""
        self.show_knowledge()
        self.knowledge.open_feature(name)

    def _open_from_dashboard(self, case_id: str, session_id) -> None:
        self.open_case(case_id, session_id)

    # ------------------------------------------------------------------
    # Window state
    # ------------------------------------------------------------------
    def notify(self, text: str, msecs: int = 5000) -> None:
        """A short message that fades away by itself (see ``motion.Toast``)."""
        self.toast.show_message(text, msecs)

    def _set_busy(self, busy: bool) -> None:
        self.busy = busy
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
                f'<span style="color:{theme.ATTENTION}">{when}</span>   <a href="backup">{tr("สำรองตอนนี้", "Back up now")}</a>'
            )
        else:
            self.backup_label.setText(f'<span style="color:{theme.MUTED}">{when}</span>')

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt override
        if getattr(self, "_restored", False):
            event.accept()
            return
        if self._replaced:  # a theme change: the new window carries on, nothing to ask
            for editor in self.session_editors():
                editor.shutdown()
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
        for editor in self.session_editors():
            editor.shutdown()
        settings = QSettings()
        settings.setValue("main/geometry", self.saveGeometry())
        if self.side_bar.isVisible():
            settings.setValue("main/workbench", self.workbench.sizes())
        self.runner.wait(3000)
        self.start_pending_update()  # a downloaded update installs once the window has agreed to close
        event.accept()

