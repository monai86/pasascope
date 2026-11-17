"""Performance & single-decode invariants for the audio-to-CHAT pipeline."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from src.audio_pipeline import child_adult_frames as caf
from src.audio_pipeline import diarization as d
from src.audio_pipeline import pipeline
from src.audio_pipeline import whisper_transcribe as wt
from src.audio_pipeline.acoustic_profile import compute_acoustic_profile
from src.audio_pipeline.whisper_transcribe import UtteranceSegment, WhisperTranscriber


def _checkpoint_like_state() -> dict:
    """Random tensors matching whisper-base_rank8_pretrained_50k.pt layout."""
    import torch

    gen = torch.Generator().manual_seed(7)
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


def _single_window_cpu_reference(model: caf.ChildAdultFrameModel, audio: np.ndarray):
    import torch

    audio = np.asarray(audio, dtype="float32")
    frames = int(len(audio) / caf.SAMPLE_RATE / caf.FRAME_SECONDS)
    totals = np.zeros((max(frames, 1), 4), dtype="float64")
    features = np.zeros((max(frames, 1), caf.FEATURE_SIZE), dtype="float32")
    counts = np.zeros(max(frames, 1), dtype="float64")
    window = int(caf.WINDOW_SECONDS * caf.SAMPLE_RATE)
    hop = int(caf.HOP_SECONDS * caf.SAMPLE_RATE)
    starts = list(range(0, max(1, len(audio) - window) + 1, hop))
    if starts[-1] + window < len(audio):
        starts.append(len(audio) - window)
    net_cpu = model.net.to("cpu")
    with torch.inference_mode():
        for start in starts:
            chunk = audio[start:start + window]
            if len(chunk) < caf.SAMPLE_RATE // 2:
                continue
            mel = model._mel(chunk, padding=0)
            mel = mel[:, : 2 * (mel.shape[1] // 2)]
            hidden, logits = net_cpu.features_and_logits(torch.from_numpy(mel).unsqueeze(0))
            probs = torch.softmax(logits[0], dim=-1).numpy()
            first = int(round(start / caf.SAMPLE_RATE / caf.FRAME_SECONDS))
            last = min(first + len(probs), len(totals))
            totals[first:last] += probs[: last - first]
            features[first:last] += hidden[0, : last - first].numpy()
            counts[first:last] += 1
    counts[counts == 0] = 1
    return features / counts[:, None].astype("float32"), totals / counts[:, None]


def test_default_torch_device_respects_env(monkeypatch):
    monkeypatch.setenv(caf.TORCH_DEVICE_ENV, "cpu")
    assert caf.default_torch_device() == "cpu"
    monkeypatch.setenv(caf.TORCH_DEVICE_ENV, "MPS")
    assert caf.default_torch_device() == "mps"


def test_frame_model_cache_loads_checkpoint_once(tmp_path, monkeypatch):
    torch = pytest.importorskip("torch")

    ckpt = tmp_path / "frame.pt"
    torch.save(_checkpoint_like_state(), ckpt)
    monkeypatch.setattr(caf, "_FRAME_MODEL_CACHE", {})

    loads = []
    real_load = torch.load

    def counting_load(*args, **kwargs):
        loads.append(args[0])
        return real_load(*args, **kwargs)

    monkeypatch.setattr(torch, "load", counting_load)

    first = caf.get_cached_frame_model(model_path=ckpt, device="cpu")
    second = caf.get_cached_frame_model(model_path=ckpt, device="cpu")
    assert first is second
    assert len(loads) == 1


def test_batched_frame_outputs_match_single_window_cpu(tmp_path):
    torch = pytest.importorskip("torch")

    ckpt = tmp_path / "frame.pt"
    torch.save(_checkpoint_like_state(), ckpt)

    # 95 s -> 18 overlapping 10 s windows (exercises >1 batch of FRAME_BATCH_SIZE=16)
    rng = np.random.default_rng(42)
    audio = (0.05 * rng.standard_normal(caf.SAMPLE_RATE * 95)).astype("float32")

    cpu_model = caf.ChildAdultFrameModel(model_path=ckpt, device="cpu")
    ref_features, ref_probs = _single_window_cpu_reference(cpu_model, audio)
    batched_features, batched_probs = cpu_model.frame_outputs(audio)

    assert np.allclose(batched_features, ref_features, atol=1e-4)
    assert np.allclose(batched_probs, ref_probs, atol=1e-4)

    if getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available():
        mps_model = caf.ChildAdultFrameModel(model_path=ckpt, device="mps")
        mps_features, mps_probs = mps_model.frame_outputs(audio)
        assert np.allclose(mps_features, ref_features, atol=1e-4)
        assert np.allclose(mps_probs, ref_probs, atol=1e-4)


def test_frame_model_falls_back_to_cpu_when_mps_fails(tmp_path, monkeypatch):
    torch = pytest.importorskip("torch")

    ckpt = tmp_path / "frame.pt"
    torch.save(_checkpoint_like_state(), ckpt)
    model = caf.ChildAdultFrameModel(model_path=ckpt, device="cpu")
    model.device = "mps"

    orig_features_and_logits = model.net.features_and_logits

    def fail_on_mps(tensor):
        if tensor.device.type != "cpu":
            raise RuntimeError("simulated MPS failure")
        return orig_features_and_logits(tensor)

    monkeypatch.setattr(model.net, "features_and_logits", fail_on_mps)
    audio = np.zeros(caf.SAMPLE_RATE * 2, dtype="float32")
    features, probs = model.frame_outputs(audio)
    assert model.device == "cpu"
    assert probs.shape[1] == 4 and features.shape[1] == caf.FEATURE_SIZE


def test_level_normalized_and_detect_language_accept_ndarray_without_redecode(tmp_path, monkeypatch):
    import soundfile
    from faster_whisper import audio as fw_audio

    t = np.arange(16000 * 120) / 16000.0
    samples = (0.01 * np.sin(2 * np.pi * 220 * t)).astype("float32")
    wav = tmp_path / "long.wav"
    soundfile.write(wav, samples, 16000)

    decoded = fw_audio.decode_audio(str(wav), sampling_rate=16000)
    decoded_before = decoded.copy()
    expected_norm = wt._level_normalized(str(wav))

    def forbid_decode(*_args, **_kwargs):
        raise AssertionError("decode_audio should not be called when ndarray is passed")

    monkeypatch.setattr(fw_audio, "decode_audio", forbid_decode)
    got_norm = wt._level_normalized(decoded)
    assert np.array_equal(got_norm, expected_norm)
    assert np.array_equal(decoded, decoded_before)

    seen_lengths = []

    class FakeDetector:
        def detect_language(self, audio, vad_filter, language_detection_segments):
            seen_lengths.append((len(audio), vad_filter, language_detection_segments))
            return "th", 0.99, []

    transcriber = WhisperTranscriber.__new__(WhisperTranscriber)
    transcriber._load_detector = lambda: FakeDetector()

    lang = transcriber._detect_language(decoded)
    assert lang == "th"
    assert seen_lengths == [(90 * 16000, True, 3)]


def test_transcribe_with_audio_samples_skips_disk_decode_on_fallback_and_redecode(monkeypatch):
    from faster_whisper import audio as fw_audio

    def forbid_decode(*_args, **_kwargs):
        raise AssertionError("decode_audio should not be called when audio_samples is supplied")

    monkeypatch.setattr(fw_audio, "decode_audio", forbid_decode)

    calls = []
    loop_text = "หอม กึ่ง " * 8 + "กร๊าก " * 8

    class FakeModel:
        def transcribe(self, audio, **kwargs):
            calls.append((isinstance(audio, np.ndarray), kwargs.get("vad_filter"), len(audio)))
            info = SimpleNamespace(language="th", duration=10.0)
            if kwargs.get("vad_filter") is True and len(calls) == 1:
                # Sparse result triggers _fallback_if_sparse(vad_filter=False)
                return iter([]), info
            if kwargs.get("vad_filter") is False:
                words = [SimpleNamespace(word=w, start=1.0 + i * 0.2, end=1.0 + i * 0.2 + 0.15, probability=0.9)
                         for i, w in enumerate(loop_text.split())]
                return iter([SimpleNamespace(
                    text=loop_text, start=1.0, end=8.0, avg_logprob=-0.2,
                    no_speech_prob=0.05, compression_ratio=1.0, words=words,
                )]), info
            return iter([]), info

    transcriber = WhisperTranscriber.__new__(WhisperTranscriber)
    transcriber._WhisperModel = object
    transcriber.model_size = "small"
    transcriber.device = "cpu"
    transcriber.compute_type = "int8"
    transcriber.strategy = "auto"
    transcriber._explicit_language = "th"
    transcriber._initial_prompt = None
    transcriber._model = FakeModel()
    transcriber._model_th = None
    transcriber.last_model_id = None
    transcriber.flag_uncertain_speech = True
    transcriber.segment_log = None

    raw_samples = (0.02 * np.sin(np.linspace(0, 100, 16000 * 10))).astype("float32")
    transcriber.transcribe("nonexistent.wav", vad_filter=True, audio_samples=raw_samples)
    # 1) primary vad_filter=True, 2) fallback_if_sparse vad_filter=False, 3) _redecode_loops span
    assert len(calls) == 3
    assert all(is_arr for is_arr, _, _ in calls)
    assert calls[0][1] is True and calls[1][1] is False


def test_ecapa_cache_reuses_classifier(monkeypatch):
    import sys
    import types

    load_calls = []

    class FakeEncoder:
        @classmethod
        def from_hparams(cls, **kwargs):
            load_calls.append(kwargs)
            return SimpleNamespace(kwargs=kwargs)

    fake_speaker_mod = types.ModuleType("speechbrain.inference.speaker")
    fake_speaker_mod.EncoderClassifier = FakeEncoder
    fake_inf_mod = types.ModuleType("speechbrain.inference")
    fake_inf_mod.speaker = fake_speaker_mod
    fake_sb_mod = types.ModuleType("speechbrain")
    fake_sb_mod.inference = fake_inf_mod

    monkeypatch.setitem(sys.modules, "speechbrain", fake_sb_mod)
    monkeypatch.setitem(sys.modules, "speechbrain.inference", fake_inf_mod)
    monkeypatch.setitem(sys.modules, "speechbrain.inference.speaker", fake_speaker_mod)
    monkeypatch.setattr(d, "_ECAPA_CACHE", {})

    d1 = d.EmbeddingDiarizer()
    d2 = d.EmbeddingDiarizer()
    assert d1._load_classifier() is d2._load_classifier()
    assert len(load_calls) == 1


def test_embedding_diarizer_populates_f0_cache_and_acoustic_profile_reuses_it(tmp_path, monkeypatch):
    import librosa
    import soundfile

    sr = 16000
    t = np.arange(sr * 6) / sr
    # Two distinct voiced speakers: child (~330 Hz) and adult (~140 Hz)
    y = np.concatenate([
        0.2 * np.sin(2 * np.pi * 330 * t[: sr * 2]),
        0.2 * np.sin(2 * np.pi * 140 * t[: sr * 2]),
        0.2 * np.sin(2 * np.pi * 330 * t[: sr * 2]),
    ]).astype("float32")
    wav = tmp_path / "dialogue.wav"
    soundfile.write(wav, y, sr)

    diarizer = d.EmbeddingDiarizer(d.EmbeddingDiarizerConfig(child_age_months=48))
    embs = iter([
        np.array([1.0, 0.0]),
        np.array([0.0, 1.0]),
        np.array([1.0, 0.0]),
        np.array([0.0, 1.0]),
        np.array([1.0, 0.0]),
        np.array([0.0, 1.0]),
    ])
    monkeypatch.setattr(diarizer, "_embed_clip", lambda clip, clip_sr: next(embs))

    yin_calls = []
    real_yin = librosa.yin

    def counting_yin(*args, **kwargs):
        yin_calls.append(len(args[0]) if args else len(kwargs["y"]))
        return real_yin(*args, **kwargs)

    monkeypatch.setattr(librosa, "yin", counting_yin)

    utts = [
        UtteranceSegment(0.1, 0.9, "hi"),
        UtteranceSegment(2.1, 2.9, "hello"),
        UtteranceSegment(4.1, 4.9, "car"),
        UtteranceSegment(2.9, 3.8, "good"),
        UtteranceSegment(1.0, 1.8, "red"),
        UtteranceSegment(3.0, 3.9, "yes"),
    ]
    out = diarizer.assign(wav, utts)
    assert diarizer.last_audio is not None and len(diarizer.last_audio[0]) == len(y)
    assert diarizer.last_f0_cache is not None and len(diarizer.last_f0_cache[0]) > 0
    assert len(yin_calls) == 1

    profile = compute_acoustic_profile(
        wav,
        out,
        y_audio=diarizer.last_audio[0],
        sr_audio=diarizer.last_audio[1],
        precomputed_f0=diarizer.last_f0_cache,
    )
    assert len(yin_calls) == 1  # compute_acoustic_profile reused cached F0 without re-running yin
    assert profile.duration_sec == pytest.approx(6.0, abs=0.05)
    assert np.isfinite(profile.f0_median_hz)


def test_audio_to_cha_single_decode_with_hybrid_diarizer(tmp_path, monkeypatch):
    import librosa
    import soundfile

    sr = 16000
    t = np.arange(sr * 4) / sr
    y = (0.15 * np.sin(2 * np.pi * 300 * t)).astype("float32")
    wav = tmp_path / "session.wav"
    soundfile.write(wav, y, sr)

    decode_calls = []
    load_calls = []
    orig_librosa_load = librosa.load

    def counting_librosa_load(*args, **kwargs):
        load_calls.append(args[0])
        return orig_librosa_load(*args, **kwargs)

    monkeypatch.setattr(librosa, "load", counting_librosa_load)

    class FakeTranscriber:
        def __init__(self, **kwargs):
            self.last_model_id = "small"

        def transcribe(self, audio_path, progress_callback=None, audio_samples=None):
            decode_calls.append(audio_samples is not None)
            return [
                UtteranceSegment(0.2, 1.2, "รถ"),
                UtteranceSegment(2.0, 3.0, "สี แดง"),
            ]

    class FakeFrameModel:
        def frame_outputs(self, audio):
            frames = max(1, int(len(audio) / caf.SAMPLE_RATE / caf.FRAME_SECONDS))
            probs = np.tile([0.05, 0.85, 0.05, 0.05], (frames, 1))
            return np.zeros((frames, caf.FEATURE_SIZE), dtype="float32"), probs

        def frame_probabilities(self, audio):
            return self.frame_outputs(audio)[1]

    monkeypatch.setattr(pipeline, "WhisperTranscriber", FakeTranscriber)

    hybrid = caf.HybridChildAdultDiarizer(caf.hybrid_config(48), model=FakeFrameModel(), clinic_head=None)
    monkeypatch.setattr(hybrid, "_embed_clip", lambda clip, clip_sr: np.array([1.0, 0.0]))

    result = pipeline.audio_to_cha(wav, diarizer=hybrid, validate=False)
    assert decode_calls == [True]
    assert load_calls == []  # neither HybridChildAdultDiarizer, EmbeddingDiarizer, nor acoustic_profile called librosa.load
    assert result.n_child_utterances == 2
    assert result.acoustic_profile is not None
