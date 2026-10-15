"""Digits in Thai ASR drafts are written as spoken Thai words."""
from __future__ import annotations

import pytest

from src.audio_pipeline.segmentation import spell_out_thai_numbers
from src.audio_pipeline.whisper_transcribe import UtteranceSegment, WordSegment


def _utterance(text: str, language: str | None = "th") -> UtteranceSegment:
    return UtteranceSegment(
        start=0.0,
        end=1.0,
        text=text,
        words=[WordSegment(piece, 0.0, 1.0, 0.9, language) for piece in text.split()],
        language=language,
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("มี 5 คัน", "มี ห้า คัน"),
        ("ชนิดราคา 5 ละ 100 ดอลลาร์", "ชนิดราคา ห้า ละ หนึ่งร้อย ดอลลาร์"),
        ("ศตวรรษที่ 1,800", "ศตวรรษที่ หนึ่งพันแปดร้อย"),
        ("สูง 1.5 เมตร", "สูง หนึ่งจุดห้า เมตร"),
        ("ไม่มีตัวเลข", "ไม่มีตัวเลข"),
    ],
)
def test_thai_digits_become_words(text, expected):
    [result] = spell_out_thai_numbers([_utterance(text)])

    assert result.text == expected
    assert " ".join(w.text for w in result.words) == expected


def test_english_digits_are_left_alone():
    [result] = spell_out_thai_numbers([_utterance("I have 5 cars", language="en")])

    assert result.text == "I have 5 cars"
