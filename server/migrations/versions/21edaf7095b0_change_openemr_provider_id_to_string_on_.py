"""change openemr_provider_id to string on provider_mappings

Revision ID: 21edaf7095b0
Revises: bc1e2fb3b8be
Create Date: 2026-04-20 21:48:19.276890

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '21edaf7095b0'
down_revision: Union[str, Sequence[str], None] = 'bc1e2fb3b8be'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('provider_mappings') as batch_op:
        batch_op.alter_column(
            'openemr_provider_id',
            existing_type=sa.INTEGER(),
            type_=sa.String(length=128),
            existing_nullable=True
        )
    # ### end Alembic commands ###

def downgrade() -> None:
    with op.batch_alter_table('provider_mappings') as batch_op:
        batch_op.alter_column(
            'openemr_provider_id',
            existing_type=sa.String(length=128),
            type_=sa.INTEGER(),
            existing_nullable=True
        )
    # ### end Alembic commands ###
