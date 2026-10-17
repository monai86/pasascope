"""Check the turn-taking measures on TalkBank toy-play transcripts before the app shows them.

Runs the therapist app's own CHAT parser and feature provider (features-basic-v3)
on the toy-play transcripts of typically developing children (TD), late talkers
(LT) and autistic children (ASD) with 50 or more child utterances, the same
selection as the Knowledge page's age charts, and reports for each measure:

* the median and quartiles by group and year of age;
* how it changes with age within each group (Spearman rho);
* whether it differs between groups within each year of age where both
  groups have 8 or more children (Mann-Whitney U).

What a measure needs to be worth showing: it is computable on almost every
sample, it moves with age in typical development the way the literature
expects, and it is not just a copy of MLU. A group difference is reported but
is not the point: the app describes a child's sample and does not classify.

Outputs:
    reports/metrics/turn_taking_reference.csv   one row per transcript
    reports/metrics/turn_taking_reference.md    summary

Usage:
    python scripts/evaluate_turn_taking.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

PROJECT_ROOT = Path(__file__).resolve().parent.parent
for entry in (PROJECT_ROOT / "apps" / "api", PROJECT_ROOT):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from app.schemas.clinical import Transcript  # noqa: E402
from app.services.cha_service import parse_cha_utterances  # noqa: E402
from app.services.providers.basic_provider import BasicFeatureProvider  # noqa: E402

REFERENCE = PROJECT_ROOT / "data" / "reference" / "english_child_reference_features.csv"
REPORT_DIR = PROJECT_ROOT / "reports" / "metrics"
GROUPS = ("TD", "LT", "ASD")
MEASURES = {
    "child_response_count": "Child responses to adults",
    "child_response_rate": "Child response rate",
    "mlt_ratio": "Turn length ratio (child / adult)",
}
MIN_UTTERANCES = 50
MIN_PER_YEAR = 8


def measures(path: Path) -> dict | None:
    text = path.read_text(encoding="utf-8", errors="replace")
    transcript = Transcript(
        transcript_id="turns", session_id="turns", case_id="turns", source="imported_chat",
        raw_text="", utterances=parse_cha_utterances(text),
    )
    values = {v.name: v.value for v in BasicFeatureProvider().extract_features(transcript).values}
    return {name: values.get(name) for name in (*MEASURES, "mean_length_of_utterance_words", "child_utterance_count")}


def build_rows() -> pd.DataFrame:
    reference = pd.read_csv(REFERENCE)
    chosen = reference[
        (reference["task_type"] == "toyplay") & reference["group"].isin(GROUPS)
        & reference["age_months"].notna() & (reference["child_utterance_count"] >= MIN_UTTERANCES)
    ]
    rows = []
    for _, row in chosen.iterrows():
        path = PROJECT_ROOT / str(row["curated_path"])
        if not path.is_file():
            path = PROJECT_ROOT / str(row["source_path"])
        if not path.is_file():
            continue
        values = measures(path)
        rows.append({"corpus": row["corpus"], "group": row["group"], "age_months": float(row["age_months"]),
                     "path": str(path.relative_to(PROJECT_ROOT)), **values})
    frame = pd.DataFrame(rows)
    frame["year"] = (frame["age_months"] // 12).astype(int)
    return frame


def summarise(frame: pd.DataFrame) -> str:
    lines = [
        "# Turn-taking Measures on TalkBank Toy-play Transcripts",
        "",
        f"Transcripts: {len(frame)} with {MIN_UTTERANCES}+ child utterances "
        f"({', '.join(f'{g} {int((frame.group == g).sum())}' for g in GROUPS)}), corpora: "
        f"{', '.join(sorted(frame.corpus.unique()))}. Computed by the app's feature provider (features-basic-v3).",
        "",
    ]
    for name, title in MEASURES.items():
        values = frame[name].astype(float)
        lines += [f"## {title}", "", f"Computed on {values.notna().mean():.0%} of transcripts.", ""]
        lines += ["| Group | " + " | ".join(f"{y} y" for y in range(2, 9)) + " | Age, Spearman rho (p) |",
                  "|---|" + "---|" * 7 + "---|"]
        for group in GROUPS:
            part = frame[frame.group == group]
            cells = []
            for year in range(2, 9):
                v = part[part.year == year][name].dropna().astype(float)
                cells.append(f"{v.median():.2f} ({len(v)})" if len(v) >= MIN_PER_YEAR else "")
            ok = part[[name, "age_months"]].dropna()
            rho, p = stats.spearmanr(ok["age_months"], ok[name]) if len(ok) > 5 else (np.nan, np.nan)
            lines.append(f"| {group} | " + " | ".join(cells) + f" | {rho:+.2f} ({p:.3f}) |")
        lines.append("")
        for other in ("LT", "ASD"):
            parts = []
            for year in range(2, 9):
                td = frame[(frame.group == "TD") & (frame.year == year)][name].dropna().astype(float)
                ot = frame[(frame.group == other) & (frame.year == year)][name].dropna().astype(float)
                if len(td) >= MIN_PER_YEAR and len(ot) >= MIN_PER_YEAR:
                    p = stats.mannwhitneyu(ot, td, alternative="two-sided").pvalue
                    parts.append(f"{year} y: {ot.median():.2f} vs {td.median():.2f} (p = {p:.2g})")
            if parts:
                lines.append(f"- {other} vs TD, same year of age: " + "; ".join(parts) + ".")
        mlu = frame[[name, "mean_length_of_utterance_words"]].dropna().astype(float)
        r = stats.spearmanr(mlu[name], mlu["mean_length_of_utterance_words"])[0]
        lines += [f"- Spearman rho with MLU-w across all transcripts: {r:+.2f}.", ""]
    lines += [
        "## Reading these numbers",
        "",
        "- Medians are pooled over corpora that recorded play differently (examiner or parent, length, task),",
        "  so a group difference can come from the corpus as much as from the children.",
        "- The app shows these measures as a description of one sample and for change across a child's",
        "  sessions. It gives no norm and makes no group call.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    frame = build_rows()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    frame.to_csv(REPORT_DIR / "turn_taking_reference.csv", index=False)
    (REPORT_DIR / "turn_taking_reference.md").write_text(summarise(frame), encoding="utf-8")
    print((REPORT_DIR / "turn_taking_reference.md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
