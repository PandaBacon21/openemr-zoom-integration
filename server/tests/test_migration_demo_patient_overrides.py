from pathlib import Path


def test_demo_patient_override_migration_adds_zoom_account_columns_only():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "071951c50951_add_demo_patient_contact_overrides_to_.py"
    )
    text = migration_path.read_text(encoding="utf-8")

    assert "op.add_column('zoom_accounts', sa.Column('demo_patient_email_override'" in text
    assert "op.add_column('zoom_accounts', sa.Column('demo_patient_phone_override'" in text
    assert "op.drop_column('zoom_accounts', 'demo_patient_phone_override')" in text
    assert "op.drop_column('zoom_accounts', 'demo_patient_email_override')" in text
    assert "provider_mappings" not in text
