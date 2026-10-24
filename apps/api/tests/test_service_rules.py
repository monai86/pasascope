"""Workflow rules of the shared service layer, called the way the desktop program calls it.

These replace the HTTP-level checks of the removed web API (git tag web-app-final).
"""

from __future__ import annotations

import pytest

from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import (
    AttestationRequest,
    FeatureExtractionRequest,
    MLReviewRequest,
    QaIssue,
    ReportGenerationRequest,
    ReviewStatus,
    TranscriptManualCreate,
    TranscriptMergeRequest,
    TranscriptPatch,
    TranscriptSplitRequest,
    TranscriptUploadCha,
)
from app.services import transcript_service
from app.services.asr_providers.base import BaseTranscriptionProvider, ProviderAvailability
from app.services.asr_providers.registry import asr_provider_registry
from app.services.audio_job_service import validate_audio_upload
from app.services.consent_service import (
    ensure_report_consent_active,
    ensure_session_consent_active,
    ensure_transcript_consent_active,
    withdraw_consent,
)
from app.services.feature_service import extract_features
from app.services.ml_providers.registry import ml_provider_registry
from app.services.ml_review_service import MLReadinessError, check_ml_readiness, create_ml_review, get_current_ml_review
from app.services.report_service import draft_report, export_report, sign_off_report
from tests.service_helpers import USER_ID, new_session

SAMPLE = "CHI: I see car\nCHI: more car\nCHI: car fast\nTHER: tell me more"


def _manual(repo, session_id: str, text: str = SAMPLE, **extra):
    return transcript_service.create_from_manual(
        repo, session_id, TranscriptManualCreate(text=text, language="English", **extra), actor_id=USER_ID
    )


def _attest(repo, transcript_id: str, reason: str = "Reviewed."):
    transcript_service.run_qa(repo, transcript_id, actor_id=USER_ID)
    return transcript_service.attest(repo, transcript_id, AttestationRequest(reason=reason), actor_id=USER_ID)


def _analysed(code: str, text: str = SAMPLE):
    """A session with an attested transcript and extracted features."""
    repo = MockRepository()
    session = new_session(repo, code, age_months=60)
    transcript = _manual(repo, session.session_id, text)
    _attest(repo, transcript.transcript_id)
    features = extract_features(repo, transcript.transcript_id, FeatureExtractionRequest(), actor_id=USER_ID)
    return repo, session.session_id, transcript.transcript_id, features


def _values(feature_set) -> dict:
    return {item.name: item.value for item in feature_set.features}


# Features


def test_feature_extraction_calculates_core_metrics():
    repo = MockRepository()
    session = new_session(repo, "C-FEATURE-METRICS", age_months=54)
    transcript = _manual(repo, session.session_id, "CHI: red car\nCHI: blue car\nCHI: car go\nTHER: tell me more\nUNK: background noise")
    utterances = [u.model_copy() for u in transcript.utterances]
    utterances[1] = utterances[1].model_copy(update={"unintelligible": True})
    patched = transcript_service.patch_transcript(
        repo, transcript.transcript_id, TranscriptPatch(utterances=utterances, reviewer_note="Mark unintelligible."), actor_id=USER_ID
    )
    _attest(repo, transcript.transcript_id)

    features = extract_features(repo, transcript.transcript_id, FeatureExtractionRequest(), actor_id=USER_ID)

    values = _values(features)
    assert values["total_utterance_count"] == 5
    assert values["child_utterance_count"] == 3
    assert values["adult_utterance_count"] == 1
    assert values["total_word_count"] == 6
    assert values["number_of_different_words"] == 4
    assert values["type_token_ratio"] == 0.6667
    assert values["mean_length_of_utterance_words"] == 2.0
    assert values["unintelligible_ratio"] == 0.2
    assert values["unknown_speaker_ratio"] == 0.2
    assert values["question_ratio"] == 0
    assert values["echolalia_cue_count"] == 0
    assert values["pronoun_reversal_cue_count"] == 0
    assert features.transcript_version == patched.version


