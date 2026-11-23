"""Static wiring checks for the ZHR Prefs OpenEMR module (skin framework).

The module is PHP, so there is no unit-test harness for its classes here. What
these tests protect is the wiring that is easy to get silently wrong: a skin
folder whose manifest id drifts from its directory name, a manifest pointing at
an asset that does not exist, or a module that stops being delivered because a
Dockerfile COPY or the modules-table INSERT was dropped.
"""

import json
from pathlib import Path

import pytest

MODULE_DIR_NAME = "oe-module-zhr-prefs"


def _repo_root() -> Path | None:
    """The repo root on the host, or None inside the zoom-bridge container.

    The container flattens server/ to /app and mounts only seed_data and
    openemr/patches, so repo-root files (Dockerfile, compose) are unreachable
    there. See TD-04 in CLAUDE.md.
    """
    root = Path(__file__).resolve().parents[2]
    return root if (root / "docker-compose.yml").is_file() else None


def _require_repo_root() -> Path:
    root = _repo_root()
    if root is None:
        pytest.skip("repo root is not mounted in this environment (TD-04)")
    return root


def _patches_dir() -> Path:
    """openemr/patches/ on the host; the container mounts it at /patches."""
    candidates = [
        Path(__file__).resolve().parents[2] / "openemr" / "patches",
        Path("/patches"),
    ]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    raise AssertionError(f"Could not locate openemr/patches; tried {candidates}")


def _module_root() -> Path:
    module_root = _patches_dir() / MODULE_DIR_NAME
    assert module_root.is_dir(), f"Missing module directory: {module_root}"
    return module_root


def _skin_dirs() -> list[Path]:
    skins_dir = _module_root() / "public" / "skins"
    assert skins_dir.is_dir(), f"Missing skins directory: {skins_dir}"
    dirs = sorted(p for p in skins_dir.iterdir() if p.is_dir())
    assert dirs, f"No skin folders found in {skins_dir}"
    return dirs


def _manifest(skin_dir: Path) -> dict:
    manifest_path = skin_dir / "skin.json"
    assert manifest_path.is_file(), f"Missing manifest: {manifest_path}"
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def test_module_ships_bootstrap_and_core_classes():
    module_root = _module_root()

    assert (module_root / "openemr.bootstrap.php").is_file()
    for class_name in ("Bootstrap", "Skin", "SkinRegistry", "SkinResolver", "SkinAssetInjector"):
        assert (module_root / "src" / f"{class_name}.php").is_file(), (
            f"Missing src/{class_name}.php"
        )


def test_bootstrap_registers_psr4_namespace():
    text = (_module_root() / "openemr.bootstrap.php").read_text(encoding="utf-8")

    # Guard clause must come before anything touches $classLoader.
    assert "if (!isset($eventDispatcher) || !isset($classLoader))" in text
    assert "registerNamespaceIfNotExists" in text
    assert "Zoomly\\\\ZhrPrefs\\\\" in text


def test_stock_skin_exists_and_injects_nothing():
    """The stock skin is the control case: selecting it must be a no-op."""
    skins_dir = _module_root() / "public" / "skins"
    manifest = _manifest(skins_dir / "openemr-stock")

    assert manifest["id"] == "openemr-stock"
    assert manifest["css"] == []
    assert manifest["js"] == []


def test_every_skin_manifest_id_matches_its_folder():
    """SkinRegistry rejects a mismatch at runtime; catch it at commit time."""
    for skin_dir in _skin_dirs():
        manifest = _manifest(skin_dir)
        assert manifest["id"] == skin_dir.name, (
            f"skin.json id {manifest['id']!r} does not match folder {skin_dir.name!r}"
        )
        assert manifest.get("name", "").strip(), f"{skin_dir.name}: manifest needs a name"


def test_every_declared_asset_exists_and_stays_inside_its_skin():
    for skin_dir in _skin_dirs():
        manifest = _manifest(skin_dir)
        for key in ("css", "js"):
            for relative in manifest.get(key, []):
                assert not relative.startswith("/"), (
                    f"{skin_dir.name}: {key} path {relative!r} must be relative"
                )
                assert ".." not in relative, (
                    f"{skin_dir.name}: {key} path {relative!r} must not escape the skin folder"
                )
                assert (skin_dir / relative).is_file(), (
                    f"{skin_dir.name}: {key} path {relative!r} does not exist"
                )


