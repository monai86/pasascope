from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any
from urllib import request as urllib_request
from urllib.error import URLError

from fastapi import HTTPException, status
import jwt
from jwt import PyJWK

from app.core.config import Settings

ALLOWED_JWKS_ALGORITHMS = {"RS256", "ES256"}
_JWKS_CACHE: dict[str, tuple[float, str]] = {}
# An unknown key id may mean the keys rotated, or that someone is sending junk
# tokens. Refetch for it at most this often so junk cannot drive outbound calls.
JWKS_FORCED_REFRESH_MIN_INTERVAL_SECONDS = 30
_JWKS_LAST_FORCED_REFRESH: dict[str, float] = {}


@dataclass(frozen=True)
class SupabasePrincipal:
    user_id: str
    role: str
    display_name: str
    organization_id: str
    aal: str


PERSONAL_ORGANIZATION_PREFIX = "personal_"


def authenticate_supabase_bearer(authorization: str | None, settings: Settings) -> SupabasePrincipal:
    """Give any verified Supabase user a workspace of their own.

    The token's signature, issuer and audience are verified. Nothing else in
    the token is trusted for access: the workspace id is derived from the
    subject, so a user can only ever reach records created under their own id,
    and organization or role claims in a token are ignored.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise _unauthorized("Bearer token required.")
    token = authorization.split(" ", 1)[1].strip()
    claims = _decode_supabase_jwt(token, settings)
    user_id = _required_str(claims, "sub")
    user_metadata = claims.get("user_metadata")
    display_name = user_id
    candidates = []
    if isinstance(user_metadata, dict):
        candidates += [user_metadata.get("display_name"), user_metadata.get("full_name"), user_metadata.get("name")]
    candidates.append(claims.get("email"))
    for value in candidates:
        if isinstance(value, str) and value.strip():
            display_name = value.strip()
            break
    aal = claims.get("aal")
    return SupabasePrincipal(
        user_id=user_id,
        role="therapist",
        display_name=display_name,
        organization_id=f"{PERSONAL_ORGANIZATION_PREFIX}{user_id}",
        aal=aal if isinstance(aal, str) and aal else "aal1",
    )


def _decode_supabase_jwt(token: str, settings: Settings) -> dict[str, Any]:
    if settings.supabase_jwt_verification_mode == "jwks_url":
        return _decode_jwks_url_jwt(token, settings)
    if settings.supabase_jwt_verification_mode == "jwks_json":
        return _decode_jwks_jwt(token, settings)
    return _decode_hs256_jwt(token, settings)


def _decode_hs256_jwt(token: str, settings: Settings) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise _unauthorized("Invalid bearer token.")
    header = _json_part(parts[0])
    if header.get("alg") != "HS256":
        raise _unauthorized("Unsupported token algorithm.")
    try:
        signing_input = f"{parts[0]}.{parts[1]}".encode("ascii")
    except UnicodeEncodeError:
        raise _unauthorized("Invalid bearer token.") from None
    expected = hmac.new(settings.supabase_jwt_secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    if not hmac.compare_digest(_b64decode(parts[2]), expected):
        raise _unauthorized("Invalid bearer token.")

    claims = _json_part(parts[1])
    now = int(time.time())
    try:
        expires_at = int(claims.get("exp") or 0)
        not_before = int(claims["nbf"]) if "nbf" in claims else None
    except (TypeError, ValueError):
        raise _unauthorized("Invalid bearer token.") from None
    if expires_at <= now:
        raise _unauthorized("Bearer token expired.")
    if not_before is not None and not_before > now:
        raise _unauthorized("Bearer token not yet valid.")
    if settings.supabase_jwt_issuer and claims.get("iss") != settings.supabase_jwt_issuer:
        raise _unauthorized("Invalid token issuer.")
    if not _audience_matches(claims.get("aud"), settings.supabase_jwt_audience):
        raise _unauthorized("Invalid token audience.")
    return claims


def _decode_jwks_jwt(token: str, settings: Settings) -> dict[str, Any]:
    try:
        header = jwt.get_unverified_header(token)
    except jwt.InvalidTokenError:
        raise _unauthorized("Invalid bearer token.") from None
    algorithm = header.get("alg")
    if algorithm not in ALLOWED_JWKS_ALGORITHMS:
        raise _unauthorized("Unsupported token algorithm.")
    kid = header.get("kid")
    if not isinstance(kid, str) or not kid.strip():
        raise _unauthorized("Bearer token kid is required.")

    jwk = _find_jwk(settings.supabase_jwt_jwks_json, kid.strip())
    jwk_algorithm = jwk.get("alg")
    if isinstance(jwk_algorithm, str) and jwk_algorithm != algorithm:
        raise _unauthorized("Bearer token algorithm does not match signing key.")
    try:
        key = PyJWK.from_dict(jwk).key
        claims = jwt.decode(
            token,
            key=key,
            algorithms=[algorithm],
            audience=settings.supabase_jwt_audience,
            issuer=settings.supabase_jwt_issuer,
            options={"require": ["exp", "sub", "iss", "aud"]},
        )
    except jwt.InvalidTokenError:
        raise _unauthorized("Invalid bearer token.") from None
    if not isinstance(claims, dict):
        raise _unauthorized("Invalid bearer token.")
    return claims


def _decode_jwks_url_jwt(token: str, settings: Settings) -> dict[str, Any]:
    try:
        jwks_json = _load_jwks_json_from_url(
            settings.supabase_jwt_jwks_url,
            settings.supabase_jwt_jwks_cache_ttl_seconds,
        )
        shadow_settings = settings.model_copy(update={"supabase_jwt_jwks_json": jwks_json})
        return _decode_jwks_jwt(token, shadow_settings)
    except HTTPException as exc:
        if exc.detail != "Bearer token signing key was not found.":
            raise
    now = time.time()
    last_forced = _JWKS_LAST_FORCED_REFRESH.get(settings.supabase_jwt_jwks_url)
    if last_forced is not None and now - last_forced < JWKS_FORCED_REFRESH_MIN_INTERVAL_SECONDS:
        raise _unauthorized("Bearer token signing key was not found.")
    _JWKS_LAST_FORCED_REFRESH[settings.supabase_jwt_jwks_url] = now
    jwks_json = _load_jwks_json_from_url(
        settings.supabase_jwt_jwks_url,
        settings.supabase_jwt_jwks_cache_ttl_seconds,
        force_refresh=True,
    )
    shadow_settings = settings.model_copy(update={"supabase_jwt_jwks_json": jwks_json})
    return _decode_jwks_jwt(token, shadow_settings)


def _json_part(value: str) -> dict[str, Any]:
    try:
        decoded = _b64decode(value)
        parsed = json.loads(decoded.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise _unauthorized("Invalid bearer token.") from None
    if not isinstance(parsed, dict):
        raise _unauthorized("Invalid bearer token.")
    return parsed


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    try:
        return base64.urlsafe_b64decode(f"{value}{padding}")
    except ValueError:
        raise _unauthorized("Invalid bearer token.") from None


def _find_jwk(jwks_json: str, kid: str) -> dict[str, Any]:
    try:
        payload = json.loads(jwks_json)
    except ValueError:
        raise _unauthorized("Supabase JWKS JSON is invalid.") from None
    if not isinstance(payload, dict) or not isinstance(payload.get("keys"), list):
        raise _unauthorized("Supabase JWKS JSON is invalid.")
    for item in payload["keys"]:
        if isinstance(item, dict) and item.get("kid") == kid:
            return item
    raise _unauthorized("Bearer token signing key was not found.")


def _load_jwks_json_from_url(url: str, cache_ttl_seconds: int, *, force_refresh: bool = False) -> str:
    now = time.time()
    cached = _JWKS_CACHE.get(url)
    if not force_refresh and cached and cached[0] > now:
        return cached[1]
    payload = _fetch_jwks_json_from_url(url)
    _JWKS_CACHE[url] = (now + cache_ttl_seconds, payload)
    return payload


def _fetch_jwks_json_from_url(url: str) -> str:
    try:
        with urllib_request.urlopen(url, timeout=5) as response:
            raw = response.read().decode("utf-8")
    except (OSError, UnicodeDecodeError, URLError):
        raise _unauthorized("Unable to fetch Supabase JWKS.") from None
    return raw


def reset_jwks_cache_for_tests() -> None:
    _JWKS_CACHE.clear()
    _JWKS_LAST_FORCED_REFRESH.clear()


def _audience_matches(claim_audience: Any, expected: str) -> bool:
    if isinstance(claim_audience, str):
        return claim_audience == expected
    if isinstance(claim_audience, list):
        return expected in claim_audience
    return False


def _required_str(container: dict[str, Any], key: str) -> str:
    value = container.get(key)
    if not isinstance(value, str) or not value.strip():
        raise _unauthorized(f"Supabase claim '{key}' is required.")
    return value.strip()


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def _forbidden(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