def test_feature_extraction_rejects_transcript_change_during_provider_work(monkeypatch):
    repo = MockRepository()
    session = new_session(repo, "C-RACE", age_months=60)
    transcript_id = _manual(repo, session.session_id, "CHI: one\nCHI: two\nCHI: three").transcript_id
    _attest(repo, transcript_id)

    from app.services.feature_service import provider_registry

    provider = provider_registry.get_default()
    original_extract = provider.extract_features

    def edit_during_extraction(transcript):
        result = original_extract(transcript)
        repo.transcripts[transcript_id].version += 1
        repo.transcripts[transcript_id].therapist_attested = False
        return result

    monkeypatch.setattr(provider, "extract_features", edit_during_extraction)
    with pytest.raises(ValueError, match="(?i)changed during feature extraction"):
        extract_features(repo, transcript_id, FeatureExtractionRequest(), actor_id=USER_ID)
    assert repo.sessions[session.session_id].feature_set_id is None


# Review cues


def test_review_cues_use_features_without_diagnostic_output():
    repo, session_id, transcript_id, _ = _analysed(
        "C-ML-SUPPORT", "THER: what do you see?\nCHI: blue car car\nCHI: I see blue car\nCHI: what is that?"
    )
    assert check_ml_readiness(repo, transcript_id).ready is True

    result = create_ml_review(repo, transcript_id, MLReviewRequest(), actor_id=USER_ID)

    assert result.status == "completed"
    assert result.cues
    assert result.not_diagnostic is True
    assert result.decision_support_only is True
    assert result.provider_id == "rule_based_review_cue"
    assert result.input_feature_hash
    assert get_current_ml_review(repo, session_id).result_id == result.result_id
    assert create_ml_review(repo, transcript_id, MLReviewRequest(), actor_id=USER_ID).result_id == result.result_id
    serialized = str(result.model_dump()).lower()
    for phrase in ("asd positive", "asd negative", "probability of asd"):
        assert phrase not in serialized


def test_review_cues_need_an_attested_transcript_and_store_nothing_otherwise():
    repo = MockRepository()
    session = new_session(repo, "C-ML-LOCK", age_months=54)
    transcript_id = _manual(repo, session.session_id, "CHI: hello\nCHI: more\nCHI: play").transcript_id
    before = len(repo.ml_results)

    with pytest.raises(MLReadinessError) as caught:
        create_ml_review(repo, transcript_id, MLReviewRequest(), actor_id=USER_ID)

    assert "transcript_requires_review" in caught.value.readiness.reason_codes
    assert len(repo.ml_results) == before


@pytest.mark.parametrize(
    ("provider_id", "reason"),
    [("baseline_research_classifier", "ml_provider_unavailable"), ("unknown-provider", "ml_provider_unsupported")],
)
def test_unavailable_or_unknown_cue_provider_is_refused_without_fallback(provider_id, reason):
    repo, _, transcript_id, _ = _analysed("C-ML-PROVIDER", "THER: tell me\nCHI: blue car\nCHI: more car\nCHI: car car")
    before = len(repo.ml_results)

    with pytest.raises(MLReadinessError) as caught:
        create_ml_review(repo, transcript_id, MLReviewRequest(provider_id=provider_id), actor_id=USER_ID)

    assert reason in caught.value.readiness.reason_codes
    assert len(repo.ml_results) == before


def test_research_classifier_stays_unavailable():
    assert ml_provider_registry.get_default().provider_name == "RuleBasedReviewCueProvider"
    assert {provider.provider_id for provider in ml_provider_registry.list_supported()} >= {
        "rule_based_review_cue",
        "baseline_research_classifier",
    }
    assert [provider.provider_id for provider in ml_provider_registry.list_available()] == ["rule_based_review_cue"]


def test_readiness_blocks_missing_values_review_state_and_blocking_issues():
    repo, _, transcript_id, features = _analysed("C-ML-READY")
    feature_set = repo.features[features.feature_set_id]
    transcript = repo.transcripts[transcript_id]

    original = list(feature_set.features)
    feature_set.features = [item for item in original if item.name != "total_word_count"]
    assert "required_features_missing" in check_ml_readiness(repo, transcript_id).reason_codes
    feature_set.features = original

    transcript.review_status = ReviewStatus.needs_review
    assert "transcript_requires_review" in check_ml_readiness(repo, transcript_id).reason_codes
    transcript.review_status = ReviewStatus.attested

    transcript.qa_issues = [QaIssue(code="BLOCKING_TEST", severity="error", message="Blocking.", blocking=True)]
    assert "blocking_chat_validation_errors" in check_ml_readiness(repo, transcript_id).reason_codes


