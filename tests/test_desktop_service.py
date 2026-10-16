"""The desktop workflow against a real SQLite workspace, without Qt or Whisper."""

from __future__ import annotations

from datetime import date

import pytest

from packages.desktop.core import DesktopService, WorkflowError, open_workspace

CHAT = """@Begin
@Languages:\ttha
@Participants:\tCHI Target_Child, INV Investigator
*INV:\tหนูชอบกินอะไร
*CHI:\tชอบกินขนม
*INV:\tขนมอะไรครับ
*CHI:\tขนมอะไรครับ
*INV:\tเล่นรถกันไหม
*CHI:\tเล่นรถ สีแดง
*INV:\tรถคันนี้สีอะไร
*CHI:\tสีแดง ไม่เอา สีฟ้า
@End
"""


@pytest.fixture
def service(tmp_path):
    workspace = open_workspace(tmp_path / "ws")
    svc = DesktopService(workspace)
    svc.set_therapist_name("นักบำบัด ทดสอบ")
    return svc


def _case_with_consent(svc: DesktopService):
    case = svc.create_case("TH-001", 48, nickname="น้องเอ")
    svc.grant_consent(case.case_id, "ผู้ปกครอง", date(2026, 10, 1))
    return case


def test_full_workflow_persists_across_restart(service, tmp_path):
    case = _case_with_consent(service)
    session = service.create_session(case.case_id, date(2026, 10, 16))

    transcript = service.import_transcript_text(session.session_id, CHAT)
    assert [u.speaker for u in transcript.utterances][:2] == ["INV", "CHI"]

    edited = [u.model_copy() for u in transcript.utterances]
    edited[1] = edited[1].model_copy(update={"text": "ชอบกินขนมครับ"})
    service.save_utterances(transcript.transcript_id, edited, note="แก้คำตามเสียง")

    attested = service.attest(transcript.transcript_id, override_reason="ตรวจกับเสียงแล้ว")
    assert attested.therapist_attested

    features, cues = service.analyze(session.session_id)
    names = {f.name for f in features.features}
    assert "child_utterance_count" in names
    assert cues.not_diagnostic

    if cues.cues:
        updated = service.set_cue_state(cues.result_id, cues.cues[0].cue_code, "acknowledged", "ตรวจแล้ว")
        assert updated.cues[0].review_state.status == "acknowledged"

    report = service.draft_report(session.session_id)
    signed = service.sign_off(report.report_id)
    assert signed.signed_by == "นักบำบัด ทดสอบ"

    out = service.export_report(signed.report_id, "markdown", tmp_path / "out" / "report.md")
    assert out.read_text(encoding="utf-8").strip()

    reopened = DesktopService(open_workspace(tmp_path / "ws"))
    assert [c.child_code for c in reopened.list_cases()] == ["TH-001"]
    again = reopened.get_transcript(session.session_id)
    assert again.utterances[1].text == "ชอบกินขนมครับ"
    assert reopened.get_report(session.session_id).signed_by == "นักบำบัด ทดสอบ"
    actions = {e["action"] for e in reopened.audit_events()}
    assert {"case.create", "report.export"} <= actions


def test_session_needs_consent(service):
    case = service.create_case("TH-002", 40)
    with pytest.raises(WorkflowError, match="บันทึกความยินยอม"):
        service.create_session(case.case_id, date(2026, 10, 16))


def test_withdrawn_consent_blocks_new_work(service):
    case = _case_with_consent(service)
    session = service.create_session(case.case_id, date(2026, 10, 16))
    service.withdraw_consent(case.case_id, "ผู้ปกครองขอถอน")
    with pytest.raises(WorkflowError):
        service.import_transcript_text(session.session_id, CHAT)


def test_duplicate_child_code_is_rejected(service):
    service.create_case("TH-003", 36)
    with pytest.raises(WorkflowError, match="TH-003"):
        service.create_case("TH-003", 36)


def test_signing_needs_a_therapist_name(tmp_path):
    svc = DesktopService(open_workspace(tmp_path / "ws"))
    case = _case_with_consent(svc)
    session = svc.create_session(case.case_id, date(2026, 10, 16))
    transcript = svc.import_transcript_text(session.session_id, CHAT)
    with pytest.raises(WorkflowError, match="ชื่อนักบำบัด"):
        svc.attest(transcript.transcript_id)


def test_analysis_requires_attestation(service):
    case = _case_with_consent(service)
    session = service.create_session(case.case_id, date(2026, 10, 16))
    service.import_transcript_text(session.session_id, CHAT)
    with pytest.raises(WorkflowError, match="รับรอง"):
        service.analyze(session.session_id)


