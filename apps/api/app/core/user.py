from pydantic import BaseModel


class CurrentUser(BaseModel):
    """The person acting on the records. The desktop program uses one local therapist."""

    user_id: str = "therapist-demo"
    role: str = "therapist"
    display_name: str = "Demo Therapist"
    organization_id: str = "pilot_org_001"
    aal: str = "aal1"
