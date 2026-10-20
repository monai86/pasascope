from __future__ import annotations

from packages.desktop.core.i18n import tr

from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QMessageBox, QWidget

from packages.desktop.core import DesktopService, WorkflowError
from packages.desktop.ui.tasks import TaskRunner


class SessionPage(QWidget):
    """A step of the session workflow.

    ``changed`` asks the main window to reload every page after a record
    changed; ``navigate`` asks it to open another step by index; ``notify``
    shows a short message that fades away.
    """

    changed = Signal()
    navigate = Signal(int)
    busy_changed = Signal(bool)
    ask_name = Signal()  # open the therapist-name dialog (connected directly, so it returns after the dialog)
    notify = Signal(str)  # a short message the window shows as a toast

    def __init__(self, service: DesktopService, runner: TaskRunner, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.service = service
        self.runner = runner
        self.case: Any = None
        self.session: Any = None

    def load(self, case: Any, session: Any) -> None:
        self.case = case
        self.session = session
        self.refresh()

    def refresh(self) -> None:  # pragma: no cover - each page overrides
        pass

    def has_unsaved_changes(self) -> bool:
        return False

    def report_error(self, exc: Exception, title: str = tr("ทำรายการไม่สำเร็จ", "Something went wrong")) -> None:
        if isinstance(exc, WorkflowError):
            QMessageBox.warning(self, title, str(exc))
            return
        detail = getattr(exc, "__traceback_text__", "")
        box = QMessageBox(QMessageBox.Icon.Critical, title, tr(f"เกิดข้อผิดพลาดที่ไม่คาดไว้: {type(exc).__name__}: {exc}", f"Unexpected error: {type(exc).__name__}: {exc}"), parent=self)
        if detail:
            box.setDetailedText(detail)
        box.exec()

    def attempt(self, fn, *args, title: str = tr("ทำรายการไม่สำเร็จ", "Something went wrong"), **kwargs):
        """Run a quick service call on the UI thread; show the error and return None on failure."""
        try:
            return fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 - shown to the user
            self.report_error(exc, title)
            return None
