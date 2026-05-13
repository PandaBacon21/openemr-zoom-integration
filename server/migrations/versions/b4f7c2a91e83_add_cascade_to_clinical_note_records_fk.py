"""add ON DELETE CASCADE to clinical_note_records.zoom_meeting_id FK

Revision ID: b4f7c2a91e83
Revises: 8e1a97239ec2
Create Date: 2026-05-13

The FK on clinical_note_records.zoom_meeting_id was originally created
without ondelete='CASCADE', while its sibling meeting_patients FK had it.
This caused a Postgres FK violation on staging when older code issued a
bare DELETE on meeting_records for canceled appointments.

The ORM relationship MeetingRecord.clinical_note already declares
cascade='all, delete-orphan' — this aligns the DB-level constraint with
that intent.

Application logic in _process_appointment_delete preserves the
MeetingRecord when a ClinicalNoteRecord exists, so this cascade will
rarely fire in practice — but it remains the correct DB-level guarantee
for any future code path that issues a raw delete.
"""
from typing import Sequence, Union

from alembic import op


revision: str = 'b4f7c2a91e83'
down_revision: Union[str, Sequence[str], None] = '8e1a97239ec2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


FK_NAME = "clinical_note_records_zoom_meeting_id_fkey"
TABLE = "clinical_note_records"
LOCAL_COLS = ["zoom_meeting_id"]
REMOTE_TABLE = "meeting_records"
REMOTE_COLS = ["zoom_meeting_id"]


def upgrade() -> None:
    with op.batch_alter_table(TABLE) as batch_op:
        batch_op.drop_constraint(FK_NAME, type_='foreignkey')
        batch_op.create_foreign_key(
            FK_NAME,
            REMOTE_TABLE,
            LOCAL_COLS,
            REMOTE_COLS,
            ondelete='CASCADE',
        )


def downgrade() -> None:
    with op.batch_alter_table(TABLE) as batch_op:
        batch_op.drop_constraint(FK_NAME, type_='foreignkey')
        batch_op.create_foreign_key(
            FK_NAME,
            REMOTE_TABLE,
            LOCAL_COLS,
            REMOTE_COLS,
        )
