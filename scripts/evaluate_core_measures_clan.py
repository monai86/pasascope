"""Compare the app's main language-sample measures with CLAN, run fresh on each transcript.

``evaluate_feature_agreement_clan.py`` compares counts with KIDEVAL values stored
in ``data/reference``. This script runs CLAN itself (UnixCLAN ``kideval`` and
``freq +b50``) on every transcript listed there, so it can also check the
measures the desktop app leads with:

* MLU-w and MLU50-w (KIDEVAL ``MLU_Words``, ``MLU50_Words``)
* NDW-100 (KIDEVAL ``NDW_100``)
* MATTR-50 (FREQ ``+b50``, on %mor lemmas like the app when the transcript has them)
* VOCD-D, different words, word tokens and MLU utterances (KIDEVAL)

For each measure it reports the share of identical values, the intraclass
correlation for absolute agreement (ICC(A,1), two raters: app and CLAN) and the
Bland-Altman mean difference with 95% limits of agreement. CLAN's outputs are
cached under ``.local/evaluation/clan_core`` so a re-run only redoes the app side.

No audio is involved: this checks how measures are computed from a transcript,
not whether the transcript is right.

Outputs:
    reports/metrics/core_measures_clan.csv   one row per transcript
    reports/metrics/core_measures_clan.md    summary for the term paper

Usage:
    python scripts/evaluate_core_measures_clan.py --clan-bin-dir ~/Downloads/talkbank/tools/unix-clan/unix-clan/unix/bin
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
import re
import subprocess
import sys
import tempfile

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
for entry in (PROJECT_ROOT / "apps" / "api", PROJECT_ROOT):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from app.schemas.clinical import Transcript  # noqa: E402
from app.services.cha_service import parse_cha_utterances  # noqa: E402
from app.services.providers.basic_provider import BasicFeatureProvider  # noqa: E402
from scripts.parse_clan_kideval import parse_kideval_xml_spreadsheet  # noqa: E402

TRANSCRIPTS = PROJECT_ROOT / "data" / "reference" / "english_child_clan_features.csv"
CACHE = PROJECT_ROOT / ".local" / "evaluation" / "clan_core"
REPORT_DIR = PROJECT_ROOT / "reports" / "metrics"
MATTR_LINE = re.compile(r"^\s*([0-9.]+)\s+MATTR\s*$", re.MULTILINE)

# (label, app feature, CLAN column, decimals used to call two values the same)
MEASURES = [
    ("MLU-w (words per utterance)", "mean_length_of_utterance_words", "clan_mlu_words", 2),
    ("MLU50-w (first 50 utterances)", "mlu50_words", "clan_mlu50_words", 2),
    ("NDW-100 (different words in 100 tokens)", "ndw_100", "clan_ndw_100", 0),
    ("MATTR-50 (moving-average TTR)", "mattr_50", "clan_mattr_50", 2),
    ("VOCD-D", "vocd_d", "clan_vocd", None),
    ("Different words (types)", "number_of_different_words", "clan_types", 0),
    ("Child word tokens", "total_word_count", "clan_tokens", 0),
    ("MLU utterances", "mlu_utterance_count", "clan_mlu_utts", 0),
]


def _number(value: object) -> float | None:
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return number if np.isfinite(number) else None


def run_clan(bin_dir: Path, uid: str, cha: Path) -> dict:
    """KIDEVAL and FREQ +b50 for one transcript, from the cache when present."""
    CACHE.mkdir(parents=True, exist_ok=True)
    kideval_out, freq_out = CACHE / f"{uid}.kideval.xls", CACHE / f"{uid}.freq.txt"
    if not kideval_out.is_file():
        with tempfile.TemporaryDirectory() as work, cha.open("rb") as source:
            subprocess.run([str(bin_dir / "kideval"), "+t*CHI", "+leng"], stdin=source, cwd=work,
                           capture_output=True, timeout=300)
            produced = Path(work) / "pipeout.kideval.xls"
            if produced.is_file():
                produced.replace(kideval_out)
    if not freq_out.is_file():
        # Like the app: %mor lemmas when the transcript has them, word forms otherwise.
        for options in (["+t%mor", "-t*", "+sm;*,o%"], []):
            with cha.open("rb") as source:
                result = subprocess.run([str(bin_dir / "freq"), "+t*CHI", *options, "+b50"], stdin=source,
                                        capture_output=True, timeout=300)
            if MATTR_LINE.search(result.stdout.decode("utf-8", errors="replace")):
                break
        freq_out.write_bytes(result.stdout)

    values: dict = {}
    if kideval_out.is_file():
        rows = parse_kideval_xml_spreadsheet(kideval_out.read_text(encoding="utf-8", errors="replace")).rows
        if rows:
            row = rows[0]
            values = {
                "clan_mlu_words": _number(row.get("MLU_Words")),
                "clan_mlu50_words": _number(row.get("MLU50_Words")),
                "clan_ndw_100": _number(row.get("NDW_100")),
                "clan_vocd": _number(row.get("VOCD_D_optimum_average")),
                "clan_types": _number(row.get("FREQ_types")),
                "clan_tokens": _number(row.get("FREQ_tokens")),
                "clan_mlu_utts": _number(row.get("MLU_Utts")),
            }
    match = MATTR_LINE.search(freq_out.read_text(encoding="utf-8", errors="replace"))
    values["clan_mattr_50"] = float(match.group(1)) if match else None
    return values


def app_measures(cha_text: str) -> dict:
    transcript = Transcript(
        transcript_id="agreement", session_id="agreement", case_id="agreement",
        source="imported_chat", raw_text="", utterances=parse_cha_utterances(cha_text),
    )
    values = {item.name: item.value for item in BasicFeatureProvider().extract_features(transcript).values}
    return {feature: values.get(feature) for _, feature, _, _ in MEASURES}


def icc_absolute(a: np.ndarray, b: np.ndarray) -> float:
    """ICC(A,1): two-way random effects, absolute agreement, single rater (McGraw & Wong 1996)."""
    data = np.column_stack([a, b]).astype(float)
    n, k = data.shape
    grand = data.mean()
    ss_rows = k * ((data.mean(axis=1) - grand) ** 2).sum()
    ss_cols = n * ((data.mean(axis=0) - grand) ** 2).sum()
    ss_error = ((data - grand) ** 2).sum() - ss_rows - ss_cols
    ms_rows, ms_cols = ss_rows / (n - 1), ss_cols / (k - 1)
    ms_error = ss_error / ((n - 1) * (k - 1))
    denominator = ms_rows + (k - 1) * ms_error + k * (ms_cols - ms_error) / n
    return float((ms_rows - ms_error) / denominator) if denominator else float("nan")


def agreement(rows: pd.DataFrame, feature: str, clan: str, decimals: int | None) -> dict:
    pairs = rows[[feature, clan]].apply(pd.to_numeric, errors="coerce").dropna()
    if len(pairs) < 3:
        return {"n": len(pairs)}
    app, ref = pairs[feature].to_numpy(), pairs[clan].to_numpy()
    difference = app - ref
    sd = difference.std(ddof=1)
    same = None if decimals is None else float((np.round(app, decimals) == np.round(ref, decimals)).mean())
    return {
        "n": len(pairs),
        "same": same,
        "icc": round(icc_absolute(app, ref), 4),
        "pearson": round(float(np.corrcoef(app, ref)[0, 1]), 4),
        "mean_difference": round(float(difference.mean()), 3),
        "loa_low": round(float(difference.mean() - 1.96 * sd), 3),
        "loa_high": round(float(difference.mean() + 1.96 * sd), 3),
        "clan_mean": round(float(ref.mean()), 2),
    }


def table(rows: pd.DataFrame) -> list[str]:
    lines = [
        "| Measure | n | Same value | ICC(A,1) | Pearson r | Mean difference (app − CLAN) | 95% limits of agreement | CLAN mean |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for label, feature, clan, decimals in MEASURES:
        stats = agreement(rows, feature, clan, decimals)
        if stats["n"] < 3:
            lines.append(f"| {label} | {stats['n']} | | | | | | |")
            continue
        same = "n/a" if stats["same"] is None else f"{stats['same']:.1%}"
        lines.append(
            f"| {label} | {stats['n']} | {same} | {stats['icc']:.4f} | {stats['pearson']:.4f} | "
            f"{stats['mean_difference']:+.3f} | {stats['loa_low']:+.3f} to {stats['loa_high']:+.3f} | {stats['clan_mean']} |"
        )
    return lines


def render(rows: pd.DataFrame) -> str:
    provider = BasicFeatureProvider()
    groups = ", ".join(f"{name} {count}" for name, count in rows["group"].value_counts().items())
    asd = rows[rows["group"] == "ASD"]
    return "\n".join([
        "# Main Measures Compared with CLAN",
        "",
        f"Run on {date.today():%Y-%m-%d}. Transcripts: {len(rows)} English child transcripts from "
        f"{rows['corpus'].nunique()} TalkBank corpora ({groups}).",
        "",
        f"App: {provider.provider_name} {provider.provider_version}, schema {provider.feature_schema_version}, "
        "the code the desktop app runs. CLAN: UnixCLAN `kideval +t*CHI +leng` and `freq +t*CHI +b50` "
        "(on %mor lemmas when present, as the app counts), "
        "run on the same files by `scripts/evaluate_core_measures_clan.py`.",
        "",
        "## All transcripts",
        "",
        *table(rows),
        "",
        f"## ASD transcripts only (n = {len(asd)})",
        "",
        *table(asd),
        "",
        "## Reading these numbers",
        "",
        "- **Same value**: the app and CLAN give the identical number (MLU-w, MLU50-w and MATTR-50 rounded "
        "to two decimals, counts exactly). VOCD-D samples words at random in both tools, so it is "
        "compared only by agreement statistics.",
        "- **ICC(A,1)** measures absolute agreement, not just ranking: 1.0 means the two tools give the same "
        "values. Above 0.90 is conventionally excellent (Koo & Li, 2016).",
        "- **Limits of agreement** (Bland & Altman, 1986): 95% of transcripts differ from CLAN by an amount "
        "inside this range.",
        "- These are English transcripts. For Thai the app splits words with PyThaiNLP, where CLAN has no "
        "Thai word rules, so there is no CLAN reference to compare with.",
        "- This checks measures computed from a transcript. Transcription accuracy is reported separately.",
        "",
    ])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--clan-bin-dir", type=Path, required=True, help="UnixCLAN unix/bin folder")
    parser.add_argument("--transcripts", type=Path, default=TRANSCRIPTS)
    parser.add_argument("--report-dir", type=Path, default=REPORT_DIR)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    listing = pd.read_csv(args.transcripts)
    listing = listing[[(PROJECT_ROOT / p).is_file() for p in listing.source_path]]
    if args.limit:
        listing = listing.head(args.limit)

    def one(record) -> dict:
        path = PROJECT_ROOT / record.source_path
        return {
            "transcript_uid": record.transcript_uid, "corpus": record.corpus, "group": record.group,
            **app_measures(path.read_text(encoding="utf-8", errors="replace")),
            **run_clan(args.clan_bin_dir.expanduser(), record.transcript_uid, path),
        }

    with ThreadPoolExecutor(args.workers) as pool:
        rows = pd.DataFrame(list(pool.map(one, listing.itertuples())))
    args.report_dir.mkdir(parents=True, exist_ok=True)
    rows.to_csv(args.report_dir / "core_measures_clan.csv", index=False)
    (args.report_dir / "core_measures_clan.md").write_text(render(rows), encoding="utf-8")
    print(render(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
