"""End-to-end check of the Supabase access-token hook against the API verifier.

Runs only when ``PASASCOPE_AUTH_HOOK_TEST_DATABASE_URL`` points at a disposable
PostgreSQL database (SQLAlchemy URL). The test migrates it, installs
``scripts/supabase/auth_claims_hook.sql`` and then feeds the hook's output
through the same verifier the API uses, so the two cannot drift apart.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.auth.supabase_auth import authenticate_supabase_bearer
from app.core.config import Settings, get_settings
from tests.path_helpers import repo_root

DATABASE_URL = os.getenv("PASASCOPE_AUTH_HOOK_TEST_DATABASE_URL", "")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="PASASCOPE_AUTH_HOOK_TEST_DATABASE_URL is not set")

SECRET = "hook-test-secret"
ISSUER = "https://project-ref.supabase.co/auth/v1"


@pytest.fixture(scope="module")
def db():
    from sqlalchemy import create_engine

    os.environ["PASASCOPE_DATABASE_URL"] = DATABASE_URL
    get_settings.cache_clear()
    try:
        from app.db.migrations_runner import run_alembic_upgrade_head

        run_alembic_upgrade_head()
    finally:
        os.environ.pop("PASASCOPE_DATABASE_URL", None)
        get_settings.cache_clear()
    engine = create_engine(DATABASE_URL)
    hook_sql = (repo_root() / "scripts" / "supabase" / "auth_claims_hook.sql").read_text(encoding="utf-8")
    # Run the file exactly as psql would: no parameter substitution.
    raw = engine.raw_connection()
    try:
        raw.cursor().execute(hook_sql)
        raw.commit()
    finally:
        raw.close()
    yield engine
    engine.dispose()


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _token_from_hook(db, user_id: str, *, aal: str = "aal2", planted: dict | None = None) -> tuple[dict, str]:
    """Issue claims the way Supabase Auth does, then sign them like its HS256 tokens."""

    from sqlalchemy import text

    base_claims = {
        "sub": user_id,
        "iss": ISSUER,
        "aud": "authenticated",
        "exp": int(time.time()) + 600,
        "aal": aal,
        "email": f"{user_id}@clinic.example",
        "app_metadata": {"provider": "email", **(planted or {})},
    }
    event = {"user_id": user_id, "claims": base_claims}
    with db.begin() as connection:
        result = connection.execute(
            text("select public.pasascope_access_token_hook(cast(:event as jsonb))"), {"event": json.dumps(event)}
        ).scalar_one()
    claims = result["claims"]
    header = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = _b64(json.dumps(claims).encode())
    signature = hmac.new(SECRET.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
    return claims, f"{header}.{payload}.{_b64(signature)}"


def _settings() -> Settings:
    return Settings(auth_mode="supabase", supabase_jwt_secret=SECRET, supabase_jwt_issuer=ISSUER)


def _provision_admin(db, organization_id: str, user_id: str) -> None:
    from sqlalchemy import text

    with db.begin() as connection:
        connection.execute(
            text("select public.pasascope_provision_first_admin(:org, :name, :user, :display)"),
            {"org": organization_id, "name": "Clinic", "user": user_id, "display": "Admin"},
        )


def _add_member(db, organization_id: str, user_id: str, role: str, *, invited: bool, active: bool = True) -> None:
    from sqlalchemy import text

    with db.begin() as connection:
        connection.execute(
            text("insert into user_profiles (user_id, display_name, created_at) values (:u, :u, now()) on conflict do nothing"),
            {"u": user_id},
        )
        connection.execute(
            text(
                "insert into organization_memberships (membership_id, organization_id, user_id, role, active, created_at)"
                " values (:m, :o, :u, :r, :a, now())"
            ),
            {"m": f"mbr_{uuid4().hex[:10]}", "o": organization_id, "u": user_id, "r": role, "a": active},
        )
        if invited:
            connection.execute(
                text(
                    "insert into organization_invitations (invitation_id, organization_id, email, display_name, role,"
                    " status, invited_by, accepted_user_id, expires_at, created_at, accepted_at)"
                    " values (:i, :o, :e, :u, :r, 'accepted', 'admin', :u, now() + interval '7 days', now(), now())"
                ),
                {"i": f"inv_{uuid4().hex[:10]}", "o": organization_id, "e": f"{user_id}@clinic.example", "u": user_id, "r": role},
            )


def test_account_without_membership_gets_no_access_and_the_api_rejects_it(db):
    claims, token = _token_from_hook(db, f"user_{uuid4().hex[:8]}")

    assert "role" not in claims["app_metadata"]
    assert "organization_id" not in claims["app_metadata"]
    with pytest.raises(HTTPException) as raised:
        authenticate_supabase_bearer(f"Bearer {token}", _settings())
    assert raised.value.status_code == 401


def test_planted_access_claims_are_discarded(db):
    planted = {"role": "org_admin", "organization_id": "victim_org", "membership_active": True, "invitation_status": "accepted"}

    claims, token = _token_from_hook(db, f"user_{uuid4().hex[:8]}", planted=planted)

    assert claims["app_metadata"] == {"provider": "email"}
    with pytest.raises(HTTPException):
        authenticate_supabase_bearer(f"Bearer {token}", _settings())


def test_provisioned_first_admin_is_accepted_by_the_api_and_cannot_be_provisioned_twice(db):
    from sqlalchemy.exc import DBAPIError

    organization_id, admin_id = f"org_{uuid4().hex[:8]}", f"admin_{uuid4().hex[:8]}"
    _provision_admin(db, organization_id, admin_id)

    _claims, token = _token_from_hook(db, admin_id)
    principal = authenticate_supabase_bearer(f"Bearer {token}", _settings())

    assert (principal.user_id, principal.organization_id, principal.role) == (admin_id, organization_id, "org_admin")
    assert principal.invitation_status == "accepted"
    with pytest.raises(DBAPIError):
        _provision_admin(db, organization_id, f"admin_{uuid4().hex[:8]}")


def test_invited_therapist_passes_and_uninvited_member_is_held_at_the_invitation_gate(db):
    organization_id = f"org_{uuid4().hex[:8]}"
    _provision_admin(db, organization_id, f"admin_{uuid4().hex[:8]}")
    invited, uninvited = f"ther_{uuid4().hex[:8]}", f"ther_{uuid4().hex[:8]}"
    _add_member(db, organization_id, invited, "therapist", invited=True)
    _add_member(db, organization_id, uninvited, "therapist", invited=False)

    _c1, invited_token = _token_from_hook(db, invited)
    _c2, uninvited_token = _token_from_hook(db, uninvited)

    principal = authenticate_supabase_bearer(f"Bearer {invited_token}", _settings())
    assert (principal.organization_id, principal.role) == (organization_id, "therapist")
    with pytest.raises(HTTPException) as raised:
        authenticate_supabase_bearer(f"Bearer {uninvited_token}", _settings())
    assert raised.value.status_code == 403
    assert raised.value.detail == "Invitation must be accepted."


def test_revoked_membership_loses_access_on_the_next_token(db):
    from sqlalchemy import text

    organization_id, user_id = f"org_{uuid4().hex[:8]}", f"ther_{uuid4().hex[:8]}"
    _provision_admin(db, organization_id, f"admin_{uuid4().hex[:8]}")
    _add_member(db, organization_id, user_id, "therapist", invited=True)
    _c, before = _token_from_hook(db, user_id)
    authenticate_supabase_bearer(f"Bearer {before}", _settings())

    with db.begin() as connection:
        connection.execute(text("update organization_memberships set active = false where user_id = :u"), {"u": user_id})
    claims, after = _token_from_hook(db, user_id)

    assert "organizations" not in claims["app_metadata"]
    with pytest.raises(HTTPException):
        authenticate_supabase_bearer(f"Bearer {after}", _settings())


def test_member_of_two_organizations_must_select_one(db):
    org_a, org_b, user_id = f"org_{uuid4().hex[:8]}", f"org_{uuid4().hex[:8]}", f"sup_{uuid4().hex[:8]}"
    for organization_id in (org_a, org_b):
        _provision_admin(db, organization_id, f"admin_{uuid4().hex[:8]}")
    _add_member(db, org_a, user_id, "therapist", invited=True)
    _add_member(db, org_b, user_id, "clinical_supervisor", invited=False)

    claims, token = _token_from_hook(db, user_id)

    assert "organization_id" not in claims["app_metadata"]
    with pytest.raises(HTTPException) as raised:
        authenticate_supabase_bearer(f"Bearer {token}", _settings())
    assert raised.value.status_code == 403
    selected = authenticate_supabase_bearer(f"Bearer {token}", _settings(), selected_organization_id=org_b)
    assert (selected.organization_id, selected.role) == (org_b, "clinical_supervisor")
    with pytest.raises(HTTPException):
        authenticate_supabase_bearer(f"Bearer {token}", _settings(), selected_organization_id="org_not_mine")


def test_mfa_requirement_still_applies_to_hook_issued_tokens(db):
    organization_id, admin_id = f"org_{uuid4().hex[:8]}", f"admin_{uuid4().hex[:8]}"
    _provision_admin(db, organization_id, admin_id)

    _claims, token = _token_from_hook(db, admin_id, aal="aal1")

    with pytest.raises(HTTPException) as raised:
        authenticate_supabase_bearer(f"Bearer {token}", _settings())
    assert raised.value.detail == "AAL2 session is required."