# Transcript edits and stale outputs


def test_transcript_edit_invalidates_attestation_and_marks_outputs_stale():
    repo, session_id, transcript_id, features = _analysed("C-STALE")
    attested_version = repo.transcripts[transcript_id].version
    cues = create_ml_review(repo, transcript_id, MLReviewRequest(), actor_id=USER_ID)
    report = draft_report(repo, session_id, actor_id=USER_ID)

    # Attesting again without an edit keeps the outputs current.
    _attest(repo, transcript_id, "Metadata-only re-attestation.")
    assert repo.features[features.feature_set_id].review_status == ReviewStatus.ready
    assert repo.reports[report.report_id].status == ReviewStatus.draft
    assert get_current_ml_review(repo, session_id).result_id == cues.result_id

    utterances = [u.model_copy() for u in repo.transcripts[transcript_id].utterances]
    utterances[0] = utterances[0].model_copy(update={"text": "I see a red car"})
    edited = transcript_service.patch_transcript(
        repo, transcript_id, TranscriptPatch(utterances=utterances, reviewer_note="Edited after outputs."), actor_id=USER_ID
    )

    assert edited.version == attested_version + 1
    assert edited.qa_status.value == "NOT_RUN"
    assert edited.qa_issues == []
    assert edited.therapist_attested is False
    session = repo.sessions[session_id]
    assert (session.feature_set_id, session.report_id) == (features.feature_set_id, report.report_id)
    assert repo.features[features.feature_set_id].review_status == ReviewStatus.stale
    assert repo.reports[report.report_id].status == ReviewStatus.stale
    with pytest.raises(KeyError, match="stale"):
        get_current_ml_review(repo, session_id)
    with pytest.raises(ValueError, match="stale"):
        sign_off_report(repo, report.report_id, "Demo Therapist", signed_by_user_id=USER_ID)


def test_transcript_replacement_marks_outputs_stale():
    repo, session_id, first_id, features = _analysed("C-REPLACE")
    report = draft_report(repo, session_id, actor_id=USER_ID)

    replacement = _manual(repo, session_id, "CHI: replacement sample\nCHI: more sample\nCHI: sample done", replace_existing=True)

    assert replacement.transcript_id != first_id
    assert repo.sessions[session_id].transcript_id == replacement.transcript_id
    assert repo.features[features.feature_set_id].review_status == ReviewStatus.stale
    assert repo.reports[report.report_id].status == ReviewStatus.stale
    with pytest.raises(ValueError):
        sign_off_report(repo, report.report_id, "Demo Therapist", signed_by_user_id=USER_ID)


def test_report_generation_rejects_transcript_change_during_provider_work(monkeypatch):
    repo, session_id, transcript_id, _ = _analysed("C-REPORT-RACE", "CHI: one\nCHI: two\nCHI: three")

    from app.services.report_service import report_provider_registry

    provider = report_provider_registry.get("template")
    original_generate = provider.generate_report

    def edit_during_report_generation(input_data, config):
        result = original_generate(input_data, config)
        repo.transcripts[transcript_id].version += 1
        return result

    monkeypatch.setattr(provider, "generate_report", edit_during_report_generation)
    with pytest.raises(ValueError, match="(?i)changed during report generation"):
        draft_report(repo, session_id, actor_id=USER_ID)
    assert repo.sessions[session_id].report_id is None


def test_creating_again_reuses_the_active_transcript_and_report_draft():
    repo, session_id, transcript_id, _ = _analysed("C-RETRY")
    first_text = repo.transcripts[transcript_id].raw_text

    retry = _manual(repo, session_id, "CHI: accidental retry")
    assert retry.transcript_id == transcript_id
    assert retry.raw_text == first_text

    first_report = draft_report(repo, session_id, actor_id=USER_ID)
    assert draft_report(repo, session_id, actor_id=USER_ID).report_id == first_report.report_id


# Transcript editing and CHAT


