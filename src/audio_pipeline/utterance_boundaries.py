"""Decide where one speaker's utterance ends, with features a therapist can read.

After speaker attribution the draft is a run of timed words per speaker.
Between two words of the same speaker the app has to decide: same utterance
or a new one? MLU depends on that choice. A fixed pause rule cut children's
utterances in the wrong places (reports/metrics/end_to_end_summary.md), so
this module scores every gap with a logistic regression on named features:

* ``pause``: log of the silence between the two words;
* ``sentence_mark``: Whisper wrote . ? or ! after the first word;
* ``comma``: Whisper wrote a comma after it;
* ``capital_next``: Whisper capitalised the next word (not "I");
* ``ends_utterances``: how often the first word ends an utterance in CHAT
  transcripts, as log-odds against the average word;
* ``starts_utterances``: the same for the next word starting one;
* ``lengthening``: the first word's duration against the recording's usual
  time per letter, as a log ratio.

Pitch was tried too (the slope over a word's end and the jump to the next
word) and carried no weight: on 32 recordings held out one at a time, pause,
pitch and lengthening together reached boundary F1 0.66, the same as the
pause alone, while the word features reached 0.81. It is left out.

The model stores each feature's mean, scale and weight, so every decision
can be explained as the sum of feature contributions (``explain``). The
word statistics come from TalkBank CHAT transcripts; see
``scripts/train_utterance_boundaries.py``, which trains and evaluates it.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import json
import math
from pathlib import Path
import re
from typing import Iterable, List, Optional, Sequence

import numpy as np

FEATURES = (
    "pause", "sentence_mark", "comma", "capital_next", "ends_utterances",
    "starts_utterances", "lengthening",
)
FEATURE_LABELS_TH = {
    "pause": "ช่วงหยุด",
    "sentence_mark": "Whisper ใส่จุดจบประโยค",
    "comma": "Whisper ใส่จุลภาค",
    "capital_next": "คำถัดไปขึ้นต้นด้วยตัวใหญ่",
    "ends_utterances": "คำนี้มักอยู่ท้ายประโยค",
    "starts_utterances": "คำถัดไปมักขึ้นต้นประโยค",
    "lengthening": "ลากเสียงคำสุดท้าย",
}
FORMAT_VERSION = 1
# Words seen fewer times than this get no word statistic (0 = average word).
MIN_WORD_COUNT = 20
# Additive smoothing toward the average rate, in pseudo-occurrences.
SMOOTHING = 20.0
DEFAULT_MODEL_PATH = Path(__file__).resolve().parent / "models" / "utterance_boundaries_en.json"

_CODE_RE = re.compile(r"\[[^\]]*\]|\x15\d+_\d+\x15|&[-=+~]?\S+|\b(?:xxx|yyy|www)\b|@\S+|\(\.+\)")
_WORD_RE = re.compile(r"[a-z]+(?:'[a-z]+)?")


def words_of(text: str) -> List[str]:
    """Lower-case words of a CHAT main tier or a Whisper word, without CHAT codes or punctuation."""
    return _WORD_RE.findall(_CODE_RE.sub(" ", text or "").lower().replace("_", " "))


# ----------------------------------------------------------------------
# Word statistics from CHAT transcripts
# ----------------------------------------------------------------------
@dataclass
class WordStatistics:
    """How often each word starts or ends an utterance, as smoothed log-odds against the average word."""

    end_log_odds: dict = field(default_factory=dict)
    start_log_odds: dict = field(default_factory=dict)
    utterances: int = 0

    @classmethod
    def from_utterances(cls, utterances: Iterable[str]) -> "WordStatistics":
        total, ends, starts = Counter(), Counter(), Counter()
        count = 0
        for text in utterances:
            words = words_of(text)
            if not words:
                continue
            count += 1
            total.update(words)
            ends[words[-1]] += 1
            starts[words[0]] += 1
        tokens = sum(total.values()) or 1
        end_rate, start_rate = count / tokens, count / tokens

        def log_odds(hits: Counter, rate: float) -> dict:
            table = {}
            for word, n in total.items():
                if n < MIN_WORD_COUNT:
                    continue
                p = (hits[word] + SMOOTHING * rate) / (n + SMOOTHING)
                table[word] = round(math.log(p / (1 - p)) - math.log(rate / (1 - rate)), 3)
            return table

        return cls(log_odds(ends, end_rate), log_odds(starts, start_rate), count)

    @classmethod
    def from_chat_files(cls, paths: Iterable[Path]) -> "WordStatistics":
        def lines():
            for path in paths:
                try:
                    content = Path(path).read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                for line in content.splitlines():
                    if line.startswith("*") and ":\t" in line:
                        yield line.split(":\t", 1)[1]
        return cls.from_utterances(lines())


# ----------------------------------------------------------------------
# Gap features
# ----------------------------------------------------------------------
@dataclass
class Word:
    text: str
    start: float
    end: float


def gap_features(words: Sequence[Word], index: int, statistics: WordStatistics, *,
                 seconds_per_letter: float = 0.08) -> dict:
    """Features of the gap between ``words[index]`` and ``words[index + 1]``."""
    first, nxt = words[index], words[index + 1]
    raw_first, raw_next = first.text.strip(), nxt.text.strip()
    first_words, next_words = words_of(raw_first), words_of(raw_next)
    letters = max(1, sum(len(w) for w in first_words))
    return {
        "pause": math.log(max(0.0, nxt.start - first.end) + 0.05),
        "sentence_mark": float(raw_first.endswith((".", "?", "!"))),
        "comma": float(raw_first.endswith(",")),
        "capital_next": float(bool(raw_next[:1].isupper()) and next_words[:1] not in (["i"], ["i'm"], ["i'll"], ["i've"], ["i'd"])),
        "ends_utterances": statistics.end_log_odds.get(first_words[-1], 0.0) if first_words else 0.0,
        "starts_utterances": statistics.start_log_odds.get(next_words[0], 0.0) if next_words else 0.0,
        "lengthening": math.log(max(first.end - first.start, 0.02) / (letters * seconds_per_letter)),
    }


def typical_seconds_per_letter(words: Sequence[Word]) -> float:
    rates = [(w.end - w.start) / n for w in words if (n := sum(len(x) for x in words_of(w.text))) and w.end > w.start]
    return float(np.median(rates)) if rates else 0.08


# ----------------------------------------------------------------------
# The model
# ----------------------------------------------------------------------
@dataclass
class BoundaryModel:
    mean: np.ndarray
    scale: np.ndarray
    weights: np.ndarray
    intercept: float
    statistics: WordStatistics
    threshold: float = 0.5
    trained_on: str = ""

    def contributions(self, features: dict) -> dict:
        """Each feature's push toward a boundary (+) or against it (-), in log-odds."""
        values = np.array([features[name] for name in FEATURES])
        return dict(zip(FEATURES, ((values - self.mean) / self.scale * self.weights).round(3)))

    def probability(self, features: dict) -> float:
        z = self.intercept + sum(self.contributions(features).values())
        return 1.0 / (1.0 + math.exp(-z))

    def explain(self, features: dict, top: int = 3) -> str:
        """The strongest reasons for this decision, in Thai, e.g. 'ช่วงหยุด +2.1, เสียงตกท้ายคำ +0.6'."""
        parts = sorted(self.contributions(features).items(), key=lambda kv: -abs(kv[1]))[:top]
        return ", ".join(f"{FEATURE_LABELS_TH[name]} {value:+.1f}" for name, value in parts)

    def to_dict(self) -> dict:
        return {
            "format": FORMAT_VERSION, "features": list(FEATURES), "mean": self.mean.tolist(), "scale": self.scale.tolist(),
            "weights": self.weights.tolist(), "intercept": self.intercept, "threshold": self.threshold,
            "trained_on": self.trained_on, "word_statistics_utterances": self.statistics.utterances,
            "end_log_odds": self.statistics.end_log_odds, "start_log_odds": self.statistics.start_log_odds,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BoundaryModel":
        if data.get("format") != FORMAT_VERSION or list(data.get("features", [])) != list(FEATURES):
            raise ValueError("Unknown utterance boundary model format")
        statistics = WordStatistics(data["end_log_odds"], data["start_log_odds"], data.get("word_statistics_utterances", 0))
        return cls(np.asarray(data["mean"], float), np.asarray(data["scale"], float), np.asarray(data["weights"], float),
                   float(data["intercept"]), statistics, float(data.get("threshold", 0.5)), data.get("trained_on", ""))

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "BoundaryModel":
        return cls.from_dict(json.loads(Path(path or DEFAULT_MODEL_PATH).read_text(encoding="utf-8")))


def fit_boundary_model(rows: Sequence[dict], labels: Sequence[int], statistics: WordStatistics, *,
                       regularization: float = 1.0, trained_on: str = "") -> BoundaryModel:
    from sklearn.linear_model import LogisticRegression

    X = np.array([[row[name] for name in FEATURES] for row in rows], dtype=float)
    mean, scale = X.mean(axis=0), X.std(axis=0)
    scale[scale < 1e-8] = 1.0
    model = LogisticRegression(C=regularization, max_iter=2000).fit((X - mean) / scale, np.asarray(labels))
    return BoundaryModel(mean, scale, model.coef_[0], float(model.intercept_[0]), statistics, trained_on=trained_on)


# ----------------------------------------------------------------------
# Use in the pipeline
# ----------------------------------------------------------------------
BOUNDARIES_ENV = "PASASCOPE_UTTERANCE_BOUNDARIES"  # "rule" keeps the pause rule


def model_for(utterances) -> Optional[BoundaryModel]:
    """The English model for a mostly English draft; None for Thai (no Thai model yet) or when turned off."""
    import os

    if os.environ.get(BOUNDARIES_ENV, "").strip().lower() == "rule" or not DEFAULT_MODEL_PATH.is_file():
        return None
    text = " ".join(u.text or "" for u in utterances)
    thai = sum(1 for c in text if "฀" <= c <= "๿")
    latin = sum(1 for c in text if c.isascii() and c.isalpha())
    if latin == 0 or thai > latin:
        return None
    try:
        return BoundaryModel.load()
    except (OSError, ValueError, KeyError):
        return None


def describe_boundary(model: BoundaryModel, features: dict, probability: float, pause: float) -> str:
    return f"ขึ้นประโยคใหม่ (โอกาส {probability:.0%}, หยุด {pause:.1f} วินาที): {model.explain(features)}"


def segment_by_model(utterances, model: BoundaryModel):
    """Cut speaker-labelled pieces into utterances where the model sees a boundary.

    A change of speaker always ends an utterance. Each utterance that starts at
    a model decision carries the reasons in ``boundary_reason``.
    """
    from .segmentation import _join_word_pieces, least_certain_basis
    from .whisper_transcribe import UtteranceSegment

    pieces = sorted(utterances, key=lambda u: u.start)
    entries = [(piece, word) for piece in pieces for word in (piece.words or []) if (word.text or "").strip()]
    if not entries:
        return pieces
    words = [Word(w.text, w.start, w.end) for _, w in entries]
    per_letter = typical_seconds_per_letter(words)

    out, group, sources, reason = [], [], [], None

    def close(next_reason):
        nonlocal group, sources, reason
        basis = least_certain_basis([source.speaker_basis for source in sources])
        out.append(UtteranceSegment(
            start=group[0].start, end=group[-1].end, text=_join_word_pieces(group), words=list(group),
            avg_logprob=float(np.mean([s.avg_logprob for s in sources])), no_speech_prob=max(s.no_speech_prob for s in sources),
            speaker=sources[0].speaker, speaker_basis=basis, language=sources[0].language, boundary_reason=reason,
        ))
        group, sources, reason = [], [], next_reason

    for i, (piece, word) in enumerate(entries):
        group.append(word)
        if not sources or sources[-1] is not piece:
            sources.append(piece)
        if i == len(entries) - 1:
            close(None)
        elif entries[i + 1][0].speaker != piece.speaker:
            close(None)
        else:
            features = gap_features(words, i, model.statistics, seconds_per_letter=per_letter)
            probability = model.probability(features)
            if probability >= model.threshold:
                close(describe_boundary(model, features, probability, words[i + 1].start - words[i].end))
    return out
