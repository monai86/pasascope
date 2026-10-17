"""Train and check the utterance boundary model (src/audio_pipeline/utterance_boundaries.py).

Inputs:
* CHAT transcripts for the word statistics (how often a word ends or starts
  an utterance). The recordings used for evaluation are left out, by corpus.
* Recordings already run through the app's pipeline up to speaker
  attribution, cached as JSON by ``--cache-dir`` (one file per recording,
  holding the timed words, their speakers and the gold transcript of the same
  stretch; ``--cache-pipeline`` makes them).

Each gap between two words of the same speaker is labelled from the gold
transcript: the draft words are aligned to the gold words, and a gap is a
boundary when its two words fall in different gold utterances. Words the
alignment cannot place are left out of training and scoring.

Checks, all with each recording (one child) held out in turn:
* boundary precision, recall and F1 against the gold, for the model and for
  the app's previous rule (a pause over 0.6 s);
* the child's MLU-w per recording from the resulting draft, against the gold.

The decision threshold is picked on the training recordings only. The final
model, trained on every recording, is written with its feature weights and
word statistics as JSON.

Usage:
    python scripts/train_utterance_boundaries.py --cache-pipeline ellisweismer=.local/evaluation/ellisweismer_media:5 \
        --cache-pipeline enni=.local/evaluation/enni_media:10      # once per corpus; runs Whisper (slow)
    python scripts/train_utterance_boundaries.py                     # train and report
Outputs: reports/metrics/utterance_boundaries.{md,csv} and the model JSON.
"""

from __future__ import annotations

import argparse
import csv
from difflib import SequenceMatcher
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.audio_pipeline.utterance_boundaries import (  # noqa: E402
    DEFAULT_MODEL_PATH,
    FEATURE_LABELS_TH,
    FEATURES,
    BoundaryModel,
    Word,
    WordStatistics,
    fit_boundary_model,
    gap_features,
    typical_seconds_per_letter,
    words_of,
)

PAUSE_RULE_SECONDS = 0.6  # the app's rule before this model (segmentation.MAX_INTRA_TURN_GAP)
EVALUATION_CORPORA = ("EllisWeismer", "ENNI")


# ----------------------------------------------------------------------
# Data
# ----------------------------------------------------------------------
def word_statistics(chat_root: Path) -> tuple[WordStatistics, int]:
    """Statistics from every CHAT file under ``chat_root`` outside the evaluation corpora, duplicates once."""
    seen, paths = set(), []
    for path in sorted(chat_root.rglob("*.cha")):
        if any(name in path.parts for name in EVALUATION_CORPORA):
            continue
        digest = hashlib.sha1(path.read_bytes()).hexdigest()
        if digest not in seen:
            seen.add(digest)
            paths.append(path)
    return WordStatistics.from_chat_files(paths), len(paths)


