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

    from packages.desktop.ui.theme import apply_theme

    apply_theme(app)

    from packages.desktop.core import DesktopService, open_workspace

    home = args.home
    if args.demo and home is None:
        from packages.desktop.core.workspace import demo_home

        home = demo_home()
        if not home.exists():
            QMessageBox.information(
                None, "ยังไม่มีข้อมูลสาธิต",
                "สร้างข้อมูลสาธิตก่อนด้วย\n.venv312/bin/python scripts/seed_desktop_demo.py",
            )
            return 1
    try:
        service = DesktopService(open_workspace(home))
    except Exception as exc:  # noqa: BLE001 - nothing else can run without the workspace
        QMessageBox.critical(None, "เปิดข้อมูลไม่ได้", f"เปิดโฟลเดอร์ข้อมูลไม่ได้\n{type(exc).__name__}: {exc}")
        return 1

    from packages.desktop.ui.main_window import MainWindow

    window = MainWindow(service, version=_version())
    if args.demo:
        window.setWindowTitle("PasaScope — ข้อมูลสาธิต (ไม่ใช่เด็กจริง)")
    window.show()
    if not service.therapist_name:
        window.ask_therapist_name(first_run=True)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