def test_split_merge_and_export_cha():
    repo = MockRepository()
    session = new_session(repo, "C-3001", age_months=60)
    transcript = _manual(repo, session.session_id, "CHI: I see red car and blue truck\nCHI: more truck please\nTHER: tell me more")

    split = transcript_service.split_utterance(
        repo,
        transcript.transcript_id,
        TranscriptSplitRequest(utterance_id=transcript.utterances[0].utterance_id, split_at_character=14),
        actor_id=USER_ID,
    )
    assert len(split.utterances) == 4
    assert split.therapist_attested is False

    merged = transcript_service.merge_utterances(
        repo,
        transcript.transcript_id,
        TranscriptMergeRequest(
            first_utterance_id=split.utterances[0].utterance_id,
            second_utterance_id=split.utterances[1].utterance_id,
        ),
        actor_id=USER_ID,
    )
    assert len(merged.utterances) == 3

    cha = transcript_service.export_cha(repo, transcript.transcript_id).cha_text
    assert "@Begin" in cha
    assert "*CHI:" in cha


@pytest.mark.parametrize(
    ("languages", "lines", "code"),
    [
        ("spa", ["*CHI:\tveo un carro rojo .", "*CHI:\tquiero mas carro .", "*CHI:\tel carro va rapido ."], "UNSUPPORTED_LANGUAGE"),
        ("eng", ["*CHI:\tI want รถ red .", "*CHI:\tmore car please .", "*CHI:\tgo fast ."], "CODE_SWITCHING_WARNING"),
    ],
)
def test_qa_warns_about_language_metadata(languages, lines, code):
    repo = MockRepository()
    session = new_session(repo, f"C-LANG-{code[:4]}", age_months=52)
    cha = "\n".join(
        ["@Begin", f"@Languages:\t{languages}", "@Participants:\tCHI Child Target_Child, THER Therapist Investigator", *lines, "@End"]
    )
    transcript = transcript_service.create_from_cha(
        repo, session.session_id, TranscriptUploadCha(filename="sample.cha", cha_text=cha), actor_id=USER_ID
    )

    report = transcript_service.run_qa(repo, transcript.transcript_id, actor_id=USER_ID)

    assert code in {issue.code for issue in report.issues}


# Reports


EXPORT_CHA = "\n".join(
    [
        "@Begin",
        "@Languages:\teng",
        "@Participants:\tCHI Child Target_Child, THER Therapist Investigator",
        "*THER:\twhat do you see ?",
        "*CHI:\tI see a red car .",
        "*CHI:\tthe car goes fast .",
        "*CHI:\tI want car again .",
        "@End",
    ]
)


def test_report_exports_as_draft_and_signed_with_a_snapshot():
    repo = MockRepository()
    session = new_session(repo, "C-EXPORT", age_months=57)
    transcript = transcript_service.create_from_cha(
        repo, session.session_id, TranscriptUploadCha(filename="export.cha", cha_text=EXPORT_CHA), actor_id=USER_ID
    )
    _attest(repo, transcript.transcript_id, "Reviewed for export.")
    extract_features(repo, transcript.transcript_id, FeatureExtractionRequest(), actor_id=USER_ID)
    report = draft_report(repo, session.session_id, actor_id=USER_ID)

    assert export_report(repo, report.report_id, "markdown").content.strip()

    signed = sign_off_report(repo, report.report_id, "Demo Therapist", signed_by_user_id=USER_ID)
    assert signed.export_timestamp is not None
    assert signed.signed_by == "Demo Therapist"
    assert signed.signed_at is not None
    assert signed.signed_snapshot_version == signed.version
    assert len(signed.signed_snapshot_hash) == 64
    snapshot = signed.signed_snapshot
    assert snapshot["report_id"] == report.report_id
    assert snapshot["report_version"] == signed.version
    assert snapshot["signed_by"] == "Demo Therapist"
    assert snapshot["report_hash"] == signed.signed_snapshot_hash
    assert "Signed by: Demo Therapist" in signed.markdown

    markdown = export_report(repo, report.report_id, "markdown")
    assert markdown.content_type == "text/markdown"
    assert markdown.report_hash == signed.signed_snapshot_hash
    assert markdown.report_version == signed.version
    assert markdown.signed_by == "Demo Therapist"
    assert "clinical decision-support prototype" in markdown.content
    assert "Signed by: Demo Therapist" in markdown.content

    html = export_report(repo, report.report_id, "html")
    assert html.content_type == "text/html"
    assert "<h1>" in html.content