def test_skin_css_is_scoped_under_the_skin_attribute():
    """No unscoped selectors — stock must render identically to today."""
    for skin_dir in _skin_dirs():
        selector = f'html[data-zhr-skin="{skin_dir.name}"]'
        for css_path in sorted(skin_dir.rglob("*.css")):
            for line in css_path.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                # Only inspect lines that open a rule block.
                if not stripped.endswith("{") or stripped.startswith(("@", "/*", "*")):
                    continue
                assert selector in stripped, (
                    f"{css_path.name}: unscoped selector {stripped!r}; "
                    f"every rule must live under {selector}"
                )


def _settings_page() -> str:
    path = _module_root() / "public" / "settings.php"
    assert path.is_file(), f"Missing settings page: {path}"
    return path.read_text(encoding="utf-8")


def test_settings_page_verifies_csrf_on_every_post():
    text = _settings_page()

    assert "CsrfUtils::verifyCsrfToken" in text
    assert "CsrfUtils::collectCsrfToken" in text
    # Both forms must carry the token, not just the first one.
    assert text.count('name="csrf_token_form"') >= 2


def test_settings_page_rechecks_admin_acl_server_side():
    """The Admin menu entry only hides the link; the POST must be refused."""
    text = _settings_page()

    assert "AclMain::aclCheckCore('admin', 'super')" in text
    assert "http_response_code(403)" in text


def test_user_scoped_writes_never_create_the_org_default_row():
    """setUserSetting's $createDefault defaults to true, which would let one
    user's save silently rewrite the install-wide default for everyone."""
    text = (_module_root() / "src" / "PreferenceService.php").read_text(encoding="utf-8")

    assert "setUserSetting($key, $value, $userId, false, true)" in text
    assert "setUserSetting($key, $value, self::ORG_USER_ID, false, true)" in text
    assert "setUserSetting($key, $value, $userId, true" not in text


def test_menu_listener_attaches_to_real_parent_menu_ids():
    text = (_module_root() / "src" / "MenuListener.php").read_text(encoding="utf-8")

    # Verified against interface/main/tabs/menu/menus/standard.json.
    assert "'misimg'" in text, "Miscellaneous parent menu id"
    assert "'admimg'" in text, "Admin parent menu id"
    assert "['admin', 'super']" in text, "Admin entry must carry an ACL requirement"


def test_veradigm_patch_key_matches_the_catalog_constant():
    """The patch uses the literal key so it survives the module being
    disabled; this guards the two copies against drifting apart."""
    catalog = (_module_root() / "src" / "PreferenceCatalog.php").read_text(encoding="utf-8")
    patch = (_patches_dir() / "veradigm" / "veradigm_nav_button.php").read_text(encoding="utf-8")

    assert "const SHOW_VERADIGM = 'zhr_show_veradigm';" in catalog
    assert "'zhr_show_veradigm'" in patch
    # Absent row must mean "show", so the gate tests for an explicit '0'.
    assert "$veradigmPrefValue !== '0'" in patch


def test_skin_resolver_no_longer_depends_on_include_order():
    """Phase 1 required library/user.inc.php by hand because globals.php does
    not load it. UserSettingsService is autoloaded, so the hack is gone."""
    text = (_module_root() / "src" / "SkinResolver.php").read_text(encoding="utf-8")

    assert "loadUserLibrary" not in text
    assert "user.inc.php" not in text


def test_dockerfile_delivers_the_module():
    text = (_require_repo_root() / "openemr" / "Dockerfile").read_text(encoding="utf-8")

    assert f"openemr/patches/{MODULE_DIR_NAME}/" in text
    assert f"custom_modules/{MODULE_DIR_NAME}/" in text
    # Recursive COPY flattens perms; the find/chmod pair restores 755 dirs, 644 files.
    assert "-type d -exec chmod 755" in text
    assert "-type f -exec chmod 644" in text


def test_compose_registers_and_activates_the_module():
    text = (_require_repo_root() / "docker-compose.yml").read_text(encoding="utf-8")

    assert f"SELECT 1 FROM modules WHERE mod_directory = '{MODULE_DIR_NAME}'" in text, (
        "modules-table INSERT must stay guarded so re-runs are idempotent"
    )
    assert f"UPDATE modules SET mod_active = 1 WHERE mod_directory = '{MODULE_DIR_NAME}'" in text


def test_dev_override_template_mounts_the_module_directory():
    """A directory mount survives a git checkout; single-file mounts do not."""
    text = (_require_repo_root() / "docker-compose.override.yml.example").read_text(encoding="utf-8")

    assert f"./openemr/patches/{MODULE_DIR_NAME}:" in text
    assert f"custom_modules/{MODULE_DIR_NAME}" in text
