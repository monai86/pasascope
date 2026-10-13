from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from fastapi import HTTPException
from fastapi.testclient import TestClient
from urllib.error import URLError

from app.api.v1.dependencies import get_repository
from app.core.config import Settings, get_settings
from app.auth.supabase_auth import reset_jwks_cache_for_tests
from app.core.security import get_current_user
from app.main import app
from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import OrganizationMembershipCreate


SECRET = "local-test-supabase-jwt-secret-with-enough-entropy"
ISSUER = "https://project-ref.supabase.co/auth/v1"
AUDIENCE = "authenticated"


def _production_settings() -> Settings:
    return Settings(
        mock_mode=False,
        auth_mode="supabase",
        supabase_jwt_secret=SECRET,
        supabase_jwt_issuer=ISSUER,
        supabase_jwt_audience=AUDIENCE,
        cors_allowed_origins="https://clinic.example",
        repository_mode="sql",
        database_url="postgresql+psycopg://prod_user:prod_password@db.example/therapist_app_v2",
        sql_create_schema=False,
        storage_mode="private",
        job_queue_mode="redis",
        redis_url="rediss://redis.example:6379/0",
        observability_enabled=True,
        observability_provider="sentry",
        critical_alert_route="pagerduty-critical",
        secret_store_provider="aws_secrets_manager",
        credential_rotation_runbook="docs/SECRET_ROTATION_RUNBOOK.md",
    )


def _production_jwks_settings(jwks_json: str) -> Settings:
    return Settings(
        mock_mode=False,
        auth_mode="supabase",
        supabase_jwt_verification_mode="jwks_json",
        supabase_jwt_jwks_json=jwks_json,
        supabase_jwt_issuer=ISSUER,
        supabase_jwt_audience=AUDIENCE,
        cors_allowed_origins="https://clinic.example",
        repository_mode="sql",
        database_url="postgresql+psycopg://prod_user:prod_password@db.example/therapist_app_v2",
        sql_create_schema=False,
        storage_mode="private",
        job_queue_mode="redis",
        redis_url="rediss://redis.example:6379/0",
        observability_enabled=True,
        observability_provider="sentry",
        critical_alert_route="pagerduty-critical",
        secret_store_provider="aws_secrets_manager",
        credential_rotation_runbook="docs/SECRET_ROTATION_RUNBOOK.md",
    )


def _production_jwks_url_settings(jwks_url: str) -> Settings:
    return Settings(
        mock_mode=False,
        auth_mode="supabase",
        supabase_jwt_verification_mode="jwks_url",
        supabase_jwt_jwks_url=jwks_url,
        supabase_jwt_jwks_cache_ttl_seconds=300,
        supabase_jwt_issuer=ISSUER,
        supabase_jwt_audience=AUDIENCE,
        cors_allowed_origins="https://clinic.example",
        repository_mode="sql",
        database_url="postgresql+psycopg://prod_user:prod_password@db.example/therapist_app_v2",
        sql_create_schema=False,
        storage_mode="private",
        job_queue_mode="redis",
        redis_url="rediss://redis.example:6379/0",
        observability_enabled=True,
        observability_provider="sentry",
        critical_alert_route="pagerduty-critical",
        secret_store_provider="aws_secrets_manager",
        credential_rotation_runbook="docs/SECRET_ROTATION_RUNBOOK.md",
    )


