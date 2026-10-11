"""Add the stale-output flags the session model reads and writes.

``sessions.findings_stale`` and ``sessions.report_stale`` exist on the ORM
model, so databases created with ``create_all`` have them, but no migration
added them. A database built from migrations alone (the only path allowed in
production) therefore failed on the first session query.

Revision ID: 0015_session_stale_flags
Revises: 0014_membership_org_user_unique
Create Date: 2026-10-11
"""

from alembic import op
import sqlalchemy as sa


revision = "0015_session_stale_flags"
down_revision = "0014_membership_org_user_unique"
branch_labels = None
depends_on = None

COLUMNS = ("findings_stale", "report_stale")


def _existing_columns() -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns("sessions")}


def upgrade() -> None:
    existing = _existing_columns()
    for name in COLUMNS:
        if name not in existing:
            op.add_column("sessions", sa.Column(name, sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    existing = _existing_columns()
    with op.batch_alter_table("sessions") as batch:
        for name in COLUMNS:
            if name in existing:
                batch.drop_column(name)