def test_report_types_include_their_focus_sections():
    repo = MockRepository()
    session = new_session(repo, "C-REPORT-TYPES", age_months=58)
    transcript = _manual(repo, session.session_id, "CHI: I see car\nCHI: more car\nTHER: tell me more")
    transcript_service.run_qa(repo, transcript.transcript_id, actor_id=USER_ID)

    qa_markdown = draft_report(
        repo, session.session_id, ReportGenerationRequest(report_type="Transcript QA Report"), actor_id=USER_ID
    ).markdown
    for heading in (
        "## Transcript QA Detail",
        "## Transcript QA Report Focus",
        "## Recommended Therapist Review",
        "## Clinical Interpretation Notes",
        "## Export Timestamp",
    ):
        assert heading in qa_markdown

    _attest(repo, transcript.transcript_id)
    extract_features(repo, transcript.transcript_id, FeatureExtractionRequest(), actor_id=USER_ID)
    research_markdown = draft_report(
        repo,
        session.session_id,
        ReportGenerationRequest(report_type="Research/Model Summary Report", replace_existing=True),
        actor_id=USER_ID,
    ).markdown
    assert "## Research/Model Summary Report Focus" in research_markdown
    assert "Feature schema version: features-basic-v3" in research_markdown
    assert "does not establish Thai clinical validation" in research_markdown


def test_feature_debug_override_is_refused_unless_the_runtime_allows_it(monkeypatch):
    repo = MockRepository()
    session = new_session(repo, "C-DEBUG-OFF", age_months=56)
    transcript_id = _manual(repo, session.session_id, "THER: tell me more").transcript_id
    assert transcript_service.run_qa(repo, transcript_id, actor_id=USER_ID).overall_status == "FAIL"

    from app.core.config import get_settings

    monkeypatch.setenv("PASASCOPE_DEBUG_FEATURE_OVERRIDE", "false")
    get_settings.cache_clear()
    try:
        with pytest.raises(ValueError, match="debug override is disabled"):
            extract_features(
                repo,
                transcript_id,
                FeatureExtractionRequest(force_debug_override=True, override_reason="Engineering QA only."),
                actor_id=USER_ID,
            )
    finally:
        monkeypatch.delenv("PASASCOPE_DEBUG_FEATURE_OVERRIDE")
        get_settings.cache_clear()


def test_exported_cha_names_linked_audio_without_its_file_name():
    from app.schemas.clinical import AudioUploadRequest
    from app.services.audio_job_service import create_audio_upload_job

    repo = MockRepository()
    session = new_session(repo, "C-MEDIA", age_months=52)
    upload = create_audio_upload_job(
        repo,
        session.session_id,
        AudioUploadRequest(filename="family_sample.wav", content_type="audio/wav", size_bytes=2048, duration_seconds=30),
        actor_id=USER_ID,
    )
    audio_file_id = upload.details["audio_file"]["audio_file_id"]
    transcript_id = _manual(repo, session.session_id, "CHI: I see car\nCHI: more car\nCHI: car fast").transcript_id

    cha = transcript_service.export_cha(repo, transcript_id).cha_text

    assert f"@Media:\t{session.session_id}_{audio_file_id}, audio" in cha
    assert "family_sample" not in cha


# Consent and uploads


def test_consent_withdrawal_unlinks_outputs_and_blocks_further_work():
    repo, session_id, transcript_id, features = _analysed("C-WD-BLOCK")
    report = draft_report(repo, session_id, actor_id=USER_ID)
    case_id = repo.sessions[session_id].case_id

    result = withdraw_consent(repo, case_id, "Guardian request", True, actor_id=USER_ID, requester_role="therapist")

    assert result.affected_records["features"] >= 1
    assert features.feature_set_id not in repo.features
    assert repo.sessions[session_id].feature_set_id is None
    for check, target in (
        (ensure_session_consent_active, session_id),
        (ensure_transcript_consent_active, transcript_id),
        (ensure_report_consent_active, report.report_id),
    ):
        with pytest.raises(ValueError, match="consent has been withdrawn"):
            check(repo, target)


def test_audio_upload_rejects_unsafe_filename():
    from app.schemas.clinical import AudioUploadRequest

    with pytest.raises(ValueError):
        validate_audio_upload(
            AudioUploadRequest(filename="../session.wav", content_type="audio/wav", size_bytes=2048, duration_seconds=30)
        )


