"""Check the product's language-sample measures against CLAN on TalkBank transcripts.

CLAN is the reference tool for CHAT transcripts. For every transcript that has
KIDEVAL output in ``data/reference/english_child_clan_features.csv`` this script
runs the therapist app's own CHAT parser and feature provider on the same file
and compares the child word count, number of different words, type-token ratio
and child utterance count with CLAN's values.

This needs no audio. It measures whether the features shown to therapists are
computed correctly from a transcript, not whether the transcript is correct.

Outputs:
    reports/metrics/feature_agreement_clan.csv   one row per transcript
    reports/metrics/feature_agreement_clan.md    summary for the term paper

Usage:
    python scripts/evaluate_feature_agreement_clan.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
for entry in (PROJECT_ROOT / "apps" / "api", PROJECT_ROOT):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from app.schemas.clinical import Transcript  # noqa: E402
from app.services.cha_service import parse_cha_utterances  # noqa: E402
from app.services.providers.basic_provider import BasicFeatureProvider  # noqa: E402

CLAN_FEATURES = PROJECT_ROOT / "data" / "reference" / "english_child_clan_features.csv"
REPORT_DIR = PROJECT_ROOT / "reports" / "metrics"
MIN_TOKENS_FOR_TTR = 50

# (label, product column, CLAN column)
MEASURES = [
    ("Child word tokens", "system_tokens", "clan_tokens"),
    ("Different words (types)", "system_types", "clan_types"),
    (f"Type-token ratio (samples with >= {MIN_TOKENS_FOR_TTR} tokens)", "system_ttr", "clan_ttr"),
    ("Child utterances", "system_child_utterances", "clan_mlu_utterances"),
]


def product_features(cha_text: str) -> dict:
    transcript = Transcript(
        transcript_id="agreement",
        session_id="agreement",
        case_id="agreement",
        source="imported_chat",
        raw_text="",
        utterances=parse_cha_utterances(cha_text),
    )
    values = {item.name: item.value for item in BasicFeatureProvider().extract_features(transcript).values}
    return {
        "system_tokens": values["total_word_count"],
        "system_types": values["number_of_different_words"],
        "system_ttr": values["type_token_ratio"],
        "system_child_utterances": values["child_utterance_count"],
    }


def build_rows(clan: pd.DataFrame, project_root: Path) -> pd.DataFrame:
    rows = []
    for record in clan.itertuples():
        path = project_root / record.source_path
        if not path.exists():
            continue
        clan_tokens = record.kideval_freq_tokens
        rows.append(
            {
                "transcript_uid": record.transcript_uid,
                "corpus": record.corpus,
                "group": record.group,
                **product_features(path.read_text(encoding="utf-8", errors="replace")),
                "clan_tokens": clan_tokens,
                "clan_types": record.kideval_freq_types,
                "clan_ttr": round(record.kideval_freq_types / clan_tokens, 4) if clan_tokens else None,
                "clan_mlu_utterances": record.kideval_mlu_utts,
            }
        )
    return pd.DataFrame(rows)


def agreement(rows: pd.DataFrame, system: str, clan: str) -> dict:
    pairs = rows[[system, clan]].dropna()
    if system == "system_ttr":
        pairs = pairs[rows.loc[pairs.index, "clan_tokens"] >= MIN_TOKENS_FOR_TTR]
    difference = pairs[system] - pairs[clan]
    relative = (difference.abs() / pairs[clan].where(pairs[clan] != 0)).dropna()
    return {
        "n": len(pairs),
        "pearson_r": round(pairs[system].corr(pairs[clan]), 3),
        "spearman_rho": round(pairs[system].corr(pairs[clan], method="spearman"), 3),
        "mean_difference": round(difference.mean(), 3),
        "median_relative_difference": round(relative.median(), 3),
    }


def summarize(rows: pd.DataFrame) -> list[dict]:
    return [{"measure": label, **agreement(rows, system, clan)} for label, system, clan in MEASURES]


def _table(summary: list[dict]) -> list[str]:
    lines = [
        "| Measure | n | Pearson r | Spearman rho | Mean difference (system - CLAN) | Median relative difference |",
        "|---|---|---|---|---|---|",
    ]
    for row in summary:
        lines.append(
            f"| {row['measure']} | {row['n']} | {row['pearson_r']} | {row['spearman_rho']} | "
            f"{row['mean_difference']} | {row['median_relative_difference']:.1%} |"
        )
    return lines


def render_markdown(rows: pd.DataFrame) -> str:
    asd = rows[rows["group"] == "ASD"]
    groups = ", ".join(f"{name} {count}" for name, count in rows["group"].value_counts().items())
    lines = [
        "# Feature Agreement with CLAN",
        "",
        f"Transcripts: {len(rows)} from {rows['corpus'].nunique()} TalkBank corpora ({groups}). English.",
        "",
        "Each transcript was processed by the therapist app's CHAT parser and feature provider "
        "and compared with CLAN KIDEVAL output for the same file.",
        "",
        "## All transcripts",
        "",
        *_table(summarize(rows)),
        "",
        f"## ASD transcripts only (n = {len(asd)})",
        "",
        *_table(summarize(asd)),
        "",
        "## Reading these numbers",
        "",
        "- High correlation means the app ranks samples the same way CLAN does. A non-zero mean "
        "difference means the two tools count differently, so app values must not be compared "
        "with published CLAN-based norms.",
        "- CLAN's utterance count is the number of utterances it accepts for MLU, which excludes "
        "some utterances the app counts.",
        "- This checks feature computation on English CHAT transcripts. It says nothing about "
        "transcription accuracy or about Thai.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--clan-features", type=Path, default=CLAN_FEATURES)
    parser.add_argument("--report-dir", type=Path, default=REPORT_DIR)
    args = parser.parse_args()
    rows = build_rows(pd.read_csv(args.clan_features), PROJECT_ROOT)
    if rows.empty:
        print("No transcripts with CLAN output were found locally.")
        return 1
    args.report_dir.mkdir(parents=True, exist_ok=True)
    rows.to_csv(args.report_dir / "feature_agreement_clan.csv", index=False)
    (args.report_dir / "feature_agreement_clan.md").write_text(render_markdown(rows), encoding="utf-8")
    for row in summarize(rows):
        print(f"{row['measure']}: r={row['pearson_r']} n={row['n']} median relative difference={row['median_relative_difference']:.1%}")
    print(f"Wrote {args.report_dir / 'feature_agreement_clan.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
