"""The explainable utterance boundary model: features, explanations and cutting a draft."""

from __future__ import annotations

import numpy as np
import pytest

from src.audio_pipeline import utterance_boundaries as ub
from src.audio_pipeline.whisper_transcribe import UtteranceSegment, WordSegment


def _statistics():
    texts = ["I want ball ."] * 30 + ["look at that ball ."] * 30 + ["want more juice ?"] * 30
    return ub.WordStatistics.from_utterances(texts)


def test_word_statistics_say_which_words_end_and_start_utterances():
    stats = _statistics()
    assert stats.end_log_odds["ball"] > 0 > stats.end_log_odds["want"]
    assert stats.start_log_odds["look"] > 0 > stats.start_log_odds["ball"]
    assert ub.words_of("I want [/] want &-um ball@o xxx .") == ["i", "want", "want", "ball"]


def test_gap_features_read_pause_punctuation_and_capitals():
    words = [ub.Word("ball.", 0.0, 0.4), ub.Word("Look", 1.4, 1.7), ub.Word("I", 1.8, 1.9)]
    first = ub.gap_features(words, 0, _statistics())
    assert first["pause"] == pytest.approx(np.log(1.05))
    assert first["sentence_mark"] == 1.0 and first["capital_next"] == 1.0
    assert ub.gap_features(words, 1, _statistics())["capital_next"] == 0.0  # "I" is always capitalised


def _pause_model(threshold=0.5):
    """Only the pause counts: a pause of about a second is even odds."""
    weights = np.zeros(len(ub.FEATURES))
    weights[ub.FEATURES.index("pause")] = 4.0
    return ub.BoundaryModel(np.zeros(len(ub.FEATURES)), np.ones(len(ub.FEATURES)), weights, 0.0, _statistics(), threshold)


def test_every_decision_is_the_sum_of_named_contributions(tmp_path):
    model = _pause_model()
    features = {name: 0.0 for name in ub.FEATURES} | {"pause": 0.5}
    assert model.contributions(features)["pause"] == 2.0
    assert model.probability(features) == pytest.approx(1 / (1 + np.exp(-2.0)))
    assert model.explain(features).startswith("ช่วงหยุด +2.0")
    model.save(tmp_path / "m.json")
    loaded = ub.BoundaryModel.load(tmp_path / "m.json")
    assert loaded.probability(features) == pytest.approx(model.probability(features))


def _piece(speaker, basis, *words):
    ws = [WordSegment(t, s, e, 0.9) for t, s, e in words]
    return UtteranceSegment(start=ws[0].start, end=ws[-1].end, text=" ".join(t for t, _, _ in words), words=ws,
                            speaker=speaker, speaker_basis=basis)


def test_the_draft_is_cut_where_the_model_sees_a_boundary_and_says_why():
    pieces = [
        _piece("CHI", "frame", ("I", 0.0, 0.2), ("want", 0.25, 0.5)),
        _piece("CHI", "frame_unsure", ("ball", 0.55, 0.9), ("more", 3.0, 3.3)),
        _piece("MOT", "frame", ("okay", 3.4, 3.8)),
    ]
    out = ub.segment_by_model(pieces, _pause_model())
    assert [(u.speaker, u.text) for u in out] == [("CHI", "I want ball"), ("CHI", "more"), ("MOT", "okay")]
    assert out[0].speaker_basis == "frame_unsure"  # made from a sure and an unsure piece
    assert out[1].boundary_reason.startswith("ขึ้นประโยคใหม่") and "ช่วงหยุด" in out[1].boundary_reason
    assert out[2].boundary_reason is None  # a change of speaker needs no reason


def test_thai_drafts_and_the_off_switch_keep_the_pause_rule(monkeypatch, tmp_path):
    model_path = tmp_path / "m.json"
    _pause_model().save(model_path)
    monkeypatch.setattr(ub, "DEFAULT_MODEL_PATH", model_path)
    english = [UtteranceSegment(start=0, end=1, text="I want the ball")]
    assert ub.model_for(english) is not None
    assert ub.model_for([UtteranceSegment(start=0, end=1, text="หนูอยากได้ลูกบอล")]) is None
    monkeypatch.setenv(ub.BOUNDARIES_ENV, "rule")
    assert ub.model_for(english) is None
