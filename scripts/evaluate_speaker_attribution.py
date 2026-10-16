"""Measure how well the pipeline tells the child's speech from the adults'.

Every language measure is computed from the utterances labelled *CHI, so a
speaker mistake moves MLU and NDW as much as a transcription mistake does.
This script checks speaker attribution on recordings whose CHAT transcript
already says who spoke when (time bullets on every utterance):

1. The gold utterance spans are given to a diarization backend, which labels
   each one child or adult. ASR is not run, so only speaker attribution is
   measured.
2. Each label is compared with the transcript: accuracy, child precision,
   recall and F1, time-weighted accuracy.
3. MLU-w and NDW are computed from the gold text twice, once with the gold
   child utterances and once with the ones the backend called child, to show
   how far a speaker mistake moves the measures a therapist reads.

The backend can also see each utterance's text (``--text gold``), as it would
see the ASR draft in the app; ``--text none`` measures the audio alone.

Audio is matched to transcripts by the ``@Media`` name (``.wav``, ``.mp3``,
``.m4a``, ``.mp4``...). TalkBank media need a free account; download them into
one folder and pass it as ``--audio-dir``.

Usage:
    python scripts/evaluate_speaker_attribution.py \\
        --cha-dir data/curated/english_child_transcripts/EllisWeismer \\
        --audio-dir ~/Downloads/EllisWeismer-media --backend embedding --max-minutes 10

Outputs (``--report-dir``, default reports/metrics):
    speaker_attribution_<backend>.csv   one row per recording
    speaker_attribution_<backend>.md    summary
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys
import tempfile
import time

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from packages.cha.clan_words import analyze_main_tier  # noqa: E402
from packages.cha.parser import normalize_utterance_text, parse_cha_file  # noqa: E402
from packages.features.language_sample import compute_language_sample_measures  # noqa: E402

AUDIO_SUFFIXES = (".wav", ".mp3", ".m4a", ".mp4", ".flac", ".ogg", ".webm", ".aac")
CHILD = "CHI"
ADULT = "ADULT"


@dataclass
class GoldUtterance:
    start: float
    end: float
    role: str  # CHILD or ADULT
    text: str  # CHAT main tier, codes kept


@dataclass
class Recording:
    cha_path: Path
    audio_path: Path
    age_months: float | None
    utterances: list[GoldUtterance]


# ---------------------------------------------------------------------------
# Gold transcripts
# ---------------------------------------------------------------------------
def read_gold(cha_path: Path, max_minutes: float | None = None) -> tuple[list[GoldUtterance], float | None, str]:
    """Timed utterances, the child's age in months and the @Media name."""
    parsed = parse_cha_file(cha_path)
    limit_ms = None if not max_minutes else max_minutes * 60_000
    utterances = [
        GoldUtterance(
            start=u.start_ms / 1000,
            end=u.end_ms / 1000,
            role=CHILD if u.speaker_code == "CHI" else ADULT,
            text=u.raw_text,
        )
        for u in parsed.utterances
        if u.start_ms is not None and u.end_ms is not None and u.end_ms > u.start_ms
        and (limit_ms is None or u.end_ms <= limit_ms)
    ]
    media = ""
    for value in parsed.headers.get("@Media", []):
        media = value.split(",")[0].strip()
    return utterances, _child_age(parsed.headers.get("@ID", [])), media


def _child_age(ids: list[str]) -> float | None:
    from src.chat_feature_extractor import age_to_months

    for value in ids:
        fields = value.split("|")
        if len(fields) > 3 and fields[2].strip() == "CHI":
            return age_to_months(fields[3].strip())
    return None


def find_audio(audio_dir: Path, media: str, cha_path: Path) -> Path | None:
    names = [n for n in (media, cha_path.stem) if n]
    for name in names:
        for suffix in AUDIO_SUFFIXES:
            hits = list(audio_dir.rglob(f"{name}{suffix}"))
            if hits:
                return hits[0]
    return None


def collect_recordings(cha_dir: Path, audio_dir: Path, *, max_minutes: float | None, limit: int | None) -> tuple[list[Recording], list[str]]:
    recordings: list[Recording] = []
    skipped: list[str] = []
    for cha_path in sorted(cha_dir.rglob("*.cha")):
        utterances, age, media = read_gold(cha_path, max_minutes)
        if not utterances:
            skipped.append(f"{cha_path.name}: no timed utterances")
            continue
        if not any(u.role == CHILD for u in utterances):
            skipped.append(f"{cha_path.name}: no timed child utterances")
            continue
        audio = find_audio(audio_dir, media, cha_path)
        if audio is None:
            skipped.append(f"{cha_path.name}: no audio named {media or cha_path.stem}")
            continue
        recordings.append(Recording(cha_path, audio, age, utterances))
        if limit and len(recordings) >= limit:
            break
    return recordings, skipped


