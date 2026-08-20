"""add integration to appointment_type_filters

Lean Veradigm demo: appointment-type filters are split by integration style.
'epic' rows drive the existing Zoom-meeting + clinical-note writeback pipeline;
'veradigm' rows are surfaced only on the external Veradigm appointment page and
are excluded from the Epic pipeline. Existing rows backfill to 'epic' so current
accounts keep today's behavior.

Revision ID: f1a2b3c4d5e6
Revises: e1f2a3b4c5d6
Create Date: 2026-07-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # server_default='epic' backfills existing rows and keeps the Epic pipeline
    # behavior unchanged for accounts created before this migration ran.
    op.add_column(
        "appointment_type_filters",
        sa.Column(
            "integration",
            sa.String(length=16),
            nullable=False,
            server_default="epic",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("appointment_type_filters", "integration")
