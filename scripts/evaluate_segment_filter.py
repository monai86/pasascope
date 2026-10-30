"""Does the hallucination filter throw away speech that was really there?

The app drops a Whisper segment when it looks invented: empty text, a high
no-speech probability, a low average log-probability, a 4-gram repeated three
times, or more letters per second than speech can carry. The LOTUSDIS test
found real short utterances dropped by the no-speech rule, but there each clip
was transcribed on its own. This script measures the same thing on whole
session recordings with timed gold transcripts.

``run`` sends each recording through the app's pipeline (EllisWeismer, ENNI and
CRSLP: the same evaluation window as the end-to-end test) or each LOTUSDIS clip
through the transcriber, with ``WhisperTranscriber.segment_log`` switched on, so
every segment Whisper returned is saved with its scores and what the filter
did with it. Nothing about the transcription changes.

``report`` labels each segment from the gold time bullets: speech when at least
half of it lies inside gold utterances, no speech when under a tenth does,
unclear otherwise (left out). It then counts real speech the filter dropped,
gold child utterances lost because of it, and non-speech the filter caught, and
scores the candidate change: keep segments dropped only on the two probability
rules, flagged for the therapist, instead of deleting them.

Usage:
    python scripts/evaluate_segment_filter.py run --corpus ellisweismer --mode accurate
    python scripts/evaluate_segment_filter.py report
Outputs: .local/evaluation/segment_filter/<corpus>_<mode>.jsonl (kept out of git),
reports/metrics/segment_filter.{md,csv}
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys
import tempfile
import time

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

EVAL = PROJECT_ROOT / ".local" / "evaluation"
OUT = EVAL / "segment_filter"
CORPORA = {
    # name: (transcripts, audio, minutes per recording, language)
    "ellisweismer": (EVAL / "ellisweismer_media" / "chat", EVAL / "ellisweismer_media", 5.0, "en"),
    "enni": (EVAL / "enni_media" / "chat", EVAL / "enni_media", 5.0, "en"),
    "crslp": (EVAL / "crslp_media" / "chat", EVAL / "crslp_media", 3.0, "th"),
}
STRATEGY = {  # the app's two modes
    ("en", "accurate"): ("medium", "english"),
    ("en", "fast"): ("medium", "english"),
    ("th", "accurate"): ("medium", "thai_specialized"),
    ("th", "fast"): ("medium", "thai"),
}
SPEECH, NO_SPEECH = 0.5, 0.1          # share of a segment inside gold utterances
PROBABILITY_RULES = {"no_speech", "low_logprob"}  # the rules the candidate change would flag instead of drop


# ---------------------------------------------------------------- run
def run_sessions(corpus: str, mode: str, limit: int) -> None:
    import soundfile

    from scripts.evaluate_end_to_end import evaluation_window
    from scripts.evaluate_speaker_attribution import CHILD, collect_recordings
    from src.audio_pipeline.pipeline import audio_to_cha, decode_to_wav
    from src.audio_pipeline.whisper_transcribe import WhisperTranscriber

    cha_dir, audio_dir, minutes, language = CORPORA[corpus]
    model, strategy = STRATEGY[(language, mode)]
    recordings = collect_recordings(cha_dir, audio_dir, max_minutes=None, limit=limit or None)[0]
    path = OUT / f"{corpus}_{mode}.jsonl"
    done = {json.loads(line)["recording"] for line in path.read_text(encoding="utf-8").splitlines()} if path.exists() else set()
    OUT.mkdir(parents=True, exist_ok=True)
    for index, rec in enumerate(recordings, start=1):
        name = rec.cha_path.stem
        if name in done:
            continue
        start, end = evaluation_window(rec.utterances, minutes)
        gold = [{"start": u.start - start, "end": u.end - start, "child": u.role == CHILD, "text": u.text}
                for u in rec.utterances if u.end > start and u.start < end]
        log: list = []
        WhisperTranscriber.segment_log = log
        started = time.perf_counter()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                full = Path(tmp) / "full.wav"
                decode_to_wav(rec.audio_path, full)
                data, sr = soundfile.read(str(full))
                clip = Path(tmp) / "clip.wav"
                soundfile.write(str(clip), data[int(start * sr): int(end * sr)], sr)
                audio_to_cha(clip, model_size=model, strategy=strategy, child_age_months=rec.age_months, validate=False)
        finally:
            WhisperTranscriber.segment_log = None
        record = {"recording": name, "corpus": corpus, "mode": mode, "window_start": round(start, 2),
                  "seconds": round(end - start, 1), "age_months": rec.age_months, "gold": gold, "segments": log,
                  "processing_seconds": round(time.perf_counter() - started, 1)}
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        dropped = sum(not s["kept"] for s in log)
        print(f"[{index}/{len(recordings)}] {corpus} {mode} {name}: {len(log)} segments, {dropped} dropped", flush=True)


def run_lotusdis(mode: str) -> None:
    from src.audio_pipeline.whisper_transcribe import WhisperTranscriber

    clips = sorted((EVAL / "lotusdis" / "wav" / "con123").glob("*.wav"))
    path = OUT / f"lotusdis_{mode}.jsonl"
    done = {json.loads(line)["recording"] for line in path.read_text(encoding="utf-8").splitlines()} if path.exists() else set()
    OUT.mkdir(parents=True, exist_ok=True)
    model, strategy = STRATEGY[("th", mode)]
    transcriber = WhisperTranscriber(model_size=model, strategy=strategy)
    for index, clip in enumerate(clips, start=1):
        if clip.stem in done:
            continue
        import soundfile
        seconds = soundfile.info(str(clip)).duration
        log: list = []
        WhisperTranscriber.segment_log = log
        try:
            transcriber.transcribe(clip)
        finally:
            WhisperTranscriber.segment_log = None
        # Every LOTUSDIS clip is one speaker talking from start to end (adult).
        record = {"recording": clip.stem, "corpus": "lotusdis", "mode": mode, "window_start": 0.0,
                  "seconds": round(seconds, 2), "age_months": None,
                  "gold": [{"start": 0.0, "end": seconds, "child": False, "text": ""}], "segments": log}
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        if index % 25 == 0:
            print(f"[{index}/{len(clips)}] lotusdis {mode}", flush=True)


# ---------------------------------------------------------------- report
def inside(segment: dict, spans: list[dict]) -> float:
    """Share of the segment's time that lies inside the given spans."""
    length = max(1e-6, segment["end"] - segment["start"])
    covered = sum(max(0.0, min(segment["end"], s["end"]) - max(segment["start"], s["start"])) for s in spans)
    return min(1.0, covered / length)


