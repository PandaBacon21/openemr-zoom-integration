from pathlib import Path


def test_nickname_migration_adds_zoom_account_column():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "5ecd2a942ca3_current_schema_with_string_primary_keys.py"
    )
    text = migration_path.read_text(encoding="utf-8")

    assert "op.create_table('zoom_accounts'" in text
    assert "sa.Column('nickname'" in text
    assert "sa.String(length=128)" in text
    assert "op.drop_table('zoom_accounts')" in text


def test_ehr_auth_migration_adds_zoom_account_columns():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "585c85c5c79c_add_ehr_auth_fields_to_zoom_accounts.py"
    )
    text = migration_path.read_text(encoding="utf-8")

    assert "op.add_column('zoom_accounts', sa.Column('tenant_id'" in text
    assert "op.add_column('zoom_accounts', sa.Column('ehr_context_username'" in text
    assert "op.add_column('zoom_accounts', sa.Column('ehr_context_password_hash'" in text
