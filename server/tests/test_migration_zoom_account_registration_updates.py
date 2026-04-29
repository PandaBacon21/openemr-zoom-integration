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


def test_demo_patient_override_enabled_migration_adds_zoom_account_column():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "5ecd2a942ca3_current_schema_with_string_primary_keys.py"
    )
    text = migration_path.read_text(encoding="utf-8")

    assert "op.create_table('zoom_accounts'" in text
    assert "'demo_patient_override_enabled'" in text
    assert "sa.Boolean()" in text
    assert "server_default='0'" in text
    assert "nullable=False" in text
    assert "op.drop_table('zoom_accounts')" in text
