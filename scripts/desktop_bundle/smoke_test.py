"""Run the desktop app's main workflow without a window, in whatever Python runs this file.

Used by scripts/build_macos_dmg.py and scripts/build_windows.py to check a
freshly built app, and to list the third-party modules the workflow imports
(``--list-modules``). ``--transcribe`` also decodes and transcribes a short
generated clip with Whisper ``tiny`` (downloaded, about 75 MB), which checks
PyAV and CTranslate2 on the build machine.
Creates a case, imports a transcript, attests it, analyses it, drafts and signs
the report, writes the PDF, and imports the speech pipeline. Exits non-zero on
any failure.
"""

from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
if (ROOT / "packages").is_dir() and str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CHAT = """@UTF8
@Begin
@Languages:\ttha
@Participants:\tCHI Target_Child, MOT Mother
@ID:\ttha|test|CHI|4;2.|female|||Target_Child|||
@ID:\ttha|test|MOT|||||Mother|||
*MOT:\tหนูอยากกินอะไร .
*CHI:\tกินขนม .
*MOT:\tขนมอะไรดี .
*CHI:\tขนมเค้ก .
*MOT:\tอร่อยไหม .
*CHI:\tอร่อย มาก .
@End
"""


def main() -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    # Windows keeps the database open a moment after the window closes; a leftover temp folder is harmless.
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        os.environ["PASASCOPE_DESKTOP_HOME"] = str(Path(tmp) / "home")
        os.environ["PASASCOPE_DESKTOP_RECORDS_PATH"] = str(Path(tmp) / "records.json")
        from PySide6.QtWidgets import QApplication

        app = QApplication([])  # noqa: F841 - fonts and PDF need a GUI application
        from datetime import date

        from packages.desktop.core import DesktopService, open_workspace
        from packages.desktop.ui.main_window import MainWindow
        from packages.desktop.ui.pdf import ReportMeta, write_report_pdf

        service = DesktopService(open_workspace(Path(tmp) / "ws"))
        service.set_therapist_name("Smoke Test")
        case = service.create_case("SMOKE-1", 50)
        service.grant_consent(case.case_id, "Mother", date(2026, 10, 1))
        session = service.create_session(case.case_id, date(2026, 10, 2))
        service.import_transcript_text(session.session_id, CHAT)
        service.attest(service.get_transcript(session.session_id).transcript_id, override_reason="smoke test")
        service.analyze(session.session_id)
        report = service.sign_off(service.draft_report(session.session_id, language="th").report_id)
        pdf = write_report_pdf(report.markdown, Path(tmp) / "report.pdf", ReportMeta(child_code="SMOKE-1"))
        assert pdf.read_bytes().startswith(b"%PDF")
        window = MainWindow(service, version="smoke")
        window.close()
        import faster_whisper  # noqa: F401
        import torch  # noqa: F401

        from src.audio_pipeline import child_adult_frames, pipeline, whisper_transcribe  # noqa: F401

        if "--transcribe" in sys.argv:
            import numpy as np
            import soundfile

            from faster_whisper import WhisperModel

            clip = Path(tmp) / "clip.wav"
            seconds = np.arange(16000 * 2) / 16000
            soundfile.write(str(clip), 0.1 * np.sin(2 * np.pi * 220 * seconds), 16000)
            segments, info = WhisperModel("tiny", device="cpu", compute_type="int8").transcribe(str(clip), language="th")
            list(segments)
            assert info.duration > 1.5, info.duration
            print(f"transcription check passed ({info.duration:.1f} s decoded)")

        if "--list-modules" in sys.argv:
            names = sorted({name.split(".")[0] for name in sys.modules})
            print("\n".join(n for n in names if n not in sys.stdlib_module_names))
    print("smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