def load_recording(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    words, speakers = [], []
    for piece in sorted(data["pieces"], key=lambda p: p["start"]):
        for text, start, end, _ in piece["words"]:
            if text.strip():
                words.append(Word(text, float(start), float(end)))
                speakers.append(piece["speaker"])
    data["words"], data["speakers"] = words, speakers
    data["gold_utterance_of_word"] = align_to_gold(words, data["gold"])
    return data


def align_to_gold(words: list[Word], gold: list[dict]) -> list[int | None]:
    """For each draft word, the index of the gold utterance its first matched token belongs to."""
    gold_tokens, gold_utterance = [], []
    for index, utterance in enumerate(sorted(gold, key=lambda u: u["start"])):
        for token in words_of(utterance["text"]):
            gold_tokens.append(token)
            gold_utterance.append(index)
    draft_tokens, draft_word = [], []
    for index, word in enumerate(words):
        for token in words_of(word.text):
            draft_tokens.append(token)
            draft_word.append(index)
    mapping: list[int | None] = [None] * len(words)
    for block in SequenceMatcher(None, draft_tokens, gold_tokens, autojunk=False).get_matching_blocks():
        for k in range(block.size):
            word = draft_word[block.a + k]
            if mapping[word] is None:
                mapping[word] = gold_utterance[block.b + k]
    return mapping


def gaps(data: dict, statistics: WordStatistics) -> list[dict]:
    """One row per gap between two words of the same speaker, with features and the gold label (or None)."""
    words, speakers, gold = data["words"], data["speakers"], data["gold_utterance_of_word"]
    per_letter = typical_seconds_per_letter(words)
    rows = []
    for i in range(len(words) - 1):
        if speakers[i] != speakers[i + 1]:
            continue
        label = None if gold[i] is None or gold[i + 1] is None else int(gold[i] != gold[i + 1])
        rows.append({"index": i, "label": label, "pause_seconds": words[i + 1].start - words[i].end,
                     **gap_features(words, i, statistics, seconds_per_letter=per_letter)})
    return rows


def cache_pipeline(spec: str, cache_dir: Path) -> None:
    """Run the app's pipeline on a corpus (``name=folder:minutes``) and keep the words before utterance cleanup."""
    import src.audio_pipeline.pipeline as pipeline
    from scripts.evaluate_end_to_end import evaluation_window, run_pipeline
    from scripts.evaluate_speaker_attribution import collect_recordings

    name, _, rest = spec.partition("=")
    folder, _, minutes = rest.rpartition(":")
    folder, minutes = Path(folder), float(minutes)
    captured = {}
    original = pipeline.clean_segments

    def capture(utterances, **kwargs):
        captured["pieces"] = [{"start": u.start, "end": u.end, "speaker": u.speaker, "basis": u.speaker_basis, "text": u.text,
                               "words": [[w.text, w.start, w.end, w.probability] for w in (u.words or [])]} for u in utterances]
        return original(utterances, **kwargs)

    pipeline.clean_segments = capture
    try:
        out = cache_dir / name
        out.mkdir(parents=True, exist_ok=True)
        recordings, _ = collect_recordings(folder / "chat", folder, max_minutes=None, limit=None)
        for rec in recordings:
            target = out / f"{rec.cha_path.stem}.json"
            if target.exists():
                continue
            start, end = evaluation_window(rec.utterances, minutes)
            gold = [{"start": u.start - start, "end": u.end - start, "role": u.role, "text": u.text}
                    for u in rec.utterances if u.start >= start and u.end <= end]
            lines, _, _ = run_pipeline(rec.audio_path, start, minutes, model="medium", strategy="english", age=rec.age_months)
            target.write_text(json.dumps({
                "corpus": name, "recording": rec.cha_path.stem, "group": rec.cha_path.parent.name, "audio": str(rec.audio_path),
                "start": start, "minutes": minutes, "age": rec.age_months, "gold": gold, "pieces": captured["pieces"],
                "current_lines": lines,
            }, ensure_ascii=False), encoding="utf-8")
            print(f"cached {name} {rec.cha_path.stem}", flush=True)
    finally:
        pipeline.clean_segments = original


# ----------------------------------------------------------------------
# Drafts and child measures
# ----------------------------------------------------------------------
def draft_lines(data: dict, cut_at: set[int]) -> list[tuple[str, str]]:
    """Speaker and CHAT text of each utterance when the words are cut at speaker changes and ``cut_at``."""
    from src.audio_pipeline.chat_formatter import draft_utterance_text
    from src.audio_pipeline.segmentation import _join_word_pieces
    from src.audio_pipeline.whisper_transcribe import UtteranceSegment, WordSegment

    words, speakers = data["words"], data["speakers"]
    lines, group = [], []
    for i, word in enumerate(words):
        group.append(word)
        last = i == len(words) - 1
        if last or speakers[i] != speakers[i + 1] or i in cut_at:
            segment_words = [WordSegment(w.text, w.start, w.end, 1.0) for w in group]
            segment = UtteranceSegment(start=group[0].start, end=group[-1].end, text=_join_word_pieces(segment_words),
                                       words=segment_words, speaker=speakers[i])
            text = draft_utterance_text(segment)
            if text.strip():
                lines.append(((speakers[i] or "UNK").upper(), text))
            group = []
    return lines


def child_mlu(texts: list[str]) -> float | None:
    from scripts.evaluate_end_to_end import measures

    return measures(texts)["mlu"] if texts else None


# ----------------------------------------------------------------------
# Training and scoring
# ----------------------------------------------------------------------
def best_threshold(probabilities: np.ndarray, labels: np.ndarray) -> float:
    best, best_f1 = 0.5, -1.0
    for threshold in np.arange(0.2, 0.81, 0.05):
        f1 = f1_score(probabilities >= threshold, labels)[2]
        if f1 > best_f1:
            best, best_f1 = float(threshold), f1
    return best


def f1_score(predicted: np.ndarray, labels: np.ndarray) -> tuple[float, float, float]:
    tp = int((predicted & (labels == 1)).sum())
    fp = int((predicted & (labels == 0)).sum())
    fn = int((~predicted & (labels == 1)).sum())
    precision, recall = tp / max(tp + fp, 1), tp / max(tp + fn, 1)
    return precision, recall, 2 * precision * recall / max(precision + recall, 1e-9)


def labelled(rows: list[dict]) -> list[dict]:
    return [r for r in rows if r["label"] is not None]


def fit(rows: list[dict], statistics: WordStatistics, trained_on: str = "") -> BoundaryModel:
    return fit_boundary_model(rows, [r["label"] for r in rows], statistics, trained_on=trained_on)


GROUPS = {
    "pause only": ["pause"],
    "sound only (pause, lengthening)": ["pause", "lengthening"],
    "words only (Whisper punctuation, word statistics)": ["sentence_mark", "comma", "capital_next", "ends_utterances", "starts_utterances"],
    "all features": list(FEATURES),
}


def feature_groups(recordings: list[dict]) -> dict:
    """Held-out boundary F1 when the model sees only some features."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    results = {}
    for name, columns in GROUPS.items():
        hits = []
        for held in recordings:
            train = labelled([r for d in recordings if d is not held for r in d["rows"]])
            X = np.array([[r[c] for c in columns] for r in train]); y = np.array([r["label"] for r in train])
            model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)).fit(X, y)
            threshold = best_threshold(model.predict_proba(X)[:, 1], y)
            test = labelled(held["rows"])
            if test:
                p = model.predict_proba(np.array([[r[c] for c in columns] for r in test]))[:, 1]
                hits += list(zip(p >= threshold, [r["label"] for r in test]))
        results[name] = f1_score(np.array([h[0] for h in hits]), np.array([h[1] for h in hits]))
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cache-dir", type=Path, default=PROJECT_ROOT / ".local" / "evaluation" / "segmentation_cache")
    parser.add_argument("--chat-root", type=Path, default=PROJECT_ROOT / "data")
    parser.add_argument("--model-out", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--report-dir", type=Path, default=PROJECT_ROOT / "reports" / "metrics")
    parser.add_argument("--cache-pipeline", action="append", default=[], metavar="NAME=FOLDER:MINUTES",
                        help="run Whisper and speaker attribution on a corpus and cache the words, then exit")
    args = parser.parse_args(argv)
    if args.cache_pipeline:
        for spec in args.cache_pipeline:
            cache_pipeline(spec, args.cache_dir)
        return 0

    statistics, n_files = word_statistics(args.chat_root)
    print(f"word statistics from {n_files} transcripts, {statistics.utterances} utterances", flush=True)
    recordings = []
    for path in sorted(args.cache_dir.glob("*/*.json")):
        data = load_recording(path)
        data["rows"] = gaps(data, statistics)
        recordings.append(data)
        print(f"  {data['corpus']} {data['recording']}: {len(data['rows'])} gaps, "
              f"{len(labelled(data['rows']))} placed in the gold", flush=True)

    per_recording, model_hits, rule_hits = [], [], []
    for held in recordings:
        train_rows = labelled([r for d in recordings if d is not held for r in d["rows"]])
        model = fit(train_rows, statistics)
        threshold = best_threshold(np.array([model.probability(r) for r in train_rows]), np.array([r["label"] for r in train_rows]))
        probabilities = {r["index"]: model.probability(r) for r in held["rows"]}
        model_cuts = {i for i, p in probabilities.items() if p >= threshold}
        rule_cuts = {r["index"] for r in held["rows"] if r["pause_seconds"] > PAUSE_RULE_SECONDS}
        for r in labelled(held["rows"]):
            model_hits.append((r["index"] in model_cuts, r["label"], held["recording"]))
            rule_hits.append((r["index"] in rule_cuts, r["label"], held["recording"]))
        gold_child = [u["text"] for u in held["gold"] if u["role"] == "CHI"]
        lines = {"model": draft_lines(held, model_cuts), "rule": draft_lines(held, rule_cuts)}
        per_recording.append({
            "corpus": held["corpus"], "recording": held["recording"], "age_months": held["age"], "threshold": round(threshold, 2),
            "mlu_gold": child_mlu(gold_child),
            "mlu_rule": child_mlu([t for s, t in lines["rule"] if s == "CHI"]),
            "mlu_model": child_mlu([t for s, t in lines["model"] if s == "CHI"]),
            "child_utterances_gold": len(gold_child),
            "child_utterances_rule": sum(1 for s, _ in lines["rule"] if s == "CHI"),
            "child_utterances_model": sum(1 for s, _ in lines["model"] if s == "CHI"),
        })
        print(f"  held out {held['recording']}: MLU gold {per_recording[-1]['mlu_gold']} rule {per_recording[-1]['mlu_rule']} "
              f"model {per_recording[-1]['mlu_model']}", flush=True)

    ablation = feature_groups(recordings)
    final = fit(labelled([r for d in recordings for r in d["rows"]]), statistics,
                trained_on=f"{len(recordings)} recordings: " + ", ".join(sorted({d['corpus'] for d in recordings})))
    all_rows = labelled([r for d in recordings for r in d["rows"]])
    final.threshold = best_threshold(np.array([final.probability(r) for r in all_rows]), np.array([r["label"] for r in all_rows]))
    final.save(args.model_out)
    write_report(args.report_dir, recordings, per_recording, model_hits, rule_hits, final, n_files, ablation)
    return 0


def write_report(report_dir, recordings, per_recording, model_hits, rule_hits, final: BoundaryModel, n_files: int,
                 ablation: dict) -> None:
    from scipy.stats import pearsonr, spearmanr

    report_dir.mkdir(parents=True, exist_ok=True)
    with (report_dir / "utterance_boundaries.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(per_recording[0]))
        writer.writeheader()
        writer.writerows(per_recording)

    def scores(hits):
        predicted = np.array([h[0] for h in hits]); labels = np.array([h[1] for h in hits])
        return f1_score(predicted, labels)

    # Bootstrap over recordings (children) for the F1 gain, and a paired test on MLU distance.
    rng = np.random.default_rng(0)
    names = sorted({h[2] for h in model_hits})
    by_model = {n: [h for h in model_hits if h[2] == n] for n in names}
    by_rule = {n: [h for h in rule_hits if h[2] == n] for n in names}
    gains = []
    for _ in range(2000):
        pick = rng.choice(names, len(names))
        gains.append(scores([h for n in pick for h in by_model[n]])[2] - scores([h for n in pick for h in by_rule[n]])[2])
    from scipy.stats import wilcoxon

    def mlu_test(rows):
        pairs = [(abs(r["mlu_rule"] - r["mlu_gold"]), abs(r["mlu_model"] - r["mlu_gold"])) for r in rows
                 if r["mlu_gold"] and r["mlu_rule"] and r["mlu_model"]]
        closer = sum(1 for a, b in pairs if b < a)
        return closer, len(pairs), wilcoxon([a for a, _ in pairs], [b for _, b in pairs]).pvalue

    def mlu_row(key: str, rows: list[dict]) -> str:
        pairs = [(r["mlu_gold"], r[key]) for r in rows if r["mlu_gold"] and r[key]]
        gold, draft = np.array([p[0] for p in pairs]), np.array([p[1] for p in pairs])
        return (f"{np.abs(gold - draft).mean():.2f} | {np.mean(draft - gold):+.2f} | {pearsonr(gold, draft)[0]:.2f} | "
                f"{spearmanr(gold, draft)[0]:.2f}")

    rp, rr, rf = scores(rule_hits)
    mp, mr, mf = scores(model_hits)
    groups = [("All", per_recording)] + [
        (title, [r for r in per_recording if keep(r)]) for title, keep in (
            ("EllisWeismer (2;6-5;6)", lambda r: r["corpus"] == "ellisweismer"),
            ("ENNI under 7", lambda r: r["corpus"] == "enni" and r["age_months"] < 84),
            ("ENNI 7 and over", lambda r: r["corpus"] == "enni" and r["age_months"] >= 84),
        )
    ]
    weights = sorted(zip(FEATURES, final.weights), key=lambda kv: -abs(kv[1]))
    lines = [
        "# Where Does an Utterance End? An Explainable Boundary Model",
        "",
        "The app cuts a speaker's words into utterances before measuring MLU. This report compares its",
        f"previous rule (a pause over {PAUSE_RULE_SECONDS} s) with a logistic regression on named features",
        "(`src/audio_pipeline/utterance_boundaries.py`). Each recording (one child) was held out in turn;",
        "the model and its decision threshold were fitted on the others. Run with",
        "`scripts/train_utterance_boundaries.py`.",
        "",
        f"Data: {len(recordings)} recordings already run through the app's Whisper and speaker attribution",
        f"({sum(len(d['rows']) for d in recordings)} same-speaker gaps, {len(model_hits)} of them placed in the gold",
        f"transcript by word alignment). Word statistics: {n_files} CHAT transcripts outside the test corpora,",
        f"{final.statistics.utterances:,} utterances.",
        "",
        "## Boundaries between words of the same speaker",
        "",
        "| Method | Precision | Recall | F1 |",
        "|---|---|---|---|",
        f"| Pause over {PAUSE_RULE_SECONDS} s (previous rule) | {rp:.2f} | {rr:.2f} | {rf:.2f} |",
        f"| Boundary model | {mp:.2f} | {mr:.2f} | {mf:.2f} |",
        "",
        f"F1 gain {mf - rf:+.2f}, 95% interval {np.percentile(gains, 2.5):+.2f} to {np.percentile(gains, 97.5):+.2f}"
        " (bootstrap over recordings).",
        "",
        "Which features matter (same held-out procedure, model given only some features):",
        "",
        "| Features | Precision | Recall | F1 |",
        "|---|---|---|---|",
        *[f"| {name} | {p:.2f} | {r:.2f} | {f:.2f} |" for name, (p, r, f) in ablation.items()],
        "",
        "## Child MLU-w per recording, from the uncorrected draft",
        "",
        "| Children | Method | Mean distance from gold | Mean bias | Pearson r | Spearman |",
        "|---|---|---|---|---|---|",
    ]
    for title, rows in groups:
        if len(rows) >= 3:
            lines.append(f"| {title} | previous rule | {mlu_row('mlu_rule', rows)} |")
            lines.append(f"| {title} | boundary model | {mlu_row('mlu_model', rows)} |")
    lines += [
        "",
        "Speaker mistakes remain in both drafts; only where utterances are cut differs. Recordings where the",
        "model's MLU is closer to the gold than the rule's (Wilcoxon signed-rank on the distances):",
        "",
        *[f"- {title}: {c} of {n} (p = {pv:.3f})" for title, rows in groups if len(rows) >= 3
          for c, n, pv in [mlu_test(rows)]],
        "",
        "## What the model weighs (final model, all recordings)",
        "",
        "Weights are on standardised features: + pushes toward a new utterance, - toward the same one.",
        f"Intercept {final.intercept:+.2f}; decision threshold {final.threshold:.2f}.",
        "",
        "| Feature | ความหมาย | Weight |",
        "|---|---|---|",
    ] + [f"| `{name}` | {FEATURE_LABELS_TH[name]} | {weight:+.2f} |" for name, weight in weights]
    (report_dir / "utterance_boundaries.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"rule F1 {rf:.3f}, model F1 {mf:.3f}; wrote {report_dir / 'utterance_boundaries.md'}")


if __name__ == "__main__":
    raise SystemExit(main())
