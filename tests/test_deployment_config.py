"""Deployment configuration must only set variables the API actually reads."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_APP = ROOT / "apps" / "api" / "app"
# Set by the platform or the container, not read through the API settings.
PLATFORM_VARIABLES = {"PORT", "PYTHONPATH"}
# Informational only: nothing in the API changes behaviour on this value.
DEPLOYMENT_LABELS = {"LINGUALENS_APP_ENV"}


def _variables_read_by_api() -> set[str]:
    names: set[str] = set()
    for path in API_APP.rglob("*.py"):
        names.update(re.findall(r'"((?:LINGUALENS|PASASCOPE)_[A-Z0-9_]+|REDIS_URL|WEB_CONCURRENCY)"', path.read_text(encoding="utf-8")))
    return names


def _render_env_keys() -> list[str]:
    return re.findall(r"^\s*- key: ([A-Z0-9_]+)\s*$", (ROOT / "render.yaml").read_text(encoding="utf-8"), re.MULTILINE)


def test_render_blueprint_declares_environment_variables():
    assert len(_render_env_keys()) >= 10


def test_render_blueprint_only_sets_variables_the_api_reads():
    known = _variables_read_by_api() | PLATFORM_VARIABLES | DEPLOYMENT_LABELS

    unknown = sorted(key for key in _render_env_keys() if key not in known)

    assert unknown == [], f"render.yaml sets variables the API never reads: {unknown}"


def test_render_blueprint_provides_the_storage_service_role_key():
    assert "LINGUALENS_SUPABASE_STORAGE_SERVICE_ROLE_KEY" in _render_env_keys()
