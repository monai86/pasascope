"""Evaluate the on-device ASR pipeline against hand-corrected Thai transcripts.

For every recording in ``.local/evaluation/audio_samples/`` that has a gold
transcript ``data/evaluation/gold_transcripts/<same stem>.cha`` this script:

  1. runs the audio pipeline (Whisper -> speaker separation -> CHAT),
  2. saves the draft to ``.local/evaluation/hypothesis_transcripts/<stem>.cha``,
  3. scores the draft against the gold transcript.

Recordings and drafts live under ``.local/`` so audio never enters the
repository; gold transcripts are tracked.

Thai has no spaces between words, so the word error rate is computed on
``tokenize_thai_words`` tokens and the character error rate is reported next to
it. Child-only scores compare the text attributed to ``*CHI`` on each side, so
they include speaker-separation mistakes as well as recognition mistakes.

Outputs:
    reports/metrics/thai_asr_evaluation.csv   one row per sample
    reports/metrics/thai_asr_evaluation.md    summary for the term paper

Usage:
    python scripts/evaluate_thai_asr.py
    python scripts/evaluate_thai_asr.py --score-only   # reuse saved drafts
    python scripts/evaluate_thai_asr.py --text-only    # single-voice samples

``--text-only`` reports recognition accuracy only. Use it for samples where
every turn was spoken by the same voice (for example text-to-speech), because
speaker separation cannot work on them and speaker-dependent figures would be
meaningless.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from statistics import mean

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import jiwer  # noqa: E402

from packages.cha.parser import parse_cha_file  # noqa: E402
from src.clinical_speech.thai_lsa import ThaiClinicalLSA, tokenize_thai_words  # noqa: E402

EVALUATION_DIR = PROJECT_ROOT / "data" / "evaluation"
LOCAL_DIR = PROJECT_ROOT / ".local" / "evaluation"
REPORT_DIR = PROJECT_ROOT / "reports" / "metrics"
AUDIO_SUFFIXES = {".wav", ".mp3", ".m4a", ".mp4", ".webm", ".ogg", ".flac"}
CHILD = "CHI"
SPEAKER_DEPENDENT_COLUMNS = [
    "wer_child",
    "cer_child",
    "gold_child_utterances",
    "hyp_child_utterances",
    "gold_mlu_words",
    "hyp_mlu_words",
    "gold_ttr",
    "hyp_ttr",
    "gold_echolalia_count",
    "hyp_echolalia_count",
]

CSV_COLUMNS = [
    "sample_id",
    "wer_all",
    "cer_all",
    "gold_utterances",
    "hyp_utterances",
    "wer_child",
    "cer_child",
    "gold_child_utterances",
    "hyp_child_utterances",
    "gold_mlu_words",
    "hyp_mlu_words",
    "gold_ttr",
    "hyp_ttr",
    "gold_echolalia_count",
    "hyp_echolalia_count",
    "audio_seconds",
    "processing_seconds",
    "real_time_factor",
]

_NON_TEXT = re.compile(r"[^\wก-๙]+")
_THAI_INNER_SPACE = re.compile(r"(?<=[\u0e00-\u0e7f])\s+(?=[\u0e00-\u0e7f])")


@dataclass(frozen=True)
class Turn:
    speaker: str
    text: str


def turns_from_cha(path: Path) -> list[Turn]:
    transcript = parse_cha_file(path)
    return [
        Turn(speaker=utterance.speaker_code, text=utterance.normalized_text)
        for utterance in transcript.utterances
        if utterance.normalized_text.strip()
    ]


def draft_chat_text(pipeline_result) -> str:
    """Plain CHAT of what the pipeline recognised, exactly as it will be scored."""
    lines = ["@UTF8", "@Begin", "@Languages:\ttha"]
    for segment in pipeline_result.utterances:
        text = " ".join((segment.text or "").split())
        if text:
            lines.append(f"*{(segment.speaker or 'UNK').upper()}:\t{text} .")
    lines.append("@End")
    return "\n".join(lines) + "\n"


def _words(turns: list[Turn]) -> str:
    """Space-separated words. Spaces inside Thai text are removed first, because
    Thai segmentation depends on them and transcribers place them differently."""
    return " ".join(
        token.lower()
        for turn in turns
        for token in tokenize_thai_words(_THAI_INNER_SPACE.sub("", turn.text))
    )


def _characters(turns: list[Turn]) -> str:
    return _NON_TEXT.sub("", "".join(turn.text for turn in turns)).lower()


def _error_rate(measure, reference: str, hypothesis: str) -> float | None:
    """Error rate against the gold text, or None when the gold text is empty."""
    if not reference:
        return None
    return round(measure(reference, hypothesis or " "), 4)


def score_sample(
    sample_id: str,
    gold: list[Turn],
    hypothesis: list[Turn],
    *,
    audio_seconds: float | None = None,
    processing_seconds: float | None = None,
) -> dict:
    gold_child = [turn for turn in gold if turn.speaker == CHILD]
    hyp_child = [turn for turn in hypothesis if turn.speaker == CHILD]
    gold_lsa = ThaiClinicalLSA.analyze_utterances([turn.__dict__ for turn in gold])
    hyp_lsa = ThaiClinicalLSA.analyze_utterances([turn.__dict__ for turn in hypothesis])
    return {
        "sample_id": sample_id,
        "wer_all": _error_rate(jiwer.wer, _words(gold), _words(hypothesis)),
        "cer_all": _error_rate(jiwer.cer, _characters(gold), _characters(hypothesis)),
        "gold_utterances": len(gold),
        "hyp_utterances": len(hypothesis),
        "wer_child": _error_rate(jiwer.wer, _words(gold_child), _words(hyp_child)),
        "cer_child": _error_rate(jiwer.cer, _characters(gold_child), _characters(hyp_child)),
        "gold_child_utterances": len(gold_child),
        "hyp_child_utterances": len(hyp_child),
        "gold_mlu_words": gold_lsa.mlu_words,
        "hyp_mlu_words": hyp_lsa.mlu_words,
        "gold_ttr": gold_lsa.ttr,
        "hyp_ttr": hyp_lsa.ttr,
        "gold_echolalia_count": gold_lsa.echolalia_count,
        "hyp_echolalia_count": hyp_lsa.echolalia_count,
        "audio_seconds": None if audio_seconds is None else round(audio_seconds, 2),
        "processing_seconds": None if processing_seconds is None else round(processing_seconds, 2),
        "real_time_factor": (
            round(processing_seconds / audio_seconds, 2)
            if audio_seconds and processing_seconds is not None
            else None
        ),
    }


def _mean_of(rows: list[dict], key: str) -> float | None:
    values = [row[key] for row in rows if row[key] is not None]
    return round(mean(values), 4) if values else None


def _mean_abs_difference(rows: list[dict], gold_key: str, hyp_key: str) -> float | None:
    rows = [row for row in rows if row[gold_key] is not None and row[hyp_key] is not None]
    return round(mean(abs(row[gold_key] - row[hyp_key]) for row in rows), 4) if rows else None


def aggregate(rows: list[dict]) -> dict:
    return {
        "samples": len(rows),
        "mean_wer_all": _mean_of(rows, "wer_all"),
        "mean_cer_all": _mean_of(rows, "cer_all"),
        "mean_abs_utterance_count_difference": _mean_abs_difference(rows, "gold_utterances", "hyp_utterances"),
        "mean_wer_child": _mean_of(rows, "wer_child"),
        "mean_cer_child": _mean_of(rows, "cer_child"),
        "mean_abs_mlu_words_difference": _mean_abs_difference(rows, "gold_mlu_words", "hyp_mlu_words"),
        "mean_abs_ttr_difference": _mean_abs_difference(rows, "gold_ttr", "hyp_ttr"),
        "mean_abs_echolalia_count_difference": _mean_abs_difference(
            rows, "gold_echolalia_count", "hyp_echolalia_count"
        ),
        "mean_real_time_factor": _mean_of(rows, "real_time_factor"),
    }


def _cell(value) -> str:
    return "-" if value is None else str(value)


def _pair(row: dict, gold_key: str, hyp_key: str) -> str:
    return "-" if row[gold_key] is None else f"{row[gold_key]}/{row[hyp_key]}"


def render_markdown(rows: list[dict], summary: dict, *, model_size: str, strategy: str) -> str:
    lines = [
        "# Thai ASR Evaluation",
        "",
        f"Samples scored: {summary['samples']}. Model: faster-whisper `{model_size}`, "
        f"language strategy `{strategy}`, run on-device.",
        "",
        "Error rates are relative to hand-corrected gold transcripts (lower is better). "
        "Child-only rates compare text attributed to `*CHI`, so they also count "
        "speaker-separation mistakes.",
        "",
        "## Summary",
        "",
        "| Measure | Mean |",
        "|---|---|",
        f"| Word error rate, all speakers | {_cell(summary['mean_wer_all'])} |",
        f"| Character error rate, all speakers | {_cell(summary['mean_cer_all'])} |",
        f"| Absolute utterance-count difference (draft vs gold) | {_cell(summary['mean_abs_utterance_count_difference'])} |",
        f"| Word error rate, child only | {_cell(summary['mean_wer_child'])} |",
        f"| Character error rate, child only | {_cell(summary['mean_cer_child'])} |",
        f"| Absolute MLU-words difference (draft vs gold) | {_cell(summary['mean_abs_mlu_words_difference'])} |",
        f"| Absolute TTR difference (draft vs gold) | {_cell(summary['mean_abs_ttr_difference'])} |",
        f"| Absolute echolalia-count difference | {_cell(summary['mean_abs_echolalia_count_difference'])} |",
        f"| Processing time / audio length | {_cell(summary['mean_real_time_factor'])} |",
        "",
        "## Per sample",
        "",
        "| Sample | WER all | CER all | Utterances (gold/draft) | WER child | CER child | Child utts (gold/draft) | "
        "MLU-w (gold/draft) | TTR (gold/draft) | Echolalia (gold/draft) | RTF |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['sample_id']} | {_cell(row['wer_all'])} | {_cell(row['cer_all'])} | "
            f"{row['gold_utterances']}/{row['hyp_utterances']} | "
            f"{_cell(row['wer_child'])} | {_cell(row['cer_child'])} | "
            f"{_pair(row, 'gold_child_utterances', 'hyp_child_utterances')} | "
            f"{_pair(row, 'gold_mlu_words', 'hyp_mlu_words')} | {_pair(row, 'gold_ttr', 'hyp_ttr')} | "
            f"{_pair(row, 'gold_echolalia_count', 'hyp_echolalia_count')} | {_cell(row['real_time_factor'])} |"
        )
    lines += [
        "",
        "## Reading these numbers",
        "",
        "- This is an engineering check on a small sample set, not clinical validation.",
        "- Results describe the recordings in `data/evaluation/` only; see its README for "
        "how they were produced.",
        "- Feature differences show how far an uncorrected draft would move a measure, "
        "which is why therapist review is required before features are used.",
        "",
    ]
    return "\n".join(lines)


def write_reports(rows: list[dict], summary: dict, report_dir: Path, *, model_size: str, strategy: str) -> tuple[Path, Path]:
    report_dir.mkdir(parents=True, exist_ok=True)
    csv_path = report_dir / "thai_asr_evaluation.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    markdown_path = report_dir / "thai_asr_evaluation.md"
    markdown_path.write_text(
        render_markdown(rows, summary, model_size=model_size, strategy=strategy), encoding="utf-8"
    )
    return csv_path, markdown_path


def find_samples(evaluation_dir: Path, local_dir: Path, *, score_only: bool) -> list[tuple[str, Path | None, Path]]:
    """(sample id, audio path or None, gold path) for every scorable sample."""
    gold_dir = evaluation_dir / "gold_transcripts"
    samples = []
    for gold_path in sorted(gold_dir.glob("*.cha")):
        if score_only:
            samples.append((gold_path.stem, None, gold_path))
            continue
        audio = sorted(
            path
            for path in (local_dir / "audio_samples").glob(f"{gold_path.stem}.*")
            if path.suffix.lower() in AUDIO_SUFFIXES
        )
        if audio:
            samples.append((gold_path.stem, audio[0], gold_path))
        else:
            print(f"[skip] {gold_path.stem}: no recording in audio_samples/")
    return samples


def evaluate(
    evaluation_dir: Path,
    report_dir: Path,
    *,
    model_size: str = "medium",
    strategy: str = "thai",
    score_only: bool = False,
    text_only: bool = False,
    local_dir: Path | None = None,
) -> tuple[list[dict], dict]:
    """``local_dir`` holds recordings and drafts; it defaults to ``evaluation_dir``."""
    local_dir = local_dir or evaluation_dir
    hypothesis_dir = local_dir / "hypothesis_transcripts"
    hypothesis_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for sample_id, audio_path, gold_path in find_samples(evaluation_dir, local_dir, score_only=score_only):
        gold = turns_from_cha(gold_path)
        hypothesis_path = hypothesis_dir / f"{sample_id}.cha"
        audio_seconds = processing_seconds = None
        if score_only:
            if not hypothesis_path.exists():
                print(f"[skip] {sample_id}: no saved draft in hypothesis_transcripts/")
                continue
            hypothesis = turns_from_cha(hypothesis_path)
        else:
            from src.audio_pipeline.pipeline import audio_to_cha

            started = time.perf_counter()
            result = audio_to_cha(audio_path, model_size=model_size, strategy=strategy, validate=False)
            processing_seconds = time.perf_counter() - started
            # Score the saved draft, so --score-only reproduces these numbers.
            hypothesis_path.write_text(draft_chat_text(result), encoding="utf-8")
            hypothesis = turns_from_cha(hypothesis_path)
            profile = result.acoustic_profile
            audio_seconds = profile.duration_sec if profile is not None else result.total_duration_sec
        rows.append(
            score_sample(
                sample_id,
                gold,
                hypothesis,
                audio_seconds=audio_seconds,
                processing_seconds=processing_seconds,
            )
        )
        if text_only:
            rows[-1].update(dict.fromkeys(SPEAKER_DEPENDENT_COLUMNS))
        print(f"[ok] {sample_id}: WER {rows[-1]['wer_all']}  CER {rows[-1]['cer_all']}")
    summary = aggregate(rows)
    if rows:
        csv_path, markdown_path = write_reports(rows, summary, report_dir, model_size=model_size, strategy=strategy)
        print(f"Wrote {csv_path} and {markdown_path}")
    else:
        print("No samples were scored. Add recordings and gold transcripts; see data/evaluation/README.md.")
    return rows, summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--evaluation-dir", type=Path, default=EVALUATION_DIR, help="Holds gold_transcripts/.")
    parser.add_argument(
        "--local-dir",
        type=Path,
        default=None,
        help="Holds audio_samples/ and hypothesis_transcripts/ (default: .local/evaluation).",
    )
    parser.add_argument("--report-dir", type=Path, default=REPORT_DIR)
    parser.add_argument("--model", default="medium", choices=["tiny", "base", "small", "medium", "large-v3"])
    parser.add_argument("--strategy", default="thai", choices=["auto", "thai", "english", "dual_pass", "thai_specialized"])
    parser.add_argument("--score-only", action="store_true", help="Score saved drafts instead of re-running ASR.")
    parser.add_argument(
        "--text-only",
        action="store_true",
        help="Report recognition accuracy only; leave speaker-dependent figures blank.",
    )
    args = parser.parse_args()
    rows, _ = evaluate(
        args.evaluation_dir,
        args.report_dir,
        model_size=args.model,
        strategy=args.strategy,
        score_only=args.score_only,
        text_only=args.text_only,
        local_dir=args.local_dir or (LOCAL_DIR if args.evaluation_dir == EVALUATION_DIR else None),
    )
    return 0 if rows else 1


if __name__ == "__main__":
    sys.exit(main())
