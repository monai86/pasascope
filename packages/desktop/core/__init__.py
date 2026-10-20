"""Clinical workflow for the desktop app, without Qt.

The UI calls :class:`DesktopService`; nothing here imports PySide6, so the
workflow is tested without a display. ``DesktopService`` and its errors load
on first use, so reading the data folder's path or language at start does not
pull in the database and speech libraries (the splash window loads those in
the background).
"""

from packages.desktop.core.workspace import Workspace, open_workspace

__all__ = ["DesktopService", "QaOverrideRequired", "Workspace", "WorkflowError", "open_workspace"]


def __getattr__(name: str):
    if name in ("DesktopService", "QaOverrideRequired", "WorkflowError"):
        from packages.desktop.core import service

        return getattr(service, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
