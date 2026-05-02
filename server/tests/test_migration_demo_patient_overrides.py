from pathlib import Path


def test_account_config_migration_moves_demo_patient_override_values():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "77ba73f9eedb_add_account_config_table_move_config_.py"
    )
    text = migration_path.read_text(encoding="utf-8")

    assert "op.create_table('account_configs'" in text
    assert "sa.Column('demo_patient_email_override', sa.String(length=256), nullable=True)" in text
    assert "sa.Column('demo_patient_phone_override', sa.String(length=32), nullable=True)" in text
    assert "op.drop_column('zoom_accounts', 'demo_patient_email_override')" in text
    assert "op.drop_column('zoom_accounts', 'demo_patient_phone_override')" in text


def test_demo_patient_override_split_migration_adds_separate_flags():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "d7de11bd0c97_split_demo_patient_override_enabled_.py"
    )
    text = migration_path.read_text(encoding="utf-8")

    assert "op.add_column('account_configs', sa.Column('demo_patient_email_override_enabled'" in text
    assert "op.add_column('account_configs', sa.Column('demo_patient_phone_override_enabled'" in text
    assert "op.drop_column('account_configs', 'demo_patient_override_enabled')" in text
