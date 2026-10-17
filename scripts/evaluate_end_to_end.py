"""How far an uncorrected draft moves the child's measures, end to end.

Each recording goes through the same pipeline as the app: Whisper ASR,
splitting at pauses, child/adult attribution and the CHAT-form draft text.
The child's measures are then computed with the app's CLAN rules twice: from
the gold transcript and from the draft's *CHI lines. The difference is what
a therapist would see if they attested the draft without correcting it.

Only ``--minutes`` of each recording are used, for the draft and the gold
transcript alike, starting just before the first transcribed utterance:
some recordings open with minutes of untranscribed warm-up (ENNI 817 starts
its transcript at 6.5 minutes), which the draft would otherwise transcribe.

Usage:
    python scripts/evaluate_end_to_end.py \\
        --cha-dir .local/evaluation/ellisweismer_media/chat \\
        --audio-dir .local/evaluation/ellisweismer_media \\
        --strategy english --model medium --minutes 5

Outputs: reports/metrics/end_to_end_<name>.{csv,md}; the drafts themselves go
to .local/evaluation/end_to_end_drafts/<name>/ (kept out of git with the media).
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import re
import sys
import tempfile
import time

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from packages.cha.clan_words import analyze_main_tier  # noqa: E402
from packages.features.language_sample import compute_language_sample_measures  # noqa: E402
from scripts.evaluate_speaker_attribution import CHILD, collect_recordings  # noqa: E402

_WORD = re.compile(r"[^\W\d_]+(?:'[^\W\d_]+)?", re.UNICODE)


def measures(texts: list[str]) -> dict:
    m = compute_language_sample_measures([analyze_main_tier(t) for t in texts], include_vocd=False)
    return {"utts": m.mlu_utterances, "words": m.freq_tokens, "mlu": m.mlu_words, "ndw": m.freq_types, "ttr": m.ttr}


def plain_words(texts: list[str]) -> str:
    """Countable words only, for word error rate."""
    return " ".join(w for t in texts for w in analyze_main_tier(t).words)


def letters(text: str) -> str:
    """Text without spaces, for a character error rate that ignores word segmentation (Thai)."""
    return re.sub(r"\s+", "", text)


def cohens_d(a: list[float], b: list[float]) -> float | None:
    """Standardised mean difference a - b with the pooled standard deviation."""
    import statistics
    if len(a) < 2 or len(b) < 2:
        return None
    pooled = (((len(a) - 1) * statistics.variance(a) + (len(b) - 1) * statistics.variance(b)) / (len(a) + len(b) - 2)) ** 0.5
    return (statistics.mean(a) - statistics.mean(b)) / pooled if pooled else None


def group_table(rows: list[dict], groups: list[str]) -> list[str]:
    """Group means from gold and draft, and the effect size between the first two groups."""
    import statistics

    def values(group, key):
        return [r[key] for r in rows if r["group"] == group and r[key] is not None]

    out = ["| Group | Recordings | MLU-w gold | MLU-w draft | NDW gold | NDW draft |", "|---|---|---|---|---|---|"]
    for g in groups:
        cells = [f"{statistics.mean(v):.2f}" if (v := values(g, k)) else "-" for k in ("mlu_gold", "mlu_draft", "ndw_gold", "ndw_draft")]
        out.append(f"| {g} | {sum(1 for r in rows if r['group'] == g)} | " + " | ".join(cells) + " |")
    a, b = groups[:2]
    out += ["", f"Effect size (Cohen's d, {a} minus {b}):", "", "| Measure | From gold | From draft |", "|---|---|---|"]
    for label, key in (("MLU-w", "mlu"), ("NDW", "ndw")):
        dg, dd = cohens_d(values(a, f"{key}_gold"), values(b, f"{key}_gold")), cohens_d(values(a, f"{key}_draft"), values(b, f"{key}_draft"))
        out.append(f"| {label} | {'-' if dg is None else f'{dg:+.2f}'} | {'-' if dd is None else f'{dd:+.2f}'} |")
    return out + [""]


def save_draft(path: Path, start: float, lines: list[tuple[str, str]]) -> None:
    """The draft's main tiers, to read next to the gold transcript."""
    path.parent.mkdir(parents=True, exist_ok=True)
    header = f"@Comment:\tdraft of the audio from {start:.1f} s, before any correction\n"
    path.write_text(header + "".join(f"*{speaker}:\t{text}\n" for speaker, text in lines), encoding="utf-8")


