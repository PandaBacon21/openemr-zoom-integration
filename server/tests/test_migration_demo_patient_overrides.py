from pathlib import Path


def test_demo_patient_override_migration_adds_zoom_account_columns_only():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "5ecd2a942ca3_current_schema_with_string_primary_keys.py"
    )
    text = migration_path.read_text(encoding="utf-8")

    assert "op.create_table('zoom_accounts'" in text
    assert "sa.Column('demo_patient_email_override', sa.String(length=256), nullable=True)" in text
    assert "sa.Column('demo_patient_phone_override', sa.String(length=32), nullable=True)" in text
    assert "op.drop_table('zoom_accounts')" in text
