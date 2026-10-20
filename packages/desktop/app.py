"""Start the desktop app: open the workspace, then show the main window."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _version() -> str:
    try:
        import tomllib

        return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    except Exception:  # noqa: BLE001 - the version is only shown in About
        return ""


def _warm_up_in_background() -> None:
    """Load what the first case opened would otherwise wait for, off the UI thread."""
    import threading

    def warm() -> None:
        try:
            from packages.cha.clan_words import warm_up

            warm_up()
        except Exception:  # noqa: BLE001 - the dictionary then loads on first use, as before
            pass

    threading.Thread(target=warm, name="thai-dictionary", daemon=True).start()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PasaScope desktop app")
    parser.add_argument("--home", type=Path, help="Data folder (default: the per-user application data folder)")
    parser.add_argument("--demo", action="store_true", help="Open the demonstration data (scripts/seed_desktop_demo.py)")
    args = parser.parse_args(argv)

    os.environ.setdefault("OBJC_DISABLE_INITIALIZE_FORK_SAFETY", "YES")
    from PySide6.QtCore import QCoreApplication
    from PySide6.QtWidgets import QApplication, QMessageBox

    QCoreApplication.setOrganizationName("PasaScope")
    QCoreApplication.setApplicationName("PasaScope")
    app = QApplication(sys.argv[:1])
    icon = ROOT / "packages" / "desktop" / "ui" / "assets" / "icon.png"
    if icon.is_file():
        from PySide6.QtGui import QIcon

        app.setWindowIcon(QIcon(str(icon)))

    from packages.desktop.ui.theme import apply_theme

    apply_theme(app)

    from packages.desktop.core import DesktopService, open_workspace

    home = args.home
    if args.demo and home is None:
        from packages.desktop.core.workspace import demo_home

        home = demo_home()
        if not home.exists():
            QMessageBox.information(
                None, "No demonstration data",
                "Create it first with\n.venv312/bin/python scripts/seed_desktop_demo.py",
            )
            return 1
    try:
        service = DesktopService(open_workspace(home))
    except Exception as exc:  # noqa: BLE001 - nothing else can run without the workspace
        QMessageBox.critical(None, "Cannot open data", f"The data folder could not be opened.\n{type(exc).__name__}: {exc}")
        return 1

    from packages.desktop.core.i18n import set_language

    set_language(service.language)  # before the window's text is built
    from packages.desktop.ui.main_window import MainWindow

    window = MainWindow(service, version=_version())
    if args.demo:
        from packages.desktop.core.i18n import tr

        window.setWindowTitle(tr("PasaScope — ข้อมูลสาธิต (ไม่ใช่เด็กจริง)", "PasaScope — demonstration data (not real children)"))
    window.show()
    _warm_up_in_background()
    if not service.therapist_name:
        window.ask_therapist_name(first_run=True)
    if service.update_check_due():
        window.check_for_updates(quiet=True)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