# ---------------------------------------------------------------------------
# Backends
# ---------------------------------------------------------------------------
def make_backend(name: str, age_months: float | None):
    from src.audio_pipeline import diarization as d

    if name == "embedding":
        return d.EmbeddingDiarizer(d.EmbeddingDiarizerConfig(child_age_months=age_months))
    if name == "pitch":
        return d.PitchHeuristicDiarizer(
            d.PitchDiarizerConfig(child_f0_threshold_hz=d.age_aware_child_f0_threshold(age_months))
        )
    raise ValueError(f"unknown backend {name!r}")


BACKENDS = ("embedding", "pitch")


def predict_roles(recording: Recording, backend_name: str, *, use_text: bool) -> list[str]:
    """CHILD/ADULT for each gold utterance, as the backend labels it."""
    from src.audio_pipeline.pipeline import decode_to_wav
    from src.audio_pipeline.whisper_transcribe import UtteranceSegment

    segments = [
        UtteranceSegment(start=u.start, end=u.end, text=normalize_utterance_text(u.text) if use_text else "")
        for u in recording.utterances
    ]
    backend = make_backend(backend_name, recording.age_months)
    with tempfile.TemporaryDirectory() as tmp:
        wav = recording.audio_path
        if wav.suffix.lower() != ".wav":
            wav = Path(tmp) / "audio.wav"
            decode_to_wav(recording.audio_path, wav)
        labelled = backend.assign(wav, segments)
    return [CHILD if (seg.speaker or "").upper() == CHILD else ADULT for seg in labelled]


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------
def score(gold: list[GoldUtterance], predicted: list[str]) -> dict:
    """Utterance and time-weighted agreement, and the effect on MLU-w and NDW."""
    pairs = list(zip(gold, predicted))
    tp = sum(1 for g, p in pairs if g.role == CHILD and p == CHILD)
    fp = sum(1 for g, p in pairs if g.role == ADULT and p == CHILD)
    fn = sum(1 for g, p in pairs if g.role == CHILD and p == ADULT)
    correct = sum(1 for g, p in pairs if g.role == p)
    seconds = sum(g.end - g.start for g, _ in pairs)
    correct_seconds = sum(g.end - g.start for g, p in pairs if g.role == p)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    gold_measures = _child_measures([g for g in gold if g.role == CHILD])
    pred_measures = _child_measures([g for g, p in pairs if p == CHILD])
    return {
        "utterances": len(pairs),
        "correct": correct,
        "child_utterances_gold": tp + fn,
        "child_utterances_predicted": tp + fp,
        "accuracy": round(correct / len(pairs), 4) if pairs else 0.0,
        "time_weighted_accuracy": round(correct_seconds / seconds, 4) if seconds else 0.0,
        "child_precision": round(precision, 4),
        "child_recall": round(recall, 4),
        "child_f1": round(2 * precision * recall / (precision + recall), 4) if precision + recall else 0.0,
        "adult_called_child": fp,
        "child_called_adult": fn,
        "mlu_gold": gold_measures["mlu"],
        "mlu_predicted": pred_measures["mlu"],
        "ndw_gold": gold_measures["ndw"],
        "ndw_predicted": pred_measures["ndw"],
    }


def _child_measures(utterances: list[GoldUtterance]) -> dict:
    measures = compute_language_sample_measures([analyze_main_tier(u.text) for u in utterances], include_vocd=False)
    return {"mlu": measures.mlu_words, "ndw": measures.freq_types}


def summarize(rows: list[dict]) -> dict:
    """Pooled counts across recordings, plus per-recording measure shifts."""
    if not rows:
        return {}
    tp = sum(r["child_utterances_gold"] - r["child_called_adult"] for r in rows)
    fp = sum(r["adult_called_child"] for r in rows)
    fn = sum(r["child_called_adult"] for r in rows)
    total = sum(r["utterances"] for r in rows)
    correct = sum(r["correct"] for r in rows)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    mlu_shift = [abs(r["mlu_predicted"] - r["mlu_gold"]) for r in rows
                 if r["mlu_predicted"] is not None and r["mlu_gold"] is not None]
    ndw_shift = [abs(r["ndw_predicted"] - r["ndw_gold"]) / r["ndw_gold"] for r in rows if r["ndw_gold"]]
    no_child = sum(1 for r in rows if r["child_utterances_predicted"] == 0)
    return {
        "recordings": len(rows),
        "utterances": total,
        "accuracy": round(correct / total, 4) if total else 0.0,
        "child_precision": round(precision, 4),
        "child_recall": round(recall, 4),
        "child_f1": round(2 * precision * recall / (precision + recall), 4) if precision + recall else 0.0,
        "median_abs_mlu_shift": round(_median(mlu_shift), 3) if mlu_shift else None,
        "median_ndw_shift": round(_median(ndw_shift), 3) if ndw_shift else None,
        "recordings_with_no_child_found": no_child,
    }


def _median(values: list[float]) -> float:
    ordered = sorted(values)
    mid = len(ordered) // 2
    return ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2


