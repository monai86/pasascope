"""Frame-level child / adult voice detection (USC SAIL whisper-child-adult).

The model labels every 20 ms of audio as silence, child, adult or overlap.
It was trained on simulated child-adult conversations (Xu et al., "Data
Efficient Child-Adult Speaker Diarization with Simulated Conversations",
ICASSP 2025, arXiv:2409.08881) and its authors report that it works zero-shot
for children up to about six years old.

Weights: https://huggingface.co/AlexXu811/whisper-child-adult, CC-BY-SA-4.0.
They are downloaded on first use to the user's cache and are not part of this
repository. The training code carries no licence, so the network below is an
independent PyTorch implementation of the architecture the checkpoint
describes:

* a Whisper-base encoder (80 log-mel bins, two convolutions, six pre-norm
  transformer layers, d=512, 8 heads) whose feed-forward layers carry
  rank-8 LoRA adapters (``loralib`` default alpha=1, so scale 1/8);
* a softmax-weighted sum of the six layer outputs (the last one after the
  encoder's final layer norm);
* four 1x1 convolutions (512 -> 256 -> 256 -> 256 -> 4) with ReLU between.

Audio is fed as 10-second windows, the length the model was trained on.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
import os
from pathlib import Path
from typing import List, Optional, Sequence

import numpy as np

from .diarization import ADULT_LABEL, CHILD_LABEL, BaseDiarizer
from .whisper_transcribe import UtteranceSegment

MODEL_URL = "https://huggingface.co/AlexXu811/whisper-child-adult/resolve/main/whisper-base_rank8_pretrained_50k.pt"
MODEL_SHA256 = "02075ccf2ee56c1ea13481264552525a2d812b39ca5c9027dfd66d2ace7d6a2b"
MODEL_PATH_ENV = "PASASCOPE_CHILD_ADULT_MODEL"
SAMPLE_RATE = 16000
FRAME_SECONDS = 0.02
WINDOW_SECONDS = 10.0
HOP_SECONDS = 5.0
SILENCE, CHILD, ADULT, OVERLAP = range(4)
FEATURE_SIZE = 512  # encoder width
LORA_SCALE = 1.0 / 8  # loralib.Linear default lora_alpha=1 over rank 8
# An utterance's label is flagged for the therapist to check when the model's
# mean child-minus-adult probability is closer to zero than this, or the
# utterance is shorter than UNSURE_SECONDS. Chosen on 8 EllisWeismer recordings
# and checked on 8 others: about a third of utterances are flagged, they hold
# about three quarters of the errors, and unflagged labels are ~95% right.
UNSURE_MARGIN = 0.3
UNSURE_SECONDS = 0.5
# Labels are trusted only between these ages; outside them every label is
# flagged. On 16 CRSLP recordings of Thai children aged 20-24 months 61% were
# right and unflagged labels were wrong a third of the time; from 2;6
# (EllisWeismer, 84%) to 6;10 (ENNI, 88%) unflagged labels were ~95% right.
# On ENNI children aged 7;6 to 9;6 (mostly heard as adults) 48%
# were right and the flags no longer singled out the errors.
MIN_CHECKED_AGE_MONTHS = 30
MAX_CHECKED_AGE_MONTHS = 84


def default_model_path() -> Path:
    configured = os.environ.get(MODEL_PATH_ENV, "").strip()
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".cache" / "pasascope" / "models" / "whisper-child-adult" / "whisper-base_rank8_pretrained_50k.pt"


def ensure_model(path: Optional[Path] = None) -> Path:
    """Return the checkpoint path, downloading and verifying it if missing."""
    path = Path(path or default_model_path())
    if path.is_file():
        return path
    import urllib.request

    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".partial")
    digest = hashlib.sha256()
    with urllib.request.urlopen(MODEL_URL, timeout=60) as response, partial.open("wb") as sink:
        for chunk in iter(lambda: response.read(1 << 20), b""):
            digest.update(chunk)
            sink.write(chunk)
    if digest.hexdigest() != MODEL_SHA256:
        partial.unlink(missing_ok=True)
        raise RuntimeError("Downloaded child/adult model does not match its expected SHA-256.")
    partial.replace(path)
    return path


def _build_network(state: dict):
    import torch
    from torch import nn
    import torch.nn.functional as F

    class EncoderLayer(nn.Module):
        def __init__(self, d: int, heads: int, ffn: int) -> None:
            super().__init__()
            self.heads = heads
            self.q = nn.Linear(d, d)
            self.k = nn.Linear(d, d, bias=False)
            self.v = nn.Linear(d, d)
            self.out = nn.Linear(d, d)
            self.attn_norm = nn.LayerNorm(d)
            self.ffn_norm = nn.LayerNorm(d)
            self.fc1 = nn.Linear(d, ffn)
            self.fc2 = nn.Linear(ffn, d)

        def forward(self, x):
            b, t, d = x.shape
            h = self.attn_norm(x)
            split = lambda y: y.view(b, t, self.heads, d // self.heads).transpose(1, 2)  # noqa: E731
            attn = F.scaled_dot_product_attention(split(self.q(h)), split(self.k(h)), split(self.v(h)))
            x = x + self.out(attn.transpose(1, 2).reshape(b, t, d))
            return x + self.fc2(F.gelu(self.fc1(self.ffn_norm(x))))

    class Network(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.conv1 = nn.Conv1d(80, 512, 3, padding=1)
            self.conv2 = nn.Conv1d(512, 512, 3, stride=2, padding=1)
            self.positions = nn.Parameter(torch.zeros(1500, 512), requires_grad=False)
            self.layers = nn.ModuleList(EncoderLayer(512, 8, 2048) for _ in range(6))
            self.final_norm = nn.LayerNorm(512)
            self.layer_weights = nn.Parameter(torch.zeros(6))
            self.head = nn.Sequential(
                nn.Conv1d(512, 256, 1), nn.ReLU(), nn.Conv1d(256, 256, 1), nn.ReLU(),
                nn.Conv1d(256, 256, 1), nn.ReLU(), nn.Conv1d(256, 4, 1),
            )

        def features_and_logits(self, mel):  # mel: (B, 80, frames)
            x = F.gelu(self.conv2(F.gelu(self.conv1(mel)))).transpose(1, 2)
            x = x + self.positions[: x.shape[1]]
            outputs = []
            for index, layer in enumerate(self.layers):
                x = layer(x)
                outputs.append(self.final_norm(x) if index == len(self.layers) - 1 else x)
            weights = F.softmax(self.layer_weights, dim=-1)
            mixed = sum(w * h for w, h in zip(weights, outputs))  # (B, T, 512)
            return mixed, self.head(mixed.transpose(1, 2)).transpose(1, 2)  # (B, T, 4)

        def forward(self, mel):
            return self.features_and_logits(mel)[1]

    net = Network()
    p = "backbone_model.encoder."
    mapped = {
        "conv1.weight": state[p + "conv1.weight"], "conv1.bias": state[p + "conv1.bias"],
        "conv2.weight": state[p + "conv2.weight"], "conv2.bias": state[p + "conv2.bias"],
        "positions": state["embed_positions"],
        "final_norm.weight": state[p + "layer_norm.weight"], "final_norm.bias": state[p + "layer_norm.bias"],
        "layer_weights": state["weights"],
    }
    for i in range(6):
        src = f"{p}layers.{i}."
        dst = f"layers.{i}."
        for ours, theirs in (("q", "q_proj"), ("v", "v_proj"), ("out", "out_proj")):
            mapped[f"{dst}{ours}.weight"] = state[f"{src}self_attn.{theirs}.weight"]
            mapped[f"{dst}{ours}.bias"] = state[f"{src}self_attn.{theirs}.bias"]
        mapped[f"{dst}k.weight"] = state[f"{src}self_attn.k_proj.weight"]
        for ours, theirs in (("attn_norm", "self_attn_layer_norm"), ("ffn_norm", "final_layer_norm")):
            mapped[f"{dst}{ours}.weight"] = state[f"{src}{theirs}.weight"]
            mapped[f"{dst}{ours}.bias"] = state[f"{src}{theirs}.bias"]
        for fc in ("fc1", "fc2"):
            weight = state[f"{src}{fc}.weight"] + LORA_SCALE * (state[f"{src}{fc}.lora_B"] @ state[f"{src}{fc}.lora_A"])
            mapped[f"{dst}{fc}.weight"] = weight
            mapped[f"{dst}{fc}.bias"] = state[f"{src}{fc}.bias"]
    # The checkpoint's head has a dropout after each ReLU, so its convolutions
    # sit at indices 0, 3, 6, 9; ours (no dropout at inference) at 0, 2, 4, 6.
    for ours, theirs in zip((0, 2, 4, 6), (0, 3, 6, 9)):
        mapped[f"head.{ours}.weight"] = state[f"model_seq.{theirs}.weight"]
        mapped[f"head.{ours}.bias"] = state[f"model_seq.{theirs}.bias"]
    net.load_state_dict(mapped, strict=True)
    return net.eval()


class ChildAdultFrameModel:
    """Labels each 20 ms frame of 16 kHz audio as silence, child, adult or overlap."""

    def __init__(self, model_path: Optional[Path] = None) -> None:
        import torch

        state = torch.load(str(ensure_model(model_path)), map_location="cpu", weights_only=True)
        self.net = _build_network(state)
        from faster_whisper.feature_extractor import FeatureExtractor

        self._mel = FeatureExtractor(feature_size=80)

    def frame_probabilities(self, audio: np.ndarray) -> np.ndarray:
        """(frames, 4) class probabilities, averaged over overlapping 10 s windows."""
        return self.frame_outputs(audio)[1]

    def frame_outputs(self, audio: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """(frames, 512) encoder features and (frames, 4) class probabilities.

        Both are averaged over the overlapping 10 s windows. The features are
        what a clinic's own speaker model is trained on
        (``clinic_speaker_model``).
        """
        import torch

        audio = np.asarray(audio, dtype="float32")
        frames = int(len(audio) / SAMPLE_RATE / FRAME_SECONDS)
        totals = np.zeros((max(frames, 1), 4), dtype="float64")
        features = np.zeros((max(frames, 1), FEATURE_SIZE), dtype="float32")
        counts = np.zeros(max(frames, 1), dtype="float64")
        window = int(WINDOW_SECONDS * SAMPLE_RATE)
        hop = int(HOP_SECONDS * SAMPLE_RATE)
        starts = list(range(0, max(1, len(audio) - window) + 1, hop))
        if starts[-1] + window < len(audio):
            starts.append(len(audio) - window)
        with torch.inference_mode():
            for start in starts:
                chunk = audio[start:start + window]
                if len(chunk) < SAMPLE_RATE // 2:
                    continue
                mel = self._mel(chunk, padding=0)
                mel = mel[:, : 2 * (mel.shape[1] // 2)]
                hidden, logits = self.net.features_and_logits(torch.from_numpy(mel).unsqueeze(0))
                probs = torch.softmax(logits[0], dim=-1).numpy()
                first = int(round(start / SAMPLE_RATE / FRAME_SECONDS))
                last = min(first + len(probs), len(totals))
                totals[first:last] += probs[: last - first]
                features[first:last] += hidden[0, : last - first].numpy()
                counts[first:last] += 1
        counts[counts == 0] = 1
        return features / counts[:, None].astype("float32"), totals / counts[:, None]


def utterance_margins(probs: np.ndarray, utterances: Sequence[UtteranceSegment]) -> list[float]:
    """Mean child-minus-adult probability over each utterance's frames."""
    margins = []
    for utt in utterances:
        first = max(0, int(math.floor(utt.start / FRAME_SECONDS)))
        last = min(len(probs), max(first + 1, int(math.ceil(utt.end / FRAME_SECONDS))))
        span = probs[first:last]
        margins.append(float((span[:, CHILD] - span[:, ADULT]).mean()) if len(span) else 0.0)
    return margins


