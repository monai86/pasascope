"""
Re-segmentation: align ASR words against VAD regions and speaker turns.

Whisper segments often span speaker changes ("hello — yeah!") or get
cut mid-word.  This module produces clean ``UtteranceSegment``s by:

1. Treating speaker-turn boundaries as hard splits
2. Treating long silences (from VAD) as soft splits
3. Dropping segments < 0.2 s (likely noise)
4. Merging adjacent same-speaker segments < 0.3 s apart

The output is consumed by the CHAT formatter.
"""

from __future__ import annotations

import re
from dataclasses import replace
from typing import List, Optional, Sequence, Tuple

from .whisper_transcribe import UtteranceSegment, WordSegment


# ----------------------------------------------------------------------
# Tunables
# ----------------------------------------------------------------------
MIN_SEGMENT_DURATION = 0.2          # seconds — drop if shorter
# A same-speaker pause over 0.6 s ends an utterance; shorter pauses stay
# inside it, because young children pause mid-utterance. Gaps tried on 16
# EllisWeismer (2;6-5;6) and 8 ENNI (4;9-6;10) recordings, draft MLU distance
# from the gold: 0.3 s 0.73 / 1.78 words, 0.6 s 0.59 / 1.69, 1 s 0.55 / 2.03
# (ENNI children speak fluently and 1 s joined separate utterances).
MAX_INTRA_TURN_GAP = 0.6            # seconds — merge same-speaker if gap < this
MIN_GAP_FOR_SPLIT = 0.6             # seconds — split same-speaker if gap > this
# Pause that may hide a change of speaker. Whisper often returns a whole
# exchange as one segment, and a segment can only get one speaker label, so
# segments are cut at these pauses before speakers are assigned. In scripted
# Thai dialogues word gaps inside a turn were at most 0.12 s and gaps between
# turns at least 0.30 s; 0.25 s sits between the two.
PRE_DIARIZATION_SPLIT_GAP = 0.25


# Speaker labels the app shows without a "?" (local_whisper_provider).
_CONFIDENT_BASES = ("voice", "frame")


def least_certain_basis(bases: Sequence[Optional[str]]) -> Optional[str]:
    """An utterance made of several pieces is only as certain as its least certain piece."""
    unsure = [basis for basis in bases if basis not in _CONFIDENT_BASES]
    return unsure[0] if unsure else (bases[0] if bases else None)


def _merged_basis(a: UtteranceSegment, b: UtteranceSegment) -> Optional[str]:
    return least_certain_basis([a.speaker_basis, b.speaker_basis])


def _merge_segments(a: UtteranceSegment, b: UtteranceSegment) -> UtteranceSegment:
    """Merge two same-speaker UtteranceSegments into one."""
    return UtteranceSegment(
        start=min(a.start, b.start),
        end=max(a.end, b.end),
        text=(a.text + " " + b.text).strip(),
        words=list(a.words) + list(b.words),
        avg_logprob=(a.avg_logprob + b.avg_logprob) / 2,
        no_speech_prob=max(a.no_speech_prob, b.no_speech_prob),
        speaker=a.speaker,
        speaker_basis=_merged_basis(a, b),
        language=a.language or b.language,
        speaker_reason=a.speaker_reason or b.speaker_reason,
        # Words from a flagged piece may be noise, so the whole line is flagged.
        speech_reason=a.speech_reason or b.speech_reason,
    )


def _is_thai(text: str) -> bool:
    return any("\u0e00" <= char <= "\u0e7f" for char in text)


def _join_word_pieces(words: Sequence[WordSegment]) -> str:
    """Rebuild utterance text from Whisper word pieces.

    Thai is written without spaces and Whisper returns it as sub-word pieces,
    so neighbouring Thai pieces are joined directly; everything else keeps a
    space between words.
    """
    text = ""
    previous = ""
    for word in words:
        piece = word.text.strip()
        if not piece:
            continue
        if text and not (_is_thai(previous) and _is_thai(piece)):
            text += " "
        text += piece
        previous = piece
    return text


