"""Account facts the token does not carry, read from Supabase Auth's admin API.

A Supabase access token says how strongly the session was signed in (`aal`)
but not whether the account has an authenticator app. Two-step verification is
optional, so an `aal1` token is only enough for an account without a verified
factor; this module asks Supabase which case it is. It also deletes an account.

Both calls use the project's service role key, which never leaves the API.
"""
from __future__ import annotations

import threading
import time
from urllib.parse import quote

import httpx

from app.core.config import Settings

_TIMEOUT = httpx.Timeout(10.0, connect=5.0)
# How long an answer about one account's factors is reused. Turning two-step
# verification on raises the session to aal2 at once, so a stale "no factor"
# only matters for an aal1 session signed in before that; it lasts this long.
FACTOR_CACHE_SECONDS = 60

_factor_cache: dict[str, tuple[float, bool]] = {}
_factor_cache_lock = threading.Lock()


class SupabaseAdminUnavailable(RuntimeError):
    """Supabase Auth could not be asked, or did not answer as expected."""


def _client() -> httpx.Client:
    return httpx.Client(timeout=_TIMEOUT)


def _user_url(base_url: str, user_id: str) -> str:
    return f"{base_url}/auth/v1/admin/users/{quote(user_id, safe='')}"


def _headers(service_role_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {service_role_key}", "apikey": service_role_key}


def has_verified_factor(user_id: str, settings: Settings) -> bool | None:
    """Whether the account has a verified second factor; ``None`` when this API cannot ask."""
    target = settings.supabase_admin_target
    if target is None:
        return None
    now = time.monotonic()
    with _factor_cache_lock:
        cached = _factor_cache.get(user_id)
        if cached and cached[0] > now:
            return cached[1]
    base_url, key = target
    try:
        with _client() as client:
            response = client.get(_user_url(base_url, user_id), headers=_headers(key))
    except httpx.HTTPError as exc:
        raise SupabaseAdminUnavailable("Supabase Auth could not be reached.") from exc
    if response.status_code != 200:
        raise SupabaseAdminUnavailable(f"Supabase Auth answered {response.status_code}.")
    try:
        factors = response.json().get("factors") or []
    except ValueError as exc:
        raise SupabaseAdminUnavailable("Supabase Auth sent an unreadable answer.") from exc
    verified = any(isinstance(factor, dict) and factor.get("status") == "verified" for factor in factors)
    with _factor_cache_lock:
        _factor_cache[user_id] = (now + FACTOR_CACHE_SECONDS, verified)
    return verified


def forget_factor_answer(user_id: str) -> None:
    with _factor_cache_lock:
        _factor_cache.pop(user_id, None)


def delete_auth_user(user_id: str, settings: Settings) -> None:
    """Delete the sign-in account. An account that is already gone counts as deleted."""
    target = settings.supabase_admin_target
    if target is None:
        raise SupabaseAdminUnavailable("This API is not set up to manage accounts.")
    base_url, key = target
    try:
        with _client() as client:
            response = client.delete(_user_url(base_url, user_id), headers=_headers(key))
    except httpx.HTTPError as exc:
        raise SupabaseAdminUnavailable("Supabase Auth could not be reached.") from exc
    if response.status_code not in {200, 204, 404}:
        raise SupabaseAdminUnavailable(f"Supabase Auth answered {response.status_code}.")
    forget_factor_answer(user_id)


def reset_factor_cache_for_tests() -> None:
    with _factor_cache_lock:
        _factor_cache.clear()