_FROM_ENVIRONMENT = object()


def _clinic_head(choice):
    if choice is not _FROM_ENVIRONMENT:
        return choice
    from .clinic_speaker_model import load_adopted_head

    return load_adopted_head()


def speaker_margins(model: "ChildAdultFrameModel", audio: np.ndarray, utterances: Sequence[UtteranceSegment], clinic_head=None) -> list[float]:
    """Child-minus-adult margin per utterance, from the clinic's model when it has one."""
    if clinic_head is None:
        return utterance_margins(model.frame_probabilities(audio), utterances)
    from .clinic_speaker_model import utterance_features

    features, probs = model.frame_outputs(audio)
    design = utterance_features(features, probs, [(u.start, u.end) for u in utterances])
    for utt, row in zip(utterances, design):
        utt.speaker_reason = clinic_head.explain(row)
    return [float(m) for m in clinic_head.margins(design)]


def frame_basis(margin: float, utterance: UtteranceSegment, child_age_months: Optional[float] = None) -> str:
    """"frame" when the model is sure, "frame_unsure" when the therapist should check."""
    unsure = (
        abs(margin) < UNSURE_MARGIN
        or (utterance.end - utterance.start) < UNSURE_SECONDS
        or (child_age_months is not None and not MIN_CHECKED_AGE_MONTHS <= child_age_months < MAX_CHECKED_AGE_MONTHS)
    )
    return "frame_unsure" if unsure else "frame"


