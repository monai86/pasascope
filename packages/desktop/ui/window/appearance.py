"""Changing the light or dark theme by building a new window that opens where this one was.

Part of :class:`packages.desktop.ui.main_window.MainWindow`."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication

from packages.desktop.core.i18n import tr
from packages.desktop.ui import motion, theme
from packages.desktop.ui.window.common import OVERVIEW, OVERVIEW_PAGE, CASE_PAGE, KNOWLEDGE_PAGE, _LIVE


class AppearanceMixin:
    def _set_appearance(self, mode: str) -> None:
        theme.save_mode(mode)
        QTimer.singleShot(0, lambda: self.restyle(ask=True))

    def _on_system_scheme(self, *_args) -> None:
        if not self._replaced and theme.saved_mode() == "system":
            QTimer.singleShot(0, self._restyle_quietly)

    def _apply_pending_restyle(self) -> None:
        if self._restyle_pending and not self._replaced:
            QTimer.singleShot(0, self._restyle_quietly)

    def _restyle_quietly(self) -> None:
        if not self._replaced:
            self.restyle(ask=False)

    def restyle(self, ask: bool = True) -> None:
        """Use the theme now chosen by building a new window that opens where this one was.

        Every widget takes its colours when it is built, so a new window is the one
        way to change them all. It waits while work runs, a dialog is open, or (when
        nobody asked, as when the computer switches to dark) there are unsaved edits.
        """
        app = QApplication.instance()
        if theme.wants_dark(app) == theme.is_dark():
            self._restyle_pending = False
            return
        waiting = None
        if self.busy or self.runner.busy or QApplication.activeModalWidget() is not None:
            waiting = tr("ธีมจะเปลี่ยนเมื่องานที่ทำอยู่เสร็จ", "The theme changes when the current work finishes.")
        elif any(page.has_unsaved_changes() for page in self.pages) and not (ask and self._confirm_leave()):
            waiting = tr("ธีมจะเปลี่ยนหลังบันทึกการแก้ไข", "The theme changes after your edits are saved.")
        if waiting:
            self._restyle_pending = True
            if ask:
                self.notify(waiting, 8000)
            return
        self._restyle_pending = False
        state = self._view_state()
        self.stop_pages()
        theme.apply_theme(app)
        successor = type(self)(self.service, version=self.version)
        successor._restore_view(state)
        _LIVE[:] = [successor]
        successor.show()
        successor.raise_()
        successor.activateWindow()
        motion.fade_in(successor.centralWidget(), duration=220)
        self._replaced = True
        self.close()
        self.deleteLater()

    def _view_state(self) -> dict:
        topic = self.knowledge.topics.currentItem()
        return {
            "page": self.stack.currentIndex(),
            "case_id": self.case.case_id if self.case else None,
            "session_id": self.session.session_id if self.session else None,
            "overview": self.case is not None and self.session is None and self.session_stack.currentIndex() == OVERVIEW_PAGE,
            "tab": self.tabs.currentIndex(),
            "topic": topic.data(Qt.ItemDataRole.UserRole) if topic else None,
            "search": self.search.text(),
            "geometry": self.saveGeometry(),
            "title": self.windowTitle(),
            "update": self._available_update,
        }

    def _restore_view(self, state: dict) -> None:
        self.setWindowTitle(state["title"])
        self.restoreGeometry(state["geometry"])
        self.search.setText(state["search"])
        if state["update"] is not None:
            self._show_update(state["update"])
        if state["page"] == CASE_PAGE and state["case_id"]:
            self.reload_cases(state["case_id"])
            self.open_case(state["case_id"], state["session_id"])
            if state["session_id"]:
                self.tabs.setCurrentIndex(state["tab"])
            elif state["overview"] and self.session_pick.findData(OVERVIEW) >= 0:
                self.session_pick.setCurrentIndex(self.session_pick.findData(OVERVIEW))
        elif state["page"] == KNOWLEDGE_PAGE:
            self.show_knowledge(state["topic"])