def read_rows(csv_path: Path) -> list[dict]:
    """Rows of an earlier run, with numbers parsed back and empty cells as None."""
    def parse(key, value):
        if key == "group":
            return value.split("/")[0]  # top-level folder, as in a fresh run
        if key == "recording":
            return value
        if value == "":
            return None
        return float(value) if any(c in value for c in ".eE") else int(value)

    with csv_path.open(encoding="utf-8") as handle:
        return [{"group": "", **{k: parse(k, v) for k, v in row.items()}} for row in csv.DictReader(handle)]


LEAD_IN_SECONDS = 2.0
MIN_GROUP_SIZE = 3


def evaluation_window(utterances, minutes: float) -> tuple[float, float]:
    """Start just before the first transcribed utterance and run for ``minutes``."""
    start = max(0.0, min(u.start for u in utterances) - LEAD_IN_SECONDS) if utterances else 0.0
    return start, start + minutes * 60


def run_pipeline(audio: Path, start: float, minutes: float, *, model: str, strategy: str, age: float | None):
    import soundfile

    from src.audio_pipeline.chat_formatter import draft_utterance_text
    from src.audio_pipeline.pipeline import audio_to_cha, decode_to_wav

    with tempfile.TemporaryDirectory() as tmp:
        full = Path(tmp) / "full.wav"
        decode_to_wav(audio, full)
        data, sr = soundfile.read(str(full))
        clip = Path(tmp) / "clip.wav"
        data = data[int(start * sr): int((start + minutes * 60) * sr)]
        soundfile.write(str(clip), data, sr)
        started = time.perf_counter()
        result = audio_to_cha(clip, model_size=model, strategy=strategy, child_age_months=age, validate=False)
        seconds = time.perf_counter() - started
    lines = [((s.speaker or "UNK").upper(), draft_utterance_text(s)) for s in result.utterances if (s.text or "").strip()]
    return lines, seconds, len(data) / sr


