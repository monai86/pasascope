
from fastapi import Header, HTTPException, status
from fastapi import Depends, Request
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

from app.auth.supabase_auth import authenticate_supabase_bearer
from app.core.config import Settings, get_settings


UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
# Local mock sign-in only: a signed-in Supabase user is always a therapist.
ALLOWED_LAUNCH_ROLES = {"therapist", "clinical_supervisor"}


class CurrentUser(BaseModel):
    user_id: str = "therapist-demo"
    role: str = "therapist"
    display_name: str = "Demo Therapist"
    organization_id: str = "pilot_org_001"
    aal: str = "aal1"


def get_current_user(
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    x_mock_user_id: str | None = Header(default=None),
    x_mock_role: str | None = Header(default=None),
    x_mock_display_name: str | None = Header(default=None),
    x_organization_id: str | None = Header(default=None, alias="X-Organization-Id"),
    settings: Settings = Depends(get_settings),
) -> CurrentUser:
    if settings.auth_mode != "mock":
        principal = authenticate_supabase_bearer(authorization, settings)
        return CurrentUser(
            user_id=principal.user_id,
            role=principal.role,
            display_name=principal.display_name,
            organization_id=principal.organization_id,
            aal=principal.aal,
        )
    return CurrentUser(
        user_id=x_user_id or x_mock_user_id or "therapist-demo",
        role=_validate_mock_role(x_mock_role or "therapist"),
        display_name=x_mock_display_name or "Demo Therapist",
        organization_id=x_organization_id or "pilot_org_001",
    )


def require_therapist(user: CurrentUser) -> CurrentUser:
    if user.role != "therapist":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Therapist role required.")
    return user


def _validate_mock_role(role: str) -> str:
    normalized = role.strip()
    if normalized not in ALLOWED_LAUNCH_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Mock role '{normalized or role}' is invalid.",
        )
    return normalized


class OriginGuardMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, *, allowed_origins: list[str], enabled: bool = True) -> None:
        super().__init__(app)
        self.allowed_origins = set(allowed_origins)
        self.enabled = enabled

    async def dispatch(self, request: Request, call_next):
        if not self.enabled or request.method not in UNSAFE_METHODS:
            return await call_next(request)
        origin = request.headers.get("origin")
        if origin is not None and origin not in self.allowed_origins:
            return JSONResponse({"detail": "Origin is not allowed."}, status_code=status.HTTP_403_FORBIDDEN)
        return await call_next(request)
