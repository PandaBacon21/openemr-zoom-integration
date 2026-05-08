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


def test_account_config_migration_adds_note_writeback_mode():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "8e1a97239ec2_add_note_writeback_mode_to_account_.py"
    )
    text = migration_path.read_text(encoding="utf-8")

    assert "op.add_column('account_configs', sa.Column('note_writeback_mode'" in text
    assert "sa.String(length=32)" in text
    assert "server_default='both'" in text
    assert "nullable=False" in text
    assert "op.drop_column('account_configs', 'note_writeback_mode')" in text