# How many word pieces a cut may move to reach a Thai word boundary.
MAX_CUT_SHIFT = 3


def _thai_word_boundaries(pieces: Sequence[str]) -> set[int]:
    """Character offsets in the joined pieces where a Thai word starts or ends."""
    from pythainlp.tokenize import word_tokenize

    offsets, position = {0}, 0
    for token in word_tokenize("".join(pieces), engine="newmm", keep_whitespace=False):
        position += len(token)
        offsets.add(position)
    return offsets


def _snap_cuts_to_thai_words(words: Sequence[WordSegment], cuts: List[int]) -> List[int]:
    """Move cuts that fall inside a Thai word to the nearest word boundary.

    Whisper returns Thai as sub-word pieces and times each piece, so a pause
    can be measured between "ครั" and "บ"; cutting there sends half a word to
    the next speaker. Cuts move forward first (the tail of a word was said
    with its head), at most ``MAX_CUT_SHIFT`` pieces.
    """
    pieces = [w.text.strip() for w in words]
    if not any(_is_thai(p) for p in pieces):
        return cuts
    boundaries = _thai_word_boundaries(pieces)
    starts = [0]
    for piece in pieces:
        starts.append(starts[-1] + len(piece))
    snapped: List[int] = []
    for cut in cuts:
        if starts[cut] in boundaries or not (_is_thai(pieces[cut - 1]) and _is_thai(pieces[cut])):
            snapped.append(cut)
            continue
        candidates = [cut + d for d in range(1, MAX_CUT_SHIFT + 1)] + [cut - d for d in range(1, MAX_CUT_SHIFT + 1)]
        target = next((c for c in candidates if 0 < c < len(pieces) and starts[c] in boundaries), cut)
        snapped.append(target)
    return sorted(set(snapped))


def _split_at_long_silences(
    seg: UtteranceSegment,
    min_gap: float = MIN_GAP_FOR_SPLIT,
) -> List[UtteranceSegment]:
    """Split a single segment wherever the gap between consecutive words exceeds min_gap."""
    if len(seg.words) < 2:
        return [seg]

    cuts = [
        index
        for index in range(1, len(seg.words))
        if seg.words[index].start - seg.words[index - 1].end > min_gap
    ]
    if not cuts:
        return [seg]
    cuts = _snap_cuts_to_thai_words(seg.words, cuts)
    bounds = [0, *cuts, len(seg.words)]
    groups: List[List[WordSegment]] = [list(seg.words[a:b]) for a, b in zip(bounds, bounds[1:]) if b > a]

    if len(groups) == 1:
        return [seg]

    out: List[UtteranceSegment] = []
    for grp in groups:
        if not grp:
            continue
        text = _join_word_pieces(grp)
        out.append(UtteranceSegment(
            start=grp[0].start,
            end=grp[-1].end,
            text=text,
            words=grp,
            avg_logprob=seg.avg_logprob,
            no_speech_prob=seg.no_speech_prob,
            speaker=seg.speaker,
            speaker_basis=seg.speaker_basis,
            language=seg.language,
            speaker_reason=seg.speaker_reason,
            speech_reason=seg.speech_reason,
        ))
    return out


_NUMBER_RE = re.compile(r"\d+(?:,\d{3})*(?:\.\d+)?")


def _thai_number_words(match: re.Match) -> str:
    from pythainlp.util import num_to_thaiword

    whole, _, fraction = match.group(0).replace(",", "").partition(".")
    words = num_to_thaiword(int(whole))
    if fraction:
        words += "จุด" + "".join(num_to_thaiword(int(digit)) for digit in fraction)
    return words


