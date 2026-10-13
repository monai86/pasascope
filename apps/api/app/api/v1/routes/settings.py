from fastapi import APIRouter

from app.core.config import get_settings
from app.services.asr_providers.registry import asr_provider_registry

router = APIRouter(prefix="/settings", tags=["settings"])


def _audio_upload_capability(config) -> str:
    if config.storage_mode in {"local", "local_private"}:
        return "experimental"
    return "unavailable"


@router.get("")
def settings():
    config = get_settings()
    audio_upload = _audio_upload_capability(config)
    local_whisper = asr_provider_registry.get("local_whisper").check_availability().available
    hosted_whisper = asr_provider_registry.get("hosted_whisper").check_availability().available
    # On-device transcription is preferred when both are switched on.
    transcription_provider = "local_whisper" if local_whisper else "hosted_whisper" if hosted_whisper else None
    transcription = (
        "experimental"
        if audio_upload == "experimental" and (transcription_provider or config.mock_mode)
        else "unavailable"
    )
    return {
        "mock_mode": config.mock_mode,
        "auth_mode": config.auth_mode,
        "model_version": "v2-mock",
        "feature_schema": "pasascope-app.1",
        "guideline_mapping": "review-support-only",
        "user_roles": ["therapist", "clinical_supervisor", "org_admin"],
        "access_model": {
            "invitation_only": config.supabase_require_invitation,
            "public_signup": config.public_signup,
            # Kept for web builds that read it: there is one way of working now.
            "review_gates": "open",
            "required_app_aal": "aal2" if config.supabase_require_mfa else "aal1",
            "active_organization_session": "explicit_selection_when_ambiguous",
            "production_mock_mode": "forbidden" if not config.mock_mode else "local_only",
        },
        "data_retention": "local demo data only unless configured otherwise",
        "consent_policy": "visible per case; withdrawal unlinks case outputs",
        "capabilities": {
            "cases": "available",
            "audio_upload": audio_upload,
            "transcription": transcription,
            "transcript_qa": "available",
            "feature_extraction": "available",
            "ai_review": "disabled",
            "report_drafting": (
                "available" if config.ai_report_drafting_enabled else "disabled"
            ),
            "pdf_export": "unavailable",
        },
        "pipeline_settings": {
            "audio_processing": "experimental_async",
            "transcription_provider": transcription_provider,
            # True when recordings are sent outside this deployment to be transcribed.
            "transcription_external": transcription_provider == "hosted_whisper",
            "job_queue_mode": config.job_queue_mode,
            "repository_mode": config.repository_mode,
            "storage_mode": config.storage_mode,
            "ai_review_policy": "organization_opt_in_default_off",
            "ai_report_drafting_enabled": config.ai_report_drafting_enabled,
        },
    }
