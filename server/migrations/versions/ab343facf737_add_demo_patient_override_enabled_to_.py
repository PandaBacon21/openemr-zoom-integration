"""add demo_patient_override_enabled to zoom_account

Revision ID: ab343facf737
Revises: 7332ab195d90
Create Date: 2026-04-28 12:29:32.940773

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ab343facf737'
down_revision: Union[str, Sequence[str], None] = '7332ab195d90'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('zoom_accounts', sa.Column('demo_patient_override_enabled', sa.Boolean(), server_default='0', nullable=False))


def downgrade() -> None:
    op.drop_column('zoom_accounts', 'demo_patient_override_enabled')