def label(segment: dict, gold: list[dict]) -> str:
    share = inside(segment, gold)
    if share >= SPEECH:
        return "speech"
    if share < NO_SPEECH:
        return "no_speech"
    return "unclear"


def lost_child_utterances(record: dict, keep) -> int:
    """Gold child utterances mostly covered by dropped segments and barely by kept ones."""
    kept = [s for s in record["segments"] if keep(s)]
    dropped = [s for s in record["segments"] if not keep(s)]
    lost = 0
    for utt in record["gold"]:
        if not utt["child"]:
            continue
        if inside(utt, dropped) >= SPEECH and inside(utt, kept) < 0.2:
            lost += 1
    return lost


def current(segment: dict) -> bool:
    return segment["kept"]


def flagged(segment: dict) -> bool:
    """The candidate: segments dropped only on a probability rule are kept (and flagged)."""
    return segment["kept"] or segment["reason"] in PROBABILITY_RULES


def summarize(records: list[dict]) -> dict:
    out = {"recordings": len(records), "minutes": round(sum(r["seconds"] for r in records) / 60, 1),
           "segments": 0, "child_gold": 0}
    for key in ("speech", "no_speech", "unclear"):
        out[f"{key}_kept"] = out[f"{key}_dropped"] = 0
    out["speech_dropped_by"] = {}
    out["no_speech_dropped_by"] = {}
    out["flag_speech"] = out["flag_no_speech"] = out["flag_unclear"] = 0
    out["lost_now"] = out["lost_flagged"] = 0
    for rec in records:
        out["child_gold"] += sum(u["child"] for u in rec["gold"])
        for seg in rec["segments"]:
            out["segments"] += 1
            kind = label(seg, rec["gold"])
            out[f"{kind}_{'kept' if seg['kept'] else 'dropped'}"] += 1
            if not seg["kept"] and kind in ("speech", "no_speech"):
                by = out[f"{kind}_dropped_by"]
                by[seg["reason"]] = by.get(seg["reason"], 0) + 1
            if not seg["kept"] and seg["reason"] in PROBABILITY_RULES:
                out[f"flag_{kind}"] += 1
        out["lost_now"] += lost_child_utterances(rec, current)
        out["lost_flagged"] += lost_child_utterances(rec, flagged)
    five_minute_blocks = max(1e-6, out["minutes"] / 5)
    out["junk_flags_per_5min"] = round(out["flag_no_speech"] / five_minute_blocks, 2)
    return out


