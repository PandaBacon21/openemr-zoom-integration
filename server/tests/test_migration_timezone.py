from pathlib import Path


def test_timezone_migration_adds_expected_column():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "a1b2c3d4e5f6_add_timezone_to_zoom_accounts.py"
    )
    text = migration_path.read_text(encoding="utf-8")

    assert "op.add_column" in text
    assert "'zoom_accounts'" in text
    assert "'timezone'" in text
    assert "sa.String(64)" in text
    assert "server_default='America/New_York'" in text
