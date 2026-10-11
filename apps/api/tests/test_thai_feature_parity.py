"""Thai transcripts must get the same measures in the web app and the offline GUI.

The API feature provider and ``ThaiClinicalLSA`` (used by the desktop GUI) once
computed echolalia and pronoun cues with different rules, so the same
transcript produced different numbers depending on which surface opened it.
"""

from __future__ import annotations

import pytest

from app.schemas.clinical import Transcript, Utterance
from app.services.providers import basic_provider
from app.services.providers.basic_provider import BasicFeatureProvider
from src.clinical_speech.thai_lsa import ThaiClinicalLSA

TURNS = [
    ("INV", "วันนี้เราจะเล่นอะไรกันดี"),
    ("CHI", "เล่นอะไรกันดี"),          # echoes most of the adult turn
    ("INV", "เล่นรถไหมครับ"),
    ("CHI", "เล่นรถไหมครับ"),          # verbatim echo
    ("INV", "รถสีอะไรครับ"),
    ("CHI", "สีแดง"),
    ("CHI", "เธออยากกินขนม"),          # second-person pronoun for own wish
    ("INV", "หิวแล้วเหรอ"),
    ("CHI", "หนูหิวน้ำ"),
]


def _features(turns) -> dict:
    transcript = Transcript(
        transcript_id="tr_parity",
        session_id="session_parity",
        case_id="case_parity",
        source="manual",
        raw_text="",
        utterances=[
            Utterance(utterance_id=f"utt_{index}", speaker=speaker, text=text)
            for index, (speaker, text) in enumerate(turns)
        ],
    )
    result = BasicFeatureProvider().extract_features(transcript)
    return {value.name: value for value in result.values}


def test_thai_measures_match_the_offline_analysis():
    features = _features(TURNS)
    lsa = ThaiClinicalLSA.analyze_utterances([{"speaker": speaker, "text": text} for speaker, text in TURNS])

    assert features["mean_length_of_utterance_words"].value == pytest.approx(lsa.mlu_words, abs=0.01)
    assert features["type_token_ratio"].value == pytest.approx(lsa.ttr, abs=0.01)
    assert features["echolalia_cue_count"].value == lsa.echolalia_count == 2
    assert features["pronoun_reversal_cue_count"].value == lsa.pronoun_reversal_count == 1


def test_thai_self_reference_is_not_a_pronoun_cue():
    features = _features([("INV", "อยากได้อะไร"), ("CHI", "หนูอยากเล่นรถ"), ("CHI", "ผมจะเอาอันนี้"), ("CHI", "เอาอีก")])

    assert features["pronoun_reversal_cue_count"].value == 0


def test_english_cue_rules_are_unchanged():
    features = _features(
        [("INV", "what do you want"), ("CHI", "what do you want"), ("CHI", "what do you want"), ("CHI", "you am hungry")]
    )

    # Verbatim rule, compared with the last adult turn even after another child turn.
    assert features["echolalia_cue_count"].value == 2
    assert features["pronoun_reversal_cue_count"].value == 1


def test_thai_pronoun_cue_is_missing_not_zero_without_the_thai_module(monkeypatch):
    monkeypatch.setattr(basic_provider, "_thai_lsa", lambda: None)

    features = _features(TURNS)

    assert features["pronoun_reversal_cue_count"].value is None
    assert any("Thai" in warning for warning in features["pronoun_reversal_cue_count"].warnings)
