"""Lines the filter doubts only by its scores are kept, flagged for the therapist."""

from types import SimpleNamespace

import pytest

from src.audio_pipeline.segmentation import _merge_segments, _split_at_long_silences
from src.audio_pipeline.whisper_transcribe import UtteranceSegment, WhisperTranscriber, WordSegment


def _segment(text, start, end, *, no_speech=0.1, logprob=-0.3):
    words = [SimpleNamespace(word=w, start=start + i * 0.3, end=start + i * 0.3 + 0.25, probability=0.8)
             for i, w in enumerate(text.split())]
    return SimpleNamespace(text=text, start=start, end=end, avg_logprob=logprob, no_speech_prob=no_speech,
                           compression_ratio=1.0, words=words)


class _Model:
    def __init__(self, segments):
        self.segments = segments

    def transcribe(self, *_args, **_kwargs):
        return iter(self.segments), SimpleNamespace(language="th", duration=30.0)


def _run(segments, *, flag=True, log=None):
    transcriber = WhisperTranscriber.__new__(WhisperTranscriber)
    transcriber.flag_uncertain_speech = flag
    transcriber.segment_log = log
    return transcriber._run_single(_Model(segments), "unused.wav", language="th", vad_filter=False,
                                   beam_size=1, prompt=None)


@pytest.fixture(autouse=True)
def _thai(monkeypatch):
    monkeypatch.setenv("PASASCOPE_LANGUAGE", "th")


def test_short_line_doubted_by_scores_is_kept_and_flagged():
    log = []
    out = _run([
        _segment("ไป เล่น", 1.0, 2.5, no_speech=0.91),
        _segment("หมา กิน ข้าว", 4.0, 6.0, logprob=-1.4),
        _segment("แม่ มา ส่ง", 7.0, 8.5),
    ], log=log)

    assert [u.text for u in out] == ["ไป เล่น", "หมา กิน ข้าว", "แม่ มา ส่ง"]
    assert out[0].speech_reason.startswith("อาจไม่มีเสียงพูด") and "91%" in out[0].speech_reason
    assert "-1.40" in out[1].speech_reason
    assert out[2].speech_reason is None
    assert [(e["kept"], e["flagged"], e["reason"]) for e in log] == [
        (True, True, None), (True, True, None), (True, False, None)]


def test_text_rules_still_drop_what_cannot_be_speech():
    log = []
    out = _run([
        _segment("", 0.0, 1.0, no_speech=0.95),                                   # empty
        _segment("thank you " * 7, 2.0, 9.0, no_speech=0.95),                     # repeated 4-gram
        _segment("สวัสดีครับคุณครูวันนี้อากาศดีมากเลย", 10.0, 10.3, no_speech=0.9),  # too fast for speech
    ], log=log)

    assert out == []
    assert [e["reason"] for e in log] == ["empty", "no_speech", "too_fast"]  # the loop: scores and text agree


def test_old_behaviour_when_flagging_is_off():
    out = _run([_segment("ไป เล่น", 1.0, 2.5, no_speech=0.91)], flag=False)
    assert out == []


def test_english_explanation(monkeypatch):
    monkeypatch.setenv("PASASCOPE_LANGUAGE", "en")
    out = _run([_segment("go play", 1.0, 2.5, no_speech=0.9)])
    assert out[0].speech_reason.startswith("Possibly no speech") and "90%" in out[0].speech_reason


def test_flag_survives_merging_and_splitting():
    words = [WordSegment("ไป", 0.0, 0.3, 0.9), WordSegment("เล่น", 1.5, 1.8, 0.9)]
    doubted = UtteranceSegment(0.0, 1.8, "ไป เล่น", words, speaker="CHI", speech_reason="อาจไม่มีเสียงพูด: x")
    sure = UtteranceSegment(2.0, 2.5, "รถ", [WordSegment("รถ", 2.0, 2.5, 0.9)], speaker="CHI")

    assert all(p.speech_reason for p in _split_at_long_silences(doubted, min_gap=0.5))
    assert _merge_segments(sure, doubted).speech_reason == "อาจไม่มีเสียงพูด: x"
    assert _merge_segments(sure, sure).speech_reason is None


def test_reason_reaches_the_stored_notes():
    from app.services.asr_providers.base import TranscriptionResult, TranscriptLine
    from app.services.audio_job_service import create_draft_transcript_from_result

    repo = SimpleNamespace(sessions={"s1": SimpleNamespace(case_id="c1", transcript_id=None, status=None)}, transcripts={})
    result = TranscriptionResult(
        status="completed", provider_id="local_whisper", provider_name="Local Whisper", provider_version="test",
        transcript_lines=[TranscriptLine(line_id="l1", speaker="CHI", text="ไป เล่น", start_ms=0, end_ms=900,
                                         confidence=0.9, speech_reason="อาจไม่มีเสียงพูด: โมเดลให้โอกาส 91% ว่าช่วงนี้ไม่มีคนพูด")],
        language="th",
    )
    transcript = create_draft_transcript_from_result(repo, "s1", result)
    assert transcript.utterances[0].notes.startswith("อาจไม่มีเสียงพูด")


def test_review_page_explains_the_flag_until_the_line_is_reviewed():
    from app.schemas.clinical import Utterance

    from packages.desktop.ui.pages.review import explain_utterance, note_parts, speech_note

    notes = ("อาจไม่มีเสียงพูด: โมเดลให้โอกาส 91% ว่าช่วงนี้ไม่มีคนพูด "
             "ขึ้นประโยคใหม่ (โอกาส 84%, หยุด 0.9 วินาที): ช่วงหยุด +1.8")
    utt = Utterance(utterance_id="u1", speaker="CHI", text="ไป เล่น", start_ms=0, end_ms=900,
                    confidence=0.9, source="asr", notes=notes)

    assert speech_note(utt) == "อาจไม่มีเสียงพูด: โมเดลให้โอกาส 91% ว่าช่วงนี้ไม่มีคนพูด"
    assert note_parts(notes)[0].startswith("ขึ้นประโยคใหม่")
    rows = dict(explain_utterance(utt))
    assert "ลบบรรทัดนี้" in rows["เสียงพูด"]
    reviewed = utt.model_copy(update={"review_status": "reviewed"})
    assert speech_note(reviewed) == "" and "เสียงพูด" not in dict(explain_utterance(reviewed))
