"""Durable copy of locally stored recordings.

The audio pipeline, playback and waveform routes all read recordings from the
local storage root. On a host whose disk is wiped at restart that loses every
recording, so when a backup target is configured each verified upload is also
written to a private Supabase Storage bucket, and a recording missing from
disk is fetched back before it is read. With no target configured this module
does nothing.
"""
from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

import httpx

from app.core.config import Settings, get_settings

_TIMEOUT = httpx.Timeout(120.0, connect=10.0)


def _client() -> httpx.Client:
    return httpx.Client(timeout=_TIMEOUT)


def backup_enabled(settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    return settings.audio_backup_mode == "supabase" and settings.has_valid_audio_backup_target


def _object_url(settings: Settings, object_key: str) -> str:
    base = settings.supabase_storage_url.rstrip("/")
    return f"{base}/storage/v1/object/{quote(settings.supabase_storage_bucket)}/{quote(object_key, safe='/')}"


def _headers(settings: Settings) -> dict[str, str]:
    key = settings.supabase_storage_service_role_key
    return {"Authorization": f"Bearer {key}", "apikey": key}


def backup_recording(object_key: str, path: Path, content_type: str) -> None:
    """Write a recording to the backup bucket. Raises if it cannot be stored."""
    settings = get_settings()
    if not backup_enabled(settings):
        return
    headers = {**_headers(settings), "Content-Type": content_type or "application/octet-stream", "x-upsert": "true"}
    # The open file is sent in chunks; a whole recording in memory is too much
    # for a small host.
    with _client() as client, path.open("rb") as handle:
        response = client.post(_object_url(settings, object_key), headers=headers, content=handle)
    response.raise_for_status()


def restore_recording(object_key: str, path: Path) -> bool:
    """Fetch a recording that is missing from disk. Returns whether it is now present."""
    settings = get_settings()
    if not backup_enabled(settings):
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(path.suffix + ".restoring")
    try:
        with _client() as client, client.stream("GET", _object_url(settings, object_key), headers=_headers(settings)) as response:
            if response.status_code != 200:
                return False
            with partial.open("wb") as handle:
                for chunk in response.iter_bytes():
                    handle.write(chunk)
        partial.replace(path)
        return True
    except httpx.HTTPError:
        return False
    finally:
        partial.unlink(missing_ok=True)


def delete_backup(object_key: str) -> bool:
    """Remove a recording from the backup bucket. Returns whether the bucket no longer has it."""
    settings = get_settings()
    if not backup_enabled(settings):
        return True
    try:
        with _client() as client:
            response = client.delete(_object_url(settings, object_key), headers=_headers(settings))
    except httpx.HTTPError:
        return False
    return response.status_code in {200, 204, 400, 404}
