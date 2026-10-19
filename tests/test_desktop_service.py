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


def _attested_asr_session(svc: DesktopService, case_id: str, tmp_path, index: int) -> None:
    """A recording with the child speaking (a tone) in every other second, attested as if Whisper drafted it."""
    import numpy as np
    import soundfile

    rate = 16000
    audio = np.zeros(6 * rate, dtype="float32")
    lines = []
    for second in range(6):
        child = second % 2 == 1
        if child:
            t = np.arange(rate) / rate
            audio[second * rate:(second + 1) * rate] = 0.3 * np.sin(2 * np.pi * 300 * t)
        lines.append(f"*{'CHI' if child else 'INV'}:\tคำ{second} . \x15{second * 1000 + 100}_{second * 1000 + 900}\x15")
    wav = tmp_path / f"rec{index}.wav"
    soundfile.write(wav, audio, rate)
    session = svc.create_session(case_id, date(2026, 10, index + 1))
    svc.store_recording(session.session_id, wav)
    chat = "@Begin\n@Languages:\ttha\n@Participants:\tCHI Target_Child, INV Investigator\n" + "\n".join(lines) + "\n@End\n"
    transcript = svc.import_transcript_text(session.session_id, chat)
    svc.attest(transcript.transcript_id, override_reason="ตรวจกับเสียงแล้ว")
    svc.repo.transcripts[transcript.transcript_id].source = "asr_draft:local_whisper"


class _LoudnessFrames:
    """Stands in for the USC model: hears every frame as adult; its features carry the loudness."""

    def frame_outputs(self, audio):
        import numpy as np

        frames = len(audio) // 320
        loud = np.sqrt((audio[: frames * 320].reshape(frames, 320) ** 2).mean(axis=1))
        return np.repeat(loud[:, None], 4, axis=1), np.tile([0.1, 0.1, 0.7, 0.1], (frames, 1))


def test_clinic_speaker_model_learns_from_attested_sessions(service, tmp_path, monkeypatch):
    import os

    import numpy as np

    from src.audio_pipeline import child_adult_frames
    from src.audio_pipeline.clinic_speaker_model import CLINIC_MODEL_ENV, load_adopted_head

    monkeypatch.setattr(child_adult_frames, "ChildAdultFrameModel", _LoudnessFrames)
    monkeypatch.delenv(CLINIC_MODEL_ENV, raising=False)
    first = _case_with_consent(service)
    second = service.create_case("TH-002", 60)
    service.grant_consent(second.case_id, "ผู้ปกครอง", date(2026, 10, 1))
    for index, case in enumerate((first, second, first)):
        _attested_asr_session(service, case.case_id, tmp_path, index)

    status = service.update_clinic_speaker_model()
    assert status["sessions_needed"] == 1 and not status["trained"] and not status["in_use"]

    _attested_asr_session(service, second.case_id, tmp_path, 3)
    status = service.update_clinic_speaker_model()
    assert status["in_use"] and status["eligible_sessions"] == 4 and status["eligible_children"] == 2
    assert status["model_accuracy"] == 1.0 and status["frame_accuracy"] == 0.5
    assert os.environ[CLINIC_MODEL_ENV] == str(service.clinic_speaker_model_path)
    head = load_adopted_head()
    assert head is not None and head.examples is not None and len(head.examples.labels) == 24
    child_row = np.r_[np.full(4, 0.2), [0.1, 0.1, 0.7, 0.1], np.log(0.8)]  # loud like the child's lines
    reason = head.explain(child_row)
    assert reason.startswith("โมเดลประจำคลินิก: เสียงเด็ก") and "(เด็ก)" in reason and "TH-00" in reason
    assert any(e["action"] == "speaker_model.train" for e in service.audit_events())

    service.set_clinic_speaker_enabled(False)
    assert CLINIC_MODEL_ENV not in os.environ and not service.clinic_speaker_status()["in_use"]
    service.set_clinic_speaker_enabled(True)
    assert os.environ[CLINIC_MODEL_ENV]

    service.withdraw_consent(second.case_id, "ผู้ปกครองขอถอน")
    assert service.clinic_speaker_status()["eligible_children"] == 1  # withdrawn children are not trained on again

    service.reset_clinic_speaker_model()
    assert not service.clinic_speaker_model_path.exists() and CLINIC_MODEL_ENV not in os.environ


def test_work_queue_lists_what_waits_for_the_therapist(service):
    consented = _case_with_consent(service)
    waiting = service.create_case("TH-009", 40)
    imported = service.create_session(consented.case_id, date(2026, 10, 10))
    transcript = service.import_transcript_text(imported.session_id, CHAT)
    empty = service.create_session(consented.case_id, date(2026, 10, 12))

    queue = service.work_queue()
    assert [(row["case"].child_code, row["step"]) for row in queue] == [("TH-009", "consent"), ("TH-001", 1), ("TH-001", 0)]
    assert queue[1]["session"].session_id == imported.session_id and queue[2]["session"].session_id == empty.session_id

    service.attest(transcript.transcript_id, override_reason="ตรวจกับเสียงแล้ว")
    assert [row["step"] for row in service.work_queue()] == ["consent", 2, 0]
    assert waiting.case_id == queue[0]["case"].case_id


