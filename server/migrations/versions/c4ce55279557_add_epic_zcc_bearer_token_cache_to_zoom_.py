"""add epic_zcc_bearer_token cache to zoom_accounts

Revision ID: c4ce55279557
Revises: db55813136ea
Create Date: 2026-06-15 18:08:53.494710

"""
from typing import Sequence, Union

import sqlalchemy as sa
import sqlalchemy_utils.types.encrypted.encrypted_type
from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'c4ce55279557'
down_revision: Union[str, Sequence[str], None] = 'db55813136ea'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('zoom_accounts', sa.Column(
        'epic_zcc_bearer_token',
        sqlalchemy_utils.types.encrypted.encrypted_type.EncryptedType(),
        nullable=True,
    ))
    op.add_column('zoom_accounts', sa.Column(
        'epic_zcc_bearer_token_expires_at',
        sa.DateTime(timezone=True),
        nullable=True,
    ))


def downgrade() -> None:
    op.drop_column('zoom_accounts', 'epic_zcc_bearer_token_expires_at')
    op.drop_column('zoom_accounts', 'epic_zcc_bearer_token')
