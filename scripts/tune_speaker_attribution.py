"""Tune and compare child/adult attribution settings on timed CHAT recordings.

Running the diarizers end to end for every setting is slow, so this script
computes what they look at once per utterance and caches it:

* an ECAPA speaker embedding (the embedding diarizer's input),
* the median F0 (its pitch fallback and child score),
* the USC frame model's mean child-minus-adult probability.

Settings are then replayed from the cache in seconds. Recordings are split
into a tuning half and a held-out half (alternating within each age), so a
setting chosen on one half is reported on the other.

Strategies compared:

* ``pitch_duration``: ECAPA clusters, child cluster by pitch and duration
  (the app's ``embedding`` diarizer);
* ``frame_model``: ECAPA clusters, child cluster by the USC frame model
  (``hybrid``);
* ``enrolled``: ECAPA clusters, child cluster by similarity to a voice
  sample of the child;
* ``enrolled_direct``: no clustering; each utterance is the child's when it
  sounds more like the child sample than like the session's other speech.

The enrollment sample is simulated with the child's first utterances in the
recording (about ``--enroll-seconds`` of speech), which are then left out of
scoring. A sample recorded separately before a session would be cleaner.

Usage:
    python scripts/tune_speaker_attribution.py \\
        --cha-dir .local/evaluation/ellisweismer_media/chat \\
        --audio-dir .local/evaluation/ellisweismer_media
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import itertools
from pathlib import Path
import sys

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.evaluate_speaker_attribution import CHILD, collect_recordings  # noqa: E402

SR = 16000
MIN_SECONDS = 0.2  # shorter utterances get no embedding at all


@dataclass
class Features:
    name: str
    age: float | None
    child: np.ndarray        # bool per utterance (gold)
    duration: np.ndarray     # seconds
    embedding: np.ndarray    # (n, 192), NaN rows when too short
    f0: np.ndarray           # Hz, NaN when unvoiced
    frame_margin: np.ndarray # USC child - adult probability


def extract(recordings, cache: Path) -> list[Features]:
    from src.audio_pipeline import diarization as d
    from src.audio_pipeline.child_adult_frames import ADULT, CHILD as FRAME_CHILD, ChildAdultFrameModel, FRAME_SECONDS
    from src.audio_pipeline.pipeline import decode_to_wav
    import librosa
    import tempfile

    cache.mkdir(parents=True, exist_ok=True)
    embedder = d.EmbeddingDiarizer(d.EmbeddingDiarizerConfig(min_embed_duration=MIN_SECONDS))
    frames = None
    out = []
    for rec in recordings:
        path = cache / f"{rec.cha_path.stem}_{len(rec.utterances)}.npz"
        if not path.exists():
            if frames is None:
                frames = ChildAdultFrameModel()
            with tempfile.TemporaryDirectory() as tmp:
                wav = Path(tmp) / "a.wav"
                decode_to_wav(rec.audio_path, wav)
                audio, _ = librosa.load(str(wav), sr=SR, mono=True)
            end = int(max(u.end for u in rec.utterances) * SR) + SR
            audio = audio[:end]
            probs = frames.frame_probabilities(audio)
            emb, f0, margin = [], [], []
            for u in rec.utterances:
                clip = audio[int(u.start * SR):int(u.end * SR)]
                vec = embedder._embed_clip(clip, SR) if len(clip) else None
                emb.append(vec if vec is not None else np.full(192, np.nan))
                pitch = embedder._pitch._median_f0(clip, SR) if len(clip) else None
                f0.append(np.nan if pitch is None else pitch)
                span = probs[int(u.start / FRAME_SECONDS):max(int(u.start / FRAME_SECONDS) + 1, int(np.ceil(u.end / FRAME_SECONDS)))]
                margin.append(float((span[:, FRAME_CHILD] - span[:, ADULT]).mean()) if len(span) else 0.0)
            np.savez(path, emb=np.array(emb), f0=np.array(f0), margin=np.array(margin))
            print(f"  cached {rec.cha_path.stem}", flush=True)
        data = np.load(path)
        out.append(Features(
            name=rec.cha_path.stem, age=rec.age_months,
            child=np.array([u.role == CHILD for u in rec.utterances]),
            duration=np.array([u.end - u.start for u in rec.utterances]),
            embedding=data["emb"], f0=data["f0"], frame_margin=data["margin"],
        ))
    return out


def _unit(rows: np.ndarray) -> np.ndarray:
    return rows / (np.linalg.norm(rows, axis=1, keepdims=True) + 1e-8)


def predict(f: Features, params: dict, scored: np.ndarray, enroll: np.ndarray | None) -> np.ndarray:
    """Child (True) or adult per utterance under one setting."""
    from sklearn.cluster import AgglomerativeClustering

    from src.audio_pipeline.diarization import age_aware_child_f0_threshold, merge_small_clusters

    thresh = age_aware_child_f0_threshold(f.age)
    usable = scored & ~np.isnan(f.embedding).any(axis=1) & (f.duration >= params["min_embed"])
    child = np.zeros(len(f.child), dtype=bool)
    fallback_by_frame = params["strategy"] in ("frame_model",)

    def fallback(i):
        if fallback_by_frame:
            return f.frame_margin[i] > 0
        return (not np.isnan(f.f0[i])) and f.f0[i] >= thresh

    if params["strategy"] == "enrolled_direct":
        X = _unit(f.embedding[usable])
        sims = X @ enroll
        cutoff = np.median(sims) if params["direct_cut"] == "median" else params["direct_cut"]
        child[np.where(usable)[0]] = sims >= cutoff
        for i in np.where(scored & ~usable)[0]:
            child[i] = fallback(i)
        return child

    idx = np.where(usable)[0]
    if len(idx) < 2:
        return np.array([fallback(i) for i in range(len(f.child))])
    X = _unit(f.embedding[idx])
    ids = AgglomerativeClustering(n_clusters=None, metric="cosine", linkage="average",
                                  distance_threshold=params["threshold"]).fit_predict(X)
    ids = merge_small_clusters(X, ids, f.duration[idx], min_fraction=params["min_fraction"], min_count=2)
    clusters = sorted(set(int(c) for c in ids))
    if len(clusters) < 2:
        for i in np.where(scored)[0]:
            child[i] = fallback(i)
        return child
    scores = {}
    for c in clusters:
        members = idx[ids == c]
        if params["strategy"] == "pitch_duration":
            f0 = f.f0[members]
            score = (np.nanmedian(f0) - thresh) if np.isfinite(f0).any() else 0.0
            scores[c] = score - 0.3 * float(np.mean(f.duration[members]))
        elif params["strategy"] == "frame_model":
            scores[c] = float(np.mean(f.frame_margin[members]))
        else:
            scores[c] = float(_unit(X[ids == c].mean(axis=0, keepdims=True))[0] @ enroll)
    winner = max(scores, key=scores.get)
    child_clusters = {winner}
    if params.get("multi_child"):
        # Any other cluster that sounds like the child sample as much as the winner does.
        child_clusters |= {c for c in clusters if c != winner and scores[c] >= scores[winner] - params["multi_child"]}
    for pos, i in enumerate(idx):
        child[i] = int(ids[pos]) in child_clusters
    for i in np.where(scored & ~usable)[0]:
        child[i] = fallback(i)
    return child


def enrollment(f: Features, seconds: float) -> tuple[np.ndarray | None, np.ndarray]:
    """Child sample embedding from the first child utterances, and which utterances stay scored."""
    scored = np.ones(len(f.child), dtype=bool)
    picked, total = [], 0.0
    for i in np.where(f.child)[0]:
        if np.isnan(f.embedding[i]).any() or f.duration[i] < 0.5:
            continue
        picked.append(i)
        total += f.duration[i]
        if total >= seconds:
            break
    if not picked:
        return None, scored
    scored[picked] = False
    weights = f.duration[picked][:, None]
    vec = (_unit(f.embedding[picked]) * weights).sum(axis=0)
    return vec / (np.linalg.norm(vec) + 1e-8), scored


def evaluate(features: list[Features], params: dict, enroll_seconds: float) -> dict:
    tp = fp = fn = correct = total = 0
    for f in features:
        enroll, scored = enrollment(f, enroll_seconds)
        if params["strategy"].startswith("enrolled") and enroll is None:
            continue
        if not params["strategy"].startswith("enrolled"):
            scored = enrollment(f, enroll_seconds)[1]  # score the same utterances in every strategy
        pred = predict(f, params, scored, enroll)
        gold = f.child[scored]
        p = pred[scored]
        tp += int(np.sum(p & gold)); fp += int(np.sum(p & ~gold)); fn += int(np.sum(~p & gold))
        correct += int(np.sum(p == gold)); total += len(gold)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"accuracy": correct / total if total else 0.0, "precision": precision, "recall": recall, "f1": f1}


GRID = {
    "pitch_duration": {"threshold": [0.4, 0.5, 0.6, 0.7], "min_fraction": [0.05, 0.1, 0.2], "min_embed": [0.2, 0.4, 0.8]},
    "frame_model": {"threshold": [0.4, 0.5, 0.6, 0.7], "min_fraction": [0.05, 0.1, 0.2], "min_embed": [0.2, 0.4, 0.8]},
    "enrolled": {"threshold": [0.4, 0.5, 0.6, 0.7], "min_fraction": [0.05, 0.1, 0.2], "min_embed": [0.2, 0.4, 0.8],
                 "multi_child": [0.0, 0.1, 0.2]},
    "enrolled_direct": {"min_embed": [0.2, 0.4, 0.8], "direct_cut": ["median", 0.3, 0.4, 0.5]},
}
CURRENT = {"pitch_duration": {"threshold": 0.5, "min_fraction": 0.1, "min_embed": 0.4}}


def split(features: list[Features]) -> tuple[list[Features], list[Features]]:
    by_age: dict = {}
    for f in sorted(features, key=lambda f: f.name):
        by_age.setdefault(f.age, []).append(f)
    tune, test = [], []
    for group in by_age.values():
        for i, f in enumerate(group):
            (tune if i % 2 == 0 else test).append(f)
    return tune, test


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--cha-dir", type=Path, required=True)
    parser.add_argument("--audio-dir", type=Path, required=True)
    parser.add_argument("--max-minutes", type=float, default=10.0)
    parser.add_argument("--enroll-seconds", type=float, default=10.0)
    parser.add_argument("--cache", type=Path, default=PROJECT_ROOT / ".local" / "evaluation" / "speaker_cache")
    parser.add_argument("--report", type=Path, default=PROJECT_ROOT / "reports" / "metrics" / "speaker_attribution_tuning.md")
    args = parser.parse_args(argv)

    recordings, skipped = collect_recordings(args.cha_dir, args.audio_dir, max_minutes=args.max_minutes, limit=None)
    print(f"{len(recordings)} recordings ({len(skipped)} skipped)")
    features = extract(recordings, args.cache)
    tune, test = split(features)
    print(f"tuning on {len(tune)}, testing on {len(test)}")

    lines = [
        "# Speaker Attribution Tuning",
        "",
        f"{len(features)} recordings, first {args.max_minutes:g} minutes each; tuned on {len(tune)} "
        f"({', '.join(f.name for f in tune)}), reported on the other {len(test)}. The child's first "
        f"~{args.enroll_seconds:g} s of speech are the simulated voice sample and are left out of scoring "
        "for every strategy.",
        "",
        "| Strategy | Setting | Tuning F1 | Held-out accuracy | Held-out child precision | Held-out child recall | Held-out child F1 |",
        "|---|---|---|---|---|---|---|",
    ]
    results = []
    for strategy, params in CURRENT.items():
        p = {"strategy": strategy, **params}
        held = evaluate(test, p, args.enroll_seconds)
        results.append(("current default", p, evaluate(tune, p, args.enroll_seconds)["f1"], held))
    for strategy, grid in GRID.items():
        best = None
        for values in itertools.product(*grid.values()):
            p = {"strategy": strategy, **dict(zip(grid.keys(), values))}
            score = evaluate(tune, p, args.enroll_seconds)["f1"]
            if best is None or score > best[0]:
                best = (score, p)
        held = evaluate(test, best[1], args.enroll_seconds)
        results.append((strategy, best[1], best[0], held))
        print(f"{strategy}: tuning F1 {best[0]:.3f} -> held-out F1 {held['f1']:.3f} ({best[1]})", flush=True)
    for name, p, tune_f1, held in results:
        setting = ", ".join(f"{k}={v}" for k, v in p.items() if k != "strategy")
        label = name if name == "current default" else p["strategy"]
        lines.append(f"| {label} | {setting} | {tune_f1:.3f} | {held['accuracy']:.1%} | {held['precision']:.1%} | "
                     f"{held['recall']:.1%} | {held['f1']:.3f} |")
    lines += [
        "",
        "Utterance spans come from the gold transcripts, so these are speaker-attribution results only.",
        "The voice sample is simulated from the session itself; a separate recording may differ.",
    ]
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {args.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
