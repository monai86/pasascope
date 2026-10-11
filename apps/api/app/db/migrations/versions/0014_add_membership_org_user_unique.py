"""Enforce one membership per user and organization.

The ORM model has always declared this constraint, so databases created with
``create_all`` have it, but no migration ever added it. Migrated databases
could therefore hold duplicate memberships for one user in one organization.

Revision ID: 0014_membership_org_user_unique
Revises: 0013_session_cues_acknowledgement
Create Date: 2026-10-11
"""

from alembic import op
import sqlalchemy as sa


revision = "0014_membership_org_user_unique"
down_revision = "0013_session_cues_acknowledgement"
branch_labels = None
depends_on = None

CONSTRAINT = "uq_organization_memberships_org_user"
TABLE = "organization_memberships"


def _has_constraint() -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(item["name"] == CONSTRAINT for item in inspector.get_unique_constraints(TABLE))


def upgrade() -> None:
    if _has_constraint():
        return
    with op.batch_alter_table(TABLE) as batch:
        batch.create_unique_constraint(CONSTRAINT, ["organization_id", "user_id"])


def downgrade() -> None:
    if not _has_constraint():
        return
    with op.batch_alter_table(TABLE) as batch:
        batch.drop_constraint(CONSTRAINT, type_="unique")
