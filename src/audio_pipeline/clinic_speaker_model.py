"""A clinic's own child/adult model, learned from transcripts its therapist attested.

The USC frame model (``child_adult_frames``) is kept as it is. Its encoder
features are averaged over each utterance, and a logistic regression trained
on the clinic's attested sessions decides child or adult from them.

Why this can work: one therapist sees many children, so a clinic's sessions
share the adults' voices, the room and the task. On ENNI story retellings
(one task and setting throughout), a model trained on 4 other children's sessions labelled 94% of a new
child's utterances correctly against 70% for the frame model; for children
aged 7 and over, 94% against 48%. A model trained on other corpora did not
carry over (ENNI 7+: 57%), so a model is learned per clinic and never shipped.
Thai toddlers (CRSLP) were not helped. Details: reports/metrics/clinic_speaker_model.md.

A trained model is used only when it beats the frame model on the clinic's
own sessions, with each child held out in turn.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import math
import os
from pathlib import Path
from typing import Iterable, Optional, Sequence

import numpy as np

from .child_adult_frames import ADULT, CHILD, FRAME_SECONDS

CLINIC_MODEL_ENV = "PASASCOPE_CLINIC_SPEAKER_MODEL"
FORMAT_VERSION = 1
MIN_SESSIONS = 4
MIN_CHILDREN = 2
# Strong L2 regularisation: a clinic has hundreds of utterances for 517
# features. C=0.01 was fixed before the held-out checks below, not tuned on them.
REGULARIZATION = 0.01
# The clinic model replaces the frame model only when its held-out balanced
# accuracy (the mean of the child's and the adults' share labelled right) is
# at least this much higher. Plain accuracy rewards calling everyone adult: on
# Thai toddlers (CRSLP) it rose from 61% to 74% while the share of the child's
# utterances found fell from 65% to 29%. On EllisWeismer (2;6-5;6), where the
# frame model is already good, the two tied and the frame model is kept.
ADOPT_MARGIN = 0.02


def balanced_accuracy(predicted_child: np.ndarray, is_child: np.ndarray) -> float:
    child, adult = is_child == 1, is_child == 0
    shares = [float(predicted_child[child].mean())] if child.any() else []
    shares += [float((~predicted_child[adult]).mean())] if adult.any() else []
    return float(np.mean(shares)) if shares else float("nan")


def utterance_features(features: np.ndarray, probs: np.ndarray, spans: Sequence[tuple[float, float]]) -> np.ndarray:
    """One row per utterance: mean encoder features, mean class probabilities, log duration."""
    rows = []
    for start, end in spans:
        first = max(0, int(math.floor(start / FRAME_SECONDS)))
        last = min(len(probs), max(first + 1, int(math.ceil(end / FRAME_SECONDS))))
        if last > first:
            mean_features, mean_probs = features[first:last].mean(axis=0), probs[first:last].mean(axis=0)
        else:
            mean_features, mean_probs = np.zeros(features.shape[1]), np.zeros(probs.shape[1])
        rows.append(np.concatenate([mean_features, mean_probs, [math.log(max(end - start, 0.01))]]))
    return np.asarray(rows, dtype="float64").reshape(len(rows), features.shape[1] + probs.shape[1] + 1)


def frame_margins(design: np.ndarray) -> np.ndarray:
    """The frame model's own child-minus-adult margin, read back from the feature rows."""
    probs = design[:, -5:-1]
    return probs[:, CHILD] - probs[:, ADULT]


@dataclass
class ClinicExamples:
    """The attested utterances the model learned from, to show which ones a new utterance sounds like."""

    rows: np.ndarray  # standardised feature rows, as the model sees them
    is_child: np.ndarray
    labels: list  # e.g. "TH-001 12/10/2026 03:12"


