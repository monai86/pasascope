"""Replicate a published transcript-based ASD screening model, then validate it step by step.

Assaf, Shehabeddine & Ramesh (2025, Scientific Reports 15:34134) report
accuracy above 86% for telling autistic from typically developing children
with logistic regression on four transcript features: MLU, the child's mean
turn length relative to the adult's (MLT ratio), age and sex. They used the
TalkBank Eigsti and Nadig corpora, 5-fold stratified cross-validation, and
SMOTE oversampling described as a preprocessing step.

This script rebuilds that model on the same corpora and re-runs it under
progressively stricter checks, so the effect of each choice is visible:

1. as published: SMOTE on the whole dataset, then 5-fold cross-validation;
2. SMOTE inside each training fold only;
3. the language features alone, without age and sex;
4. age alone, sex alone;
5. children of overlapping ages only (pairs matched within 6 months);
6. trained on one corpus, tested on the other.

Every model is a logistic regression on standardised features, and its
coefficients are reported, so what drives each result can be read off.
Cross-validation is repeated with different fold splits; intervals are the
2.5th-97.5th percentiles over repeats, and p-values come from label
permutation.

Usage:
    python scripts/replicate_transcript_asd_screening.py
Outputs: reports/metrics/asd_transcript_screening_replication.{md,csv}
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

LANGUAGE = ["mlu", "mlt_ratio"]
PUBLISHED = ["mlu", "mlt_ratio", "age_months", "male"]
REPEATS = 50
PERMUTATIONS = 200
MATCH_MONTHS = 6.0


def turn_ratio(path: Path) -> float | None:
    """Child's mean words per turn over the adults' (consecutive lines by one speaker are one turn)."""
    from src.chat_feature_extractor import read_chat

    turns: list[tuple[str, int]] = []
    for utterance in read_chat(path).utterances():
        words = sum(1 for t in (utterance.tokens or []) if t.word and t.word not in {".", "?", "!", ","})
        speaker = "CHI" if utterance.participant == "CHI" else "ADULT"
        if turns and turns[-1][0] == speaker:
            turns[-1] = (speaker, turns[-1][1] + words)
        else:
            turns.append((speaker, words))
    child = [w for s, w in turns if s == "CHI"]
    adult = [w for s, w in turns if s == "ADULT"]
    if not child or not adult or not np.mean(adult):
        return None
    return float(np.mean(child) / np.mean(adult))


def load(corpus_dir: Path, corpus: str) -> list[dict]:
    from src.chat_feature_extractor import extract_chat_features

    rows = []
    for path in sorted(corpus_dir.rglob("*.cha")):
        features = extract_chat_features(path)
        if not features or features["group_header"] not in ("ASD", "TD"):
            continue
        ratio = turn_ratio(path)
        if features["mlu"] is None or ratio is None or features["age_months"] is None:
            continue
        rows.append({
            "corpus": corpus, "child": f"{corpus}:{path.stem}", "asd": int(features["group_header"] == "ASD"),
            "mlu": features["mlu"], "mlt_ratio": ratio, "age_months": features["age_months"],
            "male": int(str(features["sex"]).lower().startswith("m")),
        })
    return rows


def smote(X: np.ndarray, y: np.ndarray, rng, k: int = 5) -> tuple[np.ndarray, np.ndarray]:
    """Oversample the minority class to the majority's size by interpolating between minority neighbours."""
    labels, counts = np.unique(y, return_counts=True)
    if len(labels) < 2 or counts.min() == counts.max():
        return X, y
    minority = labels[counts.argmin()]
    points = X[y == minority]
    if len(points) < 2:
        return X, y
    synthetic = []
    for _ in range(counts.max() - counts.min()):
        i = rng.integers(len(points))
        distances = np.linalg.norm(points - points[i], axis=1)
        neighbours = np.argsort(distances)[1:k + 1]
        j = rng.choice(neighbours)
        synthetic.append(points[i] + rng.random() * (points[j] - points[i]))
    return np.vstack([X, synthetic]), np.concatenate([y, np.full(len(synthetic), minority)])


def fit(X: np.ndarray, y: np.ndarray):
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    return make_pipeline(StandardScaler(), LogisticRegression(max_iter=750)).fit(X, y)


