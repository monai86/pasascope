"""Language sample measures computed the way CLAN's KIDEVAL computes them.

Input is one :class:`~packages.cha.clan_words.MainTierAnalysis` per child
utterance, in transcript order, with the utterance's ``%mor`` tier when it
has one. Word-level rules live in :mod:`packages.cha.clan_words`; this module
only aggregates.

* ``Total_Utts``: utterances with at least one countable word, not excluded.
* ``MLU_Utts`` / ``MLU_Words``: as above, also without ``xxx``/``yyy``/
  ``www``/``[+ mlue]``; a ``+,`` line joins the interrupted utterance before
  it. The standard deviation uses CLAN's formula
  ``sqrt(sum(len^2)/n - mean(len)^2)`` and is undefined for one utterance.
  Like CLAN, a joined ``+,`` line adds its own square to ``sum(len^2)``
  rather than enlarging the square of the utterance it joins.
* ``MLU50``: the first 50 MLU utterances.
* ``FREQ_tokens`` / ``FREQ_types`` / TTR: countable words of every included
  utterance. Like KIDEVAL, ``%mor`` lemmas are used when the utterance has a
  ``%mor`` tier, otherwise the spoken word forms.
* ``NDW_100``: different words in the first 100 tokens.
* MATTR: mean TTR of every 50-token window (CLAN FREQ ``+b50``).
* VOCD ``D``: for each sample size 35..50, the mean TTR of 100 random samples
  drawn without replacement; ``D`` is the value whose curve
  ``TTR = D/N (sqrt(1 + 2N/D) - 1)`` best fits those means (least squares),
  averaged over 3 trials. The random generator is seeded so the same sample
  always gives the same ``D``.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import math
import random
from typing import Iterable, Sequence

from packages.cha.clan_words import MainTierAnalysis, mor_stems

MLU50_UTTERANCES = 50
NDW_WINDOW = 100
MATTR_WINDOW = 50
VOCD_MIN_SAMPLE = 35
VOCD_MAX_SAMPLE = 50
VOCD_SAMPLES = 100
VOCD_TRIALS = 3
VOCD_SEED = 20261016
# KIDEVAL's minimum for DSS and IPSyn; used here as the advised sample size.
RECOMMENDED_UTTERANCES = 50


@dataclass(frozen=True)
class LanguageSampleMeasures:
    total_utterances: int
    mlu_utterances: int
    mlu_word_total: int
    mlu_words: float | None
    mlu_words_sd: float | None
    mlu50_utterances: int
    mlu50_words: float | None
    freq_tokens: int
    freq_types: int
    ttr: float | None
    ndw_100: int | None
    mattr: float | None
    vocd_d: float | None
    repetitions: int
    retracings: int
    word_errors: int
    utterance_errors: int
    excluded_utterances: int
    lexical_unit: str
    """``word`` (spoken forms), ``lemma`` (%mor) or ``mixed``."""


def compute_language_sample_measures(
    utterances: Sequence[MainTierAnalysis],
    mor_tiers: Sequence[str | None] | None = None,
    *,
    vocd_seed: int = VOCD_SEED,
    kideval_exclusions: bool = True,
    include_vocd: bool = True,
) -> LanguageSampleMeasures:
    """Aggregate per-utterance analyses into KIDEVAL's measures.

    ``kideval_exclusions=False`` reproduces CLAN's stand-alone ``mlu`` and
    ``freq`` commands instead, which keep ``[+ exc]`` utterances and count the
    other words of a ``www`` utterance in FREQ. ``include_vocd=False`` skips
    the random sampling for live previews.
    """
    mor_tiers = list(mor_tiers) if mor_tiers is not None else [None] * len(utterances)
    lengths: list[int] = []
    squares = 0
    total = 0
    excluded = 0
    can_continue = False
    tokens: list[str] = []
    units: set[str] = set()

    for analysis, mor in zip(utterances, mor_tiers):
        if kideval_exclusions and analysis.excluded:
            excluded += 1
            continue
        if mor and mor.strip():
            tokens.extend(mor_stems(mor))
            units.add("lemma")
        else:
            tokens.extend(analysis.words)
            units.add("word")
        count = len(analysis.words)
        if count == 0:
            continue
        joins = analysis.self_completion and can_continue
        if not joins:
            total += 1
        if analysis.has_www or analysis.has_unintelligible or "mlue" in analysis.postcodes:
            continue
        if joins and lengths:
            lengths[-1] += count
        else:
            lengths.append(count)
        squares += count * count
        can_continue = analysis.continues

    mlu50 = lengths[:MLU50_UTTERANCES]
    types = len(set(tokens))
    return LanguageSampleMeasures(
        total_utterances=total,
        mlu_utterances=len(lengths),
        mlu_word_total=sum(lengths),
        mlu_words=_mean(lengths),
        mlu_words_sd=_clan_sd(lengths, squares),
        mlu50_utterances=len(mlu50),
        mlu50_words=_mean(mlu50),
        freq_tokens=len(tokens),
        freq_types=types,
        ttr=round(types / len(tokens), 4) if tokens else None,
        ndw_100=len(set(tokens[:NDW_WINDOW])) if len(tokens) >= NDW_WINDOW else None,
        mattr=mattr(tokens),
        vocd_d=vocd_d(tokens, seed=vocd_seed) if include_vocd else None,
        repetitions=sum(item.repetitions for item in utterances),
        retracings=sum(item.retracings for item in utterances),
        word_errors=sum(item.word_errors for item in utterances),
        utterance_errors=sum(item.utterance_errors for item in utterances),
        excluded_utterances=excluded,
        lexical_unit="mixed" if len(units) > 1 else (units.pop() if units else "word"),
    )


def mattr(tokens: Sequence[str], window: int = MATTR_WINDOW) -> float | None:
    """Moving-average TTR over every full window; None if the sample is shorter."""
    if len(tokens) < window:
        return None
    counts = Counter(tokens[:window])
    total = len(counts)
    for index in range(window, len(tokens)):
        leaving, entering = tokens[index - window], tokens[index]
        counts[leaving] -= 1
        if counts[leaving] == 0:
            del counts[leaving]
        counts[entering] += 1
        total += len(counts)
    return round(total / ((len(tokens) - window + 1) * window), 4)


def vocd_d(tokens: Sequence[str], *, seed: int = VOCD_SEED) -> float | None:
    """VOCD's D_optimum average; None with fewer tokens than the largest sample."""
    if len(tokens) < VOCD_MAX_SAMPLE:
        return None
    rng = random.Random(seed)
    sizes = range(VOCD_MIN_SAMPLE, VOCD_MAX_SAMPLE + 1)
    trials = []
    for _ in range(VOCD_TRIALS):
        curve = [(n, _mean_sampled_ttr(tokens, n, rng)) for n in sizes]
        starts = [_d_from_point(n, t) for n, t in curve]
        starts = [d for d in starts if d > 0]
        if not starts:
            return None
        trials.append(_best_d(curve, sum(starts) / len(starts)))
    return round(sum(trials) / len(trials), 2)


