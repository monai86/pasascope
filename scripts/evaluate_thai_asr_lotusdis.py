"""Measure Thai speech-recognition accuracy on conversation the Thai model never saw.

Thonburian Whisper (the app's accurate mode) was fine-tuned on data that include
Common Voice and FLEURS, so the FLEURS figures in ``thai_asr_public.md`` may be
optimistic. This script uses LOTUSDIS instead (NECTEC, CC BY-SA 4.0; Tipaksorn
et al. 2025, arXiv:2509.18722): unscripted three-person Thai conversations,
released in October 2025, after the last update of the Thai model (February
2024). Each utterance was recorded at once by several microphones, so the same
sentences can be scored near the speaker and across the room.

A fixed random sample of test-split utterances is used: one speaker only (no
overlapping talk), 2 to 15 seconds long. Both app modes are scored on the
condenser microphone (12-15 cm from the speaker) and on the JBL device 2 m
away.

Download the four test files first (about 1.5 GB) into ``--data-dir``:
    https://huggingface.co/datasets/nectec/LOTUSDIS/resolve/main/data/test-0000{0,1,2,3}-of-00004.parquet

Outputs:
    reports/metrics/thai_asr_lotusdis.csv   one row per utterance, model and microphone (ids and scores only)
    reports/metrics/thai_asr_lotusdis.md    summary

Usage:
    python scripts/evaluate_thai_asr_lotusdis.py --utterances 200
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import random
import re
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import jiwer  # noqa: E402

from scripts.evaluate_thai_asr import Turn, _characters, _words  # noqa: E402
from scripts.evaluate_thai_asr_public import THAI_SPECIALIZED_MODEL, score_clip, summarize  # noqa: E402

DATA_DIR = PROJECT_ROOT / ".local" / "evaluation" / "lotusdis"
REPORT_DIR = PROJECT_ROOT / "reports" / "metrics"
MICROPHONES = {"con123": "condenser, 12-15 cm", "jbl": "JBL device, 2 m"}
MODELS = {THAI_SPECIALIZED_MODEL: "Accurate (default)", "medium": "Fast"}
SEED = 2026
MIN_SECONDS, MAX_SECONDS = 2.0, 15.0
LATIN = re.compile(r"[A-Za-z]")
CSV_COLUMNS = ["mic", "model", "clip_id", "reference_words", "wer", "cer", "audio_seconds", "processing_seconds"]


def load_test_split(data_dir: Path) -> dict[str, list[dict]]:
    """All test rows, grouped by microphone, in file order (the channels line up row by row)."""
    import pyarrow.parquet as pq

    by_mic: dict[str, list[dict]] = {}
    for path in sorted(data_dir.glob("test-0000*.parquet")):
        table = pq.read_table(path).to_pylist()
        for row in table:
            by_mic.setdefault(row["mic"], []).append(row)
    return by_mic


def eligible(row: dict) -> bool:
    return "&" not in row["speaker_id"] and MIN_SECONDS <= row["duration"] <= MAX_SECONDS and row["sentence"].strip() != ""


def choose_sample(by_mic: dict[str, list[dict]], count: int) -> list[int]:
    reference = by_mic["con123"]
    for mic in MICROPHONES:
        rows = by_mic[mic]
        if len(rows) != len(reference) or any(
            (a["speaker_id"], a["sentence"]) != (b["speaker_id"], b["sentence"]) for a, b in zip(rows, reference)
        ):
            raise SystemExit(f"Channel {mic} does not line up with con123; the sample would not match.")
    indices = [i for i, row in enumerate(reference) if eligible(row)]
    return sorted(random.Random(SEED).sample(indices, count))


def save_audio(row: dict, path: Path) -> None:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        import soundfile

        data, rate = soundfile.read(io.BytesIO(row["audio"]["bytes"]))
        soundfile.write(str(path), data, rate)


def pooled(rows: list[dict], references: dict[str, str], drafts: dict[str, str]) -> tuple[float, float]:
    """Error rates over the whole sample at once (as the LOTUSDIS paper reports WER)."""
    ids = [row["clip_id"] for row in rows]
    gold_words = [_words([Turn("SPK", references[i])]) for i in ids]
    draft_words = [_words([Turn("SPK", drafts[i])]) or " " for i in ids]
    gold_chars = [_characters([Turn("SPK", references[i])]) for i in ids]
    draft_chars = [_characters([Turn("SPK", drafts[i])]) or " " for i in ids]
    return round(jiwer.wer(gold_words, draft_words), 4), round(jiwer.cer(gold_chars, draft_chars), 4)


def evaluate(data_dir: Path, report_dir: Path, *, count: int) -> dict:
    from src.audio_pipeline.whisper_transcribe import WhisperTranscriber

    by_mic = load_test_split(data_dir)
    sample = choose_sample(by_mic, count)
    references = {f"u{i:05d}": by_mic["con123"][i]["sentence"] for i in sample}
    sessions = {by_mic["con123"][i]["speaker_id"] for i in sample}
    all_rows: list[dict] = []
    results: dict = {
        "sample": len(sample),
        "speakers": len(sessions),
        "eligible": sum(eligible(row) for row in by_mic["con123"]),
        "test_utterances": len(by_mic["con123"]),
        "audio_minutes": round(sum(by_mic["con123"][i]["duration"] for i in sample) / 60, 1),
        "by": {},
    }
    for model in MODELS:
        transcriber = None
        for mic in MICROPHONES:
            drafts_path = data_dir / f"drafts_{model}_{mic}.json"
            drafts = json.loads(drafts_path.read_text(encoding="utf-8")) if drafts_path.exists() else {}
            rows = []
            for i in sample:
                clip_id = f"u{i:05d}"
                path = data_dir / "wav" / mic / f"{clip_id}.wav"
                save_audio(by_mic[mic][i], path)
                if clip_id not in drafts:
                    if transcriber is None:
                        transcriber = (
                            WhisperTranscriber(model_size="medium", strategy="thai_specialized")
                            if model == THAI_SPECIALIZED_MODEL
                            else WhisperTranscriber(model_size=model, strategy="thai")
                        )
                    started = time.perf_counter()
                    segments = transcriber.transcribe(path)
                    drafts[clip_id] = {
                        "text": " ".join(segment.text.strip() for segment in segments),
                        "processing_seconds": time.perf_counter() - started,
                    }
                    drafts_path.write_text(json.dumps(drafts, ensure_ascii=False), encoding="utf-8")
                rows.append(
                    {
                        "mic": mic,
                        "model": model,
                        **score_clip(
                            clip_id,
                            references[clip_id],
                            drafts[clip_id]["text"],
                            audio_seconds=by_mic[mic][i]["duration"],
                            processing_seconds=drafts[clip_id]["processing_seconds"],
                        ),
                    }
                )
            summary = summarize(rows)
            texts = {k: v["text"] for k, v in drafts.items()}
            summary["pooled_wer"], summary["pooled_cer"] = pooled(rows, references, texts)
            # LOTUSDIS writes English loanwords in Latin letters ("Cheese"); the models usually write
            # them in Thai ("ชีส"), which scores as an error. Utterances without Latin letters avoid this.
            thai_only = [row for row in rows if not LATIN.search(references[row["clip_id"]])]
            summary["thai_only_utterances"] = len(thai_only)
            summary["pooled_wer_thai_only"], summary["pooled_cer_thai_only"] = pooled(thai_only, references, texts)
            summary["mean_cer_thai_only"] = round(sum(row["cer"] for row in thai_only) / len(thai_only), 4)
            summary["empty_drafts"] = sum(not texts[row["clip_id"]].strip() for row in rows)
            results["by"][f"{model}|{mic}"] = summary
            all_rows += rows
            print(model, mic, summary, flush=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    with (report_dir / "thai_asr_lotusdis.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(all_rows)
    (report_dir / "thai_asr_lotusdis.md").write_text(render_markdown(results), encoding="utf-8")
    return results


def render_markdown(results: dict) -> str:
    lines = [
        "# Thai ASR Accuracy on Unseen Conversation (LOTUSDIS)",
        "",
        f"Data: {results['sample']} utterances drawn at random (seed {SEED}) from the "
        f"{results['eligible']:,} single-speaker utterances of {MIN_SECONDS:g}-{MAX_SECONDS:g} s in the LOTUSDIS test split "
        f"({results['test_utterances']:,} utterances in all; {results['speakers']} adult speakers in the sample; "
        f"{results['audio_minutes']} minutes). LOTUSDIS (NECTEC, CC BY-SA 4.0; Tipaksorn et al., 2025, "
        "arXiv:2509.18722) records unscripted three-person Thai conversations with several microphones at once. "
        "It was released in October 2025, after the last update of the Thai model (February 2024), and is not "
        "among the model's stated training data, so unlike FLEURS it cannot have been seen in training.",
        "",
        "| App mode | Model | Microphone | CER, mean per utterance | CER, pooled | CER, Thai-script utterances (mean / pooled) | WER, mean | WER, pooled | Utterances under 10% CER | Empty drafts | Time / audio length |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for key, summary in results["by"].items():
        model, mic = key.split("|")
        name = "Thonburian Whisper medium" if model == THAI_SPECIALIZED_MODEL else "Whisper medium, multilingual"
        lines.append(
            f"| {MODELS[model]} | {name} | {MICROPHONES[mic]} | {summary['mean_cer']:.1%} | {summary['pooled_cer']:.1%} | "
            f"{summary['mean_cer_thai_only']:.1%} / {summary['pooled_cer_thai_only']:.1%} | {summary['mean_wer']:.1%} | {summary['pooled_wer']:.1%} | "
            f"{summary['share_clips_cer_under_10pct']:.0%} | {summary['empty_drafts']} | {summary['real_time_factor']} |"
        )
    lines += [
        "",
        f"Thai-script utterances: the {next(iter(results['by'].values()))['thai_only_utterances']} utterances whose "
        "reference has no Latin letters. LOTUSDIS writes English loanwords in Latin letters (\"Cheese\"), while the "
        "models usually write them in Thai (\"ชีส\"); that difference is a spelling convention, not a recognition "
        "error, but it counts as one in the pooled rate. Empty drafts are utterances for which the model returned no text.",
        "",
        "The mean per utterance gives each utterance equal weight, as `thai_asr_public.md` does for FLEURS clips, so "
        "the two reports compare directly; pooled rates count all errors over all reference characters (or words). "
        "WER uses the app's Thai word segmentation of both texts; the LOTUSDIS paper used PyThaiNLP newmm, so its "
        "WER figures are close to, but not exactly comparable with, these.",
        "",
        "## Reading these numbers",
        "",
        "- Speakers are adults (19-48 years) in casual conversation with fillers, code-switched English words "
        "and fast turns: harder than FLEURS read speech, closer to a therapy session, but still not children.",
        "- Overlapping talk was left out, and each utterance comes with its boundaries from the corpus, so the "
        "app's own voice detection and speaker separation are not tested here.",
        "- Empty drafts were nearly all short utterances (2-3.5 s; one of the accurate mode's was 5.5 s). Traced on the clips the fast mode left empty: the "
        "model gave a no-speech probability above 0.85, so the app's hallucination filter dropped real speech; one "
        "more was dropped as a decoding loop (a drawn-out \"โอ๊ย\"). Here every clip is transcribed on its own and "
        "padded to Whisper's 30 s window; in a session the same speech sits among other speech, so this rate may not "
        "carry over. Whether short child turns are lost in whole sessions is measured by the end-to-end test.",
        "- Time / audio length is high because each clip costs about the same time whatever its length (Whisper "
        "works in 30 s windows). It does not describe a whole session; see `asr_desktop_tuning.md` for speed.",
        "- For comparison, the LOTUSDIS paper reports zero-shot WER of 39.5% (condenser) and 46.0% (JBL) for the "
        "larger Thonburian Whisper large-v3 model on the whole test split. This sample leaves out overlapping talk "
        "and utterances under 2 s, so lower error rates than the paper's are expected.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--utterances", type=int, default=200)
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR)
    parser.add_argument("--report-dir", type=Path, default=REPORT_DIR)
    args = parser.parse_args()
    evaluate(args.data_dir, args.report_dir, count=args.utterances)
    print(f"Wrote {args.report_dir / 'thai_asr_lotusdis.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