def test_deleting_a_session_or_a_case_removes_its_records_and_recordings(service, tmp_path):
    import sqlite3

    import numpy as np
    import soundfile

    wav = tmp_path / "clip.wav"
    soundfile.write(wav, np.zeros(16000, dtype="float32"), 16000)
    kept = _case_with_consent(service)
    kept_session = service.create_session(kept.case_id, date(2026, 10, 2))
    service.import_transcript_text(kept_session.session_id, CHAT)

    case = service.create_case("TH-DEL", 50)
    service.grant_consent(case.case_id, "ผู้ปกครอง", date(2026, 10, 1))
    first = service.create_session(case.case_id, date(2026, 10, 2))
    recording = service.store_recording(first.session_id, wav)
    transcript = service.import_transcript_text(first.session_id, CHAT)
    service.attest(transcript.transcript_id, override_reason="test")
    service.analyze(first.session_id)
    service.sign_off(service.draft_report(first.session_id).report_id)
    second = service.create_session(case.case_id, date(2026, 10, 9))
    service.import_transcript_text(second.session_id, CHAT)

    summary = service.deletion_summary(case.case_id)
    assert summary == {"sessions": 2, "recordings": 1, "transcripts": 2, "reports": 1, "signed_reports": 1}

    service.delete_session(second.session_id)
    assert [s.session_id for s in service.list_sessions(case.case_id)] == [first.session_id]

    with pytest.raises(WorkflowError):
        service.delete_case(case.case_id, "TH-WRONG")
    assert service.audio_path(recording).is_file()

    service.delete_case(case.case_id, "TH-DEL")
    assert [c.child_code for c in service.list_cases()] == ["TH-001"]
    assert not any(path.is_file() for path in service.workspace.storage_root.rglob("*"))

    # Read back from disk: the other case is whole, the deleted one is gone, and the audit log says so.
    reopened = DesktopService(open_workspace(tmp_path / "ws"))
    assert [c.child_code for c in reopened.list_cases()] == ["TH-001"]
    assert len(reopened.list_sessions(kept.case_id)) == 1
    database = next(path for path in (tmp_path / "ws").rglob("*") if path.suffix in {".db", ".sqlite", ".sqlite3"})
    with sqlite3.connect(database) as db:
        assert db.execute("select count(*) from sessions").fetchone()[0] == 1
        assert db.execute("select count(*) from transcripts").fetchone()[0] == 1
        assert db.execute("select count(*) from reports").fetchone()[0] == 0
        assert db.execute("select count(*) from audio_files").fetchone()[0] == 0
        actions = [row[0] for row in db.execute("select action from audit_logs where action like '%.delete'")]
    assert sorted(actions) == ["case.delete", "session.delete"]


def test_case_details_can_be_edited_but_not_the_code(service):
    case = _case_with_consent(service)
    service.update_case(case.case_id, nickname="ภูมิ", age_months=53, language="Thai + English", notes="ย้ายมาจากคลินิกอื่น")
    edited = service.get_case(case.case_id)
    assert (edited.child_code, edited.nickname, edited.age_months, edited.language) == ("TH-001", "ภูมิ", 53, "Thai + English")
    assert edited.notes == "ย้ายมาจากคลินิกอื่น"


def test_playback_keeps_the_recordings_own_quality(service, tmp_path):
    import subprocess
    import sys

    import numpy as np
    import soundfile

    seconds = np.arange(44100 * 2) / 44100
    stereo = np.stack([0.3 * np.sin(2 * np.pi * 440 * seconds), 0.3 * np.sin(2 * np.pi * 6000 * seconds)], axis=1)
    wav = tmp_path / "clip.wav"
    soundfile.write(wav, stereo.astype("float32"), 44100)
    case = _case_with_consent(service)

    # A file the player reads as it is: no 16 kHz mono copy.
    mp3 = tmp_path / "clip.mp3"
    soundfile.write(mp3, stereo.astype("float32"), 44100, format="MP3")
    stored = service.store_recording(service.create_session(case.case_id, date(2026, 10, 16)).session_id, mp3)
    assert service.playback_path(stored) == service.audio_path(stored)

    # A container it cannot read is decoded once, at 44.1 kHz stereo.
    if sys.platform == "darwin":
        m4a = tmp_path / "clip.m4a"
        subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", str(wav), str(m4a)], check=True)
        stored = service.store_recording(service.create_session(case.case_id, date(2026, 10, 17)).session_id, m4a)
        info = soundfile.info(str(service.playback_path(stored)))
        assert (info.samplerate, info.channels) == (44100, 2)


def test_player_resamples_to_the_output_device():
    import numpy as np

    from packages.desktop.ui.audio import _for_output_device

    class Device:
        def query_devices(self, kind):
            return {"default_samplerate": 48000.0}

    data, rate = _for_output_device(Device(), np.zeros((16000, 1), dtype="float32"), 16000)
    assert rate == 48000 and data.shape == (48000, 1) and data.dtype == np.float32
