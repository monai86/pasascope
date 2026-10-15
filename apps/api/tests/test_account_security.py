"""Opt-in two-step verification and deleting one's own account."""
from __future__ import annotations

import time
from pathlib import Path

import httpx
import jwt
import pytest
from fastapi.testclient import TestClient

from app.api.v1.dependencies import get_repository
from app.auth import supabase_admin
from app.core.config import Settings, get_settings
from app.main import app
from app.repositories.mock_repository import MockRepository
from app.repositories.sqlalchemy_repository import SqlAlchemyRepository
from app.schemas.clinical import AudioFileMetadata
from app.services import audio_backup_service, storage_service
from app.services.storage_service import StorageDeletionResult

SECRET = "test-secret-with-at-least-thirty-two-bytes"
ISSUER = "https://abcdefghijklmnop.supabase.co/auth/v1"
PROJECT_URL = "https://abcdefghijklmnop.supabase.co"


def _settings(**overrides) -> Settings:
    return get_settings().model_copy(
        update={
            "auth_mode": "supabase",
            "supabase_jwt_verification_mode": "hs256_shared_secret",
            "supabase_jwt_secret": SECRET,
            "supabase_jwt_issuer": ISSUER,
            "supabase_jwt_audience": "authenticated",
            "supabase_storage_url": PROJECT_URL,
            "supabase_storage_service_role_key": "service-role-key",
            **overrides,
        }
    )


