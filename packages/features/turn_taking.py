"""Turn-taking between the child and the adults in a language sample.

Three descriptive measures, each something a therapist can count by hand:

* ``child_responses``: adult utterances directly followed by a child
  utterance, the child taking up a turn the adult left (a conversational
  turn in the sense of LENA's adult-child turn count, here on transcript
  lines rather than audio).
* ``child_response_rate``: the same as a share of the adult utterances.
* ``mlt_ratio``: the child's mean words per turn over the adults' (a turn
  is a run of consecutive lines by one side), the turn-length ratio of
  Assaf et al. (2025, Scientific Reports 15:34134).

The Siriraj Medical Bulletin review of language in autism (2023) measures
progress in conversation practice by the number of complete exchanges, not
by sentence length; these measures put that on the page. They describe the
sample. They are not norms and not a screen.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

CHILD = "CHI"
ADULT = "ADULT"


@dataclass(frozen=True)
class TurnTaking:
    adult_utterances: int
    child_responses: int
    child_response_rate: float | None  # None without adult utterances
    child_words_per_turn: float | None
    adult_words_per_turn: float | None
    mlt_ratio: float | None  # None when either side has no words


def speaker_side(speaker: str) -> str | None:
    """CHI is the child; UNK (not yet assigned) is left out; every other speaker is an adult."""
    code = str(speaker).upper()
    if code == "CHI":
        return CHILD
    if code in {"UNK", ""}:
        return None
    return ADULT


def turn_taking(lines: Iterable[tuple[str | None, int]]) -> TurnTaking:
    """Measures from ``(side, countable words)`` per transcript line, in order.

    ``side`` is ``"CHI"``, ``"ADULT"`` or None (an unassigned line, skipped).
    """
    sides = [(side, max(0, int(words))) for side, words in lines if side in (CHILD, ADULT)]
    adult_lines = sum(1 for side, _ in sides if side == ADULT)
    responses = sum(1 for (left, _), (right, _) in zip(sides, sides[1:]) if left == ADULT and right == CHILD)

    turns: list[list] = []
    for side, words in sides:
        if turns and turns[-1][0] == side:
            turns[-1][1] += words
        else:
            turns.append([side, words])
    child_turns = [words for side, words in turns if side == CHILD]
    adult_turns = [words for side, words in turns if side == ADULT]
    child_mean = sum(child_turns) / len(child_turns) if child_turns else None
    adult_mean = sum(adult_turns) / len(adult_turns) if adult_turns else None
    ratio = child_mean / adult_mean if child_mean is not None and adult_mean else None
    return TurnTaking(
        adult_utterances=adult_lines,
        child_responses=responses,
        child_response_rate=responses / adult_lines if adult_lines else None,
        child_words_per_turn=child_mean,
        adult_words_per_turn=adult_mean,
        mlt_ratio=ratio,
    )