@dataclass
class ClinicSpeakerHead:
    mean: np.ndarray
    scale: np.ndarray
    coef: np.ndarray
    intercept: float
    examples: Optional[ClinicExamples] = None

    def child_probability(self, design: np.ndarray) -> np.ndarray:
        z = ((design - self.mean) / self.scale) @ self.coef + self.intercept
        return 1.0 / (1.0 + np.exp(-z))

    def margins(self, design: np.ndarray) -> np.ndarray:
        """On the frame model's scale: -1 surely adult, +1 surely child."""
        return 2.0 * self.child_probability(design) - 1.0

    def nearest_examples(self, row: np.ndarray, count: int = 3) -> list[tuple[str, bool]]:
        """The attested utterances closest to ``row`` in the features the model weighs most."""
        if self.examples is None or not len(self.examples.rows):
            return []
        weight = np.abs(self.coef)
        query = (row - self.mean) / self.scale * weight
        bank = self.examples.rows * weight
        similarity = bank @ query / (np.linalg.norm(bank, axis=1) * np.linalg.norm(query) + 1e-9)
        order = np.argsort(-similarity)[:count]
        return [(self.examples.labels[i], bool(self.examples.is_child[i])) for i in order]

    def explain(self, row: np.ndarray) -> str:
        """Why the clinic model called this utterance child or adult, in Thai."""
        child = float(self.child_probability(row[None, :])[0])
        probs = row[-5:-1]  # the frame model's mean class probabilities
        base = float(probs[CHILD] / max(probs[CHILD] + probs[ADULT], 1e-9))
        text = f"โมเดลประจำคลินิก: เสียงเด็ก {child:.0%} (โมเดลพื้นฐาน {base:.0%})"
        similar = self.nearest_examples(row)
        if similar:
            text += "; คล้ายประโยคที่รับรองแล้ว: " + ", ".join(f"{label} ({'เด็ก' if is_child else 'ผู้ใหญ่'})" for label, is_child in similar)
        return text

    def to_dict(self) -> dict:
        return {"mean": self.mean.tolist(), "scale": self.scale.tolist(), "coef": self.coef.tolist(), "intercept": self.intercept}

    @classmethod
    def from_dict(cls, data: dict) -> "ClinicSpeakerHead":
        return cls(np.asarray(data["mean"], float), np.asarray(data["scale"], float), np.asarray(data["coef"], float), float(data["intercept"]))


def fit_head(design: np.ndarray, is_child: np.ndarray) -> ClinicSpeakerHead:
    from sklearn.linear_model import LogisticRegression

    mean = design.mean(axis=0)
    scale = design.std(axis=0)
    scale[scale < 1e-8] = 1.0
    model = LogisticRegression(C=REGULARIZATION, max_iter=3000).fit((design - mean) / scale, is_child)
    return ClinicSpeakerHead(mean, scale, model.coef_[0].astype(float), float(model.intercept_[0]))


@dataclass
class LabelledSession:
    """One attested session: a feature row and the therapist's label per utterance."""

    session_id: str
    child_id: str
    design: np.ndarray
    is_child: np.ndarray


@dataclass
class TrainingResult:
    sessions: int
    children: int
    utterances: int
    adopted: bool
    reason: str
    model_accuracy: Optional[float] = None
    frame_accuracy: Optional[float] = None
    model_balanced: Optional[float] = None
    frame_balanced: Optional[float] = None
    head: Optional[ClinicSpeakerHead] = None
    sessions_needed: int = 0
    children_needed: int = 0
    per_child: dict = field(default_factory=dict)
    # Every training utterance (feature rows, child or not, a label to show), for explanations.
    examples: Optional[tuple] = None


