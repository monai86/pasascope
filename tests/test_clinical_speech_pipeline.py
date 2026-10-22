from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.clinical_speech.chat_exporter import (  # noqa: E402
    ChatExportMetadata,
    build_reviewed_chat_export,
    format_chat_time,
    format_media_marker,
    parse_chat_to_lines,
)
from src.clinical_speech.feature_extractor import extract_clinical_features  # noqa: E402
from src.clinical_speech.models import NormalizedTranscriptLine  # noqa: E402


def _lines(reviewed: bool = True) -> list[NormalizedTranscriptLine]:
    return [
        NormalizedTranscriptLine(
            session_id="SESSION-X",
            speaker_code="INV",
            speaker_role="therapist",
            start_ms=0,
            end_ms=1000,
            text="what do you want ?",
            is_reviewed=reviewed,
            line_id="L1",
            line_number=1,
        ),
        NormalizedTranscriptLine(
            session_id="SESSION-X",
            speaker_code="CHI",
            speaker_role="child",
            start_ms=1400,
            end_ms=2400,
            text="want cookie .",
            reviewed_text="you want cookie .",
            is_reviewed=reviewed,
            line_id="L2",
            line_number=2,
        ),
        NormalizedTranscriptLine(
            session_id="SESSION-X",
            speaker_code="CHI",
            speaker_role="child",
            start_ms=5000,
            end_ms=5600,
            text="cookie cookie .",
            is_reviewed=reviewed,
            line_id="L3",
            line_number=3,
        ),
        NormalizedTranscriptLine(
            session_id="SESSION-X",
            speaker_code="MOT",
            speaker_role="parent",
            start_ms=6200,
            end_ms=7200,
            text="good talking .",
            is_reviewed=reviewed,
            line_id="L4",
            line_number=4,
        ),
    ]


def test_timestamp_formatting_and_media_marker():
    assert format_chat_time(3723456) == "01:02:03.456"
    assert format_media_marker(1400, 2400) == "\x151400_2400\x15"


def test_chat_export_uses_reviewed_text_and_media_bullets():
    chat = build_reviewed_chat_export(
        _lines(),
        metadata=ChatExportMetadata(
            session_id="SESSION-X",
            media_filename="session.wav",
            child_id="CHI-A01",
            child_age_months=48,
            child_sex="female",
        ),
    )

    assert chat.startswith("@UTF8\n@Begin\n")
    assert "@Languages:\teng" in chat
    assert "@Participants:" in chat
    assert "@Media:\tsession, audio" in chat
    assert "*CHI:\tyou want cookie . \x151400_2400\x15" in chat
    assert "*CHI:\twant cookie ." not in chat
    assert chat.endswith("@End\n")


def test_chat_export_blocks_unreviewed_lines_by_default():
    try:
        build_reviewed_chat_export(
            _lines(reviewed=False),
            metadata=ChatExportMetadata(session_id="SESSION-X"),
        )
    except ValueError as exc:
        assert "review sign-off" in str(exc)
    else:
        raise AssertionError("Expected unreviewed export to fail.")


def test_parse_chat_to_lines_supports_media_bullets_and_tim_tiers():
    chat = (
        "@Begin\n"
        "@Languages:\teng\n"
        "*CHI:\thello . \x15100_900\x15\n"
        "*INV:\ttell me more .\n"
        "%tim:\t00:00:01.000-00:00:02.250\n"
        "@End\n"
    )
    lines = parse_chat_to_lines(chat, session_id="SESSION-X")

    assert len(lines) == 2
    assert lines[0].speaker_code == "CHI"
    assert lines[0].start_ms == 100
    assert lines[0].end_ms == 900
    assert lines[1].speaker_code == "INV"
    assert lines[1].start_ms == 1000
    assert lines[1].end_ms == 2250


def test_feature_extraction_labels_possible_markers_for_review():
    features = extract_clinical_features(_lines(), age_months=48)

    assert features["core_features"]["total_utterances"] == 2
    assert features["core_features"]["total_words"] == 5
    assert features["core_features"]["pronoun_reversal_count"] == 1
    assert features["core_features"]["echolalia_count"] >= 1
    assert features["optional_indicators"]["therapist_utterances"] == 1
    assert features["optional_indicators"]["caregiver_utterances"] == 1
    assert features["optional_indicators"]["response_latency_avg"] == 0.4
    assert all(flag["label"] == "possible" for flag in features["review_flags"])
    assert all(flag["requires_clinician_review"] is True for flag in features["review_flags"])
    assert "does not diagnose ASD" in features["safety_labels"]