def render_markdown(backend: str, use_text: bool, max_minutes: float | None, summary: dict, rows: list[dict], skipped: list[str]) -> str:
    lines = [
        f"# Speaker Attribution: `{backend}`",
        "",
        f"Recordings: {summary.get('recordings', 0)}, utterances: {summary.get('utterances', 0)}. "
        f"Gold utterance spans from the CHAT time bullets; the backend {'also saw each utterance text' if use_text else 'saw audio only'}"
        + (f"; first {max_minutes:g} minutes of each recording." if max_minutes else "."),
        "",
        "| Measure | Value |",
        "|---|---|",
        f"| Utterance accuracy (child vs adult) | {summary.get('accuracy', 0):.1%} |",
        f"| Child precision | {summary.get('child_precision', 0):.1%} |",
        f"| Child recall | {summary.get('child_recall', 0):.1%} |",
        f"| Child F1 | {summary.get('child_f1', 0):.3f} |",
        f"| Median absolute MLU-w shift (predicted vs gold speakers) | {summary.get('median_abs_mlu_shift')} |",
        f"| Median relative NDW shift | {summary.get('median_ndw_shift')} |",
        f"| Recordings where no child speech was found | {summary.get('recordings_with_no_child_found', 0)} |",
        "",
        "## Per recording",
        "",
        "| Recording | Age (m) | Utts | Child gold/pred | Accuracy | Child F1 | MLU gold/pred | NDW gold/pred | Seconds |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['recording']} | {r['age_months'] if r['age_months'] is not None else '-'} | {r['utterances']} | "
            f"{r['child_utterances_gold']}/{r['child_utterances_predicted']} | {r['accuracy']:.1%} | {r['child_f1']:.3f} | "
            f"{_fmt(r['mlu_gold'])}/{_fmt(r['mlu_predicted'])} | {r['ndw_gold']}/{r['ndw_predicted']} | {r['seconds']} |"
        )
    lines += [
        "",
        "## Reading these numbers",
        "",
        "- Speaker attribution only: utterance boundaries and text come from the gold transcript, so ASR "
        "and segmentation errors are not included.",
        "- Child precision is the share of utterances called child that really are the child; recall is the "
        "share of the child's utterances that were found. Low precision adds adult words to the child's "
        "measures; low recall drops the child's words.",
        "- These recordings are English. They test the acoustic part of speaker separation on real child "
        "voices; Thai recordings are needed to test the Thai text rules.",
    ]
    if skipped:
        lines += ["", f"Skipped {len(skipped)} transcript(s): " + "; ".join(skipped[:10]) + (" …" if len(skipped) > 10 else "")]
    return "\n".join(lines) + "\n"


def _fmt(value) -> str:
    return "-" if value is None else f"{value:.2f}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--cha-dir", type=Path, required=True)
    parser.add_argument("--audio-dir", type=Path, required=True)
    parser.add_argument("--backend", choices=BACKENDS, default="embedding")
    parser.add_argument("--text", choices=("gold", "none"), default="gold",
                        help="give the backend each utterance's text, as the ASR draft would")
    parser.add_argument("--max-minutes", type=float, default=10.0, help="only the first N minutes (0 = all)")
    parser.add_argument("--limit", type=int, default=0, help="stop after N recordings (0 = all)")
    parser.add_argument("--report-dir", type=Path, default=PROJECT_ROOT / "reports" / "metrics")
    args = parser.parse_args(argv)

    recordings, skipped = collect_recordings(
        args.cha_dir.expanduser(), args.audio_dir.expanduser(),
        max_minutes=args.max_minutes or None, limit=args.limit or None,
    )
    if not recordings:
        print("No transcript had both timed utterances and matching audio.")
        for reason in skipped[:20]:
            print("  -", reason)
        return 1

    rows: list[dict] = []
    for index, recording in enumerate(recordings, start=1):
        started = time.perf_counter()
        predicted = predict_roles(recording, args.backend, use_text=args.text == "gold")
        row = {
            "recording": recording.cha_path.stem,
            "age_months": round(recording.age_months, 1) if recording.age_months is not None else None,
            **score(recording.utterances, predicted),
            "seconds": round(time.perf_counter() - started, 1),
        }
        rows.append(row)
        print(f"[{index}/{len(recordings)}] {row['recording']}: accuracy {row['accuracy']:.1%}, child F1 {row['child_f1']:.3f}")

    summary = summarize(rows)
    args.report_dir.mkdir(parents=True, exist_ok=True)
    suffix = args.backend if args.text == "gold" else f"{args.backend}_audio_only"
    import csv

    csv_path = args.report_dir / f"speaker_attribution_{suffix}.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    md_path = args.report_dir / f"speaker_attribution_{suffix}.md"
    md_path.write_text(
        render_markdown(args.backend, args.text == "gold", args.max_minutes or None, summary, rows, skipped),
        encoding="utf-8",
    )
    print(f"Overall: accuracy {summary['accuracy']:.1%}, child F1 {summary['child_f1']:.3f}")
    print(f"Wrote {md_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
