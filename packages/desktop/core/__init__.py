"""Clinical workflow for the desktop app, without Qt.

The UI calls :class:`DesktopService`; nothing here imports PySide6, so the
workflow is tested without a display.
"""

from packages.desktop.core.workspace import Workspace, open_workspace
from packages.desktop.core.service import DesktopService, QaOverrideRequired, WorkflowError

__all__ = ["DesktopService", "QaOverrideRequired", "Workspace", "WorkflowError", "open_workspace"]