def _mean_sampled_ttr(tokens: Sequence[str], n: int, rng: random.Random) -> float:
    population = range(len(tokens))
    total = 0.0
    for _ in range(VOCD_SAMPLES):
        total += len({tokens[i] for i in rng.sample(population, n)}) / n
    return total / VOCD_SAMPLES


def _d_from_point(n: int, ttr: float) -> float:
    """D for one (N, TTR) point; CLAN discards points where TTR is 1."""
    return 0.0 if ttr >= 1.0 else 0.5 * n * ttr * ttr / (1.0 - ttr)


def _ttr_curve(d: float, n: int) -> float:
    return (d / n) * (math.sqrt(1.0 + 2.0 * n / d) - 1.0)


def _squared_error(d: float, curve: Iterable[tuple[int, float]]) -> float:
    return sum((ttr - _ttr_curve(d, n)) ** 2 for n, ttr in curve)


def _best_d(curve: list[tuple[int, float]], start: float) -> float:
    """Least-squares D in (0, 2*start], where CLAN's 0.001-step search looks."""
    low, high = 1e-6, 2.0 * start
    ratio = (math.sqrt(5.0) - 1.0) / 2.0
    left, right = high - ratio * (high - low), low + ratio * (high - low)
    f_left, f_right = _squared_error(left, curve), _squared_error(right, curve)
    while high - low > 1e-4:
        if f_left < f_right:
            high, right, f_right = right, left, f_left
            left = high - ratio * (high - low)
            f_left = _squared_error(left, curve)
        else:
            low, left, f_left = left, right, f_right
            right = low + ratio * (high - low)
            f_right = _squared_error(right, curve)
    return (low + high) / 2.0


def _mean(values: Sequence[int]) -> float | None:
    return round(sum(values) / len(values), 4) if values else None


def _clan_sd(values: Sequence[int], squares: int) -> float | None:
    if len(values) < 2:
        return None
    mean = sum(values) / len(values)
    variance = squares / len(values) - mean * mean
    return round(math.sqrt(variance), 4) if variance >= 0 else None
