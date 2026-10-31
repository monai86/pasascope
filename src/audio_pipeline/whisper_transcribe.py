"""
Whisper-based ASR wrapper with TH+EN code-switching support.

Uses ``faster-whisper`` (4x faster than openai-whisper, same accuracy) to
transcribe child-therapy audio into word-level segments with timestamps,
confidence scores, and per-segment language tags.

Hallucination filter and language-aware initial prompts are applied so
the resulting CHAT transcript is closer to what was actually said in
both English and Thai.

Typical usage
-------------
>>> t = WhisperTranscriber(model_size="small", strategy="auto")
>>> utts = t.transcribe("session01.wav")
>>> for u in utts:
...     print(u.start, u.end, u.language, u.text)
"""

from __future__ import annotations

import os
import platform
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
import threading
from typing import Any, List, Literal, Optional

try:
    from openai import OpenAI as _OpenAIClient
except ImportError:
    _OpenAIClient = None

# Global in-memory cache for WhisperModel instances
_MODEL_CACHE: dict[tuple[str, str, str, int], Any] = {}
_MODEL_LOCK = threading.Lock()


THREADS_ENV = "PASASCOPE_ASR_THREADS"
COMPUTE_TYPE_ENV = "PASASCOPE_ASR_COMPUTE_TYPE"


def _sysctl_int(name: str) -> int | None:
    import subprocess

    try:
        out = subprocess.run(["sysctl", "-n", name], capture_output=True, text=True, timeout=5, check=True)
        return int(out.stdout.strip())
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def default_cpu_threads() -> int:
    """Threads for CTranslate2: the performance cores only.

    On Apple Silicon, work spread onto the efficiency cores waits for them:
    on an M2 (4+4 cores) a Thai clip took 70.6 s with 8 threads and 25.2 s
    with 4.
    """
    configured = os.environ.get(THREADS_ENV, "").strip()
    if configured.isdigit() and int(configured) > 0:
        return int(configured)
    if sys.platform == "darwin":
        performance = _sysctl_int("hw.perflevel0.physicalcpu")
        if performance:
            return max(2, performance)
    return max(2, min(8, os.cpu_count() or 4))


def default_compute_type() -> str:
    """Numeric type for transcription on this machine.

    CTranslate2's int8 kernels are slow on Apple Silicon; float32 ran the
    same clip in 15.6 s against 25.2 s for int8, with the same text, at the
    cost of about 3 GB of memory for a medium model.
    """
    configured = os.environ.get(COMPUTE_TYPE_ENV, "").strip()
    if configured:
        return configured
    if sys.platform == "darwin" and platform.machine() == "arm64":
        return "float32"
    return "int8"


def get_cached_whisper_model(
    whisper_cls: Any,
    model_size_or_path: str,
    device: str,
    compute_type: str,
    cpu_threads: int | None = None,
) -> Any:
    """Retrieve or instantiate a cached WhisperModel singleton with multi-core parallelism."""
    threads = cpu_threads or default_cpu_threads()
    key = (str(model_size_or_path), str(device), str(compute_type), threads)
    with _MODEL_LOCK:
        if key not in _MODEL_CACHE:
            try:
                _MODEL_CACHE[key] = whisper_cls(
                    model_size_or_path,
                    device=device,
                    compute_type=compute_type,
                    cpu_threads=threads,
                    num_workers=1,
                )
            except TypeError:
                _MODEL_CACHE[key] = whisper_cls(
                    model_size_or_path,
                    device=device,
                    compute_type=compute_type,
                )
        return _MODEL_CACHE[key]


# ----------------------------------------------------------------------
# Thai-specialized model (Thonburian Whisper)
# ----------------------------------------------------------------------
# The Hugging Face repository ships transformers weights only, which
# faster-whisper cannot open; scripts/convert_thai_whisper.sh converts it to
# CTranslate2 at THAI_SPECIALIZED_DEFAULT_PATH.
THAI_SPECIALIZED_SOURCE_MODEL = "biodatlab/whisper-th-medium-combined"
THAI_SPECIALIZED_PATH_ENV = "PASASCOPE_ASR_THAI_MODEL_PATH"
THAI_SPECIALIZED_DEFAULT_PATH = (
    Path(__file__).resolve().parents[2] / "models" / "whisper-th-medium-combined-ct2"
)


class ThaiModelUnavailableError(FileNotFoundError):
    """The converted Thai-specialized model is not on this machine."""


def thai_specialized_model_path() -> Path:
    """Where the converted Thai-specialized model is expected."""
    configured = os.environ.get(THAI_SPECIALIZED_PATH_ENV, "").strip()
    return Path(configured).expanduser() if configured else THAI_SPECIALIZED_DEFAULT_PATH


