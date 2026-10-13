from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.api.v1.dependencies import get_repository
from app.auth.authorization import (
    assert_case_creation_allowed,
    assert_clinical_mutation_allowed,
    filter_cases_for_user,
    require_case,
)
from app.core.config import Settings, get_settings
from app.core.errors import bad_request, not_found
from app.core.security import CurrentUser, get_current_user
from app.repositories.base import CaseVersionConflictError
from app.repositories.mock_repository import MockRepository, new_id
from app.schemas.clinical import (
    ChildCase,
    ChildCaseClientUpdate,
    ChildCaseCreate,
    ChildCaseUpdate,
    ConsentGrantRequest,
    ConsentWithdrawalRequest,
    ConsentWithdrawalResult,
    TimelineEvent,
)
from app.services.consent_service import (
    ConsentTransitionError,
    ensure_case_consent_active,
    grant_consent,
    withdraw_consent,
)

router = APIRouter(prefix="/cases", tags=["cases"])


def _resolve_case_creation_payload(payload: ChildCaseCreate, user: CurrentUser) -> ChildCaseCreate:
    """A case belongs to the person who creates it; nobody else can be put on it."""
    assert_case_creation_allowed(user)

    if payload.primary_therapist_user_id and payload.primary_therapist_user_id != user.user_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A new case must keep the signed-in user as its primary therapist.",
        )
    if any(user_id != user.user_id for user_id in payload.care_team_user_ids):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A new case cannot be shared with other users.",
        )
    return payload.model_copy(
        update={
            "organization_id": user.organization_id,
            "care_team_user_ids": [user.user_id],
            "primary_therapist_user_id": user.user_id,
        }
    )


@router.get("", response_model=list[ChildCase])
def list_cases(user: CurrentUser = Depends(get_current_user), repo: MockRepository = Depends(get_repository)):
    return [repo.clone(item) for item in filter_cases_for_user(list(repo.cases.values()), user)]


@router.post("", response_model=ChildCase)
def create_case(
    payload: ChildCaseCreate,
    user: CurrentUser = Depends(get_current_user),
    repo: MockRepository = Depends(get_repository),
    settings: Settings = Depends(get_settings),
):
    scoped_payload = _resolve_case_creation_payload(payload, user)
    if not settings.mock_mode:
        # Outside local demo mode a case always starts without consent; the
        # audited grant-consent route is the only way to record it.
        scoped_payload = scoped_payload.model_copy(update={"consent_status": "pending"})
    return repo.create_case(scoped_payload, actor_id="system", audit_actor_id=user.user_id)


@router.get("/{case_id}", response_model=ChildCase)
def get_case(case_id: str, user: CurrentUser = Depends(get_current_user), repo: MockRepository = Depends(get_repository)):
    return repo.clone(require_case(repo, case_id, user))


@router.patch("/{case_id}", response_model=ChildCase)
def update_case(
    case_id: str,
    payload: ChildCaseClientUpdate,
    user: CurrentUser = Depends(get_current_user),
    repo: MockRepository = Depends(get_repository),
):
    # Care-team access is the gate here: an org admin with an explicit
    # care-team grant may edit descriptive case fields.
    require_case(repo, case_id, user)
    try:
        ensure_case_consent_active(repo, case_id)
    except ValueError as exc:
        raise bad_request(str(exc)) from exc
    patch = ChildCaseUpdate(**payload.model_dump(exclude_unset=True, exclude={"expected_version"}))
    expected_version = payload.expected_version or repo.cases[case_id].version
    try:
        return repo.update_case(case_id, patch, expected_version=expected_version, actor_id=user.user_id)
    except CaseVersionConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Case was changed by another request; reload and retry.",
        ) from exc


# Said to the therapist when a case cannot be deleted. None of them names the child.
_CASE_NOT_EMPTY = {
    "consent_withdrawn": "This case's consent was withdrawn, so its record is kept.",
    "has_sessions": "This case has sessions and cannot be deleted. Withdraw its consent to remove its recordings.",
    "has_goals": "This case has therapy goals and cannot be deleted.",
    "has_privacy_operations": "This case has a privacy request on record and cannot be deleted.",
}


@router.delete("/{case_id}")
def delete_case(
    case_id: str,
    user: CurrentUser = Depends(get_current_user),
    repo: MockRepository = Depends(get_repository),
):
    """Delete a case that holds no clinical record, such as one created by mistake."""
    assert_clinical_mutation_allowed(user)
    require_case(repo, case_id, user)
    blocker = repo.case_deletion_blocker(case_id)
    if blocker is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_CASE_NOT_EMPTY[blocker])
    try:
        repo.delete_case(case_id, actor_id=user.user_id)
    except IntegrityError as exc:
        # The database holds a row for this case that the checks above do not know.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This case has records and cannot be deleted.",
        ) from exc
    return {"status": "deleted", "case_id": case_id}


@router.post("/{case_id}/grant-consent", response_model=ChildCase)
def grant_case_consent(
    case_id: str,
    payload: ConsentGrantRequest,
    user: CurrentUser = Depends(get_current_user),
    repo: MockRepository = Depends(get_repository),
):
    require_case(repo, case_id, user)
    assert_clinical_mutation_allowed(user)
    try:
        return grant_consent(repo, case_id, payload, actor_id=user.user_id)
    except ConsentTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.get("/{case_id}/timeline", response_model=list[TimelineEvent])
def case_timeline(case_id: str, user: CurrentUser = Depends(get_current_user), repo: MockRepository = Depends(get_repository)):
    require_case(repo, case_id, user)
    events = []
    for session in repo.sessions.values():
        if session.case_id == case_id:
            events.append(TimelineEvent(event_id=new_id("evt"), label=f"Session {session.session_date}", status=session.status, occurred_at=session.created_at, target_id=session.session_id))
    return events


@router.post("/{case_id}/withdraw-consent", response_model=ConsentWithdrawalResult)
def withdraw_case_consent(
    case_id: str,
    payload: ConsentWithdrawalRequest,
    user: CurrentUser = Depends(get_current_user),
    repo: MockRepository = Depends(get_repository),
):
    require_case(repo, case_id, user)
    return withdraw_consent(
        repo,
        case_id,
        payload.reason,
        payload.redact_notes,
        actor_id=user.user_id,
        requester_role=user.role,
    )
