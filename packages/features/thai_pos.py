"""Experimental part-of-speech counts for Thai child utterances.

CLAN's KIDEVAL reads verbs and other word classes from a %mor tier, which
Thai transcripts do not have. Here the countable words of each utterance
(see :mod:`packages.cha.clan_words`) are tagged with PyThaiNLP's perceptron
tagger trained on the Blackboard treebank. Tags used:

* ``VV`` verb (Thai adjectives are stative verbs, so สวย and แดง count);
* ``PR`` pronoun, including question words (อะไร, ไหน);
* ``PA`` sentence-final particle (ครับ, ค่ะ, จัง, นะ);
* ``NG`` negator (ไม่).

The tagger was trained on adult written Thai and has not been checked on
child speech, so these values are marked experimental and are not used for
review cues. The tagger model (about 6 MB) is downloaded by PyThaiNLP the
first time it is used; without it the values are not computed.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Sequence

from packages.cha.clan_words import MainTierAnalysis

_THAI = re.compile(r"[฀-๿]")
TAGGER_CORPUS = "blackboard"


@dataclass(frozen=True)
class ThaiPosCounts:
    utterances: int
    words: int
    verbs: int
    pronouns: int
    particles: int
    negators: int

    @property
    def verbs_per_utterance(self) -> float | None:
        return round(self.verbs / self.utterances, 4) if self.utterances else None


def thai_pos_counts(analyses: Sequence[MainTierAnalysis]) -> ThaiPosCounts | None:
    """Word-class counts over the MLU utterances that contain Thai; None if none or no tagger."""
    utterances = [a for a in analyses if not a.mlu_excluded and a.words and any(_THAI.search(w) for w in a.words)]
    if not utterances:
        return None
    try:
        from pythainlp.tag import pos_tag

        tagged = [pos_tag(list(a.words), corpus=TAGGER_CORPUS) for a in utterances]
    except Exception:  # noqa: BLE001 - tagger missing or its model could not be downloaded
        return None
    tags = [tag for sentence in tagged for _, tag in sentence]
    return ThaiPosCounts(
        utterances=len(utterances),
        words=len(tags),
        verbs=tags.count("VV"),
        pronouns=tags.count("PR"),
        particles=tags.count("PA"),
        negators=tags.count("NG"),
    )
