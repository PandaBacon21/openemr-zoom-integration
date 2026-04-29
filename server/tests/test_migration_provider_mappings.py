from pathlib import Path


def test_provider_mapping_migration_adds_openemr_provider_id_column():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "5ecd2a942ca3_current_schema_with_string_primary_keys.py"
    )
    text = migration_path.read_text(encoding="utf-8")

    assert "op.create_table('provider_mappings'" in text
    assert "'openemr_provider_id'" in text
    assert "sa.String(length=128)" in text
    assert "sa.ForeignKeyConstraint(['zoom_account_id'], ['zoom_accounts.account_id']" in text
    assert "op.drop_table('provider_mappings')" in text


def test_provider_mapping_migration_uses_string_zoom_account_fk():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "5ecd2a942ca3_current_schema_with_string_primary_keys.py"
    )
    text = migration_path.read_text(encoding="utf-8")

    assert "sa.Column('zoom_account_id', sa.String(length=128), nullable=False)" in text
    assert "op.create_index(op.f('ix_provider_mappings_zoom_account_id')" in text
