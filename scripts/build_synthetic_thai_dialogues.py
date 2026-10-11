"""Build synthetic Thai therapist-child dialogues for end-to-end pipeline checks.

No recordings of Thai children are available to this project. This script
makes scripted dialogues with the macOS Thai text-to-speech voice. Each
dialogue is written as a recording plus the exact script as its gold
transcript, ready for ``evaluate_thai_asr.py --text-only``.

Because the text is known, these samples show how well short, everyday
therapy-style Thai is transcribed. Every turn uses the same voice, so they
cannot test child/adult separation, and they say nothing about accuracy on
real children. ``--child-pitch-steps`` raises the child's turns in pitch; in
our runs that did not make the voices separable and it lowered recognition
accuracy, so it is off by default.

Requires macOS (``say`` with a Thai voice).

Usage:
    python scripts/build_synthetic_thai_dialogues.py
    python scripts/evaluate_thai_asr.py --text-only
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EVALUATION_DIR = PROJECT_ROOT / "data" / "evaluation"
LOCAL_DIR = PROJECT_ROOT / ".local" / "evaluation"
SAMPLE_RATE = 16000
CHILD_PITCH_STEPS = 0.0
PAUSE_SECONDS = 0.7
THERAPIST, CHILD = "INV", "CHI"

# (sample id, [(speaker, text), ...]). The first three contain immediate echoes
# of the therapist's turn; the last three contain none.
DIALOGUES: list[tuple[str, list[tuple[str, str]]]] = [
    (
        "synthetic_echo_01",
        [
            (THERAPIST, "วันนี้เราจะเล่นอะไรกันดี"),
            (CHILD, "เล่นอะไรกันดี"),
            (THERAPIST, "เล่นรถไหมครับ"),
            (CHILD, "เล่นรถไหมครับ"),
            (THERAPIST, "รถคันนี้สีอะไร"),
            (CHILD, "สีแดง"),
            (THERAPIST, "เก่งมากครับ"),
            (CHILD, "รถวิ่งเร็ว"),
        ],
    ),
    (
        "synthetic_echo_02",
        [
            (THERAPIST, "หนูอยากกินขนมไหม"),
            (CHILD, "อยากกินขนมไหม"),
            (THERAPIST, "นี่คือลูกบอลสีฟ้า"),
            (CHILD, "ลูกบอลสีฟ้า"),
            (THERAPIST, "โยนลูกบอลมาให้ครูหน่อย"),
            (CHILD, "โยนลูกบอล"),
            (THERAPIST, "ขอบคุณครับ"),
            (CHILD, "เอาอีก"),
        ],
    ),
    (
        "synthetic_echo_03",
        [
            (THERAPIST, "ในรูปนี้มีสัตว์อะไรบ้าง"),
            (CHILD, "มีสัตว์อะไรบ้าง"),
            (THERAPIST, "นี่คือแมวตัวใหญ่"),
            (CHILD, "แมวตัวใหญ่"),
            (THERAPIST, "แมวร้องยังไงครับ"),
            (CHILD, "เหมียว"),
            (THERAPIST, "แล้วหมาอยู่ที่ไหน"),
            (CHILD, "หมาอยู่ที่ไหน"),
        ],
    ),
    (
        "synthetic_plain_01",
        [
            (THERAPIST, "สวัสดีครับ วันนี้สบายดีไหม"),
            (CHILD, "สบายดีครับ"),
            (THERAPIST, "เมื่อเช้ากินอะไรมา"),
            (CHILD, "กินข้าวกับไข่"),
            (THERAPIST, "อร่อยไหมครับ"),
            (CHILD, "อร่อยมาก"),
            (THERAPIST, "วันนี้ใครมาส่ง"),
            (CHILD, "แม่มาส่ง"),
        ],
    ),
    (
        "synthetic_plain_02",
        [
            (THERAPIST, "หนูชอบของเล่นชิ้นไหน"),
            (CHILD, "ชอบรถไฟ"),
            (THERAPIST, "รถไฟวิ่งไปที่ไหน"),
            (CHILD, "ไปบ้านคุณยาย"),
            (THERAPIST, "บ้านคุณยายอยู่ไกลไหม"),
            (CHILD, "ไกลมากเลย"),
            (THERAPIST, "ไปถึงแล้วจะทำอะไร"),
            (CHILD, "จะเล่นกับน้องหมา"),
        ],
    ),
    (
        "synthetic_plain_03",
        [
            (THERAPIST, "ดูรูปนี้สิครับ เห็นอะไร"),
            (CHILD, "เห็นนกสองตัว"),
            (THERAPIST, "นกกำลังทำอะไรอยู่"),
            (CHILD, "กำลังบิน"),
            (THERAPIST, "บินไปไหนครับ"),
            (CHILD, "บินไปบนต้นไม้"),
            (THERAPIST, "ต้นไม้สูงไหม"),
            (CHILD, "สูงมาก"),
        ],
    ),
]


def gold_chat_text(turns: list[tuple[str, str]]) -> str:
    lines = ["@UTF8", "@Begin", "@Languages:\ttha", "@Comment:\tSynthetic text-to-speech dialogue; not a real session."]
    lines += [f"*{speaker}:\t{text} ." for speaker, text in turns]
    lines.append("@End")
    return "\n".join(lines) + "\n"


def synthesize_turn(text: str, voice: str, workdir: Path):
    import librosa

    path = workdir / "turn.wav"
    subprocess.run(
        ["say", "-v", voice, "-o", str(path), f"--data-format=LEI16@{SAMPLE_RATE}", text],
        check=True,
    )
    audio, _ = librosa.load(str(path), sr=SAMPLE_RATE, mono=True)
    return audio


def build_recording(turns: list[tuple[str, str]], voice: str, child_pitch_steps: float = CHILD_PITCH_STEPS):
    import librosa
    import numpy as np

    pause = np.zeros(int(PAUSE_SECONDS * SAMPLE_RATE), dtype="float32")
    pieces = [pause]
    with tempfile.TemporaryDirectory() as tmp:
        for speaker, text in turns:
            audio = synthesize_turn(text, voice, Path(tmp))
            if speaker == CHILD and child_pitch_steps:
                audio = librosa.effects.pitch_shift(audio, sr=SAMPLE_RATE, n_steps=child_pitch_steps)
            pieces += [audio.astype("float32"), pause]
    return np.concatenate(pieces)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--evaluation-dir", type=Path, default=EVALUATION_DIR, help="Receives gold_transcripts/.")
    parser.add_argument("--local-dir", type=Path, default=None, help="Receives audio_samples/ (default: .local/evaluation).")
    parser.add_argument("--voice", default="Kanya")
    parser.add_argument(
        "--child-pitch-steps",
        type=float,
        default=CHILD_PITCH_STEPS,
        help="Semitones to raise the child's turns; 0 keeps one unmodified voice.",
    )
    args = parser.parse_args()
    if sys.platform != "darwin":
        print("This script needs the macOS `say` command with a Thai voice.")
        return 1
    import soundfile

    local_dir = args.local_dir or (LOCAL_DIR if args.evaluation_dir == EVALUATION_DIR else args.evaluation_dir)
    audio_dir = local_dir / "audio_samples"
    gold_dir = args.evaluation_dir / "gold_transcripts"
    audio_dir.mkdir(parents=True, exist_ok=True)
    gold_dir.mkdir(parents=True, exist_ok=True)
    for sample_id, turns in DIALOGUES:
        soundfile.write(str(audio_dir / f"{sample_id}.wav"), build_recording(turns, args.voice, args.child_pitch_steps), SAMPLE_RATE)
        (gold_dir / f"{sample_id}.cha").write_text(gold_chat_text(turns), encoding="utf-8")
        print(f"[ok] {sample_id}: {len(turns)} turns")
    return 0


if __name__ == "__main__":
    sys.exit(main())