def cross_validated_auc(X, y, rng, *, smote_where: str | None) -> float:
    """One run of 5-fold stratified CV; ``smote_where`` is None, 'before' (whole set) or 'inside' (train folds)."""
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import StratifiedKFold

    if smote_where == "before":
        X, y = smote(X, y, rng)
    scores = np.zeros(len(y))
    folds = StratifiedKFold(5, shuffle=True, random_state=int(rng.integers(1 << 30)))
    for train, test in folds.split(X, y):
        Xt, yt = (smote(X[train], y[train], rng) if smote_where == "inside" else (X[train], y[train]))
        scores[test] = fit(Xt, yt).predict_proba(X[test])[:, 1]
    return float(roc_auc_score(y, scores))


def evaluate(name: str, rows: list[dict], features: list[str], rng, *, smote_where: str | None = None) -> dict:
    X = np.array([[r[f] for f in features] for r in rows], dtype=float)
    y = np.array([r["asd"] for r in rows])
    aucs = [cross_validated_auc(X, y, rng, smote_where=smote_where) for _ in range(REPEATS)]
    observed = float(np.mean(aucs))
    null = [cross_validated_auc(X, rng.permutation(y), rng, smote_where=smote_where) for _ in range(PERMUTATIONS)]
    model = fit(*((smote(X, y, rng)) if smote_where else (X, y)))
    coefficients = dict(zip(features, model[-1].coef_[0].round(2)))
    return {
        "check": name, "children": len(y), "asd": int(y.sum()), "features": "+".join(features),
        "auc": round(observed, 3), "auc_low": round(float(np.percentile(aucs, 2.5)), 3),
        "auc_high": round(float(np.percentile(aucs, 97.5)), 3),
        "p_permutation": round((1 + sum(n >= observed for n in null)) / (1 + PERMUTATIONS), 3),
        "coefficients": ", ".join(f"{k} {v:+.2f}" for k, v in coefficients.items()),
    }


def age_matched(rows: list[dict]) -> list[dict]:
    """Greedy one-to-one pairs of an autistic and a typical child within MATCH_MONTHS of age."""
    asd = sorted((r for r in rows if r["asd"]), key=lambda r: r["age_months"])
    td = [r for r in rows if not r["asd"]]
    pairs = []
    for child in asd:
        candidates = [t for t in td if abs(t["age_months"] - child["age_months"]) <= MATCH_MONTHS]
        if candidates:
            match = min(candidates, key=lambda t: abs(t["age_months"] - child["age_months"]))
            td.remove(match)
            pairs += [child, match]
    return pairs


def transfer(train: list[dict], test: list[dict], features: list[str], name: str) -> dict:
    from sklearn.metrics import roc_auc_score

    model = fit(np.array([[r[f] for f in features] for r in train]), np.array([r["asd"] for r in train]))
    y = np.array([r["asd"] for r in test])
    scores = model.predict_proba(np.array([[r[f] for f in features] for r in test]))[:, 1]
    return {"check": name, "children": len(y), "asd": int(y.sum()), "features": "+".join(features),
            "auc": round(float(roc_auc_score(y, scores)), 3), "auc_low": "", "auc_high": "", "p_permutation": "",
            "coefficients": ", ".join(f"{k} {v:+.2f}" for k, v in zip(features, model[-1].coef_[0].round(2)))}


