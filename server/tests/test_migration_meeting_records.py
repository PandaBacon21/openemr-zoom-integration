from pathlib import Path


def test_meeting_records_migration_updates_expected_columns():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "41740385eb41_meeting_records.py"
    )
    text = migration_path.read_text(encoding="utf-8")

    assert "op.add_column('meeting_records'" in text
    assert "'zoom_start_url'" in text
    assert "'zoom_join_url'" in text
    assert "'alternative_host_email'" in text
    assert "'openemr_appt_status'" in text
    assert "op.drop_column('meeting_records', 'openemr_patient_id')" in text
    assert "op.drop_column('meeting_records', 'zoom_meeting_url')" in text
    assert "op.add_column('provider_mappings'" in text
    assert "'default_alternative_host_email'" in text


def test_meeting_patients_migration_creates_expected_table():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "9f2c1a7d4b6e_create_meeting_patients_table.py"
    )
    text = migration_path.read_text(encoding="utf-8")

    assert "op.create_table(" in text
    assert '"meeting_patients"' in text
    assert '"meeting_record_id"' in text
    assert '"openemr_patient_id"' in text
    assert '"created_at"' in text
    assert "sa.ForeignKeyConstraint(" in text
    assert '["meeting_records.id"]' in text
    assert 'ondelete="CASCADE"' in text
    assert 'op.drop_table("meeting_patients")' in text
