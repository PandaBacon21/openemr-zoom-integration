"""create meeting_patients table

Revision ID: 9f2c1a7d4b6e
Revises: 41740385eb41
Create Date: 2026-04-19 17:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9f2c1a7d4b6e"
down_revision: Union[str, Sequence[str], None] = "41740385eb41"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "meeting_patients" not in inspector.get_table_names():
        op.create_table(
            "meeting_patients",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("meeting_record_id", sa.Integer(), nullable=False),
            sa.Column("openemr_patient_id", sa.String(length=128), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(
                ["meeting_record_id"],
                ["meeting_records.id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "meeting_patients" in inspector.get_table_names():
        op.drop_table("meeting_patients")
