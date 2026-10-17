"""A clinic's own child/adult model: trained on attested sessions, used only when it beats the frame model."""

from __future__ import annotations

import numpy as np
import pytest

from src.audio_pipeline import clinic_speaker_model as csm
from src.audio_pipeline.child_adult_frames import ADULT, CHILD, FRAME_SECONDS

FEATURES = 8


def _design(is_child: np.ndarray, *, frame_right: bool, rng) -> np.ndarray:
    """Rows whose features separate child from adult; the frame margin is right or always 'adult'."""
    n = len(is_child)
    features = rng.normal(size=(n, FEATURES)) + np.where(is_child[:, None] == 1, 1.5, -1.5)
    probs = np.tile([0.1, 0.2, 0.6, 0.1], (n, 1))
    if frame_right:
        probs[is_child == 1] = [0.1, 0.6, 0.2, 0.1]
    return np.c_[features, probs, np.zeros(n)]


def _sessions(count: int, children: int, *, frame_right: bool, seed: int = 0):
    rng = np.random.default_rng(seed)
    sessions = []
    for index in range(count):
        is_child = (rng.random(60) < 0.4).astype(int)
        sessions.append(csm.LabelledSession(f"s{index}", f"c{index % children}", _design(is_child, frame_right=frame_right, rng=rng), is_child))
    return sessions


def test_utterance_rows_average_the_frames_inside_each_utterance():
    features = np.zeros((100, 3))
    features[50:100] = 1.0
    probs = np.tile([0.0, 0.0, 1.0, 0.0], (100, 1))
    rows = csm.utterance_features(features, probs, [(0.0, 50 * FRAME_SECONDS), (50 * FRAME_SECONDS, 2.0)])
    assert rows.shape == (2, 3 + 4 + 1)
    assert rows[0, :3].tolist() == [0, 0, 0] and rows[1, :3].tolist() == [1, 1, 1]
    assert csm.frame_margins(rows).tolist() == [-1.0, -1.0]


def test_a_model_that_beats_the_frame_model_is_adopted():
    result = csm.train_clinic_head(_sessions(6, 3, frame_right=False))
    assert result.adopted and result.reason == "better_than_frame_model"
    assert result.model_balanced > 0.9 and result.frame_balanced == 0.5
    assert set(result.per_child) == {"c0", "c1", "c2"}


def test_the_frame_model_is_kept_when_the_clinic_model_is_not_better():
    result = csm.train_clinic_head(_sessions(6, 3, frame_right=True))
    assert result.frame_accuracy == 1.0
    assert not result.adopted and result.reason == "not_better_than_frame_model"


@pytest.mark.parametrize("count,children,sessions_needed,children_needed", [(3, 3, 1, 0), (5, 1, 0, 1)])
def test_too_few_sessions_or_children_are_not_trained_on(count, children, sessions_needed, children_needed):
    result = csm.train_clinic_head(_sessions(count, children, frame_right=False))
    assert not result.adopted and result.reason == "not_enough_sessions" and result.head is None
    assert (result.sessions_needed, result.children_needed) == (sessions_needed, children_needed)


def test_only_an_adopted_model_is_loaded(tmp_path, monkeypatch):
    path = tmp_path / "model.json"
    adopted = csm.train_clinic_head(_sessions(6, 3, frame_right=False))
    csm.save_result(path, adopted, trained_at="2026-10-17T12:00:00+07:00")
    monkeypatch.setenv(csm.CLINIC_MODEL_ENV, str(path))
    head = csm.load_adopted_head()
    assert head is not None
    rows = _design(np.array([1, 0]), frame_right=False, rng=np.random.default_rng(1))
    assert np.allclose(head.margins(rows), adopted.head.margins(rows))

    csm.save_result(path, csm.train_clinic_head(_sessions(6, 3, frame_right=True)), trained_at="2026-10-17T12:00:00+07:00")
    assert csm.load_adopted_head() is None
    monkeypatch.delenv(csm.CLINIC_MODEL_ENV)
    assert csm.load_adopted_head() is None


