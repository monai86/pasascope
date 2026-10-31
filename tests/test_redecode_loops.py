"""A segment that comes back as a decoding loop is decoded again on its own."""

from types import SimpleNamespace

import numpy as np
import pytest

from src.audio_pipeline.whisper_transcribe import WhisperTranscriber

LOOP = "หอม กึ่ง " * 8 + "กร๊าก " * 8  # two loops in a row: trimming cannot save it


def _segment(text, start, end, *, no_speech=0.05, logprob=-0.2):
    words = [SimpleNamespace(word=w, start=start + i * 0.4, end=start + i * 0.4 + 0.3, probability=0.8)
             for i, w in enumerate(text.split())]
    return SimpleNamespace(text=text, start=start, end=end, avg_logprob=logprob, no_speech_prob=no_speech,
                           compression_ratio=1.0, words=words)


class _Model:
    """Loops over the whole recording; decodes a span on its own as ``span_result``."""

    def __init__(self, span_result):
        self.span_result = span_result
        self.spans = []

    def transcribe(self, audio, **_kwargs):
        info = SimpleNamespace(language="th", duration=20.0)
        if isinstance(audio, np.ndarray):
            self.spans.append(len(audio) / 16000)
            return iter(self.span_result), info
        return iter([_segment("แม่ มา แล้ว", 0.5, 2.0), _segment(LOOP, 3.0, 13.0)]), info


@pytest.fixture
def recording(tmp_path):
    import soundfile

    path = tmp_path / "clip.wav"
    soundfile.write(str(path), np.zeros(16000 * 20, dtype="float32"), 16000)
    return str(path)


def _run(model, recording, log=None):
    transcriber = WhisperTranscriber.__new__(WhisperTranscriber)
    transcriber.flag_uncertain_speech = True
    transcriber.segment_log = log
    return transcriber._run_single(model, recording, language="th", vad_filter=False, beam_size=1, prompt=None)


def test_looped_span_is_decoded_again_and_placed_in_time(recording):
    log = []
    model = _Model([_segment("นี่ สี อะไร", 0.5, 2.0), _segment("สี เหลือง", 4.0, 5.0)])
    out = _run(model, recording, log)

    assert model.spans == [10.0]  # only the looped 3-13 s span
    assert [(u.text, u.start) for u in out] == [("แม่ มา แล้ว", 0.5), ("นี่ สี อะไร", 3.5), ("สี เหลือง", 7.0)]
    assert out[1].words[0].start == pytest.approx(3.5)
    assert [(e["reason"], e.get("redecoded", False)) for e in log] == [
        (None, False), ("repeat", False), (None, True), (None, True)]


def test_second_attempt_drops_doubtful_lines_and_does_not_loop_again(recording):
    model = _Model([_segment(LOOP, 0.0, 10.0), _segment("หมา หมา", 6.0, 7.0, no_speech=0.95)])
    out = _run(model, recording)

    assert [u.text for u in out] == ["แม่ มา แล้ว"]
    assert model.spans == [10.0]  # tried once more, not a third time
