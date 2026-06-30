"""Drop epic_zcc_client_id from zoom_accounts — client ID moves to EPIC_ZCC_CLIENT_ID env var

The Epic CTI client ID is fixed per deployment (registered once in Zoom's admin portal)
and shared across all accounts. Storing it per-account in the DB allowed it to be
accidentally regenerated. Moving it to config means it can never drift per-account.

Revision ID: e1f2a3b4c5d6
Revises: c4ce55279557
Create Date: 2026-06-29
"""
from alembic import op


revision = 'e1f2a3b4c5d6'
down_revision = 'c4ce55279557'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('zoom_accounts') as batch_op:
        batch_op.drop_column('epic_zcc_client_id')


def downgrade():
    import sqlalchemy as sa
    with op.batch_alter_table('zoom_accounts') as batch_op:
        batch_op.add_column(sa.Column('epic_zcc_client_id', sa.String(length=64), nullable=True))
