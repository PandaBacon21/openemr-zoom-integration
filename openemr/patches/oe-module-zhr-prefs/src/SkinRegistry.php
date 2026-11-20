<?php

namespace Zoomly\ZhrPrefs;

/**
 * Discovers skins by scanning for <skins-dir>/<id>/skin.json.
 *
 * Adding a skin means adding a folder — no PHP changes. A manifest that fails
 * validation is skipped and logged rather than fataling the page, because a
 * malformed skin must never take OpenEMR down.
 */
class SkinRegistry
{
    public const STOCK_SKIN_ID = 'openemr-stock';

    /** Folder and manifest id must both match this. */
    private const ID_PATTERN = '/^[a-z0-9][a-z0-9-]*$/';

    private string $skinsDir;

    /** @var array<string, Skin>|null lazily built, cached per request */
    private ?array $skins = null;

    public function __construct(string $skinsDir)
    {
        $this->skinsDir = rtrim($skinsDir, DIRECTORY_SEPARATOR);
    }

    /** @return array<string, Skin> keyed by skin id */
    public function all(): array
    {
        if ($this->skins === null) {
            $this->skins = $this->discover();
        }
        return $this->skins;
    }

    public function has(string $id): bool
    {
        return isset($this->all()[$id]);
    }

    public function get(string $id): ?Skin
    {
        return $this->all()[$id] ?? null;
    }

    /**
     * The stock skin is guaranteed to exist: if its folder is missing or
     * broken we synthesise it, so resolution always has a floor to fall to.
     */
    public function getStock(): Skin
    {
        return $this->get(self::STOCK_SKIN_ID) ?? new Skin(
            self::STOCK_SKIN_ID,
            'Stock OpenEMR',
            "OpenEMR's default appearance.",
            '1.0.0',
            [],
            [],
            null
        );
    }

    /** @return array<string, Skin> */
    private function discover(): array
    {
        $found = [];

        if (!is_dir($this->skinsDir)) {
            error_log("zhr_prefs | skin_registry | status=failed | reason=skins_dir_missing | dir={$this->skinsDir}");
            return $found;
        }

        foreach ((array)scandir($this->skinsDir) as $entry) {
            if ($entry === '.' || $entry === '..') {
                continue;
            }

            $manifestPath = $this->skinsDir . DIRECTORY_SEPARATOR . $entry . DIRECTORY_SEPARATOR . 'skin.json';
            if (!is_file($manifestPath)) {
                continue;
            }

            $skin = $this->loadManifest($entry, $manifestPath);
            if ($skin !== null) {
                $found[$skin->getId()] = $skin;
            }
        }

        return $found;
    }

    private function loadManifest(string $folder, string $manifestPath): ?Skin
    {
        $raw = file_get_contents($manifestPath);
        if ($raw === false) {
            error_log("zhr_prefs | skin_registry | status=skipped | folder={$folder} | reason=manifest_unreadable");
            return null;
        }

        $data = json_decode($raw, true);
        if (!is_array($data)) {
            error_log("zhr_prefs | skin_registry | status=skipped | folder={$folder} | reason=manifest_not_json");
            return null;
        }

        $id = (string)($data['id'] ?? '');
        if (!preg_match(self::ID_PATTERN, $id)) {
            error_log("zhr_prefs | skin_registry | status=skipped | folder={$folder} | reason=invalid_id | id={$id}");
            return null;
        }

        // Folder name is the addressable identity; a mismatch would make asset
        // URLs point somewhere other than the manifest the registry served.
        if ($id !== $folder) {
            error_log("zhr_prefs | skin_registry | status=skipped | folder={$folder} | reason=id_folder_mismatch | id={$id}");
            return null;
        }

        $name = trim((string)($data['name'] ?? ''));
        if ($name === '') {
            error_log("zhr_prefs | skin_registry | status=skipped | folder={$folder} | reason=missing_name");
            return null;
        }

        return new Skin(
            $id,
            $name,
            (string)($data['description'] ?? ''),
            (string)($data['version'] ?? '0.0.0'),
            $this->relativePaths($data['css'] ?? [], $folder, 'css'),
            $this->relativePaths($data['js'] ?? [], $folder, 'js'),
            isset($data['preview']) ? (string)$data['preview'] : null
        );
    }

    /**
     * Keeps manifest-declared assets inside their own skin folder. Anything
     * absolute or containing a parent-dir hop is dropped and logged.
     *
     * @return string[]
     */
    private function relativePaths(mixed $paths, string $folder, string $kind): array
    {
        $clean = [];

        foreach ((array)$paths as $path) {
            $path = (string)$path;

            if ($path === '' || str_contains($path, '..') || str_starts_with($path, '/')) {
                error_log("zhr_prefs | skin_registry | status=skipped_asset | folder={$folder} | kind={$kind} | reason=unsafe_path | path={$path}");
                continue;
            }

            $clean[] = $path;
        }

        return $clean;
    }
}
