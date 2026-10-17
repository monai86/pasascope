"""Build the numbers the desktop Knowledge page charts, from this repository's own data.

* ``by_age``: child MLU-w, echolalia ratio and question ratio by year of age,
  for typically developing children, late talkers and autistic children in
  toy-play transcripts with 50 or more child utterances
  (data/reference/english_child_reference_features.csv, TalkBank).
  Median and quartiles per group and year, with counts and the corpora used.
* ``screening``: the transcript ASD screening replication
  (reports/metrics/asd_transcript_screening_replication.csv).

Usage:
    python scripts/build_knowledge_data.py
Output: packages/desktop/ui/assets/knowledge_data.json
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FEATURES = PROJECT_ROOT / "data" / "reference" / "english_child_reference_features.csv"
SCREENING = PROJECT_ROOT / "reports" / "metrics" / "asd_transcript_screening_replication.csv"
OUTPUT = PROJECT_ROOT / "packages" / "desktop" / "ui" / "assets" / "knowledge_data.json"
GROUPS = ("TD", "LT", "ASD")
MEASURES = {"mluw": "mlu_words", "echolalia_ratio": "echolalia_ratio", "question_ratio": "question_ratio"}
MIN_UTTERANCES = 50
MIN_PER_YEAR = 8
YEARS = range(2, 9)


def by_age() -> dict:
    rows = [r for r in csv.DictReader(FEATURES.open(encoding="utf-8"))
            if r["task_type"] == "toyplay" and r["group"] in GROUPS and r["age_months"]
            and float(r["child_utterance_count"] or 0) >= MIN_UTTERANCES]
    out = {"groups": {}, "source": "TalkBank toy-play transcripts with 50+ child utterances", "corpora": {}}
    for group in GROUPS:
        members = [r for r in rows if r["group"] == group]
        out["corpora"][group] = sorted({r["corpus"] for r in members})
        series = {name: [] for name in MEASURES.values()}
        for year in YEARS:
            in_year = [r for r in members if int(float(r["age_months"]) // 12) == year]
            if len(in_year) < MIN_PER_YEAR:
                continue
            for column, name in MEASURES.items():
                values = np.array([float(r[column]) for r in in_year if r[column] not in ("", None)])
                q25, median, q75 = np.percentile(values, [25, 50, 75])
                series[name].append({"year": year, "n": int(len(values)), "q25": round(q25, 3),
                                     "median": round(median, 3), "q75": round(q75, 3)})
        out["groups"][group] = series
    return out


def screening() -> list[dict]:
    keep = []
    for row in csv.DictReader(SCREENING.open(encoding="utf-8")):
        keep.append({"check": row["check"], "auc": float(row["auc"]), "children": int(row["children"])})
    return keep


def main() -> int:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps({"by_age": by_age(), "screening": screening()}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Wrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