def thai_specialized_model_ready() -> bool:
    """True when a CTranslate2 conversion of the Thai model is present."""
    return (thai_specialized_model_path() / "model.bin").is_file()


# ----------------------------------------------------------------------
# Initial prompts (bias Whisper towards child-therapy / TH+EN domain)
# ----------------------------------------------------------------------
PROMPT_EN = (
    "This is a young child speaking with a parent or therapist during play. "
    "Toys, animals, colours, numbers, mom, dad, yes, no, look, more, please."
)
PROMPT_TH = (
    "เด็กเล็กกำลังพูดกับผู้ปกครองหรือนักบำบัดขณะเล่นของเล่น "
    "มีของเล่น สี ตัวเลข แม่ พ่อ ชอบ ไม่ชอบ เอา ให้."
)
PROMPT_BILINGUAL = PROMPT_EN + " " + PROMPT_TH

# Language strategy options for the dashboard / CLI
LanguageStrategy = Literal[
    "auto", "english", "thai", "dual_pass", "thai_specialized", "api_openai"
]

# Hallucination filter thresholds
_HALLUCINATION_NO_SPEECH_PROB = 0.85
_HALLUCINATION_AVG_LOGPROB = -1.25
_HALLUCINATION_REPEAT_NGRAM = 4   # reject segment if same 4-gram repeats >=3x
# Whisper sometimes appends sign-off phrases it never heard ("ขอบคุณที่ติดตาม
# สวัสดีครับ", "บ๊ายบาย") after the last speech, with confident scores but
# little or no time behind them. Speech cannot pack more letters into a
# second than this (fast Thai is ~15-20), so such segments are dropped.
_MIN_SEGMENT_SECONDS = 0.05
_MAX_LETTERS_PER_SECOND = 40.0


# Silero VAD misses quiet speech: on a far-field EllisWeismer recording it
# found 3 s of speech in 5 minutes and the draft had one line. The audio is
# scaled so its loud frames reach a fixed level before VAD and Whisper, and
# the speech threshold is lowered from Silero's 0.5. On 8 EllisWeismer
# recordings this cut the word error rate from 50% to 37% and found 211 child
# utterances against 121 (gold: 210). Silences stay at 400 ms: with 2 s, a
# scripted Thai dialogue went to Whisper as one chunk and the child's echoes of
# the adult were left out of the draft. Pieces of one utterance are re-joined
# later (segmentation.MAX_INTRA_TURN_GAP). A wider 300 ms speech pad ran the
# dialogue's turns together.
_VAD_PARAMETERS = dict(threshold=0.35, min_silence_duration_ms=400, speech_pad_ms=200)
_LOUD_FRAME_LEVEL = 0.1  # RMS the 95th-percentile 25 ms frame is scaled to
_FRAME_SAMPLES = 400