def test_the_diarizer_takes_child_or_adult_from_the_clinic_model(tmp_path):
    pytest.importorskip("torch")
    import soundfile

    from src.audio_pipeline import child_adult_frames as caf
    from src.audio_pipeline.whisper_transcribe import UtteranceSegment

    class FrameModelHearsOnlyAdults:
        def frame_outputs(self, audio):
            frames = int(len(audio) / caf.SAMPLE_RATE / caf.FRAME_SECONDS)
            features = np.zeros((frames, FEATURES))
            features[50:100] = 3.0  # the clinic model has learned this is the child
            return features, np.tile([0.1, 0.1, 0.7, 0.1], (frames, 1))

        def frame_probabilities(self, audio):
            return self.frame_outputs(audio)[1]

    head = csm.ClinicSpeakerHead(np.zeros(FEATURES + 5), np.ones(FEATURES + 5), np.r_[np.ones(FEATURES), np.zeros(5)], -4.0)
    wav = tmp_path / "a.wav"
    soundfile.write(wav, np.zeros(3 * caf.SAMPLE_RATE, dtype="float32"), caf.SAMPLE_RATE)
    utts = [UtteranceSegment(start=0.0, end=0.9, text="a"), UtteranceSegment(start=1.0, end=2.0, text="b")]

    with_clinic = caf.FrameRoleDiarizer(FrameModelHearsOnlyAdults(), clinic_head=head).assign(wav, utts)
    assert [u.speaker for u in with_clinic] == ["MOT", "CHI"]
    assert with_clinic[1].speaker_reason.startswith("โมเดลประจำคลินิก: เสียงเด็ก")  # and the base model said adult
    assert "(โมเดลพื้นฐาน 12%)" in with_clinic[1].speaker_reason  # 0.1 / (0.1 + 0.7)
    without = caf.FrameRoleDiarizer(FrameModelHearsOnlyAdults(), clinic_head=None).assign(wav, utts)
    assert [u.speaker for u in without] == ["MOT", "MOT"]


def test_calling_everyone_adult_is_not_adopted_however_accurate():
    """Most utterances are adults'; a model that drops the child must not win on plain accuracy."""
    rng = np.random.default_rng(0)
    sessions = []
    for index in range(6):
        is_child = (rng.random(100) < 0.2).astype(int)
        design = _design(is_child, frame_right=True, rng=rng)
        design[:, :FEATURES] = rng.normal(size=(100, FEATURES))  # the features carry nothing
        flip = rng.random(100) < 0.3  # the frame model finds the child but makes mistakes both ways
        design[flip, -5:-1] = design[flip, -5:-1][:, [0, 2, 1, 3]]
        sessions.append(csm.LabelledSession(f"s{index}", f"c{index % 3}", design, is_child))
    result = csm.train_clinic_head(sessions)
    assert result.model_accuracy > result.frame_accuracy  # it learned "adult" ...
    assert not result.adopted  # ... and is not used


def test_explanations_name_the_most_similar_attested_utterances(tmp_path):
    result = csm.train_clinic_head(_sessions(6, 3, frame_right=False))
    design = np.vstack([s.design for s in _sessions(6, 3, frame_right=False)])
    is_child = np.concatenate([s.is_child for s in _sessions(6, 3, frame_right=False)])
    labels = [f"TH-{i:03d} 01/10/2026 00:{i % 60:02d}" for i in range(len(is_child))]
    path = tmp_path / "model.json"
    csm.save_result(path, result, trained_at="2026-10-17T12:00:00+07:00")
    csm.save_examples(path, result.head, design, is_child, labels)
    head = csm.load_adopted_head(path)
    child_like = _design(np.array([1]), frame_right=False, rng=np.random.default_rng(5))[0]
    similar = head.nearest_examples(child_like)
    assert len(similar) == 3 and all(is_child for _, is_child in similar)
    assert "คล้ายประโยคที่รับรองแล้ว: TH-" in head.explain(child_like)