def _jwt(claims: dict, secret: str = SECRET) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    signing_input = ".".join(
        [
            _b64(json.dumps(header, separators=(",", ":")).encode("utf-8")),
            _b64(json.dumps(claims, separators=(",", ":")).encode("utf-8")),
        ]
    )
    signature = hmac.new(secret.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
    return f"{signing_input}.{_b64(signature)}"


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _rsa_bundle(kid: str = "test-rs256-key") -> tuple[object, str]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    numbers = private_key.public_key().public_numbers()
    jwks = {
        "keys": [
            {
                "kty": "RSA",
                "kid": kid,
                "use": "sig",
                "alg": "RS256",
                "n": _b64(numbers.n.to_bytes((numbers.n.bit_length() + 7) // 8, "big")),
                "e": _b64(numbers.e.to_bytes((numbers.e.bit_length() + 7) // 8, "big")),
            }
        ]
    }
    return private_key, json.dumps(jwks)


def _ec_bundle(kid: str = "test-es256-key", *, jwk_alg: str = "ES256") -> tuple[object, str]:
    private_key = ec.generate_private_key(ec.SECP256R1())
    numbers = private_key.public_key().public_numbers()
    jwks = {
        "keys": [
            {
                "kty": "EC",
                "kid": kid,
                "use": "sig",
                "alg": jwk_alg,
                "crv": "P-256",
                "x": _b64(numbers.x.to_bytes(32, "big")),
                "y": _b64(numbers.y.to_bytes(32, "big")),
            }
        ]
    }
    return private_key, json.dumps(jwks)


def _claims(**metadata_overrides) -> dict:
    now = int(time.time())
    app_metadata = {
        "organization_id": "org_a",
        "role": "therapist",
        "membership_active": True,
        "invitation_status": "accepted",
        **metadata_overrides,
    }
    return {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "aal": "aal2",
        "sub": "clinician_a",
        "email": "clinician@example.test",
        "iat": now - 30,
        "exp": now + 300,
        "app_metadata": app_metadata,
    }


def _jwt_rs256(claims: dict, private_key: object, kid: str = "test-rs256-key") -> str:
    return jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": kid})


def _jwt_es256(claims: dict, private_key: object, kid: str = "test-es256-key") -> str:
    return jwt.encode(claims, private_key, algorithm="ES256", headers={"kid": kid})


def _claims_for_user(user_id: str, **metadata_overrides) -> dict:
    claims = _claims(**metadata_overrides)
    claims["sub"] = user_id
    return claims


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


def test_runtime_security_requires_supabase_jwt_configuration():
    with pytest.raises(ValueError, match="Supabase JWT"):
        Settings(
            mock_mode=False,
            auth_mode="supabase",
            cors_allowed_origins="https://clinic.example",
            repository_mode="sql",
            database_url="postgresql+psycopg://prod_user:prod_password@db.example/therapist_app_v2",
            sql_create_schema=False,
            storage_mode="private",
            job_queue_mode="redis",
            redis_url="rediss://redis.example:6379/0",
            observability_enabled=True,
            observability_provider="sentry",
            critical_alert_route="pagerduty-critical",
            secret_store_provider="aws_secrets_manager",
            credential_rotation_runbook="docs/SECRET_ROTATION_RUNBOOK.md",
        ).validate_runtime_security()


def test_runtime_security_requires_jwks_json_for_asymmetric_verification():
    with pytest.raises(ValueError, match="JWKS JSON"):
        Settings(
            mock_mode=False,
            auth_mode="supabase",
            supabase_jwt_verification_mode="jwks_json",
            cors_allowed_origins="https://clinic.example",
            repository_mode="sql",
            database_url="postgresql+psycopg://prod_user:prod_password@db.example/therapist_app_v2",
            sql_create_schema=False,
            storage_mode="private",
            job_queue_mode="redis",
            redis_url="rediss://redis.example:6379/0",
            observability_enabled=True,
            observability_provider="sentry",
            critical_alert_route="pagerduty-critical",
            secret_store_provider="aws_secrets_manager",
            credential_rotation_runbook="docs/SECRET_ROTATION_RUNBOOK.md",
            supabase_jwt_issuer=ISSUER,
        ).validate_runtime_security()


def test_runtime_security_requires_jwks_url_for_remote_asymmetric_verification():
    with pytest.raises(ValueError, match="JWKS URL"):
        Settings(
            mock_mode=False,
            auth_mode="supabase",
            supabase_jwt_verification_mode="jwks_url",
            cors_allowed_origins="https://clinic.example",
            repository_mode="sql",
            database_url="postgresql+psycopg://prod_user:prod_password@db.example/therapist_app_v2",
            sql_create_schema=False,
            storage_mode="private",
            job_queue_mode="redis",
            redis_url="rediss://redis.example:6379/0",
            observability_enabled=True,
            observability_provider="sentry",
            critical_alert_route="pagerduty-critical",
            secret_store_provider="aws_secrets_manager",
            credential_rotation_runbook="docs/SECRET_ROTATION_RUNBOOK.md",
            supabase_jwt_issuer=ISSUER,
        ).validate_runtime_security()


def test_supabase_auth_accepts_valid_token_and_ignores_mock_headers():
    repo = MockRepository()
    repo.cases["case_demo_001"].organization_id = "personal_clinician_a"
    repo.cases["case_demo_001"].care_team_user_ids = ["clinician_a"]
    app.dependency_overrides[get_repository] = lambda: repo
    app.dependency_overrides[get_settings] = _production_settings
    client = TestClient(app)
    try:
        response = client.get(
            "/api/v1/cases/case_demo_001",
            headers={
                "authorization": f"Bearer {_jwt(_claims())}",
                "x-mock-user-id": "attacker",
                "x-mock-role": "org_admin",
                "x-organization-id": "org_a",
            },
        )
    finally:
        _clear_overrides()

    assert response.status_code == 200
    assert response.json()["organization_id"] == "personal_clinician_a"


def test_supabase_auth_accepts_valid_rs256_token_from_local_jwks():
    repo = MockRepository()
    repo.cases["case_demo_001"].organization_id = "personal_clinician_a"
    repo.cases["case_demo_001"].care_team_user_ids = ["clinician_a"]
    private_key, jwks_json = _rsa_bundle()
    app.dependency_overrides[get_repository] = lambda: repo
    app.dependency_overrides[get_settings] = lambda: _production_jwks_settings(jwks_json)
    client = TestClient(app)
    try:
        response = client.get(
            "/api/v1/cases/case_demo_001",
            headers={
                "authorization": f"Bearer {_jwt_rs256(_claims(organizations=[{'organization_id': 'org_a', 'role': 'therapist'}]), private_key)}",
            },
        )
    finally:
        _clear_overrides()

    assert response.status_code == 200
    assert response.json()["organization_id"] == "personal_clinician_a"


def test_supabase_auth_accepts_valid_es256_token_from_local_jwks():
    repo = MockRepository()
    repo.cases["case_demo_001"].organization_id = "personal_clinician_a"
    repo.cases["case_demo_001"].care_team_user_ids = ["clinician_a"]
    private_key, jwks_json = _ec_bundle()
    app.dependency_overrides[get_repository] = lambda: repo
    app.dependency_overrides[get_settings] = lambda: _production_jwks_settings(jwks_json)
    client = TestClient(app)
    try:
        response = client.get(
            "/api/v1/cases/case_demo_001",
            headers={
                "authorization": f"Bearer {_jwt_es256(_claims(organizations=[{'organization_id': 'org_a', 'role': 'therapist'}]), private_key)}",
            },
        )
    finally:
        _clear_overrides()

    assert response.status_code == 200
    assert response.json()["organization_id"] == "personal_clinician_a"


def test_supabase_auth_accepts_valid_rs256_token_from_fetched_jwks(monkeypatch):
    repo = MockRepository()
    repo.cases["case_demo_001"].organization_id = "personal_clinician_a"
    repo.cases["case_demo_001"].care_team_user_ids = ["clinician_a"]
    private_key, jwks_json = _rsa_bundle()
    fetch_calls: list[str] = []

    def fake_fetch(url: str) -> str:
        fetch_calls.append(url)
        return jwks_json

    from app.auth import supabase_auth as supabase_auth_module

    reset_jwks_cache_for_tests()
    monkeypatch.setattr(supabase_auth_module, "_fetch_jwks_json_from_url", fake_fetch)
    app.dependency_overrides[get_repository] = lambda: repo
    app.dependency_overrides[get_settings] = lambda: _production_jwks_url_settings("https://supabase.example/jwks")
    client = TestClient(app)
    try:
        response = client.get(
            "/api/v1/cases/case_demo_001",
            headers={
                "authorization": f"Bearer {_jwt_rs256(_claims(organizations=[{'organization_id': 'org_a', 'role': 'therapist'}]), private_key)}",
            },
        )
    finally:
        _clear_overrides()
        reset_jwks_cache_for_tests()

    assert response.status_code == 200
    assert fetch_calls == ["https://supabase.example/jwks"]


def test_supabase_auth_reuses_cached_jwks_url_payload(monkeypatch):
    private_key, jwks_json = _rsa_bundle()
    fetch_calls: list[str] = []

    def fake_fetch(url: str) -> str:
        fetch_calls.append(url)
        return jwks_json

    from app.auth import supabase_auth as supabase_auth_module

    reset_jwks_cache_for_tests()
    monkeypatch.setattr(supabase_auth_module, "_fetch_jwks_json_from_url", fake_fetch)
    settings = _production_jwks_url_settings("https://supabase.example/jwks")
    token = _jwt_rs256(_claims(), private_key)

    get_current_user(authorization=f"Bearer {token}", settings=settings)
    get_current_user(authorization=f"Bearer {token}", settings=settings)

    reset_jwks_cache_for_tests()
    assert fetch_calls == ["https://supabase.example/jwks"]


def test_supabase_auth_refreshes_jwks_url_when_cached_keys_miss_new_kid(monkeypatch):
    old_private_key, old_jwks_json = _rsa_bundle(kid="old-key")
    new_private_key, new_jwks_json = _rsa_bundle(kid="new-key")
    fetch_calls: list[str] = []
    responses = [old_jwks_json, new_jwks_json]

    def fake_fetch(url: str) -> str:
        fetch_calls.append(url)
        return responses.pop(0)

    from app.auth import supabase_auth as supabase_auth_module

    reset_jwks_cache_for_tests()
    monkeypatch.setattr(supabase_auth_module, "_fetch_jwks_json_from_url", fake_fetch)
    settings = _production_jwks_url_settings("https://supabase.example/jwks")

    get_current_user(
        authorization=f"Bearer {_jwt_rs256(_claims(), old_private_key, kid='old-key')}",
        settings=settings,
    )
    principal = get_current_user(
        authorization=f"Bearer {_jwt_rs256(_claims(), new_private_key, kid='new-key')}",
        settings=settings,
    )

    reset_jwks_cache_for_tests()
    assert principal.organization_id == "personal_clinician_a"
    assert fetch_calls == [
        "https://supabase.example/jwks",
        "https://supabase.example/jwks",
    ]


def test_supabase_auth_fails_closed_when_jwks_refresh_still_lacks_signing_key(monkeypatch):
    private_key, old_jwks_json = _rsa_bundle(kid="old-key")
    fetch_calls: list[str] = []

    def fake_fetch(url: str) -> str:
        fetch_calls.append(url)
        return old_jwks_json

    from app.auth import supabase_auth as supabase_auth_module

    reset_jwks_cache_for_tests()
    monkeypatch.setattr(supabase_auth_module, "_fetch_jwks_json_from_url", fake_fetch)
    settings = _production_jwks_url_settings("https://supabase.example/jwks")

    with pytest.raises(HTTPException) as exc:
        get_current_user(
            authorization=f"Bearer {_jwt_rs256(_claims(), private_key, kid='missing-key')}",
            settings=settings,
        )

    reset_jwks_cache_for_tests()
    assert exc.value.status_code == 401
    assert exc.value.detail == "Bearer token signing key was not found."
    assert fetch_calls == [
        "https://supabase.example/jwks",
        "https://supabase.example/jwks",
    ]


def test_supabase_auth_fails_closed_when_remote_jwks_fetch_fails(monkeypatch):
    private_key, _jwks_json = _rsa_bundle()

    def fake_urlopen(*_args, **_kwargs):
        raise URLError("temporary failure")

    from app.auth import supabase_auth as supabase_auth_module

    reset_jwks_cache_for_tests()
    monkeypatch.setattr(supabase_auth_module.urllib_request, "urlopen", fake_urlopen)
    settings = _production_jwks_url_settings("https://supabase.example/jwks")

    with pytest.raises(HTTPException) as exc:
        get_current_user(
            authorization=f"Bearer {_jwt_rs256(_claims(), private_key)}",
            settings=settings,
        )

    reset_jwks_cache_for_tests()
    assert exc.value.status_code == 401
    assert exc.value.detail == "Unable to fetch Supabase JWKS."


def test_supabase_auth_mode_fails_closed_with_only_mock_headers():
    repo = MockRepository()
    app.dependency_overrides[get_repository] = lambda: repo
    app.dependency_overrides[get_settings] = _production_settings
    client = TestClient(app)
    try:
        response = client.get(
            "/api/v1/cases/case_demo_001",
            headers={
                "x-mock-user-id": "attacker",
                "x-mock-role": "org_admin",
                "x-organization-id": "pilot_org_001",
            },
        )
    finally:
        _clear_overrides()

    assert response.status_code == 401


def test_supabase_auth_rejects_missing_invalid_and_expired_tokens():
    settings = _production_settings()
    now = int(time.time())

    with pytest.raises(HTTPException) as missing:
        get_current_user(authorization=None, settings=settings)
    with pytest.raises(HTTPException) as invalid:
        get_current_user(authorization="Bearer not-a-token", settings=settings)
    expired_claims = _claims()
    expired_claims["exp"] = now - 1
    with pytest.raises(HTTPException) as expired:
        get_current_user(authorization=f"Bearer {_jwt(expired_claims)}", settings=settings)

    assert missing.value.status_code == 401
    assert invalid.value.status_code == 401
    assert expired.value.status_code == 401


def test_supabase_auth_rejects_rs256_token_when_kid_is_missing_from_jwks():
    private_key, jwks_json = _rsa_bundle(kid="known-key")
    with pytest.raises(HTTPException) as exc:
        get_current_user(
            authorization=f"Bearer {_jwt_rs256(_claims(), private_key, kid='unknown-key')}",
            settings=_production_jwks_settings(jwks_json),
        )

    assert exc.value.status_code == 401
    assert exc.value.detail == "Bearer token signing key was not found."


def test_supabase_auth_rejects_jwks_algorithm_mismatch():
    private_key, jwks_json = _ec_bundle(jwk_alg="RS256")
    with pytest.raises(HTTPException) as exc:
        get_current_user(
            authorization=f"Bearer {_jwt_es256(_claims(), private_key)}",
            settings=_production_jwks_settings(jwks_json),
        )

    assert exc.value.status_code == 401
    assert exc.value.detail == "Bearer token algorithm does not match signing key."
