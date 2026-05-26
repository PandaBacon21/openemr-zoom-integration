"""add zoom_user_timezone to provider_mappings

Sprint 13 follow-up: meeting TZ resolution moves from account-level
(AccountConfig.timezone) to provider-level (ProviderMapping.zoom_user_timezone)
so multi-facility / multi-time-zone demos schedule meetings against each
provider's actual Zoom user TZ rather than a single account-wide setting.

Account-level TZ stays in place as a fallback when a mapping has no TZ
cached yet (Zoom user with no profile TZ, mapping created before this
migration ran, etc.).

Revision ID: c1d2e3f4a5b6
Revises: a3f4e1c92b04
Create Date: 2026-05-26 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, Sequence[str], None] = "a3f4e1c92b04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Nullable — captured at provider-mapping create time via a Zoom GET
    # /users/{userId} call. Mappings created before this migration ran will
    # render with no TZ until re-mapped; meeting creation falls back to
    # AccountConfig.timezone in that case.
    op.add_column(
        "provider_mappings",
        sa.Column("zoom_user_timezone", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("provider_mappings", "zoom_user_timezone")
