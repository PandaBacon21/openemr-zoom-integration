"""Archaeology check on the Sprint 6 schema migration (5ecd2a942ca3).

The test names and content reference `provider_mappings` / `openemr_provider_id`
because that's the historical schema the migration created. Sprint 11 (S11-01)
renamed the table to `user_mappings` and the column to `openemr_user_id` in a
later migration (fadc607b7921). The old migration file is frozen history; this
test asserts it still says what it always said.
"""

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