def main(argv=None) -> int:
    import jiwer

    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--cha-dir", type=Path, required=True)
    parser.add_argument("--audio-dir", type=Path, required=True)
    parser.add_argument("--minutes", type=float, default=5.0)
    parser.add_argument("--model", default="medium")
    parser.add_argument("--strategy", default="english", choices=["english", "thai", "thai_specialized", "auto"])
    parser.add_argument("--limit", type=int, default=0, help="stop after N recordings (0 = all)")
    parser.add_argument("--name", default="ellisweismer")
    parser.add_argument("--report-dir", type=Path, default=PROJECT_ROOT / "reports" / "metrics")
    parser.add_argument("--report-only", action="store_true", help="rewrite the report from the existing CSV")
    parser.add_argument("--drafts-dir", type=Path, default=PROJECT_ROOT / ".local" / "evaluation" / "end_to_end_drafts")
    args = parser.parse_args(argv)

    csv_path = args.report_dir / f"end_to_end_{args.name}.csv"
    recordings = [] if args.report_only else collect_recordings(args.cha_dir, args.audio_dir, max_minutes=None, limit=args.limit or None)[0]
    rows = read_rows(csv_path) if args.report_only else []
    for index, rec in enumerate(recordings, start=1):
        start, end = evaluation_window(rec.utterances, args.minutes)
        gold = [u for u in rec.utterances if u.start >= start and u.end <= end]
        lines, seconds, audio_seconds = run_pipeline(rec.audio_path, start, args.minutes, model=args.model,
                                                     strategy=args.strategy, age=rec.age_months)
        save_draft(args.drafts_dir / args.name / f"{rec.cha_path.stem}.txt", start, lines)
        gold_child = [u.text for u in gold if u.role == CHILD]
        draft_child = [text for speaker, text in lines if speaker == "CHI"]
        g, d = measures(gold_child), measures(draft_child)
        gold_all, draft_all = plain_words([u.text for u in gold]), plain_words([t for _, t in lines])
        folder = rec.cha_path.parent.relative_to(args.cha_dir).parts[:1]
        row = {
            "recording": rec.cha_path.stem,
            "group": folder[0] if folder else "",
            "start_seconds": round(start, 1),
            "age_months": rec.age_months,
            "wer_all": round(jiwer.wer(gold_all, draft_all or "x"), 4) if gold_all else None,
            "cer_all": round(jiwer.cer(letters(gold_all), letters(draft_all) or "x"), 4) if gold_all else None,
            "wer_child": round(jiwer.wer(plain_words(gold_child), plain_words(draft_child) or "x"), 4) if gold_child else None,
            "utterances_gold": len(gold),
            "utterances_draft": len(lines),
            **{f"{k}_gold": v for k, v in g.items()},
            **{f"{k}_draft": v for k, v in d.items()},
            "real_time_factor": round(seconds / audio_seconds, 2) if audio_seconds else None,
        }
        rows.append(row)
        print(f"[{index}/{len(recordings)}] {row['recording']}: WER {row['wer_all']}, child MLU {g['mlu']} -> {d['mlu']}, "
              f"child utts {g['utts']} -> {d['utts']}", flush=True)

    if not rows:
        print("No recordings."); return 1
    args.report_dir.mkdir(parents=True, exist_ok=True)
    if not args.report_only:
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)

    def mean(key):
        vals = [r[key] for r in rows if r.get(key) is not None]
        return sum(vals) / len(vals) if vals else None

    def mean_abs(a, b, rel=False):
        vals = [abs(r[a] - r[b]) / (r[b] if rel else 1) for r in rows if r[a] is not None and r[b] not in (None, 0)]
        return sum(vals) / len(vals) if vals else None

    def corr(a, b, rank=False):
        import numpy as np
        from scipy.stats import spearmanr
        pairs = [(r[a], r[b]) for r in rows if r[a] is not None and r[b] is not None]
        if len(pairs) < 3:
            return None
        x, y = zip(*pairs)
        return float(spearmanr(x, y)[0]) if rank else float(np.corrcoef(x, y)[0, 1])

    def fmt(value, spec):
        return "-" if value is None else format(value, spec)

    lines = [
        f"# End-to-end Draft Accuracy: {args.name}",
        "",
        f"{len(rows)} recordings, {args.minutes:g} minutes each from just before the first transcribed utterance. Pipeline: faster-whisper `{args.model}`, "
        f"strategy `{args.strategy}`, the app's default child/adult attribution, CHAT-form drafts; measures with "
        "the app's CLAN rules. Nothing was corrected by hand.",
        "",
        "| Measure | Value |",
        "|---|---|",
        f"| Word error rate, all speakers (mean) | {fmt(mean('wer_all'), '.1%')} |",
        f"| Character error rate, all speakers, spaces ignored (mean) | {fmt(mean('cer_all'), '.1%')} |",
        f"| Word error rate, child's words (mean; includes speaker errors) | {fmt(mean('wer_child'), '.1%')} |",
        f"| Child MLU-w, mean absolute difference draft vs gold | {fmt(mean_abs('mlu_draft', 'mlu_gold'), '.2f')} words |",
        f"| Child MLU-w, correlation draft vs gold across recordings (Pearson) | {fmt(corr('mlu_draft', 'mlu_gold'), '.2f')} |",
        f"| Child MLU-w, rank correlation draft vs gold (Spearman) | {fmt(corr('mlu_draft', 'mlu_gold', rank=True), '.2f')} |",
        f"| Child NDW, mean relative difference | {fmt(mean_abs('ndw_draft', 'ndw_gold', rel=True), '.1%')} |",
        f"| Child utterances, mean relative difference | {fmt(mean_abs('utts_draft', 'utts_gold', rel=True), '.1%')} |",
        f"| Processing time / audio length (mean) | {fmt(mean('real_time_factor'), '.2f')} |",
        "",
    ]
    failed = [r["recording"] for r in rows if r["mlu_draft"] is None]
    if failed:
        lines += [f"MLU differences and correlations leave out {len(failed)} recording(s) whose draft has no child "
                  f"utterance: {', '.join(failed)}.", ""]
    groups = sorted({r["group"] for r in rows if r["group"]})
    # Folders are compared only when they look like groups (SLI/TD, LT/TD),
    # not one folder per child as in CRSLP.
    if len(groups) > 1 and all(sum(r["group"] == g for r in rows) >= MIN_GROUP_SIZE for g in groups):
        lines += group_table(rows, groups)
    lines += [
        "| Recording | Group | Age (m) | WER all | WER child | Child utts gold/draft | MLU-w gold/draft | NDW gold/draft |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(f"| {r['recording']} | {r['group'] or '-'} | {r['age_months']:.0f} | {fmt(r['wer_all'], '.1%')} | {fmt(r['wer_child'], '.1%')} | "
                     f"{r['utts_gold']}/{r['utts_draft']} | {r['mlu_gold'] or 0:.2f}/{r['mlu_draft'] or 0:.2f} | "
                     f"{r['ndw_gold']}/{r['ndw_draft']} |")
    lines += [
        "",
        "- The gold transcripts were coded by trained transcribers (retracings, fillers, unintelligible words);",
        "  the draft has only what the pipeline adds automatically.",
        "- This is the draft before therapist review; the app requires review and attestation before analysis.",
    ]
    (args.report_dir / f"end_to_end_{args.name}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {args.report_dir / f'end_to_end_{args.name}.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
