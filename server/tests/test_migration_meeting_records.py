from pathlib import Path


def test_meeting_records_migration_updates_expected_columns():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "5ecd2a942ca3_current_schema_with_string_primary_keys.py"
    )
    text = migration_path.read_text(encoding="utf-8")

    assert "op.create_table('meeting_records'" in text
    assert "sa.Column('zoom_meeting_id', sa.String(length=128), nullable=False)" in text
    assert "'zoom_start_url'" in text
    assert "'zoom_join_url'" in text
    assert "'alternative_host_email'" in text
    assert "'openemr_appt_status'" in text
    assert "sa.ForeignKeyConstraint(['zoom_account_id'], ['zoom_accounts.account_id']" in text
    assert "sa.PrimaryKeyConstraint('zoom_meeting_id')" in text
    assert "op.drop_table('meeting_records')" in text


def test_meeting_patients_migration_creates_expected_table():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "5ecd2a942ca3_current_schema_with_string_primary_keys.py"
    )
    text = migration_path.read_text(encoding="utf-8")

    assert "op.create_table('meeting_patients'" in text
    assert "'zoom_meeting_id'" in text
    assert "'openemr_patient_id'" in text
    assert "'created_at'" in text
    assert "sa.ForeignKeyConstraint(" in text
    assert "['meeting_records.zoom_meeting_id']" in text
    assert "ondelete='CASCADE'" in text
    assert "op.drop_table('meeting_patients')" in text


def test_meeting_started_at_migration_adds_meeting_timestamp_and_tenant_index():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "18c6821766b3_add_meeting_started_at_to_meeting_.py"
    )
    text = migration_path.read_text(encoding="utf-8")

    assert "op.add_column('meeting_records', sa.Column('meeting_started_at'" in text
    assert "sa.DateTime(timezone=True)" in text
    assert "nullable=True" in text
    assert "op.create_index(op.f('ix_zoom_accounts_tenant_id')" in text
    assert "['tenant_id']" in text
    assert "unique=True" in text
    assert "op.drop_index(op.f('ix_zoom_accounts_tenant_id')" in text
    assert "op.drop_column('meeting_records', 'meeting_started_at')" in text
