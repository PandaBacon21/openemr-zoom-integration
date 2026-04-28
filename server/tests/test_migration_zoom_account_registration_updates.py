from pathlib import Path


def test_nickname_migration_adds_zoom_account_column():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "7332ab195d90_add_nickname_to_zoom_account.py"
    )
    text = migration_path.read_text(encoding="utf-8")

    assert "op.add_column('zoom_accounts', sa.Column('nickname'" in text
    assert "sa.String(length=128)" in text
    assert "op.drop_column('zoom_accounts', 'nickname')" in text


def test_demo_patient_override_enabled_migration_adds_zoom_account_column():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "ab343facf737_add_demo_patient_override_enabled_to_.py"
    )
    text = migration_path.read_text(encoding="utf-8")

    assert "op.add_column('zoom_accounts'" in text
    assert "'demo_patient_override_enabled'" in text
    assert "sa.Boolean()" in text
    assert "server_default='0'" in text
    assert "nullable=False" in text
    assert "op.drop_column('zoom_accounts', 'demo_patient_override_enabled')" in text
