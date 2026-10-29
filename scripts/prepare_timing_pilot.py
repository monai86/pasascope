"""Cut the audio excerpts and gold transcripts for the timing pilot.

The timing pilot (docs/TIMING_PILOT_PROTOCOL_TH.md) compares how long a
therapist takes to produce a child's transcript and MLU/NDW by hand with how
long it takes with PasaScope, and how accurate each result is. It uses the
CRSLP recordings (CHILDES EastAsian/Thai, Thai children aged 20-24 months in
toy play with a parent), already downloaded through the project owner's
TalkBank account into ``.local/evaluation/crslp_media`` with their CHAT files
in ``chat/``. No new recordings of children are made.

For four different children, the script picks the three-minute window, at
least a minute into the recording, with the most intelligible child utterances.
Not every CRSLP utterance carries a time stamp, so each window starts and ends
at a time-stamped utterance and keeps every utterance in between.

Outputs (in .local/, never committed):
    .local/evaluation/timing_pilot/excerpt_A.wav ... excerpt_D.wav   16 kHz mono
    .local/evaluation/timing_pilot/gold/excerpt_A.cha ...           gold transcript of each excerpt
    .local/evaluation/timing_pilot/key.csv                          where each excerpt comes from (facilitator only)

Usage:
    python scripts/prepare_timing_pilot.py
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from packages.cha.parser import parse_cha_file  # noqa: E402

MEDIA_DIR = PROJECT_ROOT / ".local" / "evaluation" / "crslp_media"
OUT_DIR = PROJECT_ROOT / ".local" / "evaluation" / "timing_pilot"
WINDOW_MS = 180_000
SKIP_MS = 60_000
EXCERPTS = "ABCD"
RATE = 16_000
BULLET = re.compile(r"\s*\x15?\d+_\d+\x15?")
HEADER = ("@UTF8", "@Begin", "@Languages", "@Participants", "@ID")


def intelligible_child(utterance) -> bool:
    text = utterance.normalized_text.strip()
    return utterance.speaker_code == "CHI" and text != "" and "xxx" not in text and "yyy" not in text


def best_window(cha_path: Path) -> dict | None:
    """The three-minute window with the most intelligible child utterances."""
    utterances = parse_cha_file(cha_path).utterances
    timed = [i for i, u in enumerate(utterances) if u.start_ms is not None]
    best = None
    for position, first in enumerate(timed):
        start = utterances[first].start_ms
        if start < SKIP_MS:
            continue
        # The excerpt ends where the first time-stamped utterance at or after start + 3 min begins.
        after = next((i for i in timed[position + 1:] if utterances[i].start_ms >= start + WINDOW_MS), None)
        if after is None:
            break
        chosen = utterances[first:after]
        score = sum(intelligible_child(u) for u in chosen)
        if best is None or score > best["child_utterances"]:
            best = {
                "cha": cha_path,
                "first": first,
                "after": after,
                "start_ms": start,
                "end_ms": utterances[after].start_ms,
                "utterances": len(chosen),
                "child_utterances": score,
            }
    return best


def gold_text(window: dict) -> str:
    lines = window["cha"].read_text(encoding="utf-8").splitlines()
    header = [line for line in lines if line.startswith(HEADER)]
    utterances = parse_cha_file(window["cha"]).utterances[window["first"]:window["after"]]
    body = []
    for utterance in utterances:
        source = lines[utterance.line_number - 1] if utterance.line_number else ""
        if not source.startswith("*"):
            source = f"*{utterance.speaker_code}:\t{utterance.raw_text}"
        body.append(BULLET.sub("", source).rstrip())
    return "\n".join(header + body + ["@End", ""])


def cut_audio(media: Path, start_ms: int, end_ms: int, target: Path) -> float:
    import soundfile
    from faster_whisper.audio import decode_audio

    audio = decode_audio(str(media), sampling_rate=RATE)
    piece = audio[start_ms * RATE // 1000:end_ms * RATE // 1000]
    soundfile.write(str(target), piece, RATE)
    return len(piece) / RATE


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--media-dir", type=Path, default=MEDIA_DIR)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args()

    per_child: dict[str, dict] = {}
    for cha in sorted((args.media_dir / "chat").glob("*/*.cha")):
        window = best_window(cha)
        child = cha.parent.name
        if window and (child not in per_child or window["child_utterances"] > per_child[child]["child_utterances"]):
            per_child[child] = window
    chosen = sorted(per_child.values(), key=lambda w: (-w["child_utterances"], str(w["cha"])))[: len(EXCERPTS)]
    if len(chosen) < len(EXCERPTS):
        raise SystemExit(f"Only {len(chosen)} recordings with a usable window in {args.media_dir}")

    (args.out_dir / "gold").mkdir(parents=True, exist_ok=True)
    rows = []
    for letter, window in zip(EXCERPTS, chosen):
        child = window["cha"].parent.name
        media = args.media_dir / child / f"{window['cha'].stem}.mp4"
        seconds = cut_audio(media, window["start_ms"], window["end_ms"], args.out_dir / f"excerpt_{letter}.wav")
        (args.out_dir / "gold" / f"excerpt_{letter}.cha").write_text(gold_text(window), encoding="utf-8")
        rows.append(
            {
                "excerpt": letter,
                "child_folder": child,
                "recording": window["cha"].stem,
                "start_s": round(window["start_ms"] / 1000, 1),
                "end_s": round(window["end_ms"] / 1000, 1),
                "seconds": round(seconds, 1),
                "gold_utterances": window["utterances"],
                "gold_intelligible_child_utterances": window["child_utterances"],
            }
        )
        print(rows[-1])
    with (args.out_dir / "key.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} excerpts to {args.out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