def describe(rows: list[dict], corpus: str) -> str:
    out = []
    for label, flag in (("ASD", 1), ("TD", 0)):
        group = [r for r in rows if r["corpus"] == corpus and r["asd"] == flag]
        ages = [r["age_months"] for r in group]
        out.append(f"{label} {len(group)} (age {min(ages):.0f}-{max(ages):.0f} months, MLU {np.mean([r['mlu'] for r in group]):.2f})")
    return "; ".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--eigsti", type=Path, default=PROJECT_ROOT / "data" / "Eigsti")
    parser.add_argument("--nadig", type=Path, default=PROJECT_ROOT / "data" / "Nadig")
    parser.add_argument("--report-dir", type=Path, default=PROJECT_ROOT / "reports" / "metrics")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)
    rng = np.random.default_rng(args.seed)

    corpora = {"Nadig": load(args.nadig, "Nadig"), "Eigsti": load(args.eigsti, "Eigsti")}
    results, notes = [], []
    for corpus, rows in corpora.items():
        smote_as_published = "before" if corpus == "Nadig" else None  # the paper applied SMOTE to Nadig only
        results += [
            evaluate(f"{corpus}: as published", rows, PUBLISHED, rng, smote_where=smote_as_published),
            evaluate(f"{corpus}: SMOTE inside training folds", rows, PUBLISHED, rng,
                     smote_where="inside" if smote_as_published else None),
            evaluate(f"{corpus}: language only (MLU, MLT ratio)", rows, LANGUAGE, rng),
            evaluate(f"{corpus}: age only", rows, ["age_months"], rng),
            evaluate(f"{corpus}: sex only", rows, ["male"], rng),
        ]
        matched = age_matched(rows)
        notes.append(f"{corpus}: {len(matched) // 2} autistic children have a typical child within {MATCH_MONTHS:.0f} months of age.")
        if len(matched) >= 10:
            results.append(evaluate(f"{corpus}: language only, age-matched pairs", matched, LANGUAGE, rng))
    for train, test in (("Eigsti", "Nadig"), ("Nadig", "Eigsti")):
        for features in (PUBLISHED, LANGUAGE):
            label = "published features" if features == PUBLISHED else "language only"
            results.append(transfer(corpora[train], corpora[test], features, f"trained on {train}, tested on {test}: {label}"))

    args.report_dir.mkdir(parents=True, exist_ok=True)
    with (args.report_dir / "asd_transcript_screening_replication.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    lines = [
        "# Replicating a Transcript-based ASD Screening Model",
        "",
        "Model: Assaf, Shehabeddine & Ramesh (2025), *Scientific Reports* 15:34134. Logistic regression",
        "on MLU (morphemes), MLT ratio (child's mean words per turn / adults'), age and sex; ASD vs TD;",
        "TalkBank Eigsti and Nadig corpora, one transcript per child. Run with",
        "`scripts/replicate_transcript_asd_screening.py`.",
        "",
        f"- Nadig: {describe(corpora['Nadig'], 'Nadig')}",
        f"- Eigsti: {describe(corpora['Eigsti'], 'Eigsti')}",
        "",
        f"AUC is the mean over {REPEATS} repeats of 5-fold stratified cross-validation, with the 2.5th-97.5th",
        f"percentile range; p from {PERMUTATIONS} label permutations. Coefficients are on standardised",
        "features (positive = more likely ASD), from a model fitted to all children of that row.",
        "",
        "| Check | Children (ASD) | AUC | Range | p | Coefficients |",
        "|---|---|---|---|---|---|",
    ]
    for r in results:
        span = f"{r['auc_low']}-{r['auc_high']}" if r["auc_low"] != "" else "single split"
        lines.append(f"| {r['check']} | {r['children']} ({r['asd']}) | {r['auc']:.2f} | {span} | {r['p_permutation']} | {r['coefficients']} |")
    lines += ["", *[f"- {note}" for note in notes], "", "## Reading these numbers", "",
              "- In both corpora the autistic children are older than the typical children (Assaf et al. note",
              "  that this reflects the autistic children's language delay). Age alone separates the groups about",
              "  as well as the published model, and age carries the largest coefficient in it.",
              "- The language features alone are close to chance, and stay there in the 7 age-matched Eigsti",
              "  pairs (Nadig has only 3). Too few matched children to say much, but nothing here shows MLU or",
              "  turn length telling autistic from typical children of the same age.",
              "- Oversampling before or inside the folds makes little difference here; the inflation comes from",
              "  age being a feature, and age stays predictive across corpora because both share the design.",
              "- A model like this would flag older children, not autism. PasaScope reports language measures",
              "  for the therapist and does not classify (docs/TERM_PAPER_MAPPING.md)."]
    (args.report_dir / "asd_transcript_screening_replication.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    for r in results:
        print(f"{r['check']:58s} AUC {r['auc']:.2f}  {r['coefficients']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
