from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.auth import supabase_auth
from app.auth.supabase_auth import authenticate_supabase_bearer, reset_jwks_cache_for_tests
from app.core.config import Settings, get_settings
from app.core.rate_limit import InMemoryRateLimiter, _client_key, clear_rate_limit_state
from app.main import app

ORIGIN = {"Origin": "http://localhost:3000"}


@pytest.fixture()
def limited(monkeypatch):
    monkeypatch.setenv("LINGUALENS_RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("LINGUALENS_RATE_LIMIT_REQUESTS", "2")
    get_settings.cache_clear()
    clear_rate_limit_state()
    yield TestClient(app)
    monkeypatch.undo()
    get_settings.cache_clear()
    clear_rate_limit_state()


def test_rate_limited_response_keeps_cors_headers_and_request_id(limited):
    for _ in range(2):
        assert limited.get("/api/v1/settings", headers=ORIGIN).status_code == 200

    blocked = limited.get("/api/v1/settings", headers=ORIGIN)

    assert blocked.status_code == 429
    assert blocked.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert blocked.headers["x-request-id"]


def test_rate_limit_cannot_be_bypassed_with_forwarded_for_header(limited):
    for _ in range(2):
        assert limited.get("/api/v1/settings").status_code == 200

    spoofed = limited.get("/api/v1/settings", headers={"X-Forwarded-For": "198.51.100.9"})

    assert spoofed.status_code == 429


def test_preflight_requests_are_not_rate_limited(limited):
    preflight = {**ORIGIN, "Access-Control-Request-Method": "GET"}
    for _ in range(5):
        assert limited.options("/api/v1/settings", headers=preflight).status_code == 200

    assert limited.get("/api/v1/settings", headers=ORIGIN).status_code == 200


def _request(forwarded_for: str | None) -> Request:
    headers = [(b"x-forwarded-for", forwarded_for.encode())] if forwarded_for else []
    return Request({"type": "http", "headers": headers, "client": ("10.0.0.5", 1234)})


def test_client_key_reads_forwarded_for_only_behind_declared_proxies():
    assert _client_key(_request("198.51.100.9"), 0) == "10.0.0.5"
    assert _client_key(_request("spoofed, 203.0.113.7"), 1) == "203.0.113.7"
    assert _client_key(_request("spoofed, 203.0.113.7, 10.1.1.1"), 2) == "203.0.113.7"
    assert _client_key(_request(None), 1) == "10.0.0.5"


def test_rate_limiter_bounds_tracked_clients():
    limiter = InMemoryRateLimiter(max_clients=50)

    for index in range(500):
        limiter.check(f"client-{index}", limit=5, window_seconds=60, now=float(index))

    assert len(limiter._buckets) <= 50
    assert limiter.check("client-499", limit=1, window_seconds=60, now=499.5) == (False, 60)


def test_unsafe_request_id_is_replaced_before_logging_and_echo():
    client = TestClient(app)

    kept = client.get("/health", headers={"x-request-id": "req-test-001"})
    replaced = client.get("/health", headers={"x-request-id": "child name with spaces"})

    assert kept.headers["x-request-id"] == "req-test-001"
    assert replaced.headers["x-request-id"] != "child name with spaces"
    assert " " not in replaced.headers["x-request-id"]


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _hs256(claims: dict, secret: str) -> str:
    header = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = _b64(json.dumps(claims).encode())
    signature = hmac.new(secret.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
    return f"{header}.{payload}.{_b64(signature)}"


@pytest.mark.parametrize(
    "token",
    [
        "eyJhbGciOiJIUzI1NiJ9.é.x",
        _hs256({"exp": "not-a-number"}, "unit-secret"),
        _hs256({"exp": int(time.time()) + 60, "nbf": {"bad": 1}}, "unit-secret"),
    ],
)
def test_malformed_hs256_tokens_are_unauthorized_not_server_errors(token):
    settings = Settings(auth_mode="supabase", supabase_jwt_secret="unit-secret")

    with pytest.raises(HTTPException) as raised:
        authenticate_supabase_bearer(f"Bearer {token}", settings)

    assert raised.value.status_code == 401


def test_unknown_key_id_does_not_refetch_jwks_on_every_request(monkeypatch):
    reset_jwks_cache_for_tests()
    fetches: list[str] = []

    def fake_fetch(url: str) -> str:
        fetches.append(url)
        return json.dumps({"keys": []})

    monkeypatch.setattr(supabase_auth, "_fetch_jwks_json_from_url", fake_fetch)
    settings = Settings(
        auth_mode="supabase",
        supabase_jwt_verification_mode="jwks_url",
        supabase_jwt_jwks_url="https://project-ref.supabase.co/auth/v1/.well-known/jwks.json",
    )
    header = _b64(json.dumps({"alg": "RS256", "kid": "unknown-kid"}).encode())
    token = f"{header}.{_b64(b'{}')}.{_b64(b'sig')}"
    try:
        for _ in range(10):
            with pytest.raises(HTTPException) as raised:
                authenticate_supabase_bearer(f"Bearer {token}", settings)
            assert raised.value.status_code == 401
    finally:
        reset_jwks_cache_for_tests()

    # One cached load plus one forced refresh, not one fetch per request.
    assert len(fetches) == 2


@pytest.mark.parametrize(
    "database_url",
    [
        "postgresql+psycopg://user:pw@127.0.0.1/therapist_app_v2",
        "postgresql+psycopg://user:pw@localhost/therapist_app_v2",
        "postgresql+psycopg://user:pw@[::1]/therapist_app_v2",
    ],
)
def test_loopback_hosts_are_recognised_in_any_spelling(database_url):
    from app.core.config import _points_at_loopback

    assert _points_at_loopback(database_url) is True
    assert _points_at_loopback("postgresql+psycopg://user:pw@db.example/therapist_app_v2") is False
