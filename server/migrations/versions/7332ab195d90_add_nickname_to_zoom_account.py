"""add nickname to zoom_account

Revision ID: 7332ab195d90
Revises: 0051b818835b
Create Date: 2026-04-27 16:04:36.806842

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7332ab195d90'
down_revision: Union[str, Sequence[str], None] = '0051b818835b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('zoom_accounts', sa.Column('nickname', sa.String(length=128), nullable=True))


def downgrade() -> None:
    op.drop_column('zoom_accounts', 'nickname')