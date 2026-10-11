"""Measure Thai speech-recognition accuracy on a public read-speech sample.

No Thai child-speech dataset is available to this project, so this script uses
FLEURS (Google, CC BY 4.0): short sentences read aloud by adult Thai speakers,
each with a reference transcription. It downloads the first N clips of the
Thai test split, transcribes them with the on-device Whisper models named on
the command line, and reports word and character error rates per model.

Adult read speech is far easier than a young child's spontaneous speech, so
these figures are an upper bound on what to expect in a therapy session.

Outputs:
    reports/metrics/thai_asr_public.csv   one row per clip (ids and scores only)
    reports/metrics/thai_asr_public.md    summary for the term paper

Usage:
    python scripts/evaluate_thai_asr_public.py --clips 60 --models small medium
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import tarfile
import time
import urllib.request
from pathlib import Path
from statistics import mean, median

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import jiwer  # noqa: E402

from scripts.evaluate_thai_asr import Turn, _characters, _error_rate, _words  # noqa: E402

FLEURS_BASE = "https://huggingface.co/datasets/google/fleurs/resolve/main/data/th_th"
DOWNLOAD_DIR = PROJECT_ROOT / ".local" / "evaluation" / "public_thai"
REPORT_DIR = PROJECT_ROOT / "reports" / "metrics"
CSV_COLUMNS = ["model", "clip_id", "reference_words", "wer", "cer", "audio_seconds", "processing_seconds"]


def load_references(tsv_text: str) -> dict[str, str]:
    """Map clip file name to its reference transcription."""
    references = {}
    for line in tsv_text.splitlines():
        fields = line.split("\t")
        if len(fields) >= 3:
            references[fields[1]] = fields[2]
    return references


def download_sample(download_dir: Path, clips: int) -> dict[str, str]:
    """Fetch the reference table and the first ``clips`` recordings of the test split."""
    download_dir.mkdir(parents=True, exist_ok=True)
    tsv_path = download_dir / "test.tsv"
    if not tsv_path.exists():
        with urllib.request.urlopen(f"{FLEURS_BASE}/test.tsv") as response:
            tsv_path.write_bytes(response.read())
    references = load_references(tsv_path.read_text(encoding="utf-8"))
    have = sorted(path.name for path in download_dir.glob("*.wav"))
    if len(have) < clips:
        # The archive is read as a stream and abandoned once enough clips are saved.
        with urllib.request.urlopen(f"{FLEURS_BASE}/audio/test.tar.gz") as response:
            with tarfile.open(fileobj=response, mode="r|gz") as archive:
                saved = 0
                for member in archive:
                    name = Path(member.name).name
                    if not member.isfile() or name not in references:
                        continue
                    (download_dir / name).write_bytes(archive.extractfile(member).read())
                    saved += 1
                    if saved >= clips:
                        break
        have = sorted(path.name for path in download_dir.glob("*.wav"))
    return {name: references[name] for name in have[:clips] if name in references}


def score_clip(clip_id: str, reference: str, hypothesis: str, *, audio_seconds: float, processing_seconds: float) -> dict:
    gold, draft = [Turn("SPK", reference)], [Turn("SPK", hypothesis)]
    return {
        "clip_id": clip_id,
        "reference_words": len(_words(gold).split()),
        "wer": _error_rate(jiwer.wer, _words(gold), _words(draft)),
        "cer": _error_rate(jiwer.cer, _characters(gold), _characters(draft)),
        "audio_seconds": round(audio_seconds, 2),
        "processing_seconds": round(processing_seconds, 2),
    }


def summarize(rows: list[dict]) -> dict:
    audio = sum(row["audio_seconds"] for row in rows)
    return {
        "clips": len(rows),
        "audio_minutes": round(audio / 60, 1),
        "mean_wer": round(mean(row["wer"] for row in rows), 4),
        "median_wer": round(median(row["wer"] for row in rows), 4),
        "mean_cer": round(mean(row["cer"] for row in rows), 4),
        "median_cer": round(median(row["cer"] for row in rows), 4),
        "share_clips_cer_under_10pct": round(mean(row["cer"] < 0.10 for row in rows), 3),
        "real_time_factor": round(sum(row["processing_seconds"] for row in rows) / audio, 2) if audio else None,
    }


def render_markdown(summaries: dict[str, dict]) -> str:
    first = next(iter(summaries.values()))
    lines = [
        "# Thai ASR Accuracy on Public Read Speech",
        "",
        f"Data: first {first['clips']} clips of the FLEURS Thai test split "
        f"({first['audio_minutes']} minutes; adult speakers reading sentences; CC BY 4.0). "
        "Models: faster-whisper, run on-device.",
        "",
        "| Model | WER mean | WER median | CER mean | CER median | Clips with CER under 10% | Processing time / audio length |",
        "|---|---|---|---|---|---|---|",
    ]
    for model, summary in summaries.items():
        lines.append(
            f"| `{model}` | {summary['mean_wer']:.1%} | {summary['median_wer']:.1%} | "
            f"{summary['mean_cer']:.1%} | {summary['median_cer']:.1%} | "
            f"{summary['share_clips_cer_under_10pct']:.0%} | {summary['real_time_factor']} |"
        )
    lines += [
        "",
        "WER is word error rate after Thai word segmentation of both the reference and the "
        "draft; CER is character error rate. A misspelt Thai word usually segments into several "
        "wrong words, so WER is much higher than CER and CER is the steadier measure.",
        "",
        "## Reading these numbers",
        "",
        "- The sentences are formal, with technical terms and foreign names, read by adults in "
        "quiet conditions. Therapy-session speech has simpler vocabulary but younger voices, "
        "background noise and overlapping talk, so these figures do not transfer directly.",
        "- No speaker separation is involved; each clip has one speaker.",
        "- This is the reason every draft transcript must be corrected and attested by the "
        "therapist before features are extracted.",
        "",
    ]
    return "\n".join(lines)


def evaluate(download_dir: Path, report_dir: Path, *, clips: int, models: list[str]) -> tuple[list[dict], dict[str, dict]]:
    import soundfile

    from src.audio_pipeline.whisper_transcribe import WhisperTranscriber

    references = download_sample(download_dir, clips)
    rows: list[dict] = []
    summaries: dict[str, dict] = {}
    for model in models:
        # Drafts are kept next to the downloads so a re-run only re-scores them.
        drafts_path = download_dir / f"drafts_{model}.json"
        drafts = json.loads(drafts_path.read_text(encoding="utf-8")) if drafts_path.exists() else {}
        transcriber = None
        model_rows = []
        for clip_id, reference in references.items():
            path = download_dir / clip_id
            if clip_id not in drafts:
                transcriber = transcriber or WhisperTranscriber(model_size=model, strategy="thai")
                started = time.perf_counter()
                segments = transcriber.transcribe(path)
                drafts[clip_id] = {
                    "text": " ".join(segment.text.strip() for segment in segments),
                    "processing_seconds": time.perf_counter() - started,
                }
                drafts_path.write_text(json.dumps(drafts, ensure_ascii=False), encoding="utf-8")
            model_rows.append(
                {
                    "model": model,
                    **score_clip(
                        Path(clip_id).stem,
                        reference,
                        drafts[clip_id]["text"],
                        audio_seconds=soundfile.info(str(path)).duration,
                        processing_seconds=drafts[clip_id]["processing_seconds"],
                    ),
                }
            )
        summaries[model] = summarize(model_rows)
        rows += model_rows
        print(model, summaries[model], flush=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    with (report_dir / "thai_asr_public.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    (report_dir / "thai_asr_public.md").write_text(render_markdown(summaries), encoding="utf-8")
    return rows, summaries


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--clips", type=int, default=60)
    parser.add_argument(
        "--models", nargs="+", default=["small"], choices=["tiny", "base", "small", "medium", "large-v3"]
    )
    parser.add_argument("--download-dir", type=Path, default=DOWNLOAD_DIR)
    parser.add_argument("--report-dir", type=Path, default=REPORT_DIR)
    args = parser.parse_args()
    evaluate(args.download_dir, args.report_dir, clips=args.clips, models=args.models)
    print(f"Wrote {args.report_dir / 'thai_asr_public.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
