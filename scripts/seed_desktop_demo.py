"""Fill a separate desktop workspace with demonstration cases.

The demo folder is never the therapist's real data folder: by default it sits
next to it as "PasaScope Demo", and the app opens it with ``--demo``. Every
transcript comes from the scripted text-to-speech dialogues in
``data/evaluation/gold_transcripts``; no child's data is used.

What it creates:

* DEMO-001: three analysed sessions with a trend across them (the first two
  reports signed), and a fourth session whose recording was transcribed by
  on-device Whisper and is waiting for review, to correct live.
* DEMO-002: consent not recorded yet, to show that sessions are blocked.

Usage:
    python scripts/seed_desktop_demo.py              # create, or refuse if it exists
    python scripts/seed_desktop_demo.py --reset      # rebuild the demo folder
    python scripts/seed_desktop_demo.py --no-audio   # skip the Whisper session
    ./run_gui.sh --demo                               # open it
"""

from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import shutil
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

GOLD_DIR = PROJECT_ROOT / "data" / "evaluation" / "gold_transcripts"
AUDIO_DIR = PROJECT_ROOT / ".local" / "evaluation" / "audio_samples"
MARKER = "pasascope-demo.json"
THERAPIST = "นักบำบัดสาธิต (Demo)"

# Session date, gold dialogues joined into its transcript, therapist's cue decision and note
SESSIONS = [
    (date(2026, 9, 4), ["synthetic_plain_01"], "acknowledged", "ตอบสั้น ใช้คำเดิมของผู้ใหญ่บ่อย"),
    (date(2026, 9, 18), ["synthetic_plain_02", "synthetic_echo_02"], "acknowledged", "พูดตามทันทีหลังคำถาม 2 ครั้ง"),
    (date(2026, 10, 2), ["synthetic_plain_03", "synthetic_echo_03", "synthetic_plain_01"], "dismissed", "ส่วนใหญ่เป็นคำตอบต่อคำถาม ไม่ใช่การพูดตาม"),
]
AUDIO_SESSION = (date(2026, 10, 16), "synthetic_echo_01.wav")

INTERPRETATION = {
    0: "เด็กตอบคำถามสั้น ๆ ได้ ยังไม่ขยายประโยคเอง",
    1: "ประโยคยาวขึ้นในกิจกรรมเล่นรถไฟ ยังพูดตามคำถามของครูบางครั้ง",
}


def _utterance_lines(stem: str) -> list[str]:
    text = (GOLD_DIR / f"{stem}.cha").read_text(encoding="utf-8")
    return [line for line in text.splitlines() if line.startswith("*")]


def _chat(stems: list[str]) -> str:
    lines = [line for stem in stems for line in _utterance_lines(stem)]
    header = [
        "@UTF8",
        "@Begin",
        "@Languages:\ttha",
        "@Participants:\tCHI Target_Child, INV Investigator",
        "@Comment:\tDemonstration: scripted dialogue, not a real child.",
    ]
    return "\n".join([*header, *lines, "@End", ""])


def prepare_folder(home: Path, reset: bool) -> None:
    if home.exists() and any(home.iterdir()):
        if not (home / MARKER).is_file():
            raise SystemExit(f"{home} has files but is not a demo folder; refusing to touch it.")
        if not reset:
            raise SystemExit(f"Demo folder already exists at {home}. Use --reset to rebuild it.")
        shutil.rmtree(home)
    home.mkdir(parents=True, exist_ok=True)
    (home / MARKER).write_text(json.dumps({"demo": True}), encoding="utf-8")


def seed(home: Path, *, with_audio: bool = True, audio_dir: Path = AUDIO_DIR, log=print) -> dict:
    from packages.desktop.core import DesktopService, open_workspace

    service = DesktopService(open_workspace(home))
    service.set_therapist_name(THERAPIST)

    case = service.create_case(
        "DEMO-001", 50, nickname="ภูมิ (สาธิต)", language="Thai",
        notes="ข้อมูลสาธิตจากบทสนทนาที่เขียนขึ้นและเสียงสังเคราะห์ ไม่ใช่เด็กจริง",
    )
    service.grant_consent(case.case_id, "ผู้ปกครอง (สาธิต)", date(2026, 9, 1), "เอกสารสาธิต")

    for index, (when, stems, cue_status, cue_note) in enumerate(SESSIONS):
        session = service.create_session(case.case_id, when, notes="กิจกรรมเล่นของเล่นและถามตอบ")
        transcript = service.import_transcript_text(session.session_id, _chat(stems), filename=f"demo_{when}.cha")
        service.attest(transcript.transcript_id, override_reason="ข้อมูลสาธิต ตรวจกับบทสนทนาต้นฉบับแล้ว")
        _, cues = service.analyze(session.session_id)
        for cue in cues.cues:
            service.set_cue_state(cues.result_id, cue.cue_code, cue_status, cue_note)
        report = service.draft_report(session.session_id, therapist_notes=INTERPRETATION.get(index, ""))
        if index in INTERPRETATION:
            service.sign_off(report.report_id)
        log(f"  session {when}: {len(transcript.utterances)} utterances, {len(cues.cues)} cue(s)")

    audio_note = "skipped"
    if with_audio:
        when, filename = AUDIO_SESSION
        source = audio_dir / filename
        session = service.create_session(case.case_id, when, notes="บันทึกเสียงในห้องบำบัด (เสียงสังเคราะห์)")
        if source.is_file():
            available, reason = service.transcription_availability()
            stored = service.store_recording(session.session_id, source)
            if available:
                log(f"  session {when}: transcribing {filename} on this computer…")
                transcript = service.transcribe(session.session_id, stored.audio_file_id)
                audio_note = f"{len(transcript.utterances)} utterances waiting for review"
            else:
                audio_note = f"recording stored; transcription unavailable ({reason})"
        else:
            audio_note = f"{source} not found; the session has no recording"
        log(f"  session {when}: {audio_note}")

    pending = service.create_case("DEMO-002", 38, nickname="มายด์ (สาธิต)", notes="ข้อมูลสาธิต ยังไม่บันทึกความยินยอม")
    return {"home": str(home), "cases": [case.case_id, pending.case_id], "audio": audio_note}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--home", type=Path, help="Demo folder (default: next to the real data folder)")
    parser.add_argument("--reset", action="store_true", help="Delete and rebuild an existing demo folder")
    parser.add_argument("--no-audio", action="store_true", help="Do not transcribe a recording")
    parser.add_argument("--audio-dir", type=Path, default=AUDIO_DIR)
    args = parser.parse_args()

    from packages.desktop.core.workspace import default_home, demo_home

    home = (args.home or demo_home()).expanduser().resolve()

    if home == default_home().expanduser().resolve():
        raise SystemExit("Refusing to seed demo data into the real data folder.")
    prepare_folder(home, args.reset)
    print(f"Seeding demo data in {home}")
    result = seed(home, with_audio=not args.no_audio, audio_dir=args.audio_dir)
    print(f"Done. Open it with: ./run_gui.sh --demo   ({result['audio']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
