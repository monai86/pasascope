"""The command palette's contents: every case, session, Knowledge topic and command.

Part of :class:`packages.desktop.ui.main_window.MainWindow`. Ctrl/Cmd+Shift+P
lists everything; Ctrl/Cmd+P lists only cases and sessions to open. The list
is built each time it opens, so it always matches the records.
"""

from __future__ import annotations

from PySide6.QtCore import Qt

from packages.desktop.core.i18n import tr
from packages.desktop.ui import labels
from packages.desktop.ui.editors import case_name, session_day
from packages.desktop.ui.workbench import Command, CommandPalette


class CommandsMixin:
    def show_command_palette(self, quick_open: bool = False) -> None:
        if getattr(self, "command_palette", None) is None:
            self.command_palette = CommandPalette(self)
        commands = self._open_commands() if quick_open else self._all_commands()
        placeholder = (tr("พิมพ์รหัสเด็ก ชื่อเล่น หรือวันที่ของ session", "Type a child code, nickname or session date")
                       if quick_open else tr("พิมพ์ชื่อคำสั่ง เคส หรือหัวข้อ", "Type a command, case or topic"))
        self.command_palette.open(commands, placeholder)

    def _open_commands(self) -> list[Command]:
        found: list[Command] = []
        opened = tr("เปิด", "Open")
        for case in self.service.list_cases():
            name = case_name(case)
            found.append(Command(name, lambda c=case.case_id: self.open_case_editor(c), labels.age_text(case.age_months), opened))
            for session in self.service.list_sessions(case.case_id):
                found.append(Command(f"{name} · {session_day(session)}", lambda s=session.session_id: self.open_session(s),
                                     labels.status_text(session.status), opened))
        return found

    def _all_commands(self) -> list[Command]:
        general = tr("ทั่วไป", "General")
        case_group = tr("เคส", "Case")
        settings = tr("ตั้งค่า", "Settings")
        data = tr("ข้อมูล", "Data")
        commands = [
            Command(tr("หน้าแรก", "Home"), self.show_home, group=general),
            Command(tr("เพิ่มเคส…", "New case…"), self.new_case, group=case_group),
            Command(tr("แสดง/ซ่อน side bar", "Show or hide the side bar"), self.toggle_side_bar, group=general),
            Command(tr("ปิดแท็บ", "Close tab"), self.close_tab, group=general),
            Command(tr("สำรองข้อมูล…", "Back up…"), self.backup, group=data),
            Command(tr("กู้คืนจากไฟล์สำรอง…", "Restore from backup…"), self.restore, group=data),
            Command(tr("เปิดโฟลเดอร์ข้อมูล", "Open data folder"), self._open_data_folder, group=data),
            Command(tr("ชื่อนักบำบัด…", "Therapist name…"), lambda: self.ask_therapist_name(first_run=False), group=settings),
            Command(tr("ชื่อหน่วยงานบนรายงาน…", "Clinic name on reports…"), self.ask_organization, group=settings),
            Command(tr("ดาวน์โหลดโมเดลถอดเสียง…", "Download speech models…"), self.download_models, group=settings),
            Command(tr("แยกเสียงเด็ก/ผู้ใหญ่ของคลินิก…", "Child/adult voices…"), self.show_speaker_model, group=settings),
            Command(tr("ธีม: ตามเครื่อง", "Theme: match the computer"), lambda: self._set_appearance("system"), group=settings),
            Command(tr("ธีม: สว่าง", "Theme: light"), lambda: self._set_appearance("light"), group=settings),
            Command(tr("ธีม: มืด", "Theme: dark"), lambda: self._set_appearance("dark"), group=settings),
            Command(tr("ประวัติการทำงาน (audit log)", "Audit log"), self.show_audit_log, group=general),
            Command(tr("ตรวจหาอัปเดต…", "Check for updates…"), lambda: self.check_for_updates(quiet=False), group=general),
            Command(tr("เกี่ยวกับ PasaScope", "About PasaScope"), self.show_about, group=general),
        ]
        if self.case is not None:
            case_id = self.case.case_id
            commands[2:2] = [
                Command(tr("Session ใหม่…", "New session…"), lambda: self._select_case(case_id) and self.new_session(),
                        case_name(self.case), case_group),
                Command(tr("แก้ไขข้อมูลเคส…", "Edit case…"), lambda: self.edit_case(case_id), case_name(self.case), case_group),
            ]
        topic_group = tr("ความรู้", "Knowledge")
        for row in range(self.knowledge.topics.count()):
            item = self.knowledge.topics.item(row)
            key = item.data(Qt.ItemDataRole.UserRole)
            commands.append(Command(item.text(), lambda k=key: self.show_knowledge(k), group=topic_group))
        return commands + self._open_commands()

    def _open_data_folder(self) -> None:
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.service.workspace.root)))
