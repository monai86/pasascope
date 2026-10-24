"""Settings for the shared service layer, read from ``PASASCOPE_*`` environment variables.

The desktop program sets ``PASASCOPE_DATABASE_URL`` and the storage root for its
workspace; everything else keeps its default unless a developer overrides it.
The web server's settings (sign-in, CORS, rate limits, queues, production
checks) were removed with the web app (git tag web-app-final).
"""

from functools import lru_cache
import os
from pathlib import Path
import re
from urllib.parse import urlparse
import warnings

from pydantic import BaseModel, Field


DEFAULT_DATABASE_URL = "sqlite:///.local/pasascope.sqlite3"
_SUPABASE_BUCKET_NAME_RE = re.compile(r"[a-z0-9][a-z0-9._-]{0,62}")
_SUPABASE_PROJECT_HOST_RE = re.compile(
    r"(?P<project_ref>[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)\.supabase\.co"
)


PREVIOUS_ENV_PREFIX = "LINGUALENS_"


def getenv_compat(name: str, legacy_name: str = "", default: str = "") -> str:
    """Read a ``PASASCOPE_*`` setting, accepting the names it had before.

    The project's previous ``LINGUALENS_*`` spelling is still read, so an
    existing deployment or ``.env`` file keeps working after the rename.
    """
    if name in os.environ:
        return os.environ[name]
    previous_name = name.replace("PASASCOPE_", PREVIOUS_ENV_PREFIX, 1)
    if previous_name in os.environ:
        return os.environ[previous_name]
    if legacy_name and legacy_name in os.environ:
        warnings.warn(
            f"{legacy_name} is deprecated; use {name} instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return os.environ[legacy_name]
    return default


def _is_valid_https_url(value: str) -> bool:
    if not isinstance(value, str) or value != value.strip():
        return False
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname:
        return False
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        return False
    try:
        _ = parsed.port
    except ValueError:
        return False
    return True


def _supabase_project_ref_from_host(host: str) -> str | None:
    normalized_host = host.casefold()
    match = _SUPABASE_PROJECT_HOST_RE.fullmatch(normalized_host)
    return match.group("project_ref") if match else None


def _is_valid_supabase_project_url(value: str) -> bool:
    if not _is_valid_https_url(value):
        return False
    parsed = urlparse(value)
    return parsed.path in {"", "/"} and _supabase_project_ref_from_host(parsed.hostname or "") is not None


def _is_valid_supabase_service_role_key(value: str) -> bool:
    return isinstance(value, str) and bool(value) and value == value.strip() and not any(
        character.isspace() for character in value
    )


def _is_valid_supabase_bucket_name(value: str) -> bool:
    return isinstance(value, str) and _SUPABASE_BUCKET_NAME_RE.fullmatch(value) is not None


class Settings(BaseModel):
    mock_mode: bool = True
    # Optional copy of each recording in a private Supabase bucket (off by default).
    audio_backup_mode: str = "none"
    debug_feature_override: bool = False
    database_url: str = DEFAULT_DATABASE_URL
    # Local Whisper runs on this machine only; recordings are never sent out.
    asr_local_whisper_enabled: bool = False
    asr_whisper_model_size: str = "medium"
    # "thai_specialized" sends recordings heard as Thai to the Thai fine-tuned
    # model (converted by scripts/convert_thai_whisper.sh) and others to the
    # multilingual one. "auto" lets the multilingual model hear the language;
    # "thai" or "english" forces one, which makes speech in the other language
    # come out transliterated.
    asr_language_strategy: str = "thai_specialized"
    # Hosted Whisper sends the recording to an external service. Off unless the
    # operator turns it on and discloses it to users.
    asr_hosted_enabled: bool = False
    asr_hosted_base_url: str = "https://api.groq.com/openai/v1"
    asr_hosted_api_key: str = ""
    asr_hosted_model: str = "whisper-large-v3"
    storage_mode: str = "local_private"
    local_storage_root: str = ".local/storage"
    supabase_storage_url: str = ""
    supabase_storage_service_role_key: str = Field(default="", repr=False)
    supabase_storage_bucket: str = ""
    ai_report_drafting_enabled: bool = False
    reference_artifact_dir: str = "artifacts/reference_evidence/current"

    @property
    def resolved_local_storage_root(self) -> Path:
        return Path(self.local_storage_root)

    @property
    def has_valid_audio_backup_target(self) -> bool:
        """Project URL, bucket and service role key for the recording backup."""
        return (
            _is_valid_supabase_project_url(self.supabase_storage_url)
            and _is_valid_supabase_service_role_key(self.supabase_storage_service_role_key)
            and _is_valid_supabase_bucket_name(self.supabase_storage_bucket)
        )

    def validate_runtime_security(self) -> "Settings":
        if self.audio_backup_mode not in {"none", "supabase"}:
            raise ValueError("Audio backup mode must be 'none' or 'supabase'.")
        if self.audio_backup_mode == "supabase" and not self.has_valid_audio_backup_target:
            raise ValueError("Audio backup to Supabase needs a valid storage URL, bucket and service role key.")
        if self.asr_hosted_enabled and not (
            self.asr_hosted_api_key.strip() and self.asr_hosted_base_url.startswith("https://")
        ):
            raise ValueError("Hosted transcription needs an API key and an https base URL.")
        return self

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            mock_mode=getenv_compat("PASASCOPE_MOCK_MODE", "THERAPIST_APP_V2_MOCK_MODE", "true").lower() != "false",
            audio_backup_mode=getenv_compat("PASASCOPE_AUDIO_BACKUP_MODE", default="none").strip().lower(),
            debug_feature_override=getenv_compat(
                "PASASCOPE_DEBUG_FEATURE_OVERRIDE",
                "THERAPIST_APP_V2_DEBUG_FEATURE_OVERRIDE",
                "false",
            ).lower()
            == "true",
            database_url=getenv_compat("PASASCOPE_DATABASE_URL", "THERAPIST_APP_V2_DATABASE_URL", DEFAULT_DATABASE_URL),
            asr_local_whisper_enabled=getenv_compat("PASASCOPE_ASR_LOCAL_WHISPER_ENABLED", default="false").lower()
            == "true",
            asr_whisper_model_size=getenv_compat("PASASCOPE_ASR_WHISPER_MODEL_SIZE", default="medium"),
            asr_language_strategy=getenv_compat("PASASCOPE_ASR_LANGUAGE_STRATEGY", default="thai_specialized"),
            asr_hosted_enabled=getenv_compat("PASASCOPE_ASR_HOSTED_ENABLED", default="false").lower() == "true",
            asr_hosted_base_url=getenv_compat(
                "PASASCOPE_ASR_HOSTED_BASE_URL", default="https://api.groq.com/openai/v1"
            ).rstrip("/"),
            asr_hosted_api_key=getenv_compat("PASASCOPE_ASR_HOSTED_API_KEY", default=""),
            asr_hosted_model=getenv_compat("PASASCOPE_ASR_HOSTED_MODEL", default="whisper-large-v3"),
            storage_mode=getenv_compat("PASASCOPE_STORAGE_MODE", "THERAPIST_APP_V2_STORAGE_MODE", "local_private"),
            local_storage_root=getenv_compat(
                "PASASCOPE_LOCAL_STORAGE_ROOT",
                "THERAPIST_APP_V2_LOCAL_STORAGE_ROOT",
                ".local/storage",
            ),
            supabase_storage_url=getenv_compat(
                "PASASCOPE_SUPABASE_STORAGE_URL",
                "THERAPIST_APP_V2_SUPABASE_STORAGE_URL",
                "",
            ),
            supabase_storage_service_role_key=getenv_compat(
                "PASASCOPE_SUPABASE_STORAGE_SERVICE_ROLE_KEY",
                "THERAPIST_APP_V2_SUPABASE_STORAGE_SERVICE_ROLE_KEY",
                "",
            ),
            supabase_storage_bucket=getenv_compat(
                "PASASCOPE_SUPABASE_STORAGE_BUCKET",
                "THERAPIST_APP_V2_SUPABASE_STORAGE_BUCKET",
                "",
            ),
            ai_report_drafting_enabled=getenv_compat(
                "PASASCOPE_AI_REPORT_DRAFTING_ENABLED",
                "THERAPIST_APP_V2_AI_REPORT_DRAFTING_ENABLED",
                "false",
            ).lower()
            == "true",
            reference_artifact_dir=getenv_compat(
                "PASASCOPE_REFERENCE_ARTIFACT_DIR",
                "THERAPIST_APP_V2_REFERENCE_ARTIFACT_DIR",
                "artifacts/reference_evidence/current",
            ),
        ).validate_runtime_security()


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()
