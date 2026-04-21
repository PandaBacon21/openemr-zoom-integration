from pathlib import Path


def test_provider_mapping_migration_adds_openemr_provider_id_column():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "bc1e2fb3b8be_add_openemr_provider_id_to_provider_.py"
    )
    text = migration_path.read_text(encoding="utf-8")

    assert "op.add_column('provider_mappings'" in text
    assert "'openemr_provider_id'" in text
    assert "sa.Integer()" in text
    assert "op.drop_column('provider_mappings', 'openemr_provider_id')" in text


def test_provider_mapping_migration_changes_openemr_provider_id_to_string():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "21edaf7095b0_change_openemr_provider_id_to_string_on_.py"
    )
    text = migration_path.read_text(encoding="utf-8")

    assert "with op.batch_alter_table('provider_mappings')" in text
    assert "'openemr_provider_id'" in text
    assert "existing_type=sa.INTEGER()" in text
    assert "type_=sa.String(length=128)" in text
    assert "existing_type=sa.String(length=128)" in text
    assert "type_=sa.INTEGER()" in text