def spell_out_thai_numbers(utterances: Sequence[UtteranceSegment]) -> List[UtteranceSegment]:
    """Write digits in Thai utterances as Thai words ("5" -> "ห้า").

    CHAT transcribes numbers as spoken words, and word counts should count
    "หนึ่งร้อย" the way the child said it rather than as one "100" token.
    Batchalign does the same for its languages. English utterances are left
    unchanged.
    """
    out: List[UtteranceSegment] = []
    for u in utterances:
        if not (_is_thai(u.text) or u.language == "th") or not _NUMBER_RE.search(u.text):
            out.append(u)
            continue
        out.append(replace(
            u,
            text=_NUMBER_RE.sub(_thai_number_words, u.text),
            words=[replace(w, text=_NUMBER_RE.sub(_thai_number_words, w.text)) for w in u.words],
        ))
    return out


def drop_short_segments(
    utterances: Sequence[UtteranceSegment],
    min_duration: float = MIN_SEGMENT_DURATION,
) -> List[UtteranceSegment]:
    """Remove recogniser segments too short to be speech (likely noise)."""
    return [u for u in utterances if (u.end - u.start) >= min_duration]


def split_at_pauses(
    utterances: Sequence[UtteranceSegment],
    min_gap: float = PRE_DIARIZATION_SPLIT_GAP,
) -> List[UtteranceSegment]:
    """Cut each segment wherever consecutive words are more than ``min_gap`` apart.

    Run this before speaker assignment so that each side of a pause can get
    its own speaker; ``clean_segments`` re-joins neighbours that turn out to
    belong to the same speaker.
    """
    pieces: List[UtteranceSegment] = []
    for utterance in sorted(utterances, key=lambda u: u.start):
        pieces.extend(_split_at_long_silences(utterance, min_gap=min_gap))
    return pieces


def clean_segments(
    utterances: Sequence[UtteranceSegment],
    *,
    min_duration: float = MIN_SEGMENT_DURATION,
    intra_turn_gap: float = MAX_INTRA_TURN_GAP,
    split_silence_gap: float = MIN_GAP_FOR_SPLIT,
) -> List[UtteranceSegment]:
    """Apply post-processing rules to a list of utterances.

    1. Drop too-short segments (likely noise)
    2. Split utterances at long internal silences
    3. Merge adjacent same-speaker utterances with very short gaps

    Speaker labels are required (run diarization first).
    """
    # Sort by start time
    segs = sorted(utterances, key=lambda u: u.start)

    # Drop too-short
    segs = [s for s in segs if (s.end - s.start) >= min_duration]

    # Split at long silences within a single utterance
    expanded: List[UtteranceSegment] = []
    for s in segs:
        expanded.extend(_split_at_long_silences(s, min_gap=split_silence_gap))

    # Merge same-speaker neighbours that are too close
    merged: List[UtteranceSegment] = []
    for s in expanded:
        if (
            merged
            and merged[-1].speaker == s.speaker
            and (s.start - merged[-1].end) < intra_turn_gap
        ):
            merged[-1] = _merge_segments(merged[-1], s)
        else:
            merged.append(s)

    return merged


def filter_to_speech_regions(
    utterances: Sequence[UtteranceSegment],
    speech_regions: Sequence[Tuple[float, float]],
    *,
    min_overlap_ratio: float = 0.3,
) -> List[UtteranceSegment]:
    """Keep only utterances that overlap with at least one VAD speech region.

    Useful when you have a high-quality VAD (e.g. silero) and want to
    discard Whisper segments that fell entirely on silence/noise.
    """
    if not speech_regions:
        return list(utterances)

    out: List[UtteranceSegment] = []
    for u in utterances:
        u_dur = max(0.0, u.end - u.start) or 1e-6
        # Compute total overlap with any speech region
        overlap = sum(
            max(0.0, min(u.end, e) - max(u.start, s))
            for s, e in speech_regions
        )
        if overlap / u_dur >= min_overlap_ratio:
            out.append(u)
    return out