class FrameRoleDiarizer(BaseDiarizer):
    """Child or adult per utterance, from the frame model alone.

    On 16 EllisWeismer recordings (children 2;6-5;6 with examiners and
    parents) this labelled 87% of utterances correctly, against 73% for the
    embedding diarizer, with no setting tuned to the data.
    """

    def __init__(
        self, model: Optional[ChildAdultFrameModel] = None, child_age_months: Optional[float] = None, clinic_head=_FROM_ENVIRONMENT,
    ) -> None:
        super().__init__()
        self.model = model or ChildAdultFrameModel()
        self.child_age_months = child_age_months
        self.clinic_head = _clinic_head(clinic_head)

    def assign(self, audio_path, utterances: Sequence[UtteranceSegment]) -> List[UtteranceSegment]:
        import librosa

        audio, _ = librosa.load(str(audio_path), sr=SAMPLE_RATE, mono=True)
        margins = speaker_margins(self.model, audio, utterances, self.clinic_head)
        for utt, margin in zip(utterances, margins):
            utt.speaker = CHILD_LABEL if margin > 0 else ADULT_LABEL
            utt.speaker_basis = frame_basis(margin, utt, self.child_age_months)
        return list(utterances)


def hybrid_config(child_age_months: Optional[float] = None):
    """EmbeddingDiarizerConfig for naming the adults, with the child's age."""
    from .diarization import EmbeddingDiarizerConfig

    return EmbeddingDiarizerConfig(child_age_months=child_age_months)


