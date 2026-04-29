from pathlib import Path


def test_timezone_migration_adds_expected_column():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "5ecd2a942ca3_current_schema_with_string_primary_keys.py"
    )
    text = migration_path.read_text(encoding="utf-8")

    assert "op.create_table('zoom_accounts'" in text
    assert "'timezone'" in text
    assert "sa.String(length=64)" in text
