"""Score the timing pilot: time per excerpt, and how close each result is to gold.

Reads what the facilitator recorded (docs/TIMING_PILOT_PROTOCOL_TH.md):

    .local/evaluation/timing_pilot/results/timing.csv
        participant, excerpt, condition (manual | app), active_minutes,
        waiting_minutes, help_requests, ease_1to7, hand_mlu_w, hand_ndw, notes
    .local/evaluation/timing_pilot/results/<participant>_<excerpt>.cha (or .txt)
        the participant's final transcript: a CHAT file exported from PasaScope,
        or plain lines such as "CHI: ปวด ฉี่" typed by hand

Both arms' transcripts are re-split into Thai words the same way and counted by
the app's own feature code, so the measure differences show transcript
differences, not counting conventions or spacing.
Hand counts from the manual arm are reported next to them.

Outputs (numbers only, no transcript text):
    reports/metrics/timing_pilot.csv
    reports/metrics/timing_pilot.md

Usage:
    python scripts/score_timing_pilot.py
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path
from statistics import median

PROJECT_ROOT = Path(__file__).resolve().parent.parent
for entry in (PROJECT_ROOT / "apps" / "api", PROJECT_ROOT):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

import jiwer  # noqa: E402

from packages.cha.parser import parse_cha_text  # noqa: E402
from scripts.evaluate_core_measures_clan import app_measures  # noqa: E402
from scripts.evaluate_thai_asr import _THAI_INNER_SPACE, Turn, _characters, _error_rate  # noqa: E402
from src.clinical_speech.thai_lsa import tokenize_thai_words  # noqa: E402

PILOT_DIR = PROJECT_ROOT / ".local" / "evaluation" / "timing_pilot"
REPORT_DIR = PROJECT_ROOT / "reports" / "metrics"
PLAIN_LINE = re.compile(r"^\*?([A-Za-z0-9]{2,4})\s*:\s*(.+)$")
COLUMNS = [
    "participant", "excerpt", "condition", "audio_minutes", "active_minutes", "waiting_minutes",
    "active_per_audio_minute", "help_requests", "ease_1to7", "cer_all", "cer_child",
    "child_utterances_gold", "child_utterances_result", "mlu_w_gold", "mlu_w_result", "ndw_gold", "ndw_result",
    "hand_mlu_w", "hand_ndw",
]


def as_chat(text: str) -> str:
    """Accept a CHAT file as is; turn plain "CHI: ..." lines into CHAT main tiers."""
    if any(line.startswith("*") for line in text.splitlines()):
        return text
    body = []
    for line in text.splitlines():
        match = PLAIN_LINE.match(line.strip())
        if match:
            body.append(f"*{match.group(1).upper()}:\t{match.group(2).strip()}")
    return "\n".join(["@UTF8", "@Begin", "@Languages:\ttha", "@Participants:\tCHI Target_Child, MOT Mother"] + body + ["@End", ""])


def resegment(chat: str) -> str:
    """Split the Thai words of every main tier the same way (PyThaiNLP, as the app does), so word
    counts do not depend on where the gold transcriber or the participant put spaces."""
    lines = []
    for line in chat.splitlines():
        if line.startswith("*") and "\t" in line:
            speaker, text = line.split("\t", 1)
            joined = _THAI_INNER_SPACE.sub("", text)
            line = f"{speaker}\t" + " ".join(t for t in tokenize_thai_words(joined) if t.strip())
        lines.append(line)
    return "\n".join(lines)


def turns(chat: str) -> list[Turn]:
    return [Turn(u.speaker_code, u.normalized_text) for u in parse_cha_text(chat).utterances if u.normalized_text.strip()]


def number(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def score(row: dict, pilot_dir: Path, audio_minutes: dict[str, float]) -> dict:
    gold_chat = (pilot_dir / "gold" / f"excerpt_{row['excerpt']}.cha").read_text(encoding="utf-8")
    stem = f"{row['participant']}_{row['excerpt']}"
    result_path = next((p for p in (pilot_dir / "results").glob(f"{stem}.*") if p.suffix in {".cha", ".txt"}), None)
    if result_path is None:
        raise SystemExit(f"No transcript for {stem} in {pilot_dir / 'results'}")
    result_chat = as_chat(result_path.read_text(encoding="utf-8"))
    gold, result = turns(gold_chat), turns(result_chat)
    gold_child = [t for t in gold if t.speaker == "CHI"]
    result_child = [t for t in result if t.speaker == "CHI"]
    gold_values, result_values = app_measures(resegment(gold_chat)), app_measures(resegment(result_chat))
    active = number(row["active_minutes"])
    minutes = audio_minutes[row["excerpt"]]
    return {
        "participant": row["participant"],
        "excerpt": row["excerpt"],
        "condition": row["condition"].strip().lower(),
        "audio_minutes": round(minutes, 2),
        "active_minutes": active,
        "waiting_minutes": number(row.get("waiting_minutes")),
        "active_per_audio_minute": round(active / minutes, 2) if active is not None else None,
        "help_requests": number(row.get("help_requests")),
        "ease_1to7": number(row.get("ease_1to7")),
        "cer_all": _error_rate(jiwer.cer, _characters(gold), _characters(result)),
        "cer_child": _error_rate(jiwer.cer, _characters(gold_child), _characters(result_child)),
        "child_utterances_gold": len(gold_child),
        "child_utterances_result": len(result_child),
        "mlu_w_gold": gold_values["mean_length_of_utterance_words"],
        "mlu_w_result": result_values["mean_length_of_utterance_words"],
        "ndw_gold": gold_values["number_of_different_words"],
        "ndw_result": result_values["number_of_different_words"],
        "hand_mlu_w": number(row.get("hand_mlu_w")),
        "hand_ndw": number(row.get("hand_ndw")),
    }


def _median(rows: list[dict], key: str) -> str:
    values = [r[key] for r in rows if r[key] is not None]
    return "-" if not values else f"{median(values):.2f} ({min(values):.2f}-{max(values):.2f})"


def _median_abs(rows: list[dict], a: str, b: str) -> str:
    values = [abs(r[a] - r[b]) for r in rows if r[a] is not None and r[b] is not None]
    return "-" if not values else f"{median(values):.2f}"


def render(rows: list[dict]) -> str:
    participants = sorted({r["participant"] for r in rows})
    lines = [
        "# Timing Pilot: By Hand or With PasaScope",
        "",
        f"Participants: {len(participants)}. Material: 3-minute excerpts of CRSLP toy-play recordings "
        "(Thai children aged 20-24 months with a parent), prepared by `scripts/prepare_timing_pilot.py`. "
        "Protocol: `docs/TIMING_PILOT_PROTOCOL_TH.md`.",
        "",
        "Values are median (range) across excerpts. Active time excludes time spent waiting for the app to "
        "transcribe; waiting time is shown separately because the therapist can do other work meanwhile.",
        "",
        "| Measure | By hand | With PasaScope |",
        "|---|---|---|",
    ]
    arms = {c: [r for r in rows if r["condition"] == c] for c in ("manual", "app")}
    for label, key in [
        ("Excerpts", None),
        ("Active minutes", "active_minutes"),
        ("Active minutes per minute of audio", "active_per_audio_minute"),
        ("Waiting minutes", "waiting_minutes"),
        ("Help requests", "help_requests"),
        ("Ease, Single Ease Question (1 = very difficult, 7 = very easy)", "ease_1to7"),
        ("CER of the final transcript vs gold, all speakers", "cer_all"),
        ("CER, child only", "cer_child"),
    ]:
        if key is None:
            lines.append(f"| {label} | {len(arms['manual'])} | {len(arms['app'])} |")
        else:
            lines.append(f"| {label} | {_median(arms['manual'], key)} | {_median(arms['app'], key)} |")
    lines += [
        f"| MLU-w difference from gold (absolute) | {_median_abs(arms['manual'], 'mlu_w_result', 'mlu_w_gold')} | "
        f"{_median_abs(arms['app'], 'mlu_w_result', 'mlu_w_gold')} |",
        f"| NDW difference from gold (absolute) | {_median_abs(arms['manual'], 'ndw_result', 'ndw_gold')} | "
        f"{_median_abs(arms['app'], 'ndw_result', 'ndw_gold')} |",
        f"| Hand-counted MLU-w vs the app's count of the same transcript | "
        f"{_median_abs(arms['manual'], 'hand_mlu_w', 'mlu_w_result')} | - |",
        "",
        "## Reading these numbers",
        "",
        "- This is a pilot with few participants and excerpts; report medians and ranges, no statistical tests.",
        "- Excerpts differ in difficulty. The assignment in the protocol balances which excerpt is done by "
        "hand and which with the app, and the order of the two arms.",
        "- Gold transcripts are the CRSLP transcriber's; their word spacing follows the corpus, which the app's "
        "Thai word segmentation may split differently. Both arms are counted by the same code.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--pilot-dir", type=Path, default=PILOT_DIR)
    parser.add_argument("--report-dir", type=Path, default=REPORT_DIR)
    args = parser.parse_args()
    with (args.pilot_dir / "key.csv").open(encoding="utf-8") as handle:
        audio_minutes = {r["excerpt"]: float(r["seconds"]) / 60 for r in csv.DictReader(handle)}
    with (args.pilot_dir / "results" / "timing.csv").open(encoding="utf-8-sig") as handle:
        rows = [score(r, args.pilot_dir, audio_minutes) for r in csv.DictReader(handle) if r.get("participant")]
    args.report_dir.mkdir(parents=True, exist_ok=True)
    with (args.report_dir / "timing_pilot.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    (args.report_dir / "timing_pilot.md").write_text(render(rows), encoding="utf-8")
    print(f"Scored {len(rows)} rows -> {args.report_dir / 'timing_pilot.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
