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


# Qt prints these when a macOS accessibility client (VoiceOver, or a menu-bar
# utility reading the screen) asks a widget about text or rows that just
# changed; Qt recovers by itself, so they only flood the log.
QUIET_QT_MESSAGES = ("QTextCursor::setPosition: Position", "Cell requested for row")


def _install_qt_message_filter() -> None:
    """Pass Qt's messages to stderr (the log) as usual, except the harmless accessibility ones."""
    from PySide6.QtCore import qInstallMessageHandler

    def handler(_mode, context, message: str) -> None:
        if message.startswith(QUIET_QT_MESSAGES) or (context.category == "qt.accessibility.table"):
            return
        category = f"{context.category}: " if context.category and context.category != "default" else ""
        sys.stderr.write(f"{category}{message}\n")

    qInstallMessageHandler(handler)


def _profile_language(root: Path) -> str | None:
    """The language saved in the data folder, read without loading the workflow."""
    import json

    try:
        code = json.loads((root / "profile.json").read_text(encoding="utf-8")).get("language")
    except (OSError, ValueError, AttributeError):
        return None
    return code if code in ("en", "th") else None


def _preload(state: dict) -> None:
    """Import what opening the data and the window need, off the UI thread, while the splash plays.

    Each step names itself in ``state["stage"]`` for the splash. A failure here
    is left for the main thread to meet again and report when it opens the data.
    """
    from packages.desktop.core.i18n import tr

    steps = [
        (tr("กำลังเตรียมฐานข้อมูล…", "Preparing the database…"),
         lambda: __import__("app.repositories.sqlalchemy_repository")),
        (tr("กำลังโหลดระบบถอดเสียง…", "Loading speech recognition…"),
         lambda: __import__("src.audio_pipeline.whisper_transcribe")),
        (tr("กำลังโหลดพจนานุกรมภาษาไทย…", "Loading the Thai dictionary…"),
         lambda: __import__("packages.cha.clan_words", fromlist=["warm_up"]).warm_up()),
        (tr("กำลังเตรียมขั้นตอนการทำงาน…", "Preparing the workflow…"),
         lambda: __import__("packages.desktop.core.service")),
    ]
    try:
        for stage, step in steps:
            state["stage"] = stage
            step()
    except Exception:  # noqa: BLE001 - reported by the main thread when it opens the data
        pass
    finally:
        state["done"] = True


def _wait_with_splash(app, splash, state: dict) -> None:
    """Run the event loop (so the splash animates) until preloading is done and the intro has played."""
    from PySide6.QtCore import QEventLoop, QTimer

    loop = QEventLoop()
    timer = QTimer()
    timer.setInterval(30)

    def check() -> None:
        splash.set_status(state.get("stage", ""))
        if state.get("done") and splash.minimum_shown():
            loop.quit()

    timer.timeout.connect(check)
    timer.start()
    loop.exec()
    timer.stop()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PasaScope desktop app")
    parser.add_argument("--home", type=Path, help="Data folder (default: the per-user application data folder)")
    parser.add_argument("--demo", action="store_true", help="Open the demonstration data (scripts/seed_desktop_demo.py)")
    args = parser.parse_args(argv)

    os.environ.setdefault("OBJC_DISABLE_INITIALIZE_FORK_SAFETY", "YES")
    import threading

    from PySide6.QtCore import QCoreApplication, QTimer
    from PySide6.QtWidgets import QApplication, QMessageBox

    QCoreApplication.setOrganizationName("PasaScope")
    QCoreApplication.setApplicationName("PasaScope")
    _install_qt_message_filter()
    app = QApplication(sys.argv[:1])
    icon = ROOT / "packages" / "desktop" / "ui" / "assets" / "icon.png"
    if icon.is_file():
        from PySide6.QtGui import QIcon

        app.setWindowIcon(QIcon(str(icon)))

    from packages.desktop.ui.theme import apply_theme

    apply_theme(app)

    from packages.desktop.core.i18n import set_language, tr
    from packages.desktop.core.workspace import default_home, demo_home

    home = args.home
    if args.demo and home is None:
        home = demo_home()
        if not home.exists():
            QMessageBox.information(
                None, "No demonstration data",
                "Create it first with\n.venv312/bin/python scripts/seed_desktop_demo.py",
            )
            return 1
    root = (home or default_home()).expanduser()
    from packages.desktop.ui.onboarding import default_language

    set_language(_profile_language(root) or default_language())  # the splash speaks it

    from packages.desktop.ui.splash import Splash

    version = _version()
    splash = Splash(version, demo=args.demo)
    splash.show()
    app.processEvents()
    state = {"stage": tr("กำลังเริ่มโปรแกรม…", "Starting…"), "done": False}
    threading.Thread(target=_preload, args=(state,), name="startup-preload", daemon=True).start()
    _wait_with_splash(app, splash, state)
    splash.set_status(tr("กำลังเปิดข้อมูล…", "Opening your data…"))
    app.processEvents()

    from packages.desktop.core import DesktopService, open_workspace

    try:
        service = DesktopService(open_workspace(home))
    except Exception as exc:  # noqa: BLE001 - nothing else can run without the workspace
        splash.finish()
        QMessageBox.critical(None, "Cannot open data", f"The data folder could not be opened.\n{type(exc).__name__}: {exc}")
        return 1

    first_start = None
    if not service.therapist_name and not args.demo:
        # A new data folder: say what PasaScope is and ask who signs. An update or
        # reinstall keeps the data folder and its name, so this does not come back.
        splash.finish()
        from packages.desktop.ui.onboarding import run_onboarding

        first_start = run_onboarding(service, service.workspace.root)
        if first_start is None:
            return 0

    set_language(service.language)  # before the window's text is built
    from packages.desktop.ui import motion
    from packages.desktop.ui.main_window import MainWindow

    window = MainWindow(service, version=version)
    if args.demo:
        window.setWindowTitle(tr("PasaScope — ข้อมูลสาธิต (ไม่ใช่เด็กจริง)", "PasaScope — demonstration data (not real children)"))
    splash.finish()
    window.show()
    window.raise_()
    window.activateWindow()
    motion.fade_in(window.centralWidget(), duration=220)
    if first_start is not None and first_start.download_models:
        QTimer.singleShot(500, lambda: window.download_models(confirm=False))
    elif service.update_check_due():
        window.check_for_updates(quiet=True)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
