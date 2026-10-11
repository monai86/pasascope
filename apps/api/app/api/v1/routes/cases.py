from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.dependencies import get_repository
from app.auth.authorization import (
    assert_case_creation_allowed,
    assert_clinical_mutation_allowed,
    filter_cases_for_user,
    require_case,
)
from app.core.errors import bad_request, not_found
from app.core.security import CurrentUser, get_current_user
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


def _resolve_case_creation_payload(payload: ChildCaseCreate, repo: MockRepository, user: CurrentUser) -> ChildCaseCreate:
    assert_case_creation_allowed(user)

    if user.role == "therapist":
        if payload.primary_therapist_user_id and payload.primary_therapist_user_id != user.user_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Therapist-created cases must keep the authenticated therapist as primary.",
            )
        extra_care_team = [user_id for user_id in payload.care_team_user_ids if user_id != user.user_id]
        if extra_care_team:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Additional care-team members must be assigned through the care-team route.",
            )
        return payload.model_copy(
            update={
                "organization_id": user.organization_id,
                "care_team_user_ids": [user.user_id],
                "primary_therapist_user_id": user.user_id,
            }
        )

    primary_therapist_user_id = payload.primary_therapist_user_id
    if primary_therapist_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Primary therapist assignment required at case creation.",
        )
    membership = next(
        (
            item
            for item in repo.memberships.values()
            if item.organization_id == user.organization_id
            and item.user_id == primary_therapist_user_id
            and item.role == "therapist"
            and item.active
        ),
        None,
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Primary therapist assignment must be an active therapist membership.",
        )
    extra_care_team = [
        user_id
        for user_id in payload.care_team_user_ids
        if user_id not in {user.user_id, primary_therapist_user_id}
    ]
    if extra_care_team:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Additional care-team members must be assigned through the care-team route.",
        )
    return payload.model_copy(
        update={
            "organization_id": user.organization_id,
            "care_team_user_ids": [primary_therapist_user_id],
            "primary_therapist_user_id": primary_therapist_user_id,
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
):
    scoped_payload = _resolve_case_creation_payload(payload, repo, user)
    return repo.create_case(scoped_payload, actor_id="system")


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
    patch = ChildCaseUpdate(**payload.model_dump(exclude_unset=True))
    return repo.update_case(case_id, patch, expected_version=repo.cases[case_id].version, actor_id=user.user_id)


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
    return withdraw_consent(repo, case_id, payload.reason, payload.redact_notes)
