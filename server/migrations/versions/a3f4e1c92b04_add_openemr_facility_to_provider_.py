"""add openemr_facility_id + openemr_facility_name to provider_mappings (S7-14)

Revision ID: a3f4e1c92b04
Revises: b4f7c2a91e83
Create Date: 2026-05-14 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a3f4e1c92b04"
down_revision: Union[str, Sequence[str], None] = "b4f7c2a91e83"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Both nullable so existing ProviderMapping rows (pre-S7-14) keep working —
    # they'll just render with no facility in the UI until they're re-mapped.
    op.add_column(
        "provider_mappings",
        sa.Column("openemr_facility_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "provider_mappings",
        sa.Column("openemr_facility_name", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("provider_mappings", "openemr_facility_name")
    op.drop_column("provider_mappings", "openemr_facility_id")
