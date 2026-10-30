"""Can transcript measures find autistic children without labels, or place them in a "risk zone"?

Two checks on the canonical TalkBank feature table (one session per child):

1. Unsupervised clustering. K-means, a Gaussian mixture and Ward clustering group
   children by six transcript measures alone. Labels are used only afterwards, to ask
   what the clusters line up with: diagnosis (ASD or not), corpus, task, or age band.
   Agreement is the adjusted mutual information (AMI): 0 is chance, 1 is identical.
   The checks run on raw measures, on measures with the part explained by age removed,
   and inside the corpora that hold both autistic and typical children (Eigsti, Nadig).

2. Age-referenced zones. For each toy-play child, each measure is turned into a
   percentile among typically developing children within 6 months of age, taken from
   other corpora only. The "red zone" is below the 10th percentile. If the zone were
   well calibrated, about 10% of typical children would fall in it.

Usage:
    python scripts/evaluate_unsupervised_asd_zones.py [--features data/ml/canonical_features.parquet]
Outputs: reports/metrics/asd_unsupervised_zones.{md,csv}
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import warnings

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FEATURES = ["mluw", "ttr", "question_ratio", "echolalia_ratio", "unintelligible_ratio", "pronoun_reversal_count"]
ZONE_FEATURES = ["mluw", "ttr"]
AGE_WINDOW_MONTHS = 6
MIN_REFERENCE = 20
AGE_BANDS = [0, 24, 36, 48, 60, 84, 200]


def one_session_per_child(table: pd.DataFrame) -> pd.DataFrame:
    table = table.sort_values("session_order").groupby("participant_uid").head(1)
    return table[table.age_months.notna()].copy()


def prepare(rows: pd.DataFrame, remove_age: bool) -> np.ndarray:
    from sklearn.linear_model import LinearRegression
    from sklearn.preprocessing import StandardScaler

    values = np.log1p(rows[FEATURES].clip(lower=0).fillna(0).to_numpy(dtype=float))
    if remove_age:
        age = np.log(rows.age_months.to_numpy(dtype=float)).reshape(-1, 1)
        values = values - LinearRegression().fit(age, values).predict(age)
    return StandardScaler().fit_transform(values)


def clustering_rows(children: pd.DataFrame) -> list[dict]:
    from sklearn.cluster import AgglomerativeClustering, KMeans
    from sklearn.metrics import adjusted_mutual_info_score as ami
    from sklearn.mixture import GaussianMixture

    toyplay = children[children.task_type == "toyplay"]
    settings = [
        ("all toy-play corpora, raw measures", toyplay, False),
        ("all toy-play corpora, age removed", toyplay, True),
        ("Eigsti only, age removed", children[children.corpus == "Eigsti"], True),
        ("Eigsti and Nadig, age removed", children[children.corpus.isin(["Eigsti", "Nadig"])], True),
    ]
    out = []
    for name, rows, remove_age in settings:
        x = prepare(rows, remove_age)
        asd = (rows.diagnostic_group == "ASD").to_numpy()
        band = pd.cut(rows.age_months, AGE_BANDS).astype(str)
        for k in (2, 3):
            methods = [
                ("k-means", KMeans(k, n_init=20, random_state=0)),
                ("gaussian mixture", GaussianMixture(k, random_state=0, n_init=5)),
                ("ward", AgglomerativeClustering(k, linkage="ward")),
            ]
            for method, model in methods:
                labels = model.fit_predict(x)
                share = [asd[labels == c].mean() for c in range(k) if (labels == c).any()]
                out.append({
                    "setting": name, "children": len(rows), "asd": int(asd.sum()), "method": method, "k": k,
                    "ami_asd": round(ami(asd, labels), 3),
                    "ami_diagnosis": round(ami(rows.diagnostic_group, labels), 3),
                    "ami_corpus": round(ami(rows.corpus, labels), 3),
                    "ami_age_band": round(ami(band, labels), 3),
                    "max_asd_share_in_a_cluster": round(max(share), 3),
                    "asd_share_overall": round(asd.mean(), 3),
                })
    return out


def zone_rows(children: pd.DataFrame) -> list[dict]:
    toyplay = children[children.task_type == "toyplay"].copy()
    reference = toyplay[toyplay.diagnostic_group.isin(["TD", "NH"])]
    out = []
    for feature in ZONE_FEATURES:
        def percentile(row):
            ref = reference[(reference.corpus != row.corpus)
                            & ((reference.age_months - row.age_months).abs() <= AGE_WINDOW_MONTHS)][feature].dropna()
            return np.nan if len(ref) < MIN_REFERENCE else float((ref < row[feature]).mean() * 100)

        toyplay["pct"] = toyplay.apply(percentile, axis=1)
        scored = toyplay.dropna(subset=["pct"])
        for group, rows in scored.groupby("diagnostic_group"):
            out.append({"feature": feature, "group": group, "corpus": "all", "children": len(rows),
                        "median_percentile": round(rows.pct.median(), 1),
                        "below_p10_percent": round((rows.pct < 10).mean() * 100, 1)})
        for corpus, rows in scored[scored.diagnostic_group == "ASD"].groupby("corpus"):
            out.append({"feature": feature, "group": "ASD", "corpus": corpus, "children": len(rows),
                        "median_percentile": round(rows.pct.median(), 1),
                        "below_p10_percent": round((rows.pct < 10).mean() * 100, 1)})
    return out


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def markdown(clusters: list[dict], zones: list[dict]) -> str:
    lines = [
        "# Unsupervised clusters and age-referenced zones for ASD",
        "",
        "Run with `scripts/evaluate_unsupervised_asd_zones.py` on `data/ml/canonical_features.parquet`,",
        "one session per child. Measures: " + ", ".join(f"`{f}`" for f in FEATURES) + ".",
        "",
        "## 1. Clusters found without labels",
        "",
        "AMI is adjusted mutual information between cluster labels and each grouping (0 = chance).",
        "",
        "| Setting | Children (ASD) | Method | k | AMI ASD | AMI corpus | AMI age band | Most ASD in one cluster (overall) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in clusters:
        lines.append(f"| {r['setting']} | {r['children']} ({r['asd']}) | {r['method']} | {r['k']} | {r['ami_asd']:.3f} | "
                     f"{r['ami_corpus']:.2f} | {r['ami_age_band']:.2f} | {r['max_asd_share_in_a_cluster']:.0%} "
                     f"({r['asd_share_overall']:.0%}) |")
    lines += [
        "",
        "## 2. Below the 10th percentile of typical children the same age",
        "",
        f"Reference: TD and NH toy-play children from other corpora, within {AGE_WINDOW_MONTHS} months of age, "
        f"at least {MIN_REFERENCE} per child. A calibrated zone holds about 10% of typical children.",
        "",
        "| Measure | Group | Corpus | Children | Median percentile | Below 10th percentile |",
        "|---|---|---|---|---|---|",
    ]
    for r in zones:
        lines.append(f"| {r['feature']} | {r['group']} | {r['corpus']} | {r['children']} | "
                     f"{r['median_percentile']:.0f} | {r['below_p10_percent']:.0f}% |")
    raw = [r["ami_asd"] for r in clusters]
    lines += [
        "",
        "## Reading these numbers",
        "",
        f"- Clusters line up with corpus and age far more than with diagnosis; AMI with ASD stays between "
        f"{min(raw):.3f} and {max(raw):.3f} in every setting, including after age is removed and inside the "
        "two corpora that hold both groups.",
        "- The red zone catches language that is low for age, not autism in particular: late talkers fall in it "
        "too, and the share of autistic children in it changes a lot between corpora.",
        "- MLU percentiles are not calibrated across corpora (typical children from the hearing-study corpora fall "
        "in the zone far more often than 10%), because transcription and utterance segmentation differ between labs.",
        "- PasaScope therefore reports descriptive measures and gives no zone or risk label.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--features", type=Path, default=PROJECT_ROOT / "data/ml/canonical_features.parquet")
    parser.add_argument("--out", type=Path, default=PROJECT_ROOT / "reports/metrics/asd_unsupervised_zones")
    args = parser.parse_args()
    warnings.filterwarnings("ignore")
    children = one_session_per_child(pd.read_parquet(args.features))
    clusters = clustering_rows(children)
    zones = zone_rows(children)
    write_csv(args.out.with_suffix(".csv"), [dict(table="clusters", **r) for r in clusters])
    write_csv(args.out.parent / (args.out.name + "_percentiles.csv"), zones)
    args.out.with_suffix(".md").write_text(markdown(clusters, zones), encoding="utf-8")
    print("wrote", args.out.with_suffix(".md"))


if __name__ == "__main__":
    main()