# Transcription jobs (the desktop creates a job and runs it at once)


class _FailingAsrProvider(BaseTranscriptionProvider):
    provider_id = "failing_test_provider"
    provider_name = "FailingTestProvider"
    provider_version = "test"

    def get_provider_metadata(self) -> dict:
        return {"provider_id": self.provider_id}

    def check_availability(self) -> ProviderAvailability:
        return ProviderAvailability(available=True)

    def transcribe(self, audio_ref, config=None):
        raise RuntimeError("ASR failed")


@pytest.fixture
def failing_asr_provider():
    provider = _FailingAsrProvider()
    asr_provider_registry.register(provider)
    yield provider
    asr_provider_registry.unregister(provider.provider_id)


def _run_job(repo, session_id: str, **request):
    from app.schemas.clinical import AudioProcessRequest
    from app.services.audio_job_service import create_audio_processing_job, run_audio_processing_job

    job = create_audio_processing_job(repo, session_id, AudioProcessRequest(**request), actor_id=USER_ID)
    assert job.status.value == "queued"
    return run_audio_processing_job(repo, job.job_id, actor_id=USER_ID)


def test_transcription_creates_an_unreviewed_draft():
    repo = MockRepository()
    session = new_session(repo, "C-4001")

    job = _run_job(
        repo,
        session.session_id,
        provider="manual",
        draft_text="THER: what do you see\nCHI: I see car",
        duration_seconds=120,
        sample_rate_hz=16000,
        channels=1,
    )

    assert job.status.value == "needs_review"
    assert job.details["status_history"] == ["queued", "processing", "transcription_completed", "needs_review"]
    assert "diarization failed" in job.details["asr_draft"]["warnings"]
    transcript = repo.transcripts[job.details["asr_draft"]["transcript_id"]]
    assert transcript.source == "asr_draft:manual"
    assert transcript.therapist_attested is False
    assert any(item.speaker == "UNK" for item in transcript.utterances)


def test_transcription_warns_when_no_child_speech_is_detected():
    repo = MockRepository()
    session = new_session(repo, "C-AUDIO-NO-CHI")

    job = _run_job(
        repo, session.session_id, provider="manual", draft_text="THER: tell me what happened",
        duration_seconds=30, sample_rate_hz=16000, channels=1,
    )

    warnings = job.details["asr_draft"]["warnings"]
    assert job.status.value == "needs_review"
    assert {"transcript too short", "no child speech detected", "diarization failed"} <= set(warnings)


def test_asr_failure_is_recorded_as_a_failed_job_with_no_text(failing_asr_provider):
    repo = MockRepository()
    session = new_session(repo, "C-ASR-FAILED")

    job = _run_job(
        repo, session.session_id, provider=failing_asr_provider.provider_id,
        duration_seconds=30, sample_rate_hz=16000, channels=1,
    )

    assert job.status.value == "failed"
    assert job.error_code == "asr_failed"
    assert job.message == "ASR failed"
    assert job.details["status_history"] == ["queued", "processing", "failed"]
    assert repo.sessions[session.session_id].transcript_id is None


def test_transcription_fails_on_a_quality_blocker():
    repo = MockRepository()
    session = new_session(repo, "C-AUDIO-QUALITY")

    job = _run_job(repo, session.session_id, provider="manual", duration_seconds=3700, channels=1)

    assert job.status.value == "failed"
    assert job.error_code == "audio_quality_failed"


# Coverage, storage and progress


def test_qa_warns_when_timestamps_cover_too_little_linked_audio():
    from app.schemas.clinical import AudioUploadRequest
    from app.services.audio_job_service import create_audio_upload_job

    repo = MockRepository()
    session = new_session(repo, "C-COVERAGE", age_months=52)
    create_audio_upload_job(
        repo,
        session.session_id,
        AudioUploadRequest(
            filename="coverage.wav", content_type="audio/wav", size_bytes=2048,
            duration_seconds=120, sample_rate_hz=16000, channels=1,
        ),
        actor_id=USER_ID,
    )
    transcript = _manual(repo, session.session_id)
    utterances = [
        u.model_copy(update={"start_ms": index * 2500, "end_ms": (index + 1) * 2500})
        for index, u in enumerate(transcript.utterances)
    ]
    transcript_service.patch_transcript(
        repo, transcript.transcript_id, TranscriptPatch(utterances=utterances, reviewer_note="Draft timestamps."), actor_id=USER_ID
    )

    report = transcript_service.run_qa(repo, transcript.transcript_id, actor_id=USER_ID)

    assert "LOW_TRANSCRIPT_COVERAGE" in {issue.code for issue in report.issues}


