from pathlib import Path


def test_account_config_migration_moves_timezone_to_config_table():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "77ba73f9eedb_add_account_config_table_move_config_.py"
    )
    text = migration_path.read_text(encoding="utf-8")

    assert "op.create_table('account_configs'" in text
    assert "'timezone'" in text
    assert "sa.String(length=64)" in text
    assert "op.drop_column('zoom_accounts', 'timezone')" in text
