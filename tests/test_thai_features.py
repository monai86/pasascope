from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from src.clinical_speech.feature_extractor import extract_clinical_features
from src.clinical_speech.models import NormalizedTranscriptLine


def test_thai_mlu_calculations():
    # Construct some child utterances in Thai
    lines = [
        NormalizedTranscriptLine(
            session_id="S1",
            speaker_code="CHI",
            speaker_role="child",
            start_ms=0,
            end_ms=1000,
            text="สวัสดีครับ",  # 3 syllables, 2 words ("สวัสดี", "ครับ")
            reviewed_text="สวัสดีครับ",
            is_reviewed=True,
            line_id="1",
            line_number=1,
        ),
        NormalizedTranscriptLine(
            session_id="S1",
            speaker_code="CHI",
            speaker_role="child",
            start_ms=1500,
            end_ms=3000,
            text="ไปเที่ยวกันไหม", # 4 syllables, 4 words ("ไป", "เที่ยว", "กัน", "ไหม")
            reviewed_text="ไปเที่ยวกันไหม",
            is_reviewed=True,
            line_id="2",
            line_number=2,
        )
    ]
    
    result = extract_clinical_features(lines)
    features = result["features"]
    
    assert "mlu_s" in features
    assert "mlu_w" in features
    
    # 7 syllables total, 2 utterances -> MLU-s = 3.5
    assert features["mlu_s"] == pytest.approx(3.5)
    
    # 5 words total ('สวัสดี', 'ครับ', 'ไปเที่ยว', 'กัน', 'ไหม'), 2 utterances -> MLU-w = 2.5
    assert features["mlu_w"] == pytest.approx(2.5)


def test_non_thai_mlu_calculations():
    # English only
    lines = [
        NormalizedTranscriptLine(
            session_id="S1",
            speaker_code="CHI",
            speaker_role="child",
            start_ms=0,
            end_ms=1000,
            text="hello world",
            reviewed_text="hello world",
            is_reviewed=True,
            line_id="1",
            line_number=1,
        )
    ]
    
    result = extract_clinical_features(lines)
    features = result["features"]
    
    assert features["mlu_s"] == 0.0
    assert features["mlu_w"] == 2.0