def train_clinic_head(sessions: Iterable[LabelledSession]) -> TrainingResult:
    """Train on all sessions, after checking each child held out against the frame model."""
    sessions = [s for s in sessions if len(s.is_child)]
    children = sorted({s.child_id for s in sessions})
    utterances = sum(len(s.is_child) for s in sessions)
    sessions_needed = max(0, MIN_SESSIONS - len(sessions))
    children_needed = max(0, MIN_CHILDREN - len(children))
    labels = np.concatenate([s.is_child for s in sessions]) if sessions else np.zeros(0)
    if sessions_needed or children_needed:
        return TrainingResult(len(sessions), len(children), utterances, False, "not_enough_sessions",
                              sessions_needed=sessions_needed, children_needed=children_needed)
    if labels.min() == labels.max():
        return TrainingResult(len(sessions), len(children), utterances, False, "one_speaker_type")

    truth, model_says, frame_says = [], [], []
    per_child = {}
    for child in children:
        train = [s for s in sessions if s.child_id != child]
        test = [s for s in sessions if s.child_id == child]
        y_train = np.concatenate([s.is_child for s in train])
        if y_train.min() == y_train.max():
            return TrainingResult(len(sessions), len(children), utterances, False, "one_speaker_type")
        head = fit_head(np.vstack([s.design for s in train]), y_train)
        design, y = np.vstack([s.design for s in test]), np.concatenate([s.is_child for s in test])
        model_child, frame_child = head.margins(design) > 0, frame_margins(design) > 0
        per_child[child] = {
            "utterances": int(len(y)), "model_right": int((model_child == y).sum()), "frame_right": int((frame_child == y).sum()),
        }
        truth.append(y)
        model_says.append(model_child)
        frame_says.append(frame_child)

    y, model_child, frame_child = np.concatenate(truth), np.concatenate(model_says), np.concatenate(frame_says)
    model_balanced, frame_balanced = balanced_accuracy(model_child, y), balanced_accuracy(frame_child, y)
    adopted = model_balanced >= frame_balanced + ADOPT_MARGIN
    return TrainingResult(
        len(sessions), len(children), utterances, adopted,
        "better_than_frame_model" if adopted else "not_better_than_frame_model",
        model_accuracy=float((model_child == y).mean()), frame_accuracy=float((frame_child == y).mean()),
        model_balanced=model_balanced, frame_balanced=frame_balanced,
        head=fit_head(np.vstack([s.design for s in sessions]), labels),
        per_child=per_child,
    )


def examples_path(path: Path) -> Path:
    return Path(path).with_suffix(".examples.npz")


def save_examples(path: Path, head: ClinicSpeakerHead, design: np.ndarray, is_child: np.ndarray, labels: list) -> None:
    """Keep the training utterances beside the model, standardised as the model sees them."""
    rows = ((design - head.mean) / head.scale).astype("float16")
    np.savez_compressed(examples_path(path), rows=rows, is_child=is_child.astype("int8"), labels=np.array(labels))


def save_result(path: Path, result: TrainingResult, *, trained_at: str) -> None:
    data = {
        "format": FORMAT_VERSION,
        "trained_at": trained_at,
        "adopted": result.adopted,
        "reason": result.reason,
        "sessions": result.sessions,
        "children": result.children,
        "utterances": result.utterances,
        "model_accuracy": result.model_accuracy,
        "frame_accuracy": result.frame_accuracy,
        "model_balanced": result.model_balanced,
        "frame_balanced": result.frame_balanced,
        "sessions_needed": result.sessions_needed,
        "children_needed": result.children_needed,
        "per_child": result.per_child,
        "head": result.head.to_dict() if result.head else None,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(path)


def read_result(path: Path) -> Optional[dict]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) and data.get("format") == FORMAT_VERSION else None


def load_adopted_head(path: Optional[Path | str] = None) -> Optional[ClinicSpeakerHead]:
    """The clinic model named by ``PASASCOPE_CLINIC_SPEAKER_MODEL``, if it was adopted."""
    path = path or os.environ.get(CLINIC_MODEL_ENV, "").strip()
    if not path:
        return None
    data = read_result(Path(path))
    if not data or not data.get("adopted") or not data.get("head"):
        return None
    try:
        head = ClinicSpeakerHead.from_dict(data["head"])
    except (KeyError, TypeError, ValueError):
        return None
    try:
        with np.load(examples_path(Path(path))) as stored:
            head.examples = ClinicExamples(stored["rows"].astype("float32"), stored["is_child"], list(stored["labels"]))
    except (OSError, KeyError, ValueError):
        pass  # explanations then give the probabilities only
    return head