def report(report_dir: Path) -> int:
    files = sorted(OUT.glob("*.jsonl"))
    if not files:
        print("No logs yet; run first.")
        return 1
    rows = []
    for path in files:
        records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not records:
            continue
        s = summarize(records)
        s["corpus"], s["mode"] = records[0]["corpus"], records[0]["mode"]
        rows.append(s)
    order = {"ellisweismer": 0, "lotusdis": 1, "enni": 2, "crslp": 3}
    rows.sort(key=lambda r: (order.get(r["corpus"], 9), r["mode"]))
    report_dir.mkdir(parents=True, exist_ok=True)
    flat_keys = ["corpus", "mode", "recordings", "minutes", "segments", "speech_kept", "speech_dropped",
                 "no_speech_kept", "no_speech_dropped", "unclear_kept", "unclear_dropped", "child_gold",
                 "lost_now", "lost_flagged", "flag_speech", "flag_no_speech", "flag_unclear", "junk_flags_per_5min"]
    with (report_dir / "segment_filter.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=flat_keys + ["speech_dropped_by", "no_speech_dropped_by"])
        writer.writeheader()
        for r in rows:
            writer.writerow({**{k: r[k] for k in flat_keys},
                             "speech_dropped_by": json.dumps(r["speech_dropped_by"]),
                             "no_speech_dropped_by": json.dumps(r["no_speech_dropped_by"])})
    tuning = {"ellisweismer", "lotusdis"}
    lines = [
        "# Does the hallucination filter drop real speech?",
        "",
        "Every segment Whisper returned was logged with what the app's filter did with it "
        "(`scripts/evaluate_segment_filter.py`), on the end-to-end evaluation windows of whole session "
        "recordings (EllisWeismer, ENNI 5 minutes each; CRSLP 3 minutes each) and on the 150 LOTUSDIS clips "
        "(near microphone). A segment counts as speech when at least half of it lies inside gold utterances "
        "and as no speech when under a tenth does; the rest are unclear and left out of both counts. Gold "
        "transcripts do not mark every sound, so a few \"no speech\" segments may be untranscribed talk.",
        "",
        "Candidate change: a segment dropped only because of the two probability rules (no-speech "
        "probability above 0.85, average log-probability below -1.25) is kept and flagged for the therapist "
        "instead. Empty text, repeated 4-grams and text too fast to be speech are still dropped. Decision rule, "
        "set before the results: adopt it if, on the corpora not used to choose it (ENNI, CRSLP), it recovers "
        "at least one real speech segment and adds on average at most one flagged non-speech line per "
        "5 minutes.",
        "",
        "| Corpus | Mode | Minutes | Segments | Speech kept / dropped | No speech kept / dropped | "
        "Child utterances (gold) | Lost now | Lost with flags | Flagged: speech / no speech / unclear | "
        "Flagged non-speech per 5 min |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        held = "" if r["corpus"] in tuning else " (held out)"
        lines.append(
            f"| {r['corpus']}{held} | {r['mode']} | {r['minutes']} | {r['segments']} | "
            f"{r['speech_kept']} / {r['speech_dropped']} | {r['no_speech_kept']} / {r['no_speech_dropped']} | "
            f"{r['child_gold'] if r['corpus'] != 'lotusdis' else '–'} | {r['lost_now']} | {r['lost_flagged']} | "
            f"{r['flag_speech']} / {r['flag_no_speech']} / {r['flag_unclear']} | {r['junk_flags_per_5min']} |")
    lines += ["", "Real speech dropped, by rule:", ""]
    for r in rows:
        lines.append(f"- {r['corpus']} {r['mode']}: {r['speech_dropped_by'] or 'none'}; "
                     f"non-speech dropped: {r['no_speech_dropped_by'] or 'none'}")
    held = [r for r in rows if r["corpus"] not in tuning]
    if held:
        recovered = sum(r["flag_speech"] for r in held)
        junk = sum(r["flag_no_speech"] for r in held) / max(1e-6, sum(r["minutes"] for r in held) / 5)
        verdict = "adopt" if recovered >= 1 and junk <= 1.0 else "do not adopt"
        lines += ["", f"Held-out corpora: {recovered} real speech segments recovered, "
                      f"{junk:.2f} flagged non-speech lines per 5 minutes. Decision: **{verdict}**.", ""]
    (report_dir / "segment_filter.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    r = sub.add_parser("run")
    r.add_argument("--corpus", required=True, choices=[*CORPORA, "lotusdis"])
    r.add_argument("--mode", default="accurate", choices=["accurate", "fast"])
    r.add_argument("--limit", type=int, default=0)
    p = sub.add_parser("report")
    p.add_argument("--report-dir", type=Path, default=PROJECT_ROOT / "reports" / "metrics")
    args = parser.parse_args(argv)
    if args.command == "run":
        if args.corpus == "lotusdis":
            run_lotusdis(args.mode)
        else:
            run_sessions(args.corpus, args.mode, args.limit)
        return 0
    return report(args.report_dir)


if __name__ == "__main__":
    raise SystemExit(main(argv=None))