def test_store_recording_copies_audio_into_workspace(service, tmp_path):
    import numpy as np
    import soundfile

    wav = tmp_path / "clip.wav"
    soundfile.write(wav, np.zeros(16000, dtype="float32"), 16000)
    case = _case_with_consent(service)
    session = service.create_session(case.case_id, date(2026, 10, 16))

    stored = service.store_recording(session.session_id, wav)

    assert stored.upload_status == "uploaded"
    assert stored.duration_seconds == pytest.approx(1.0)
    path = service.audio_path(stored)
    assert path.is_file() and service.workspace.storage_root in path.parents
    assert service.session_audio(session.session_id).audio_file_id == stored.audio_file_id


def test_transcribe_reports_progress_and_can_be_cancelled(service, tmp_path, monkeypatch):
    import threading

    import numpy as np
    import soundfile

    from app.services.asr_providers import local_whisper_provider
    from app.services.asr_providers.base import ProviderAvailability

    wav = tmp_path / "clip.wav"
    soundfile.write(wav, np.zeros(16000, dtype="float32"), 16000)
    case = _case_with_consent(service)
    session = service.create_session(case.case_id, date(2026, 10, 16))
    stored = service.store_recording(session.session_id, wav)

    cancel = threading.Event()

    def fake_audio_to_cha(path, **kwargs):
        kwargs["progress_callback"](0.2, "ASR")
        cancel.set()
        kwargs["progress_callback"](0.4, "ASR")
        raise AssertionError("should have stopped")

    monkeypatch.setattr(
        local_whisper_provider.LocalWhisperProvider,
        "check_availability",
        lambda self: ProviderAvailability(available=True, reason="ok"),
    )
    monkeypatch.setattr(
        local_whisper_provider,
        "import_module",
        lambda name: type("M", (), {"audio_to_cha": staticmethod(fake_audio_to_cha)}),
    )
    seen = []
    with pytest.raises(WorkflowError, match="ยกเลิก"):
        service.transcribe(session.session_id, stored.audio_file_id, progress=lambda f, s: seen.append(f), cancel=cancel)
    assert seen == [0.2]
    assert service.get_transcript(session.session_id) is None


def test_lists_mix_records_read_back_and_new_ones(tmp_path):
    first = DesktopService(open_workspace(tmp_path / "ws"))
    first.create_case("TH-100", 40)
    reopened = DesktopService(open_workspace(tmp_path / "ws"))
    reopened.list_cases()  # loads the stored case
    reopened.create_case("TH-101", 41)
    assert [c.child_code for c in reopened.list_cases()] == ["TH-101", "TH-100"]


def test_review_time_report_reads_the_desktop_database(service, tmp_path, monkeypatch):
    import importlib.util
    import types

    import numpy as np
    import soundfile

    from app.services.asr_providers import local_whisper_provider
    from app.services.asr_providers.base import ProviderAvailability

    wav = tmp_path / "clip.wav"
    soundfile.write(wav, np.zeros(32000, dtype="float32"), 16000)
    case = _case_with_consent(service)
    session = service.create_session(case.case_id, date(2026, 10, 16))
    stored = service.store_recording(session.session_id, wav)

    def fake_audio_to_cha(path, **kwargs):
        words = [types.SimpleNamespace(probability=0.9)]
        segment = lambda spk, text, a, b: types.SimpleNamespace(  # noqa: E731
            text=text, speaker=spk, start=a, end=b, words=words, language="th"
        )
        return types.SimpleNamespace(
            utterances=[segment("INV", "เล่นอะไรดี", 0.0, 0.8), segment("CHI", "เล่นรถ", 1.0, 1.6)],
            asr_model="test",
        )

    monkeypatch.setattr(
        local_whisper_provider.LocalWhisperProvider, "check_availability",
        lambda self: ProviderAvailability(available=True, reason="ok"),
    )
    monkeypatch.setattr(
        local_whisper_provider, "import_module",
        lambda name: types.SimpleNamespace(audio_to_cha=fake_audio_to_cha),
    )
    transcript = service.transcribe(session.session_id, stored.audio_file_id)
    service.attest(transcript.transcript_id)

    spec = importlib.util.spec_from_file_location("review_time", "scripts/report_transcript_review_time.py")
    review_time = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(review_time)
    rows = review_time.review_times(review_time.repository_from_desktop(service.workspace.root))

    assert len(rows) == 1
    assert rows[0]["transcript_id"] == transcript.transcript_id
    assert rows[0]["audio_seconds"] == 2.0
    assert rows[0]["review_minutes"] >= 0


def test_transcription_mode_switches_the_strategy_and_is_remembered(tmp_path):
    from app.core.config import get_settings

    svc = DesktopService(open_workspace(tmp_path / "ws"))
    assert svc.transcription_mode == "accurate"
    assert get_settings().asr_language_strategy == "thai_specialized"

    svc.set_transcription_mode("fast")
    assert get_settings().asr_language_strategy == "thai"

    reopened = DesktopService(open_workspace(tmp_path / "ws"))
    assert reopened.transcription_mode == "fast"
    reopened.set_transcription_mode("accurate")
    assert get_settings().asr_language_strategy == "thai_specialized"
