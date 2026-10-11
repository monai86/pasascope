"""Check the Thai echolalia cue against hand-labelled adult/child turn pairs.

``data/evaluation/echolalia_labelled_pairs.csv`` holds scripted Thai turn pairs
written for this project: echoes of several kinds (verbatim, polite particle
added or dropped, the end of the adult's utterance, a short fragment) and
ordinary replies, including replies that naturally reuse the adult's words.
The cue rule (``detect_echolalia`` in ``src/clinical_speech/thai_lsa.py``) is
run on each pair and compared with the label.

The pairs were written by the developer, not sampled from real sessions, so the
result shows which kinds of turn the rule handles, not how often it is right in
practice.

Output:
    reports/metrics/echolalia_cue_check.md

Usage:
    python scripts/evaluate_echolalia_cue.py
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.clinical_speech.thai_lsa import detect_echolalia  # noqa: E402

PAIRS_PATH = PROJECT_ROOT / "data" / "evaluation" / "echolalia_labelled_pairs.csv"
REPORT_PATH = PROJECT_ROOT / "reports" / "metrics" / "echolalia_cue_check.md"


def load_pairs(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [{**row, "is_echo": row["is_echo"] == "1"} for row in csv.DictReader(handle)]


def classify(pairs: list[dict]) -> list[dict]:
    return [
        {**pair, "flagged": detect_echolalia(pair["adult_text"], pair["child_text"])[0] is not None}
        for pair in pairs
    ]


def summarize(results: list[dict]) -> dict:
    true_positive = sum(r["is_echo"] and r["flagged"] for r in results)
    false_positive = sum(not r["is_echo"] and r["flagged"] for r in results)
    false_negative = sum(r["is_echo"] and not r["flagged"] for r in results)
    true_negative = sum(not r["is_echo"] and not r["flagged"] for r in results)
    flagged = true_positive + false_positive
    echoes = true_positive + false_negative
    return {
        "pairs": len(results),
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "true_negative": true_negative,
        "recall": round(true_positive / echoes, 3) if echoes else None,
        "precision": round(true_positive / flagged, 3) if flagged else None,
    }


def by_category(results: list[dict]) -> list[dict]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for result in results:
        groups[result["category"]].append(result)
    return [
        {
            "category": category,
            "is_echo": rows[0]["is_echo"],
            "pairs": len(rows),
            "flagged": sum(row["flagged"] for row in rows),
        }
        for category, rows in groups.items()
    ]


def render_markdown(results: list[dict]) -> str:
    summary = summarize(results)
    lines = [
        "# Thai Echolalia Cue Check",
        "",
        f"{summary['pairs']} scripted adult/child turn pairs, labelled by hand as echo or not.",
        "",
        "| | Flagged by the rule | Not flagged |",
        "|---|---|---|",
        f"| Labelled echo | {summary['true_positive']} | {summary['false_negative']} |",
        f"| Labelled not echo | {summary['false_positive']} | {summary['true_negative']} |",
        "",
        f"Recall {summary['recall']:.0%}, precision {summary['precision']:.0%}.",
        "",
        "## By kind of turn",
        "",
        "| Kind | Labelled | Pairs | Flagged |",
        "|---|---|---|---|",
    ]
    for row in by_category(results):
        lines.append(
            f"| {row['category']} | {'echo' if row['is_echo'] else 'not echo'} | {row['pairs']} | {row['flagged']} |"
        )
    wrong = [r for r in results if r["is_echo"] != r["flagged"]]
    if wrong:
        lines += ["", "## Pairs the rule got wrong", "", "| Pair | Kind | Adult | Child | Rule said |", "|---|---|---|---|---|"]
        for r in wrong:
            lines.append(
                f"| {r['pair_id']} | {r['category']} | {r['adult_text']} | {r['child_text']} | "
                f"{'echo' if r['flagged'] else 'not echo'} |"
            )
    lines += [
        "",
        "## Reading these numbers",
        "",
        "- The pairs were written for this check; they are not a sample of real sessions, so "
        "these rates do not estimate accuracy in practice.",
        "- The rule sees one adult turn and the child's next turn. It cannot judge whether an "
        "echo is functional, and it does not detect delayed echolalia.",
        "- Each flagged turn is shown to the therapist as a cue to confirm or dismiss.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--pairs", type=Path, default=PAIRS_PATH)
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    args = parser.parse_args()
    results = classify(load_pairs(args.pairs))
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(render_markdown(results), encoding="utf-8")
    print(summarize(results))
    print(f"Wrote {args.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