def test_consent_withdrawal_deletes_the_stored_recording(tmp_path, monkeypatch):
    from app.core.config import get_settings
    from app.schemas.clinical import AudioUploadRequest
    from app.services.audio_job_service import create_audio_upload_job

    monkeypatch.setenv("PASASCOPE_STORAGE_MODE", "local")
    monkeypatch.setenv("PASASCOPE_LOCAL_STORAGE_ROOT", str(tmp_path))
    get_settings.cache_clear()
    try:
        repo = MockRepository()
        session = new_session(repo, "C-AUDIO-LOCAL", age_months=52)
        upload = create_audio_upload_job(
            repo,
            session.session_id,
            AudioUploadRequest(filename="local.wav", content_type="audio/wav", size_bytes=2048, duration_seconds=30),
            actor_id=USER_ID,
        )
        audio_file = repo.audio_files[upload.details["audio_file"]["audio_file_id"]]
        assert audio_file.object_key.startswith("audio/obj_")
        assert "local.wav" not in audio_file.object_key
        object_path = tmp_path / audio_file.object_key
        object_path.parent.mkdir(parents=True)
        object_path.write_bytes(b"placeholder")

        withdraw_consent(
            repo, session.case_id, "Guardian withdrew consent", True, actor_id=USER_ID, requester_role="therapist"
        )

        stored = repo.audio_files[audio_file.audio_file_id]
        assert stored.storage_mode == "local_private"
        assert stored.storage_delete_status == "deleted"
        assert not object_path.exists()
    finally:
        get_settings.cache_clear()


def test_report_draft_compares_with_the_previous_session():
    from app.schemas.clinical import TherapySessionCreate

    repo = MockRepository()
    first = new_session(repo, "C-PROGRESS", age_months=58)
    second = repo.create_session(first.case_id, TherapySessionCreate(session_date="2026-07-20"), actor_id=USER_ID)
    texts = {
        first.session_id: "CHI: car\nCHI: more car\nCHI: go car\nTHER: tell me more",
        second.session_id: "CHI: I see red car\nCHI: the car goes fast\nCHI: I want more car\nTHER: tell me more",
    }
    for session_id, text in texts.items():
        transcript_id = _manual(repo, session_id, text).transcript_id
        _attest(repo, transcript_id)
        extract_features(repo, transcript_id, FeatureExtractionRequest(), actor_id=USER_ID)

    markdown = draft_report(repo, second.session_id, actor_id=USER_ID).markdown

    assert "## Progress Comparison" in markdown
    assert "mean_length_of_utterance_words" in markdown
    assert "Progress comparison is descriptive and requires therapist interpretation." in markdown


def test_profile_positions_use_the_shared_iqr_classifier(tmp_path):
    from app.services.ml_providers.reference_evidence import ReferenceEvidenceProvider, iqr_position
    from tests.service_helpers import write_reference_artifact

    provider = ReferenceEvidenceProvider(write_reference_artifact(tmp_path))
    previous = ml_provider_registry.providers.get(provider.provider_id)
    ml_provider_registry.register(provider)
    try:
        repo = MockRepository()
        session = new_session(repo, "C-ML-IQR", age_months=62)
        transcript_id = _manual(repo, session.session_id, "CHI: I see car\nCHI: more car\nCHI: car fast").transcript_id
        _attest(repo, transcript_id)
        extract_features(repo, transcript_id, FeatureExtractionRequest(), actor_id=USER_ID)
        result = create_ml_review(repo, transcript_id, MLReviewRequest(provider_id=provider.provider_id), actor_id=USER_ID)
    finally:
        if previous is None:
            ml_provider_registry.providers.pop(provider.provider_id, None)
        else:
            ml_provider_registry.register(previous)

    assert result.status == "completed"
    td = next(profile for profile in result.profile_evidence if profile.profile_code == "TD")
    assert td.associated_features
    for feature in td.associated_features:
        assert feature.position == iqr_position(feature.observed_value, feature.q1, feature.q3)