def _level_normalized(audio_path: str):
    """16 kHz mono samples with the loud frames at a fixed level."""
    import numpy as np
    from faster_whisper.audio import decode_audio

    audio = decode_audio(audio_path, sampling_rate=16000)
    frames = audio[: len(audio) // _FRAME_SAMPLES * _FRAME_SAMPLES].reshape(-1, _FRAME_SAMPLES)
    if not len(frames):
        return audio
    loud = float(np.percentile(np.sqrt((frames ** 2).mean(axis=1)), 95))
    if loud < 1e-5:
        return audio
    return np.clip(audio * (_LOUD_FRAME_LEVEL / loud), -1.0, 1.0).astype("float32")


def _shifted(seg, offset: float):
    """A faster-whisper segment with its times moved by ``offset`` seconds."""
    import copy

    def moved(item):
        item = copy.copy(item)
        item.start = None if item.start is None else item.start + offset
        item.end = None if item.end is None else item.end + offset
        return item

    seg = moved(seg)
    seg.words = [moved(w) for w in seg.words] if seg.words else seg.words
    return seg


def _too_fast_to_be_speech(text: str, start: float, end: float) -> bool:
    """True when a segment has (almost) no audio behind its text."""
    duration = end - start
    letters = len(re.sub(r"\s", "", text or ""))
    return duration < _MIN_SEGMENT_SECONDS or letters / duration > _MAX_LETTERS_PER_SECOND


def _hallucination_reason(text: str, avg_logprob: float, no_speech_prob: float) -> Optional[str]:
    """Why a segment looks like a Whisper hallucination on silence or noise, or None.

    "empty", "no_speech" (the model thinks nobody spoke), "low_logprob" (it was
    unsure of its own words) or "repeat" (the same 4-gram three times).
    """
    if not text or not text.strip():
        return "empty"
    if no_speech_prob > _HALLUCINATION_NO_SPEECH_PROB:
        return "no_speech"
    if avg_logprob < _HALLUCINATION_AVG_LOGPROB:
        return "low_logprob"
    # Detect repeated n-grams ("thank you. thank you. thank you. ...")
    tokens = re.findall(r"\w+", text.lower())
    if len(tokens) >= _HALLUCINATION_REPEAT_NGRAM * 3:
        n = _HALLUCINATION_REPEAT_NGRAM
        ngrams = [tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]
        if ngrams:
            top = max(ngrams.count(g) for g in set(ngrams))
            if top >= 3:
                return "repeat"
    return None


# Rules that rest only on the model's scores. A segment caught by one of these
# alone may still be a short real utterance (LOTUSDIS: 11 of 150 fast-mode
# lines), so it is kept and flagged for the therapist instead of deleted.
# Empty text, repeated n-grams and text too fast to be speech are still dropped.
UNCERTAIN_SPEECH_RULES = ("no_speech", "low_logprob")
SPEECH_MARKS = ("อาจไม่มีเสียงพูด", "Possibly no speech")


def describe_uncertain_speech(reason: str, avg_logprob: float, no_speech_prob: float) -> str:
    """Why a kept line may have no speech behind it, in the app's language."""
    import os

    english = os.environ.get("PASASCOPE_LANGUAGE", "th") == "en"
    if reason == "no_speech":
        if english:
            return f"Possibly no speech: the model gives a {no_speech_prob:.0%} chance that nobody spoke here."
        return f"อาจไม่มีเสียงพูด: โมเดลให้โอกาส {no_speech_prob:.0%} ว่าช่วงนี้ไม่มีคนพูด"
    if english:
        return f"Possibly no speech: the model was unsure of the words it wrote (mean log-probability {avg_logprob:.2f})."
    return f"อาจไม่มีเสียงพูด: โมเดลไม่มั่นใจคำที่ถอดได้ (log-probability เฉลี่ย {avg_logprob:.2f})"


def _looks_hallucinated(text: str, avg_logprob: float, no_speech_prob: float) -> bool:
    """Heuristic to drop common Whisper hallucinations on silence / noise."""
    return _hallucination_reason(text, avg_logprob, no_speech_prob) is not None


# A run of the same phrase three or more times (spaces optional, as Thai output
# may or may not separate words).
_LOOP = re.compile(r"(?P<unit>\S.{0,59}?)(?:\s*(?P=unit)){2,}")


def _trim_repetition_loop(text: str) -> str:
    """Cut a phrase the decoder kept repeating at the end of a segment.

    Fine-tuned models sometimes transcribe a turn correctly and then loop on
    its last phrase ("… แม่ มา ส่ง แม่ มา ส่ง แม่ มา ส่ง …"). One copy of the
    phrase is kept, since it was usually said once. Returns the text
    unchanged when the repetition does not run to the end.
    """
    for match in _LOOP.finditer(text):
        unit = match.group("unit").strip()
        rest = text[match.end():].strip()
        if not rest or unit.replace(" ", "").startswith(rest.replace(" ", "")):
            return (text[:match.start()] + match.group("unit")).strip()
    return text


# Greedy decoding sometimes writes a whole sentence twice in one segment
# (a 7 s FLEURS clip came back as the same 68-letter sentence twice). Shorter
# repeats are left alone: a child echoing the adult's sentence straight back
# can land in the same segment, and echoes are evidence the app has to keep.
# Thai echoes in the test dialogues run up to 22 letters.
_DOUBLED_MIN_LETTERS = 50


def _collapse_doubled_sentence(text: str) -> str:
    """One copy when the whole segment is a long sentence written twice."""
    letters = re.sub(r"\s", "", text or "")
    half = len(letters) // 2
    if len(letters) % 2 or half < _DOUBLED_MIN_LETTERS or letters[:half] != letters[half:]:
        return text
    kept, count = [], 0
    for char in text:
        if count == half:
            break
        kept.append(char)
        count += not char.isspace()
    return "".join(kept).strip()


def _keep_words_for(text: str, words: list) -> list:
    """The leading words whose letters make up ``text``."""
    budget = len(text.replace(" ", ""))
    kept, used = [], 0
    for word in words:
        letters = len((word.text or "").replace(" ", ""))
        if used + letters > budget:
            break
        kept.append(word)
        used += letters
    return kept


@dataclass
class WordSegment:
    """A single recognised word with timing and confidence."""
    text: str
    start: float           # seconds from start of audio
    end: float
    probability: float     # Whisper's word-level log-prob converted to [0,1]
    language: Optional[str] = None   # "en" / "th" / None


@dataclass
class UtteranceSegment:
    """A Whisper segment (sentence-ish) containing multiple words.

    Speaker is filled in later by the diarization stage; Whisper itself
    doesn't know who spoke.
    """
    start: float
    end: float
    text: str
    words: List[WordSegment] = field(default_factory=list)
    avg_logprob: float = 0.0
    no_speech_prob: float = 0.0
    speaker: Optional[str] = None   # "CHI", "MOT", "INV", ... set by diarizer
    # What the speaker label rests on: "voice" (a voice cluster), "frame"
    # (the child/adult frame model), "pitch", "context" (neighbouring labels)
    # or "rule" (a dialogue rule overrode it). Only the first two are confident.
    speaker_basis: Optional[str] = None
    language: Optional[str] = None  # detected language: "en" / "th" / None
    # Why this utterance starts here, when the boundary model decided it
    # (utterance_boundaries.segment_by_model), for the therapist to read.
    boundary_reason: Optional[str] = None
    # Why the clinic's own speaker model chose child or adult (clinic_speaker_model).
    speaker_reason: Optional[str] = None
    # Set when the filter's scores say nobody may have spoken here, but the text
    # looks like speech: the line is kept for the therapist to listen to.
    speech_reason: Optional[str] = None


class WhisperTranscriber:
    """Thin wrapper around faster_whisper that returns ``UtteranceSegment``s.

    Parameters
    ----------
    model_size : str
        Any faster-whisper model name.  ``"small"`` (244M) is the new
        default — much better than ``"base"`` on child speech and Thai.
        ``"medium"`` (769M) is best but slow on CPU.
    device : str
        ``"cpu"`` | ``"cuda"`` | ``"auto"``.
    compute_type : str
        ``"int8"`` (fastest on CPU), ``"float16"`` (GPU), ``"float32"``
        (most accurate).
    language : Optional[str]
        ISO-639-1 code (``"en"``/``"th"``) or ``None`` to auto-detect.
        Setting this overrides ``strategy``.
    strategy : LanguageStrategy
        Higher-level language strategy:

        * ``"auto"``  — single pass, Whisper detects language (default).
        * ``"english"`` / ``"thai"`` — force a single language.
        * ``"dual_pass"`` — run EN and TH passes, pick per-segment winner.
        * ``"thai_specialized"`` — use a Thai-fine-tuned Whisper model.
        * ``"api_openai"`` — send child audio to OpenAI's server when ``OPENAI_API_KEY`` is present, falling back to local auto.
    initial_prompt : Optional[str]
        Override the default TH/EN clinical prompt.
    """

    DEFAULT_MODEL = "small"   # was "base" — small is markedly better on child speech and Thai

    # Evaluation hook: when a list is set here, every segment Whisper returns is
    # recorded with its scores and what the filters did with it
    # (scripts/evaluate_segment_filter.py). None in the app.
    segment_log: Optional[list] = None
    # Keep lines dropped only by UNCERTAIN_SPEECH_RULES, flagged (speech_reason).
    flag_uncertain_speech: bool = True

    def __init__(
        self,
        model_size: str = DEFAULT_MODEL,
        device: str = "auto",
        compute_type: Optional[str] = None,
        language: Optional[str] = None,
        strategy: LanguageStrategy = "auto",
        initial_prompt: Optional[str] = None,
    ) -> None:
        # Import here so the rest of the project doesn't have to install
        # faster-whisper just to run the classifier/dashboard.
        try:
            from faster_whisper import WhisperModel
        except ImportError as e:
            raise ImportError(
                "faster-whisper is required for the audio pipeline.\n"
                "  pip install faster-whisper"
            ) from e

        self._WhisperModel = WhisperModel
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type or default_compute_type()
        self.strategy = strategy
        # `language` overrides strategy if explicitly set ("en" / "th" / None)
        if language is not None:
            self._explicit_language: Optional[str] = language
        else:
            self._explicit_language = {
                "english": "en", "thai": "th", "auto": None,
                "dual_pass": None, "thai_specialized": None,
                "api_openai": None,
            }.get(strategy, None)
        self._initial_prompt = initial_prompt
        self._model: Optional["WhisperModel"] = None      # lazy-loaded primary
        self._model_th: Optional["WhisperModel"] = None   # lazy-loaded Thai-specialized
        # Which checkpoint produced the last transcript, for provenance.
        self.last_model_id: Optional[str] = None

    # ------------------------------------------------------------------
    # Model management
    # ------------------------------------------------------------------
    def _load(self):
        """Lazy-load or retrieve cached primary multilingual Whisper model."""
        if self._model is None:
            self._model = get_cached_whisper_model(
                self._WhisperModel,
                self.model_size,
                self.device,
                self.compute_type,
            )
        return self._model

    def _load_detector(self):
        """The multilingual model used only to tell Thai from other languages.

        Under ``thai_specialized`` it never transcribes, so the small int8
        build is enough and keeps memory down next to the Thai model.
        """
        if self.strategy != "thai_specialized":
            return self._load()
        return get_cached_whisper_model(self._WhisperModel, self.model_size, self.device, "int8")

    def _load_thai_specialized(self):
        """Lazy-load or retrieve cached Thai-specialized Whisper checkpoint.

        Raises ``ThaiModelUnavailableError`` instead of quietly using the
        multilingual model, so a draft is never labelled with a model that
        did not produce it.
        """
        if self._model_th is not None:
            return self._model_th
        if not thai_specialized_model_ready():
            raise ThaiModelUnavailableError(
                f"Thai-specialized Whisper model not found at {thai_specialized_model_path()}. "
                "Run scripts/convert_thai_whisper.sh or set "
                f"{THAI_SPECIALIZED_PATH_ENV}."
            )
        self._model_th = get_cached_whisper_model(
            self._WhisperModel,
            str(thai_specialized_model_path()),
            self.device,
            self.compute_type,
        )
        return self._model_th

    def _detect_language(self, audio_path: str) -> Optional[str]:
        """Spoken language of the recording, from the multilingual model.

        The Thai fine-tuned model writes everything as Thai, so it is only
        given recordings the multilingual model hears as Thai.
        """
        from faster_whisper import decode_audio

        audio = decode_audio(audio_path, sampling_rate=16000)
        if not len(audio):
            return None
        language, _probability, _all = self._load_detector().detect_language(
            audio=audio, vad_filter=True, language_detection_segments=3,
        )
        return language

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _run_single(
        self,
        model,
        audio_path,
        *,
        language: Optional[str],
        vad_filter: bool,
        beam_size: int,
        prompt: Optional[str],
        temperature: float | list[float] = 0.0,
        progress_callback: Optional[Any] = None,
        offset: float = 0.0,
        redecode: bool = True,
    ) -> List[UtteranceSegment]:
        """Run one Whisper pass and return parsed UtteranceSegments.

        Applies hallucination filtering, Silero VAD acceleration, and per-segment language tagging.
        ``audio_path`` may also be 16 kHz samples already level-normalized (a re-decoded span);
        ``offset`` is then where they start in the recording.
        """
        import numpy as np

        is_samples = isinstance(audio_path, np.ndarray)
        source = audio_path if is_samples else (_level_normalized(audio_path) if vad_filter else audio_path)
        vad_params = dict(_VAD_PARAMETERS) if vad_filter else None
        segments, info = model.transcribe(
            source,
            language=language,
            beam_size=beam_size,
            best_of=1,
            vad_filter=vad_filter,
            vad_parameters=vad_params,
            word_timestamps=True,
            initial_prompt=prompt,
            condition_on_previous_text=False,
            temperature=temperature,
            compression_ratio_threshold=2.4,
            log_prob_threshold=-1.0,
            no_speech_threshold=0.6,
        )
        detected_lang = getattr(info, "language", language)
        total_duration = getattr(info, "duration", 0.0)

        out: List[UtteranceSegment] = []
        looped: list[tuple[float, float]] = []  # spans dropped as decoding loops, to decode again
        for seg in segments:
            if offset:
                seg = _shifted(seg, offset)
            avg_logprob = float(getattr(seg, "avg_logprob", 0.0))
            no_speech_prob = float(getattr(seg, "no_speech_prob", 0.0))
            text = (seg.text or "").strip()
            if progress_callback and total_duration > 0:
                cur_prog = min(0.70, 0.20 + (float(seg.end) / total_duration) * 0.50)
                progress_callback(cur_prog, f"ASR Transcribing: {float(seg.start):.1f}s - {float(seg.end):.1f}s...")

            log = self.segment_log
            entry = None
            if log is not None:
                entry = {
                    "start": float(seg.start), "end": float(seg.end), "text": text,
                    "avg_logprob": avg_logprob, "no_speech_prob": no_speech_prob,
                    "compression_ratio": float(getattr(seg, "compression_ratio", 0.0) or 0.0),
                    "kept": False, "reason": None,
                }
                if not redecode:
                    entry["redecoded"] = True
                log.append(entry)

            trimmed = False
            reason = _hallucination_reason(text, avg_logprob, no_speech_prob)
            speech_reason = None
            if (reason in UNCERTAIN_SPEECH_RULES and self.flag_uncertain_speech and redecode
                    and _hallucination_reason(text, 0.0, 0.0) is None):
                # Only the scores are against it: keep the line, flagged for the therapist.
                speech_reason = describe_uncertain_speech(reason, avg_logprob, no_speech_prob)
                reason = None
            if reason:
                # A correct turn followed by a decoding loop: keep the turn.
                shorter = _trim_repetition_loop(text)
                if shorter == text or _looks_hallucinated(shorter, avg_logprob, no_speech_prob):
                    if entry is not None:
                        entry["reason"] = reason
                    if reason == "repeat" and redecode:
                        looped.append((float(seg.start), float(seg.end)))
                    continue
                text, trimmed = shorter, True
            collapsed = _collapse_doubled_sentence(text)
            if collapsed != text:
                text, trimmed = collapsed, True
            seg_lang = getattr(seg, "language", None) or detected_lang
            words: List[WordSegment] = []
            if seg.words:
                for w in seg.words:
                    words.append(WordSegment(
                        text=(w.word or "").strip(),
                        start=float(w.start) if w.start is not None else float(seg.start),
                        end=float(w.end) if w.end is not None else float(seg.end),
                        probability=float(w.probability) if w.probability is not None else 0.0,
                        language=seg_lang,
                    ))
            seg_end = float(seg.end)
            if trimmed and words:
                words = _keep_words_for(text, words) or words[:1]
                seg_end = words[-1].end
            if _too_fast_to_be_speech(text, float(seg.start), seg_end):
                if entry is not None:
                    entry["reason"] = "too_fast"
                continue
            if entry is not None:
                entry["kept"] = True
                entry["flagged"] = speech_reason is not None
            out.append(UtteranceSegment(
                start=float(seg.start),
                end=seg_end,
                text=text,
                words=words,
                avg_logprob=avg_logprob,
                no_speech_prob=no_speech_prob,
                language=seg_lang,
                speech_reason=speech_reason,
            ))
        if looped:
            out = self._redecode_loops(model, source, looped, out, language=language, vad_filter=vad_filter,
                                       beam_size=beam_size, prompt=prompt, temperature=temperature)
        return out

    def _redecode_loops(self, model, source, spans, out, *, language, vad_filter, beam_size, prompt, temperature):
        """Decode each span that came back as a loop again, on its own.

        Whisper can lock into repeating one phrase for a whole 30 s window, and the
        repeat rule then drops the window with the real speech in it (26 of 196 CRSLP
        child utterances in the Thai accurate mode). Decoded alone, the span falls into
        different windows and usually decodes normally. The second attempt is filtered
        like the first, but lines doubted only by their scores are dropped rather than
        flagged, and a span that loops again is not tried a third time.
        """
        import numpy as np

        if not isinstance(source, np.ndarray):
            from faster_whisper.audio import decode_audio

            source = decode_audio(source, sampling_rate=16000)
        for start, end in spans:
            piece = source[int(start * 16000): int(end * 16000)]
            if len(piece) < 16000 * _MIN_SEGMENT_SECONDS:
                continue
            out.extend(self._run_single(
                model, piece, language=language, vad_filter=vad_filter, beam_size=beam_size,
                prompt=prompt, temperature=temperature, offset=start, redecode=False,
            ))
        return sorted(out, key=lambda seg: seg.start)

    @staticmethod
    def _merge_dual_pass(
        en_segs: List[UtteranceSegment],
        th_segs: List[UtteranceSegment],
    ) -> List[UtteranceSegment]:
        """Merge English-pass and Thai-pass results, picking per-segment winner.

        Two segments are considered overlapping if their time ranges
        overlap by >=20% of the shorter one.  The one with higher
        ``avg_logprob`` wins.  Non-overlapping segments are kept as-is.

        .. warning::
            * **Accidental turn-taking deletion**: Because this merge runs before
              speaker diarization, there is a risk that a child's short utterance
              and a therapist's overlapping prompt could be falsely merged,
              resulting in one being discarded.
            * **Greedy matching order dependency**: Sequential iteration through
              segments can lead to sub-optimal matches if a segment overlaps
              with multiple candidates.
        """
        merged: List[UtteranceSegment] = []
        used_th = [False] * len(th_segs)
        for en in en_segs:
            best_idx = -1
            best_overlap = 0.0
            for j, th in enumerate(th_segs):
                if used_th[j]:
                    continue
                overlap = max(0.0, min(en.end, th.end) - max(en.start, th.start))
                shorter = min(en.end - en.start, th.end - th.start) or 1e-6
                if overlap / shorter >= 0.2 and overlap > best_overlap:
                    best_overlap = overlap
                    best_idx = j
            if best_idx >= 0:
                th = th_segs[best_idx]
                used_th[best_idx] = True
                winner = en if en.avg_logprob >= th.avg_logprob else th
                merged.append(winner)
            else:
                merged.append(en)
        for j, th in enumerate(th_segs):
            if not used_th[j]:
                merged.append(th)
        merged.sort(key=lambda s: s.start)
        return merged

    @staticmethod
    def _recognized_word_count(segments: List[UtteranceSegment]) -> int:
        return sum(len(re.findall(r"\w+", seg.text)) for seg in segments)

    def _fallback_if_sparse(
        self,
        primary: List[UtteranceSegment],
        model,
        audio_path: str,
        *,
        language: Optional[str],
        beam_size: int,
        prompt: Optional[str],
        temperature: float | list[float] = 0.0,
    ) -> List[UtteranceSegment]:
        """Retry without VAD only when the first pass found virtually no speech."""
        # Flagged lines may be noise, so they do not count as having found speech.
        sure = [seg for seg in primary if not seg.speech_reason]
        if sure and (len(sure) >= 2 or self._recognized_word_count(sure) >= 4):
            return primary

        fallback = self._run_single(
            model,
            audio_path,
            language=language,
            vad_filter=False,
            beam_size=beam_size,
            prompt=prompt,
            temperature=temperature,
        )
        if len(fallback) > len(primary) or self._recognized_word_count(fallback) > self._recognized_word_count(primary):
            return fallback
        return primary

    # ------------------------------------------------------------------
    # Main API
    # ------------------------------------------------------------------
    def transcribe(
        self,
        audio_path: str | Path,
        *,
        vad_filter: bool = True,
        beam_size: int = 1,
        temperature: float | list[float] = 0.0,
        progress_callback: Optional[Any] = None,
    ) -> List[UtteranceSegment]:
        """Transcribe audio into a list of utterance segments.

        The ``strategy`` set on the constructor controls how language is
        handled (see class docstring).

        Parameters
        ----------
        audio_path : Path-like
            Any format supported by ffmpeg (wav, mp3, m4a, ...).
        vad_filter : bool
            Use Whisper's built-in voice-activity-detector to skip
            non-speech chunks.  Greatly reduces hallucinations during
            silences common in therapy recordings.
        beam_size : int
            Beam-search width.  Defaults to 1 (greedy search) for maximum speed.
        temperature : float | list[float]
            Sampling temperature. Defaults to 0.0 for deterministic fast decoding.
        progress_callback : Callable[[float, str], None] | None
            Optional callback to report real-time fraction (0.0 - 1.0) and status message.
        """
        audio_path = str(audio_path)

        if self.strategy == "api_openai":
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                print("[ASR] OPENAI_API_KEY missing, falling back to local model.")
                self.strategy = "auto"
                return self.transcribe(audio_path, vad_filter=vad_filter, beam_size=beam_size, temperature=temperature, progress_callback=progress_callback)

            if _OpenAIClient is None:
                print("[ASR] OpenAI SDK unavailable, falling back to local model.")
                self.strategy = "auto"
                return self.transcribe(audio_path, vad_filter=vad_filter, beam_size=beam_size, temperature=temperature, progress_callback=progress_callback)

            try:
                client = _OpenAIClient(api_key=api_key)
                self.last_model_id = "whisper-1"
                with open(audio_path, "rb") as audio_file:
                    # verbose_json returns segments and word timings if requested
                    response = client.audio.transcriptions.create(
                        file=audio_file,
                        model="whisper-1",
                        response_format="verbose_json",
                        timestamp_granularities=["word"]
                    )
            except Exception as e:
                print(f"[ASR] OpenAI API error: {e}, falling back to local model.")
                self.strategy = "auto"
                return self.transcribe(audio_path, vad_filter=vad_filter, beam_size=beam_size, temperature=temperature, progress_callback=progress_callback)
            
            out: List[UtteranceSegment] = []
            segments = getattr(response, "segments", []) or []
            for seg in segments:
                avg_logprob = float(seg.get("avg_logprob", 0.0) if isinstance(seg, dict) else getattr(seg, "avg_logprob", 0.0) or 0.0)
                no_speech_prob = float(seg.get("no_speech_prob", 0.0) if isinstance(seg, dict) else getattr(seg, "no_speech_prob", 0.0) or 0.0)
                text = (seg.get("text", "") if isinstance(seg, dict) else getattr(seg, "text", "") or "").strip()
                
                words: List[WordSegment] = []
                raw_words = seg.get("words", []) if isinstance(seg, dict) else getattr(seg, "words", []) or []
                for w in raw_words:
                    w_word = w.get("word", "") if isinstance(w, dict) else getattr(w, "word", "") or ""
                    w_start = float(w.get("start", 0.0) if isinstance(w, dict) else getattr(w, "start", 0.0) or 0.0)
                    w_end = float(w.get("end", 0.0) if isinstance(w, dict) else getattr(w, "end", 0.0) or 0.0)
                    w_prob = float(w.get("probability", 1.0) if isinstance(w, dict) else getattr(w, "probability", 1.0) or 1.0)
                    
                    words.append(WordSegment(
                        text=w_word.strip(),
                        start=w_start,
                        end=w_end,
                        probability=w_prob,
                        language=getattr(response, "language", None)
                    ))
                
                out.append(UtteranceSegment(
                    start=float(seg.get("start", 0.0) if isinstance(seg, dict) else getattr(seg, "start", 0.0) or 0.0),
                    end=float(seg.get("end", 0.0) if isinstance(seg, dict) else getattr(seg, "end", 0.0) or 0.0),
                    text=text,
                    words=words,
                    avg_logprob=avg_logprob,
                    no_speech_prob=no_speech_prob,
                    language=getattr(response, "language", None)
                ))
            return out

        # Choose initial prompt based on the language we're targeting
        if self._initial_prompt is not None:
            prompt: Optional[str] = self._initial_prompt
        elif self.strategy == "english" or self._explicit_language == "en":
            prompt = PROMPT_EN
        elif self.strategy == "thai" or self._explicit_language == "th":
            prompt = PROMPT_TH
        else:
            prompt = PROMPT_BILINGUAL

        if self.strategy == "dual_pass":
            model = self._load()
            self.last_model_id = self.model_size
            en = self._run_single(
                model, audio_path, language="en",
                vad_filter=vad_filter, beam_size=beam_size, prompt=PROMPT_EN,
                temperature=temperature, progress_callback=progress_callback,
            )
            if vad_filter:
                en = self._fallback_if_sparse(
                    en, model, audio_path,
                    language="en", beam_size=beam_size, prompt=PROMPT_EN,
                    temperature=temperature,
                )
            th = self._run_single(
                model, audio_path, language="th",
                vad_filter=vad_filter, beam_size=beam_size, prompt=PROMPT_TH,
                temperature=temperature, progress_callback=progress_callback,
            )
            if vad_filter:
                th = self._fallback_if_sparse(
                    th, model, audio_path,
                    language="th", beam_size=beam_size, prompt=PROMPT_TH,
                    temperature=temperature,
                )
            return self._merge_dual_pass(en, th)

        if self.strategy == "thai_specialized" and self._detect_language(audio_path) in (None, "th"):
            model = self._load_thai_specialized()
            self.last_model_id = THAI_SPECIALIZED_SOURCE_MODEL
            # Thonburian Whisper was fine-tuned without prompts: with PROMPT_TH
            # it appends looping greetings ("ขอบคุณครับ สวัสดีค่ะ ...") and one
            # 9 s FLEURS clip took 512 s instead of 14 s. Only an explicit
            # caller prompt is passed.
            th_prompt = self._initial_prompt
            primary = self._run_single(
                model, audio_path, language="th",
                vad_filter=vad_filter, beam_size=beam_size, prompt=th_prompt,
                temperature=temperature, progress_callback=progress_callback,
            )
            if vad_filter:
                return self._fallback_if_sparse(
                    primary, model, audio_path,
                    language="th", beam_size=beam_size, prompt=th_prompt,
                    temperature=temperature,
                )
            return primary

        # auto / english / thai, and thai_specialized recordings that are
        # not Thai => single pass with the multilingual model
        model = self._load()
        self.last_model_id = self.model_size
        primary = self._run_single(
            model, audio_path, language=self._explicit_language,
            vad_filter=vad_filter, beam_size=beam_size, prompt=prompt,
            temperature=temperature, progress_callback=progress_callback,
        )
        if vad_filter:
            return self._fallback_if_sparse(
                primary, model, audio_path,
                language=self._explicit_language, beam_size=beam_size, prompt=prompt,
                temperature=temperature,
            )
        return primary


# ----------------------------------------------------------------------
# CLI quick-test
# ----------------------------------------------------------------------
def _cli() -> None:
    import argparse, json, sys
    ap = argparse.ArgumentParser(description="Quick Whisper transcription test.")
    ap.add_argument("audio", type=Path)
    ap.add_argument("--model", default="small",
                    choices=["tiny", "base", "small", "medium", "large-v3"])
    ap.add_argument("--strategy", default="auto",
                    choices=["auto", "english", "thai", "dual_pass", "thai_specialized", "api_openai"])
    ap.add_argument("--lang", default=None,
                    help="Override language: 'en'/'th'/None (auto)")
    ap.add_argument("--json", action="store_true",
                    help="Emit JSON instead of human-readable text.")
    args = ap.parse_args()

    t = WhisperTranscriber(
        model_size=args.model, language=args.lang, strategy=args.strategy,
    )
    utts = t.transcribe(args.audio)

    if args.json:
        json.dump(
            [{"start": u.start, "end": u.end, "lang": u.language,
              "text": u.text, "words": [vars(w) for w in u.words]} for u in utts],
            sys.stdout, indent=2, ensure_ascii=False,
        )
    else:
        for u in utts:
            lang = u.language or "??"
            print(f"[{u.start:6.2f} -> {u.end:6.2f}]  ({lang})  {u.text}")


if __name__ == "__main__":
    _cli()
