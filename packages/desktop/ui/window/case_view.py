"""The case tree in the side bar, and the editor tabs for cases and sessions.

Part of :class:`packages.desktop.ui.main_window.MainWindow`.

Cases are listed as a tree with their sessions under them. A session opens
in its own tab (several can be open at once, each with its own place and
unsaved edits); a case opens a tab with its details and sessions. Opening a
case with exactly one session goes straight to that session, as before.
Leaving a tab never asks anything: a tab asks about unsaved edits only when
it is closed, as does the window.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QMessageBox, QTreeWidgetItem

from packages.desktop.core.i18n import tr
from packages.desktop.ui import labels, theme
from packages.desktop.ui.editors import CaseEditor, SessionEditor, case_key, case_name, session_day, session_key

ROLE = Qt.ItemDataRole.UserRole  # ("case" | "session", id) on each tree item


class CaseViewMixin:
    # ------------------------------------------------------------------
    # What is in front
    # ------------------------------------------------------------------
    @property
    def current_editor(self):
        return self.editor_area.current_editor()

    @property
    def case(self):
        editor = self.current_editor
        return editor.case if isinstance(editor, (SessionEditor, CaseEditor)) else None

    @property
    def session(self):
        editor = self.current_editor
        return editor.session if isinstance(editor, SessionEditor) else None

    @property
    def session_editor(self) -> SessionEditor | None:
        editor = self.current_editor
        return editor if isinstance(editor, SessionEditor) else None

    @property
    def case_editor(self) -> CaseEditor | None:
        editor = self.current_editor
        return editor if isinstance(editor, CaseEditor) else None

    @property
    def pages(self) -> list:
        """The current session's pages (none when no session tab is in front)."""
        editor = self.session_editor
        return editor.pages if editor else []

    @property
    def tabs(self):
        editor = self.session_editor
        return editor.tabs if editor else None

    @property
    def overview(self):
        editor = self.case_editor
        return editor.overview if editor else None

    @property
    def steps_done(self) -> list[bool]:
        editor = self.session_editor
        return editor.steps_done if editor else [False] * 4

    def session_editors(self, case_id: str | None = None) -> list[SessionEditor]:
        return [e for e in self.editor_area.editors.values() if isinstance(e, SessionEditor)
                and (case_id is None or e.case.case_id == case_id)]

    def has_unsaved_changes(self) -> bool:
        return any(editor.has_unsaved_changes() for editor in self.session_editors())

    # ------------------------------------------------------------------
    # The case tree
    # ------------------------------------------------------------------
    def reload_cases(self, select_id: str | None = None) -> None:
        """Rebuild the tree, keeping open branches; select ``select_id`` or what is in front."""
        expanded = {self.case_list.topLevelItem(i).data(0, ROLE)[1] for i in range(self.case_list.topLevelItemCount())
                    if self.case_list.topLevelItem(i).isExpanded()}
        current = self.session.session_id if self.session else None
        select_id = select_id or (self.case.case_id if self.case else None)
        if self.case is not None:
            expanded.add(self.case.case_id)
        search = self.search.text()
        cases = self.service.list_cases(search)
        self._switching = True
        self.case_list.clear()
        chosen = None
        for case in cases:
            item = QTreeWidgetItem([case_name(case)])
            consent, _ = labels.CONSENT.get(case.consent_status, (case.consent_status, ""))
            item.setToolTip(0, f"{labels.age_text(case.age_months)} · {consent}")
            item.setData(0, ROLE, ("case", case.case_id))
            if case.consent_status != "granted":
                item.setForeground(0, QColor(theme.ATTENTION if case.consent_status == "pending" else theme.FAINT))
            for session in self.service.list_sessions(case.case_id):
                child = QTreeWidgetItem([f"{session_day(session)} · {labels.status_text(session.status)}"])
                child.setData(0, ROLE, ("session", session.session_id))
                child.setToolTip(0, labels.status_text(session.status))
                item.addChild(child)
                if session.session_id == current:
                    chosen = child
            self.case_list.addTopLevelItem(item)
            item.setExpanded(case.case_id in expanded or bool(search))
            if case.case_id == select_id and chosen is None:
                chosen = item
        if chosen is not None:
            self.case_list.setCurrentItem(chosen)
        self._switching = False
        total = len(self.service.list_cases())
        self.case_count.setText(
            tr(f"{len(cases)} จาก {total} เคส", f"{len(cases)} of {total} cases") if search
            else tr(f"{total} เคส", f"{total} cases" if total != 1 else "1 case")
        )

    def _select_in_tree(self) -> bool:
        """Select what is in front without rebuilding the tree (a click may still be on its way through it)."""
        wanted = ("session", self.session.session_id) if self.session else ("case", self.case.case_id) if self.case else None
        self._switching = True
        try:
            if wanted is None:
                self.case_list.clearSelection()
                return True
            for index in range(self.case_list.topLevelItemCount()):
                top = self.case_list.topLevelItem(index)
                for item in [top] + [top.child(i) for i in range(top.childCount())]:
                    if tuple(item.data(0, ROLE) or ()) == wanted:  # Qt hands the pair back as a list
                        if wanted[0] == "session":
                            top.setExpanded(True)
                        self.case_list.setCurrentItem(item)
                        return True
            return False
        finally:
            self._switching = False

    def _on_tree_item(self, item: QTreeWidgetItem, _column: int = 0) -> None:
        if self._switching or item is None:
            return
        kind, identifier = item.data(0, ROLE)
        if kind == "session":
            self.open_session(identifier)
        else:
            self.open_case_editor(identifier)

    # ------------------------------------------------------------------
    # Opening tabs
    # ------------------------------------------------------------------
    def open_case(self, case_id: str, session_id: str | None = None) -> None:
        """A session's tab when given; else the case, or its only session when it has just one."""
        if session_id:
            self.open_session(session_id)
            return
        sessions = self.service.list_sessions(case_id)
        if len(sessions) == 1:
            self.open_session(sessions[0].session_id)
        else:
            self.open_case_editor(case_id)

    def open_case_editor(self, case_id: str) -> CaseEditor:
        key = case_key(case_id)
        editor = self.editor_area.editors.get(key)
        if editor is None:
            editor = CaseEditor(self.service, self.service.get_case(case_id))
            editor.consent_btn.clicked.connect(self._consent_action)
            editor.new_session_btn.clicked.connect(self.new_session)
            editor.no_session_btn.clicked.connect(self._no_session_action)
            editor.more_btn.clicked.connect(
                lambda: self._case_menu(editor.case.case_id).exec(editor.more_btn.mapToGlobal(editor.more_btn.rect().bottomLeft()))
            )
            editor.overview.open_session.connect(self.open_session)
            editor.overview.delete_session.connect(self.delete_session)
        editor.load()
        self.editor_area.open_editor(key, editor, editor.title(), editor.tooltip())
        self._after_switch()
        return editor

    def open_session(self, session_id: str) -> SessionEditor:
        key = session_key(session_id)
        editor = self.editor_area.editors.get(key)
        if editor is None:
            session = self.service.get_session(session_id)
            editor = SessionEditor(self.service, self.runner, self.service.get_case(session.case_id), session)
            editor.changed.connect(lambda e=editor: self.refresh_session(e))
            editor.busy_changed.connect(lambda _busy: self._set_busy(any(e.busy for e in self.session_editors())))
            editor.open_case.connect(self.open_case_editor)
            for page in editor.pages:
                page.ask_name.connect(lambda: self.ask_therapist_name(first_run=False))
                page.notify.connect(self.notify)
            editor.pages[1].attested.connect(self.learn_speakers_in_background)
            editor.pages[2].open_guide.connect(self.show_feature_guide)
            editor.load()
        elif not editor.busy and not editor.has_unsaved_changes():
            editor.load()  # back to an open tab: show what the records say now
        self.editor_area.open_editor(key, editor, editor.title(), editor.tooltip())
        self._after_switch()
        return editor

    def open_key(self, key: str) -> None:
        """Open a tab from its key ("home", "knowledge", "case:…", "session:…"), if what it shows still exists."""
        kind, _, identifier = key.partition(":")
        try:
            if kind == "home":
                self.show_home()
            elif kind == "knowledge":
                self.show_knowledge()
            elif kind == "case":
                self.open_case_editor(identifier)
            elif kind == "session":
                self.open_session(identifier)
        except Exception:  # noqa: BLE001 - deleted since; nothing to reopen
            pass

    def _after_switch(self) -> None:
        """Keep the tree's selection on what is in front; a new case or session is added to it first."""
        if not self._select_in_tree():
            self.reload_cases()
        self.home_btn.setChecked(self.editor_area.current_key() == "home")

    def _on_editor_changed(self, key: str) -> None:
        for editor in self.session_editors():
            if editor is not self.current_editor:
                editor.stop_playback()
        self._select_in_tree()
        self.home_btn.setChecked(key == "home")
        if key == "home":
            self.dashboard.refresh()

    # ------------------------------------------------------------------
    # Closing tabs
    # ------------------------------------------------------------------
    def close_tab(self, key: str | None = None) -> bool:
        """Close ``key`` (the tab in front by default); False when it stays open."""
        key = key or self.editor_area.current_key()
        if not key:
            return False
        editor = self.editor_area.editors.get(key)
        if isinstance(editor, SessionEditor):
            if editor.busy:
                QMessageBox.information(self, tr("รอสักครู่", "Please wait"),
                                        tr("session นี้ยังบันทึกเสียงหรือถอดเสียงอยู่ ปิดได้เมื่อเสร็จแล้ว",
                                           "This session is still recording or transcribing; close it when that finishes."))
                return False
            if not self._confirm_leave([editor]):
                return False
            editor.stop_playback()
            editor.shutdown()
        self.editor_area.close_editor(key)
        if editor is not None and editor not in (self.dashboard, self.knowledge):
            editor.deleteLater()
        self.reload_cases()
        return True

    def close_case_tabs(self, case_id: str, session_id: str | None = None) -> None:
        """Close what shows a case (or just one of its sessions) after it was deleted; edits there are gone."""
        keys = [session_key(session_id)] if session_id else [case_key(case_id)] + [
            session_key(e.session.session_id) for e in self.session_editors(case_id)]
        for key in keys:
            editor = self.editor_area.editors.get(key)
            if editor is None:
                continue
            if isinstance(editor, SessionEditor):
                editor.stop_playback()
                editor.shutdown()
            self.editor_area.close_editor(key)
            editor.deleteLater()

    def _confirm_leave(self, editors: list | None = None) -> bool:
        """Save or discard the unsaved edits of ``editors`` (every open session by default)."""
        editors = self.session_editors() if editors is None else editors
        dirty = [page for editor in editors for page in editor.dirty_pages()]
        if not dirty:
            return True
        answer = QMessageBox.question(
            self, tr("มีการแก้ไขที่ยังไม่บันทึก", "Unsaved changes"),
            tr("บันทึกการแก้ไขก่อน?", "Save your changes first?"),
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
        )
        if answer == QMessageBox.StandardButton.Cancel:
            return False
        if answer == QMessageBox.StandardButton.Save:
            return all(page.save() for page in dirty)
        return True

    def stop_pages(self) -> None:
        """Stop playback in every session (before a window rebuild or a restore)."""
        for editor in self.session_editors():
            editor.stop_playback()

    # ------------------------------------------------------------------
    # Keeping tabs in step with the records
    # ------------------------------------------------------------------
    def refresh_session(self, editor: SessionEditor | None = None) -> None:
        """Reload a session tab after one of its pages changed a record (the one in front by default)."""
        editor = editor or self.session_editor
        if editor is None:
            if self.case_editor is not None:
                self.case_editor.load()
            self.reload_cases()
            return
        editor.load()
        self.editor_area.set_title(session_key(editor.session.session_id), editor.title(), editor.tooltip())
        self._refresh_case_views(editor.case.case_id, skip=editor)
        self._apply_pending_restyle()  # a save may have cleared the edits a theme change waited for

    def _refresh_case_views(self, case_id: str, skip=None) -> None:
        """After a change to a case: its case tab, the other sessions' headers, the tree and Home."""
        case = self.service.get_case(case_id)
        case_editor = self.editor_area.editors.get(case_key(case_id))
        if case_editor is not None:
            case_editor.load()
            self.editor_area.set_title(case_key(case_id), case_editor.title(), case_editor.tooltip())
        for other in self.session_editors(case_id):
            if other is not skip:
                other.update_header(case)
        self.reload_cases()
        self.refresh_home()

    def _poll_dirty(self) -> None:
        """Mark tabs with unsaved edits (●), as editors do."""
        for key, editor in self.editor_area.editors.items():
            if isinstance(editor, SessionEditor):
                self.editor_area.set_dirty(key, editor.has_unsaved_changes())

    def _no_session_action(self) -> None:
        if self.case is None:
            return
        if self.case.consent_status == "granted":
            self.new_session()
        else:
            self.record_consent()
