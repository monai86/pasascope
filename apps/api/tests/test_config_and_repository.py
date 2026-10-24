"""Settings and local persistence of the service layer."""

import json
from pathlib import Path
import warnings

import pytest

from app.core.config import get_settings
from app.repositories.mock_repository import JsonFileRepository, MockRepository
from tests.path_helpers import repo_root


def test_demo_manifest_includes_required_non_identifying_assets():
    repository_root = repo_root()
    manifest_path = repository_root / "data" / "demo" / "demo_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["demo_mode"] == "lingualens-app-local"
    assert {account["role"] for account in manifest["mock_accounts"]} == {"therapist", "org_admin"}
    assert len(manifest["cases"]) >= 2
    assert len(manifest["sessions"]) >= 2
    assert (repository_root / manifest["artifacts"]["sample_cha"]).exists()
    assert (repository_root / manifest["artifacts"]["sample_report"]).exists()

    serialized = json.dumps(manifest).lower()
    forbidden_terms = ["_".join(["audio", "bytes"]), "storage_key", "email@", "surname"]
    assert not any(term in serialized for term in forbidden_terms)
    assert all(case["child_code"].startswith("C-") for case in manifest["cases"])


def test_storage_mode_defaults_to_local_private(monkeypatch):
    monkeypatch.delenv("PASASCOPE_STORAGE_MODE", raising=False)
    monkeypatch.delenv("THERAPIST_APP_V2_STORAGE_MODE", raising=False)
    get_settings.cache_clear()

    assert get_settings().storage_mode == "local_private"

    get_settings.cache_clear()


def test_pasascope_prefix_wins_over_the_older_names(monkeypatch):
    monkeypatch.setenv("PASASCOPE_STORAGE_MODE", "local")
    monkeypatch.setenv("LINGUALENS_STORAGE_MODE", "local_private")
    monkeypatch.setenv("THERAPIST_APP_V2_STORAGE_MODE", "local_private")
    monkeypatch.setenv("PASASCOPE_DATABASE_URL", "sqlite:///./compat-preferred.db")
    monkeypatch.setenv("THERAPIST_APP_V2_DATABASE_URL", "sqlite:///./compat-legacy.db")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.storage_mode == "local"
    assert settings.database_url == "sqlite:///./compat-preferred.db"

    get_settings.cache_clear()


def test_therapist_app_v2_names_still_work_with_a_deprecation_warning(monkeypatch):
    monkeypatch.delenv("PASASCOPE_STORAGE_MODE", raising=False)
    monkeypatch.delenv("LINGUALENS_STORAGE_MODE", raising=False)
    monkeypatch.setenv("THERAPIST_APP_V2_STORAGE_MODE", "local")
    get_settings.cache_clear()

    with pytest.warns(DeprecationWarning, match="THERAPIST_APP_V2_STORAGE_MODE"):
        assert get_settings().storage_mode == "local"

    get_settings.cache_clear()


def test_previous_project_prefix_is_still_read_without_warning(monkeypatch):
    monkeypatch.delenv("PASASCOPE_STORAGE_MODE", raising=False)
    monkeypatch.delenv("THERAPIST_APP_V2_STORAGE_MODE", raising=False)
    monkeypatch.setenv("LINGUALENS_STORAGE_MODE", "local")
    monkeypatch.setenv("LINGUALENS_ASR_LOCAL_WHISPER_ENABLED", "true")
    get_settings.cache_clear()

    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        settings = get_settings()

    assert settings.storage_mode == "local"
    assert settings.asr_local_whisper_enabled is True
    assert not [warning for warning in recorded if warning.category is DeprecationWarning]

    get_settings.cache_clear()


def test_debug_feature_override_falls_back_to_therapist_prefix(monkeypatch):
    monkeypatch.delenv("PASASCOPE_DEBUG_FEATURE_OVERRIDE", raising=False)
    monkeypatch.setenv("THERAPIST_APP_V2_DEBUG_FEATURE_OVERRIDE", "true")
    get_settings.cache_clear()

    assert get_settings().debug_feature_override is True

    get_settings.cache_clear()


