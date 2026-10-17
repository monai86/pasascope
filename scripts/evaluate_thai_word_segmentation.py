"""Does the app split Thai into the words a transcriber would?

Thai has no spaces between words, so MLU-w and NDW in Thai depend on the
app's word segmentation (``tokenize_thai_words``, pythainlp newmm). CHAT
transcripts of Thai put a space between words, so each utterance can be
joined back together, segmented by the app, and compared with the
transcriber's words:

* word-boundary precision, recall and F1, and the share of utterances split
  exactly like the transcriber;
* the child's MLU-w per recording, from the transcriber's words and from the
  app's.

CHAT codes, unintelligible words and non-Thai tokens are left out on both
sides.

Usage:
    python scripts/evaluate_thai_word_segmentation.py --cha-dir .local/evaluation/crslp_media/chat
Outputs: reports/metrics/thai_word_segmentation.{md,csv}
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import re
import sys

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from packages.cha.parser import parse_cha_file  # noqa: E402
from src.clinical_speech.thai_lsa import tokenize_thai_words  # noqa: E402

THAI = re.compile(r"[ก-๙]")


def transcriber_words(text: str) -> list[str]:
    """The transcriber's Thai words, without CHAT codes or unintelligible markers."""
    raw = re.sub(r"\x15\d+_\d+\x15", " ", text)
    raw = re.sub(r"\[[^\]]+\]", " ", raw)
    raw = re.sub(r"&[-=+]?\S+", " ", raw)
    raw = re.sub(r"\b(?:xxx|yyy|www)\b", " ", raw)
    raw = re.sub(r"[<>()+/@:^~_]+\S*", " ", raw)
    return [w for w in raw.split() if THAI.search(w) and not re.fullmatch(r"[.,!?;:\"']+", w)]


def boundaries(words: list[str]) -> set[int]:
    cuts, position = set(), 0
    for word in words[:-1]:
        position += len(word)
        cuts.add(position)
    return cuts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cha-dir", type=Path, required=True)
    parser.add_argument("--report-dir", type=Path, default=PROJECT_ROOT / "reports" / "metrics")
    args = parser.parse_args(argv)

    tp = fp = fn = exact = scored = skipped = 0
    rows = []
    for path in sorted(args.cha_dir.rglob("*.cha")):
        parsed = parse_cha_file(path)
        gold_words = app_words = child_utterances = 0
        for utterance in parsed.utterances:
            gold = transcriber_words(utterance.raw_text)
            if not gold:
                continue
            joined = "".join(gold)
            app = [t for t in tokenize_thai_words(joined) if THAI.search(t)]
            if "".join(app) != joined:  # the app dropped or changed characters; boundaries are not comparable
                skipped += 1
                continue
            scored += 1
            exact += gold == app
            gold_cuts, app_cuts = boundaries(gold), boundaries(app)
            tp += len(gold_cuts & app_cuts)
            fp += len(app_cuts - gold_cuts)
            fn += len(gold_cuts - app_cuts)
            if utterance.speaker_code == "CHI":
                child_utterances += 1
                gold_words += len(gold)
                app_words += len(app)
        if child_utterances:
            rows.append({
                "recording": str(path.relative_to(args.cha_dir)), "child_utterances": child_utterances,
                "mlu_w_transcriber": round(gold_words / child_utterances, 3), "mlu_w_app": round(app_words / child_utterances, 3),
            })

    precision, recall = tp / max(tp + fp, 1), tp / max(tp + fn, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-9)
    gold = np.array([r["mlu_w_transcriber"] for r in rows])
    app = np.array([r["mlu_w_app"] for r in rows])
    r = float(np.corrcoef(gold, app)[0, 1]) if len(rows) > 1 else float("nan")

    args.report_dir.mkdir(parents=True, exist_ok=True)
    with (args.report_dir / "thai_word_segmentation.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    lines = [
        "# Thai Word Segmentation against Transcribers",
        "",
        f"Transcripts: `{args.cha_dir}` ({len(rows)} recordings, {scored} utterances scored, {skipped} left out",
        "because the segmenter changed their characters). Each utterance's transcriber words were joined",
        "and segmented again by the app (`tokenize_thai_words`, pythainlp newmm).",
        "",
        "| Measure | Value |",
        "|---|---|",
        f"| Utterances split exactly like the transcriber | {exact / max(scored, 1):.1%} |",
        f"| Word-boundary precision | {precision:.3f} |",
        f"| Word-boundary recall | {recall:.3f} |",
        f"| Word-boundary F1 | {f1:.3f} |",
        f"| Child MLU-w, transcriber / app (mean over recordings) | {gold.mean():.2f} / {app.mean():.2f} |",
        f"| Child MLU-w, mean absolute difference | {np.abs(gold - app).mean():.2f} words |",
        f"| Child MLU-w, correlation across recordings (Pearson) | {r:.3f} |",
        "",
        "| Recording | Child utterances | MLU-w transcriber | MLU-w app |",
        "|---|---|---|---|",
    ] + [f"| {x['recording']} | {x['child_utterances']} | {x['mlu_w_transcriber']:.2f} | {x['mlu_w_app']:.2f} |" for x in rows] + [
        "",
        "- One corpus and one transcription convention; another team may split compounds differently.",
        "- Toddler speech is mostly one- and two-word utterances, so few boundaries per utterance are at",
        "  stake. Longer utterances from older children have more.",
    ]
    (args.report_dir / "thai_word_segmentation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"F1 {f1:.3f}; MLU-w {gold.mean():.2f} vs {app.mean():.2f}, r {r:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