class HybridChildAdultDiarizer:
    """The frame model decides child or adult; voice clusters tell the adults apart.

    Measured on real child recordings, the frame model alone separates child
    from adult better than any way of choosing a child cluster from ECAPA
    embeddings, so it has the last word on CHI. The embedding diarizer still
    runs to give different adults different codes (MOT, INV, FAT); an
    utterance it called CHI that the frame model hears as adult becomes MOT.
    """

    def __new__(cls, *args, **kwargs):  # build a subclass lazily to avoid importing speechbrain early
        from .diarization import EmbeddingDiarizer

        class _Hybrid(EmbeddingDiarizer):
            def __init__(self, config=None, model: Optional[ChildAdultFrameModel] = None, clinic_head=_FROM_ENVIRONMENT) -> None:
                super().__init__(config or hybrid_config())
                self.frame_model = model or ChildAdultFrameModel()
                self.clinic_head = _clinic_head(clinic_head)

            def assign(self, audio_path, utterances):
                import librosa

                audio, _ = librosa.load(str(audio_path), sr=SAMPLE_RATE, mono=True)
                margins = speaker_margins(self.frame_model, audio, utterances, self.clinic_head)
                try:
                    labelled = super().assign(audio_path, utterances)
                except Exception as exc:  # noqa: BLE001 - adults just stay unnamed
                    print(f"[diarization] adult naming by voice failed: {exc}")
                    labelled = list(utterances)
                for utt, margin in zip(labelled, margins):
                    if margin > 0:
                        utt.speaker = CHILD_LABEL
                    elif utt.speaker in (None, CHILD_LABEL):
                        utt.speaker = ADULT_LABEL
                    utt.speaker_basis = frame_basis(margin, utt, self.config.child_age_months)
                return labelled

        return _Hybrid(*args, **kwargs)
