"""Deleting an account and everything in its workspace, at the account holder's request."""
from __future__ import annotations

from app.auth.supabase_admin import delete_auth_user
from app.auth.supabase_auth import PERSONAL_ORGANIZATION_PREFIX
from app.core.config import Settings
from app.core.security import CurrentUser
from app.repositories.mock_repository import MockRepository
from app.services.storage_service import get_storage_adapter


class AccountDeletionUnavailable(RuntimeError):
    """This deployment cannot delete accounts: no real sign-in, or no way to manage accounts."""


class RecordingsNotRemoved(RuntimeError):
    """A stored recording could not be removed, so nothing else was deleted."""


def delete_account(repo: MockRepository, user: CurrentUser, settings: Settings) -> dict[str, int]:
    """Remove the account's recordings, then its records, then the sign-in account.

    The steps go from what is hardest to find again to what is easiest to
    retry. Recordings first: if one cannot be removed, the records that point
    to it are kept and the request can be repeated. The sign-in account goes
    last; if Supabase cannot be reached then, the records are already gone and
    a repeat finds nothing left but the account.
    """
    if settings.auth_mode != "supabase" or not user.organization_id.startswith(PERSONAL_ORGANIZATION_PREFIX):
        raise AccountDeletionUnavailable("Accounts can be deleted only where people sign in with their own account.")
    if settings.supabase_admin_target is None:
        raise AccountDeletionUnavailable("This server is not set up to delete accounts.")

    storage = get_storage_adapter()
    for audio_file in repo.workspace_records(user.organization_id)["audio_files"]:
        if not audio_file.object_key:
            continue
        # A missing local file is fine once the backup copy is gone; a backup
        # that could not be deleted would outlive the account.
        if storage.delete_object(audio_file.object_key).status == "backup_delete_failed":
            raise RecordingsNotRemoved("A recording could not be removed from storage.")

    removed = repo.delete_workspace(user.organization_id, user_id=user.user_id)
    delete_auth_user(user.user_id, settings)
    return removed
