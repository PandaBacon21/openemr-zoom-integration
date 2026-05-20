from pathlib import Path
import re


def _demo_sql_text() -> str:
    repo_root = Path(__file__).resolve().parents[2]
    sql_path = repo_root / "seed_data" / "demo_data.sql"
    assert sql_path.exists(), f"Missing seed SQL file: {sql_path}"
    return sql_path.read_text(encoding="utf-8")


def _reset_script_text() -> str:
    repo_root = Path(__file__).resolve().parents[2]
    reset_path = repo_root / "seed_data" / "reset.sh"
    assert reset_path.exists(), f"Missing reset script file: {reset_path}"
    return reset_path.read_text(encoding="utf-8")


def _seed_script_text() -> str:
    repo_root = Path(__file__).resolve().parents[2]
    seed_path = repo_root / "seed_data" / "seed.sh"
    assert seed_path.exists(), f"Missing seed script file: {seed_path}"
    return seed_path.read_text(encoding="utf-8")


def _patient_insert_values(text: str) -> str:
    match = re.search(
        r"INSERT INTO `patient_data`\s*\(.*?\)\s*VALUES(?P<values>.*?);\n",
        text,
        flags=re.DOTALL,
    )
    assert match is not None, "Could not find patient_data INSERT statement"
    return match.group("values")


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


def test_seed_data_includes_users_secure_rows_for_staff_logins():
    text = _demo_sql_text()

    assert "INSERT INTO users_secure" in text
    for username in ["moconnor", "erodriguez", "amiller", "mthompson", "blee", "amartin", "bwilliams", "hsong"]:
        assert f"'{username}'" in text


def test_seed_data_includes_patient_portal_credentials_for_demo_patients():
    text = _demo_sql_text()

    assert "INSERT IGNORE INTO patient_access_onsite" in text
    for portal_username in [
        "james.harrison",
        "sofia.reyes",
        "david.kim",
        "rachel.nguyen",
        "carlos.mendez",
        "linda.whitaker",
    ]:
        assert f"'{portal_username}'" in text


def test_seed_data_uses_reserved_patient_email_addresses():
    text = _demo_sql_text()
    patient_values = _patient_insert_values(text)
    emails = re.findall(r"'([^']+@[^']+)'", patient_values)

    assert len(emails) == 51
    assert all(email.endswith("@example.org") for email in emails)


def test_seed_data_uses_only_reserved_example_email_addresses():
    text = _demo_sql_text()
    emails = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+", text)

    assert emails
    assert all(email.endswith("@example.org") for email in emails)


def test_seed_script_loads_demo_sql_without_email_override():
    text = _seed_script_text()

    assert "SEED_EMAIL" not in text
    assert "SEED_EMAIL_PLACEHOLDER" not in text
    assert "demo_data.sql" in text
    assert "docker exec -i" in text


def test_reset_script_cleans_up_new_demo_auth_tables():
    text = _reset_script_text()

    assert "DELETE FROM users_secure" in text
    assert "DELETE FROM patient_access_onsite" in text
    assert "DELETE FROM gacl_aro" in text