def _auth(sub: str, aal: str = "aal1") -> dict[str, str]:
    token = jwt.encode(
        {"sub": sub, "aud": "authenticated", "iss": ISSUER, "exp": int(time.time()) + 600, "aal": aal},
        SECRET,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


class FakeSupabaseAuth:
    """Supabase Auth's admin API: which accounts have a verified factor, and which were deleted."""

    def __init__(self) -> None:
        self.enrolled: set[str] = set()
        self.deleted: list[str] = []
        self.fail_with: int | None = None
        self.lookups = 0

    def handle(self, request: httpx.Request) -> httpx.Response:
        assert request.headers["apikey"] == "service-role-key"
        assert request.headers["authorization"] == "Bearer service-role-key"
        user_id = request.url.path.rsplit("/", 1)[-1]
        if self.fail_with:
            return httpx.Response(self.fail_with)
        if request.method == "GET":
            self.lookups += 1
            factors = [{"id": "f1", "factor_type": "totp", "status": "verified"}] if user_id in self.enrolled else []
            return httpx.Response(200, json={"id": user_id, "factors": factors})
        if request.method == "DELETE":
            self.deleted.append(user_id)
            return httpx.Response(200, json={})
        return httpx.Response(405)


@pytest.fixture()
def supabase(monkeypatch):
    fake = FakeSupabaseAuth()
    monkeypatch.setattr(supabase_admin, "_client", lambda: httpx.Client(transport=httpx.MockTransport(fake.handle)))
    supabase_admin.reset_factor_cache_for_tests()
    yield fake
    supabase_admin.reset_factor_cache_for_tests()


@pytest.fixture()
def storage_root(tmp_path, monkeypatch) -> Path:
    root = tmp_path / "storage"
    root.mkdir()
    local = Settings(storage_mode="local_private", local_storage_root=str(root), audio_backup_mode="none")
    monkeypatch.setattr(storage_service, "get_settings", lambda: local)
    monkeypatch.setattr(audio_backup_service, "get_settings", lambda: local)
    return root


def _client(repo, settings: Settings | None = None) -> TestClient:
    app.dependency_overrides[get_repository] = lambda: repo
    app.dependency_overrides[get_settings] = lambda: settings or _settings()
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


# -- two-step verification ---------------------------------------------------


def test_an_account_without_two_step_verification_works_with_an_aal1_session(supabase):
    client = _client(MockRepository(seed_demo=False))

    assert client.get("/api/v1/cases", headers=_auth("user-a")).status_code == 200


def test_an_account_with_two_step_verification_needs_an_aal2_session(supabase):
    supabase.enrolled.add("user-a")
    client = _client(MockRepository(seed_demo=False))

    refused = client.get("/api/v1/cases", headers=_auth("user-a", aal="aal1"))
    assert refused.status_code == 403
    assert refused.json()["detail"] == "Two-step verification is required for this account."
    assert client.get("/api/v1/cases", headers=_auth("user-a", aal="aal2")).status_code == 200


def test_an_aal2_session_is_not_checked_against_supabase(supabase):
    client = _client(MockRepository(seed_demo=False))

    client.get("/api/v1/cases", headers=_auth("user-a", aal="aal2"))

    assert supabase.lookups == 0


def test_the_answer_about_an_account_is_reused_for_a_while(supabase):
    client = _client(MockRepository(seed_demo=False))

    for _ in range(3):
        client.get("/api/v1/cases", headers=_auth("user-a"))

    assert supabase.lookups == 1


def test_an_aal1_session_is_refused_while_supabase_cannot_say(supabase):
    supabase.fail_with = 500
    client = _client(MockRepository(seed_demo=False))

    response = client.get("/api/v1/cases", headers=_auth("user-a"))

    assert response.status_code == 503


def test_an_api_without_the_service_role_key_does_not_check(supabase):
    client = _client(MockRepository(seed_demo=False), _settings(supabase_storage_service_role_key=""))

    assert client.get("/api/v1/cases", headers=_auth("user-a")).status_code == 200
    assert supabase.lookups == 0


def test_accounts_are_managed_only_with_a_project_url_and_service_role_key():
    assert _settings().supabase_admin_target == (PROJECT_URL, "service-role-key")
    assert _settings(supabase_storage_url="http://localhost:54321").supabase_admin_target is None
    assert _settings(supabase_storage_service_role_key="").supabase_admin_target is None


def test_settings_say_whether_two_step_verification_and_deletion_are_offered(monkeypatch):
    from app.api.v1.routes import settings as settings_route

    monkeypatch.setattr(settings_route, "get_settings", lambda: _settings())
    offered = TestClient(app).get("/api/v1/settings").json()["access_model"]
    assert offered["two_step_verification"] == "optional"
    assert offered["account_deletion"] == "available"

    monkeypatch.setattr(settings_route, "get_settings", lambda: _settings(supabase_storage_service_role_key=""))
    withheld = TestClient(app).get("/api/v1/settings").json()["access_model"]
    assert withheld["two_step_verification"] == "unavailable"
    assert withheld["account_deletion"] == "unavailable"


# -- deleting an account -------------------------------------------------------


def _repository(kind: str, tmp_path: Path):
    if kind == "memory":
        return MockRepository(seed_demo=False)
    return SqlAlchemyRepository(f"sqlite:///{tmp_path / 'accounts.db'}", seed_demo=False)


def _workspace(client: TestClient, repo, user: str, storage_root: Path) -> dict:
    headers = _auth(user)
    case = client.post("/api/v1/cases", headers=headers, json={"child_code": f"C-{user}", "age_months": 54}).json()
    session = client.post(
        f"/api/v1/cases/{case['case_id']}/sessions",
        headers=headers,
        json={"session_date": "2026-10-15", "session_type": "therapy_session"},
    ).json()
    transcript = client.post(
        f"/api/v1/sessions/{session['session_id']}/transcripts/manual",
        headers=headers,
        json={"text": "THER: what do you see\nCHI: i see a big blue car", "language": "English"},
    )
    assert transcript.status_code in {200, 201}, transcript.text
    object_key = f"audio/obj_{user}.webm"
    (storage_root / "audio").mkdir(exist_ok=True)
    (storage_root / object_key).write_bytes(b"recording")
    repo.audio_files[f"audio_{user}"] = AudioFileMetadata(
        audio_file_id=f"audio_{user}",
        organization_id=f"personal_{user}",
        session_id=session["session_id"],
        case_id=case["case_id"],
        original_filename="recording.webm",
        content_type="audio/webm",
        size_bytes=9,
        storage_mode="local_private",
        object_key=object_key,
        upload_status="uploaded",
    )
    if isinstance(repo, SqlAlchemyRepository):
        repo.save()
    return {"case": case, "session": session, "object_key": object_key}


@pytest.mark.parametrize("kind", ["memory", "sql"])
def test_deleting_an_account_removes_its_workspace_recordings_and_sign_in(kind, tmp_path, supabase, storage_root):
    repo = _repository(kind, tmp_path)
    client = _client(repo)
    mine = _workspace(client, repo, "user-a", storage_root)
    theirs = _workspace(client, repo, "user-b", storage_root)

    response = client.delete("/api/v1/account", headers=_auth("user-a"))

    assert response.status_code == 200, response.text
    assert response.json()["removed"]["cases"] == 1
    assert supabase.deleted == ["user-a"]
    assert not (storage_root / mine["object_key"]).exists()
    assert (storage_root / theirs["object_key"]).exists()
    for collection in ("cases", "sessions", "transcripts", "audio_files"):
        assert repo.find(collection, organization_id="personal_user-a") == []
        assert repo.find(collection, organization_id="personal_user-b") != []
    events = repo.audit_events(organization_id="personal_user-a")
    assert [event["action"] for event in events] == ["account.delete"]
    assert client.get(f"/api/v1/cases/{theirs['case']['case_id']}", headers=_auth("user-b")).status_code == 200


def test_a_fresh_sql_repository_finds_nothing_of_a_deleted_account(tmp_path, supabase, storage_root):
    repo = _repository("sql", tmp_path)
    client = _client(repo)
    mine = _workspace(client, repo, "user-a", storage_root)
    client.delete("/api/v1/account", headers=_auth("user-a"))

    reopened = SqlAlchemyRepository(f"sqlite:///{tmp_path / 'accounts.db'}", seed_demo=False)

    assert reopened.get_case(mine["case"]["case_id"]) is None
    assert reopened.find("sessions", case_id=mine["case"]["case_id"]) == []


def test_nothing_is_deleted_when_a_recording_cannot_be_removed(tmp_path, supabase, storage_root, monkeypatch):
    repo = _repository("memory", tmp_path)
    client = _client(repo)
    mine = _workspace(client, repo, "user-a", storage_root)

    class BackupDown(storage_service.LocalPrivateStorageAdapter):
        def delete_object(self, object_key):
            return StorageDeletionResult(storage_mode=self.storage_mode, deleted=False, status="backup_delete_failed")

    monkeypatch.setattr("app.services.account_service.get_storage_adapter", lambda: BackupDown(storage_root))

    response = client.delete("/api/v1/account", headers=_auth("user-a"))

    assert response.status_code == 503
    assert repo.find("cases", organization_id="personal_user-a") != []
    assert supabase.deleted == []
    assert (storage_root / mine["object_key"]).exists()


def test_a_failed_sign_in_removal_says_the_records_are_gone_and_can_be_retried(tmp_path, supabase, storage_root):
    repo = _repository("memory", tmp_path)
    client = _client(repo)
    _workspace(client, repo, "user-a", storage_root)
    original = supabase.handle

    def refuse_delete(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500) if request.method == "DELETE" else original(request)

    supabase.handle = refuse_delete  # type: ignore[method-assign]
    first = client.delete("/api/v1/account", headers=_auth("user-a"))
    assert first.status_code == 502
    assert "records were deleted" in first.json()["detail"]
    assert repo.find("cases", organization_id="personal_user-a") == []

    supabase.handle = original  # type: ignore[method-assign]
    second = client.delete("/api/v1/account", headers=_auth("user-a"))
    assert second.status_code == 200
    assert supabase.deleted == ["user-a"]


def test_an_account_with_two_step_verification_must_verify_before_deleting(tmp_path, supabase, storage_root):
    supabase.enrolled.add("user-a")
    repo = _repository("memory", tmp_path)
    client = _client(repo)

    assert client.delete("/api/v1/account", headers=_auth("user-a", aal="aal1")).status_code == 403
    assert supabase.deleted == []


def test_accounts_cannot_be_deleted_without_real_sign_in(tmp_path):
    repo = _repository("memory", tmp_path)
    client = _client(repo, get_settings().model_copy(update={"auth_mode": "mock"}))

    response = client.delete("/api/v1/account", headers={"x-mock-user-id": "therapist-demo"})

    assert response.status_code == 409


def test_accounts_cannot_be_deleted_where_the_api_cannot_manage_them(tmp_path, supabase):
    repo = _repository("memory", tmp_path)
    client = _client(repo, _settings(supabase_storage_service_role_key=""))

    assert client.delete("/api/v1/account", headers=_auth("user-a")).status_code == 409