def test_json_file_repository_round_trip(tmp_path):
    path = tmp_path / "repository.json"
    repo = JsonFileRepository(path)
    repo.cases["case_json"] = repo.cases["case_demo_001"].model_copy(update={"case_id": "case_json"})
    repo.add_audit("test.persist", "case_json", "Persisted test case.")

    restored = JsonFileRepository(path)
    assert "case_json" in restored.cases
    assert any(item["action"] == "test.persist" for item in restored.audit_log)


def test_sqlalchemy_repository_round_trip_when_available(tmp_path):
    pytest.importorskip("sqlalchemy")
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    database_url = f"sqlite:///{tmp_path / 'therapist_v2.db'}"
    repo = SqlAlchemyRepository(database_url)
    repo.cases["case_sql"] = repo.cases["case_demo_001"].model_copy(update={"case_id": "case_sql", "child_code": "C-SQL"})
    repo.add_audit("test.sql_persist", "case_sql", "Persisted SQL repository test case.")

    restored = SqlAlchemyRepository(database_url)
    assert restored.cases["case_sql"].child_code == "C-SQL"
    assert any(item["action"] == "test.sql_persist" for item in restored.audit_events())


def test_sqlalchemy_metadata_contains_v2_clinical_tables():
    pytest.importorskip("sqlalchemy")
    from app.db.models import Base

    expected = {
        "child_cases",
        "therapy_goals",
        "sessions",
        "transcripts",
        "feature_sets",
        "audio_files",
        "ai_reviews",
        "reports",
        "processing_jobs",
        "privacy_operations",
        "audit_logs",
    }
    assert expected.issubset(set(Base.metadata.tables))


def test_iqr_position_classifier_uses_inclusive_band_boundaries():
    from app.services.ml_providers.reference_evidence import iqr_position

    assert iqr_position(0.9, 1, 3) == "below_iqr"
    assert iqr_position(1, 1, 3) == "within_iqr"
    assert iqr_position(1.5, 1, 3) == "within_iqr"
    assert iqr_position(3, 1, 3) == "within_iqr"
    assert iqr_position(3.1, 1, 3) == "above_iqr"


def test_band_number_formats_reference_statistics_without_trailing_zeros():
    from app.services.ml_providers.reference_evidence import band_number

    assert band_number(2.0) == "2"
    assert band_number(2.5) == "2.5"
    assert band_number(1.234) == "1.23"
    assert band_number(2.996) == "3"


def test_json_repository_direct_restart_persistence(tmp_path):
    from app.repositories.mock_repository import JsonFileRepository
    from app.schemas.clinical import ChildCase, TherapySession, Transcript, Report, ReviewStatus
    path = tmp_path / "persistence-direct.json"
    
    repo = JsonFileRepository(path)
    # Create entities
    case = ChildCase(case_id="case_t1", child_code="C-T1", age_months=48, language="English", consent_status="granted")
    repo.cases[case.case_id] = case
    
    session = TherapySession(session_id="session_t1", case_id=case.case_id, session_date="2026-06-19", session_type="therapy_session")
    repo.sessions[session.session_id] = session
    
    transcript = Transcript(transcript_id="trans_t1", session_id=session.session_id, case_id=case.case_id, source="paste-transcript", raw_text="@Begin\n*CHI:\thello .\n@End", therapist_attested=True, qa_status="PASS")
    repo.transcripts[transcript.transcript_id] = transcript
    
    report = Report(report_id="rep_t1", session_id=session.session_id, case_id=case.case_id, report_type="Session Review Report", title="Report Title", markdown="# Report", html="<p>Report</p>", status=ReviewStatus.signed_off)
    repo.reports[report.report_id] = report
    
    repo.add_audit("test.setup", "case_t1", "Created test entities.")
    
    # Reinitialize
    reopened = JsonFileRepository(path)
    assert "case_t1" in reopened.cases
    assert reopened.cases["case_t1"].child_code == "C-T1"
    assert "session_t1" in reopened.sessions
    assert reopened.sessions["session_t1"].case_id == "case_t1"
    assert "trans_t1" in reopened.transcripts
    assert reopened.transcripts["trans_t1"].raw_text == "@Begin\n*CHI:\thello .\n@End"
    assert reopened.transcripts["trans_t1"].therapist_attested is True
    assert "rep_t1" in reopened.reports
    assert reopened.reports["rep_t1"].title == "Report Title"
    assert reopened.reports["rep_t1"].status == ReviewStatus.signed_off


