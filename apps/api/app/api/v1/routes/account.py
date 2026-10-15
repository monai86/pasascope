from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.dependencies import get_repository
from app.auth.supabase_admin import SupabaseAdminUnavailable
from app.core.config import Settings, get_settings
from app.core.security import CurrentUser, get_current_user
from app.repositories.mock_repository import MockRepository
from app.services.account_service import AccountDeletionUnavailable, RecordingsNotRemoved, delete_account

router = APIRouter(prefix="/account", tags=["account"])


@router.delete("")
def delete_own_account(
    user: CurrentUser = Depends(get_current_user),
    repo: MockRepository = Depends(get_repository),
    settings: Settings = Depends(get_settings),
):
    """Delete the signed-in account with its cases, sessions, recordings, transcripts and reports."""
    try:
        removed = delete_account(repo, user, settings)
    except AccountDeletionUnavailable as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except RecordingsNotRemoved as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="A recording could not be removed, so nothing was deleted. Try again in a moment.",
        ) from exc
    except SupabaseAdminUnavailable as exc:
        # 502, not 503: the records are gone and only the sign-in account is left.
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Your records were deleted, but the sign-in account could not be removed yet. Try again in a moment.",
        ) from exc
    return {"status": "deleted", "removed": removed}
