"""add veradigm_meetings table

Lean Veradigm demo: appointment -> Zoom meeting mapping for the external
Veradigm appointment page, isolated from MeetingRecord so Veradigm meetings
never enter the Epic note-writeback / status pipeline. Minted on demand from
Start/Join; keyed on the appointment id for idempotency.

Revision ID: a1b2c3d4e5f7
Revises: f1a2b3c4d5e6
Create Date: 2026-07-15 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f7"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "veradigm_meetings",
        sa.Column("openemr_appointment_id", sa.String(length=128), nullable=False),
        sa.Column("zoom_account_id", sa.String(length=128), nullable=False),
        sa.Column("openemr_provider_user_id", sa.String(length=128), nullable=True),
        sa.Column("zoom_meeting_id", sa.String(length=128), nullable=False),
        sa.Column("start_url", sa.String(length=1024), nullable=True),
        sa.Column("join_url", sa.String(length=1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["zoom_account_id"], ["zoom_accounts.account_id"]),
        sa.PrimaryKeyConstraint("openemr_appointment_id"),
    )
    op.create_index(
        op.f("ix_veradigm_meetings_zoom_account_id"),
        "veradigm_meetings",
        ["zoom_account_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_veradigm_meetings_zoom_account_id"),
        table_name="veradigm_meetings",
    )
    op.drop_table("veradigm_meetings")
