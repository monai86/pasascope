"""The USC child/adult frame model loads its checkpoint layout and labels utterances.

The real checkpoint (292 MB) is not downloaded here: a random state dict with
the checkpoint's exact key names and shapes checks the mapping, and a fake
frame model checks how frames become utterance labels. Equality with the
authors' code was checked once by hand (max logit difference ~1e-5).
"""

from __future__ import annotations

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from src.audio_pipeline import child_adult_frames as caf  # noqa: E402
from src.audio_pipeline.whisper_transcribe import UtteranceSegment  # noqa: E402


def _checkpoint_like_state() -> dict:
    """Random tensors under the key names and shapes of whisper-base_rank8_pretrained_50k.pt."""
    gen = torch.Generator().manual_seed(0)
    rand = lambda *shape: torch.randn(*shape, generator=gen) * 0.02  # noqa: E731
    p = "backbone_model.encoder."
    state = {
        "embed_positions": rand(1500, 512), "weights": rand(6),
        p + "conv1.weight": rand(512, 80, 3), p + "conv1.bias": rand(512),
        p + "conv2.weight": rand(512, 512, 3), p + "conv2.bias": rand(512),
        p + "embed_positions.weight": rand(500, 512),
        p + "layer_norm.weight": torch.ones(512), p + "layer_norm.bias": rand(512),
    }
    for i in range(6):
        q = f"{p}layers.{i}."
        for name in ("q_proj", "v_proj", "out_proj"):
            state[f"{q}self_attn.{name}.weight"] = rand(512, 512)
            state[f"{q}self_attn.{name}.bias"] = rand(512)
        state[f"{q}self_attn.k_proj.weight"] = rand(512, 512)
        for norm in ("self_attn_layer_norm", "final_layer_norm"):
            state[f"{q}{norm}.weight"] = torch.ones(512)
            state[f"{q}{norm}.bias"] = rand(512)
        state[f"{q}fc1.weight"], state[f"{q}fc1.bias"] = rand(2048, 512), rand(2048)
        state[f"{q}fc1.lora_A"], state[f"{q}fc1.lora_B"] = rand(8, 512), rand(2048, 8)
        state[f"{q}fc2.weight"], state[f"{q}fc2.bias"] = rand(512, 2048), rand(512)
        state[f"{q}fc2.lora_A"], state[f"{q}fc2.lora_B"] = rand(8, 2048), rand(512, 8)
    for index, (out_ch, in_ch) in zip((0, 3, 6, 9), ((256, 512), (256, 256), (256, 256), (4, 256))):
        state[f"model_seq.{index}.weight"] = rand(out_ch, in_ch, 1)
        state[f"model_seq.{index}.bias"] = rand(out_ch)
    return state


def test_checkpoint_layout_maps_onto_the_network_with_lora_merged():
    state = _checkpoint_like_state()
    net = caf._build_network(state)
    fc1 = net.layers[0].fc1.weight
    expected = state["backbone_model.encoder.layers.0.fc1.weight"] + caf.LORA_SCALE * (
        state["backbone_model.encoder.layers.0.fc1.lora_B"] @ state["backbone_model.encoder.layers.0.fc1.lora_A"]
    )
    assert torch.allclose(fc1, expected)
    assert torch.equal(net.head[6].weight, state["model_seq.9.weight"])
    with torch.inference_mode():
        out = net(torch.randn(1, 80, 1000))
    assert out.shape == (1, 500, 4)  # one row per 20 ms of a 10 s window


class _FakeFrames:
    """Child from 1.0 s to 2.0 s, adult elsewhere."""

    def frame_probabilities(self, audio):
        frames = int(len(audio) / caf.SAMPLE_RATE / caf.FRAME_SECONDS)
        probs = np.tile([0.05, 0.05, 0.85, 0.05], (frames, 1))
        probs[50:100] = [0.05, 0.85, 0.05, 0.05]
        return probs


def _wav(tmp_path, seconds=3.0):
    import soundfile

    path = tmp_path / "a.wav"
    soundfile.write(path, np.zeros(int(seconds * caf.SAMPLE_RATE), dtype="float32"), caf.SAMPLE_RATE)
    return path


def test_frame_majority_labels_each_utterance(tmp_path):
    utterances = [UtteranceSegment(0.1, 0.9, ""), UtteranceSegment(1.1, 1.9, ""), UtteranceSegment(2.1, 2.9, "")]
    labelled = caf.FrameRoleDiarizer(model=_FakeFrames()).assign(_wav(tmp_path), utterances)
    assert [u.speaker for u in labelled] == ["MOT", "CHI", "MOT"]


def test_hybrid_uses_the_frame_model_only_when_it_separates_clusters():
    from src.audio_pipeline.diarization import EmbeddingDiarizerConfig

    hybrid = caf.HybridChildAdultDiarizer(EmbeddingDiarizerConfig(child_age_months=48), model=_FakeFrames())
    audio = np.zeros(3 * caf.SAMPLE_RATE, dtype="float32")
    utterances = [UtteranceSegment(0.1, 0.9, ""), UtteranceSegment(1.1, 1.9, ""), UtteranceSegment(2.1, 2.9, "")]
    # Cluster 1 holds the child-sounding utterance even though its pitch is lower.
    scores = hybrid._score_clusters([0, 1], [0, 1, 0], [300.0, 150.0, 300.0], [0.8, 0.8, 0.8],
                                    [None] * 3, audio, caf.SAMPLE_RATE, utterances)
    assert max(scores, key=scores.get) == 1

    class Undecided:
        def frame_probabilities(self, audio):
            return np.tile([0.1, 0.0, 0.9, 0.0], (150, 1))

    hybrid.frame_model = Undecided()
    scores = hybrid._score_clusters([0, 1], [0, 1, 0], [300.0, 150.0, 300.0], [0.8, 0.8, 0.8],
                                    [None] * 3, audio, caf.SAMPLE_RATE, utterances)
    assert max(scores, key=scores.get) == 0  # falls back to pitch: cluster 0 is higher
