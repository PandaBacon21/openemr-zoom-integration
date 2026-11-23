<?php

namespace Zoomly\ZhrPrefs;

use OpenEMR\Services\Globals\UserSettingsService;

/**
 * Reads and writes preferences against OpenEMR's user_settings table.
 *
 * A row with setting_user = <id> is that user's own choice; a row with
 * setting_user = 0 is OpenEMR's global-default convention and is what we use
 * for the install-wide default. UserSettingsService::getUserSetting() already
 * resolves "user's row, else default row" in one query.
 *
 * Uses UserSettingsService directly rather than the library/user.inc.php
 * wrappers: the wrappers are @deprecated as of 7.0.3, and more importantly
 * interface/globals.php does not load that library, so depending on it made
 * resolution sensitive to the calling page's include order.
 */
class PreferenceService
{
    private const ORG_USER_ID = 0;

    private PreferenceCatalog $catalog;

    public function __construct(PreferenceCatalog $catalog)
    {
        $this->catalog = $catalog;
    }

    /**
     * What this user actually gets: own choice, else org default, else the
     * catalog's built-in default.
     */
    public function effectiveValue(string $key, int $userId): string
    {
        $own = $this->ownValue($key, $userId);
        if ($own !== null) {
            return $own;
        }

        return $this->orgDefault($key);
    }

    /**
     * This user's own stored value, or null if they have never chosen.
     *
     * Passing $defaultUser === $user collapses getUserSetting()'s
     * "(setting_user=? OR setting_user=?)" to this user alone, which is how we
     * distinguish "chose the default explicitly" from "has no preference".
     */
    public function ownValue(string $key, int $userId): ?string
    {
        if ($userId <= 0) {
            return null;
        }

        $value = UserSettingsService::getUserSetting($key, $userId, $userId);

        return is_string($value) && $value !== '' ? $value : null;
    }

    public function orgDefault(string $key): string
    {
        $value = UserSettingsService::getUserSetting($key, self::ORG_USER_ID, self::ORG_USER_ID);
        if (is_string($value) && $value !== '') {
            return $value;
        }

        $preference = $this->catalog->get($key);

        return $preference !== null ? $preference->getDefault() : '';
    }

    public function setForUser(string $key, string $value, int $userId): bool
    {
        $preference = $this->catalog->get($key);
        if ($userId <= 0 || $preference === null || !$preference->accepts($value)) {
            error_log("zhr_prefs | preference_service | status=rejected | key={$key} | user={$userId} | reason=invalid_value");
            return false;
        }

        // $createDefault MUST stay false. With the default of true,
        // setUserSetting() also writes a setting_user = 0 row, so saving one
        // person's preference would silently rewrite the install default for
        // everyone.
        UserSettingsService::setUserSetting($key, $value, $userId, false, true);

        return true;
    }

    /** Drops the user's own row so they fall back to the org default. */
    public function clearForUser(string $key, int $userId): void
    {
        if ($userId > 0) {
            UserSettingsService::removeUserSetting($key, $userId);
        }
    }

    public function setOrgDefault(string $key, string $value): bool
    {
        $preference = $this->catalog->get($key);
        if ($preference === null || !$preference->accepts($value)) {
            error_log("zhr_prefs | preference_service | status=rejected | key={$key} | scope=org | reason=invalid_value");
            return false;
        }

        UserSettingsService::setUserSetting($key, $value, self::ORG_USER_ID, false, true);

        return true;
    }

    public function userChoiceAllowed(): bool
    {
        return $this->orgDefault(PreferenceCatalog::ALLOW_USER_SKIN) !== '0';
    }

    /**
     * Skin resolution, including the org-level lock. When user choice is off,
     * the user's own row is ignored rather than deleted, so turning the toggle
     * back on restores everyone's previous selection.
     */
    public function effectiveSkinId(int $userId): string
    {
        if (!$this->userChoiceAllowed()) {
            return $this->orgDefault(PreferenceCatalog::SKIN);
        }

        return $this->effectiveValue(PreferenceCatalog::SKIN, $userId);
    }
}
