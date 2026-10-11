from datetime import timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, Response

from app.api.v1.dependencies import get_repository
from app.auth.authorization import assert_sensitive_clinical_export_allowed, require_session
from app.core.errors import not_found
from app.core.security import CurrentUser, get_current_user
from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import utc_now
from app.services.audio_job_service import _local_audio_path
from app.services.consent_service import ensure_session_consent_active

router = APIRouter(tags=["audio-review"])


WAVEFORM_POINTS_PER_SECOND = 50
WAVEFORM_DECODE_RATE = 8000


def recording_peaks(path: Path, points_per_second: int = WAVEFORM_POINTS_PER_SECOND) -> tuple[bytes, float] | None:
    """Peak envelope of a stored recording as signed int8 (0-127), and its duration.

    Each point is the largest absolute sample in its window, scaled to the
    loudest point of the clip. Returns None when the recording cannot be
    decoded on this server; a waveform is never invented.
    """
    try:
        import numpy as np
        from faster_whisper.audio import decode_audio

        samples = decode_audio(str(path), sampling_rate=WAVEFORM_DECODE_RATE)
    except Exception:
        return None
    window = WAVEFORM_DECODE_RATE // points_per_second
    points = len(samples) // window
    if points == 0:
        return None
    peaks = np.abs(samples[: points * window]).reshape(points, window).max(axis=1)
    loudest = float(peaks.max())
    scaled = np.zeros(points, dtype=np.int8) if loudest <= 0 else np.round(peaks / loudest * 127).astype(np.int8)
    return scaled.tobytes(), len(samples) / WAVEFORM_DECODE_RATE


@router.get("/sessions/{session_id}/audio/waveform-peaks")
def get_waveform_peaks(
    session_id: str,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    require_session(repo, session_id, user)
    session = repo.sessions.get(session_id)
    if not session or session.case_id not in repo.cases:
        raise not_found("Session or case not found.")
    case = repo.cases[session.case_id]
    if case.consent_status.lower() != "granted":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Active patient consent is required.")
    ensure_session_consent_active(repo, session_id)

    audio_files = [
        a for a in repo.audio_files.values()
        if a.session_id == session_id and a.upload_status == "uploaded"
    ]
    if not audio_files:
        raise not_found("No verified audio file for this session.")
    audio = audio_files[0]

    recording = _local_audio_path(audio)
    result = recording_peaks(recording) if recording is not None else None
    if result is None:
        raise not_found("A waveform is not available for this recording.")
    peaks_data, duration = result

    headers = {
        "Content-Type": "application/octet-stream",
        "X-Sample-Rate": str(audio.sample_rate_hz or 16000),
        "X-Duration-Ms": str(int(duration * 1000)),
        "X-Points-Per-Second": str(WAVEFORM_POINTS_PER_SECOND),
        "X-Channels": "1",
        "X-Waveform-Source": "recording",
    }
    return Response(content=peaks_data, media_type="application/octet-stream", headers=headers)


@router.post("/sessions/{session_id}/audio/playback-grant")
def get_playback_grant(
    session_id: str,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    require_session(repo, session_id, user)
    session = repo.sessions.get(session_id)
    if not session or session.case_id not in repo.cases:
        raise not_found("Session or case not found.")
    case = repo.cases[session.case_id]
    if case.consent_status.lower() != "granted":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Active patient consent is required.")
    ensure_session_consent_active(repo, session_id)
    assert_sensitive_clinical_export_allowed(user)

    audio_files = [
        a for a in repo.audio_files.values()
        if a.session_id == session_id and a.upload_status == "uploaded"
    ]
    if not audio_files:
        raise not_found("No verified audio file for this session.")
    audio = audio_files[0]

    expires_at = (utc_now() + timedelta(minutes=15)).isoformat()
    return {
        "playback_url": f"/api/v1/audio/{audio.audio_file_id}/file",
        "expires_at": expires_at,
        "audio_sha256": audio.checksum_sha256 or "unknown",
    }
