from pathlib import Path
import re


def _demo_sql_text() -> str:
    repo_root = Path(__file__).resolve().parents[2]
    sql_path = repo_root / "seed_data" / "demo_data.sql"
    assert sql_path.exists(), f"Missing seed SQL file: {sql_path}"
    return sql_path.read_text(encoding="utf-8")


def test_users_insert_includes_npi_column():
    text = _demo_sql_text()

    match = re.search(
        r"INSERT INTO `users`\s*\((?P<columns>.*?)\)\s*VALUES",
        text,
        flags=re.DOTALL,
    )
    assert match is not None, "Could not find users INSERT statement"
    columns = match.group("columns")

    assert "`npi`" in columns


def test_provider_seed_rows_include_expected_npi_values():
    text = _demo_sql_text()

    expected_npis = {
        "1234567890",
        "1234567891",
        "1234567892",
        "1234567893",
    }

    for npi in expected_npis:
        assert f"'{npi}'" in text, f"Expected NPI {npi} not found in demo_data.sql"
