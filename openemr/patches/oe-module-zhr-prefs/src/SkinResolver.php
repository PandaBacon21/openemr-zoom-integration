<?php

namespace Zoomly\ZhrPrefs;

/**
 * Picks the active skin for the current request.
 *
 * Order: the user's own choice -> the install-wide default -> stock.
 *
 * Phase 1 reads only the user setting; the install default and the
 * "allow users to choose" toggle arrive with the settings page in Phase 2,
 * which is why getInstallDefault() is isolated behind its own method.
 */
class SkinResolver
{
    public const USER_SETTING_LABEL = 'zhr_skin';

    private SkinRegistry $registry;

    public function __construct(SkinRegistry $registry)
    {
        $this->registry = $registry;
    }

    public function resolve(?int $userId = null): Skin
    {
        $userId ??= (int)($_SESSION['authUserID'] ?? 0);

        $chosen = $this->getUserChoice($userId);
        if ($chosen !== null) {
            $skin = $this->registry->get($chosen);
            if ($skin !== null) {
                return $skin;
            }
            // A skin can be removed after a user has selected it.
            error_log("zhr_prefs | skin_resolver | status=fallback | user={$userId} | reason=unknown_skin | requested={$chosen}");
        }

        $default = $this->getInstallDefault();
        if ($default !== null) {
            $skin = $this->registry->get($default);
            if ($skin !== null) {
                return $skin;
            }
            error_log("zhr_prefs | skin_resolver | status=fallback | reason=unknown_default | requested={$default}");
        }

        return $this->registry->getStock();
    }

    private function getUserChoice(int $userId): ?string
    {
        if ($userId <= 0 || !$this->loadUserLibrary()) {
            return null;
        }

        $value = getUserSetting(self::USER_SETTING_LABEL, $userId);
        $value = is_string($value) ? trim($value) : '';

        return $value !== '' ? $value : null;
    }

    /**
     * Makes getUserSetting() available regardless of the calling page.
     *
     * interface/globals.php does NOT load library/user.inc.php — individual
     * pages require it ad hoc. The Patient Finder and Flow Board happen to;
     * the calendar does not. Relying on function_exists() alone therefore made
     * skin resolution depend on the host page's include order, which silently
     * dropped the skin on every page that had not already loaded the library.
     */
    private function loadUserLibrary(): bool
    {
        if (function_exists('getUserSetting')) {
            return true;
        }

        $userLib = ($GLOBALS['srcdir'] ?? '') . '/user.inc.php';
        if (!is_readable($userLib)) {
            error_log("zhr_prefs | skin_resolver | status=failed | reason=user_lib_unreadable | path={$userLib}");
            return false;
        }

        require_once $userLib;

        return function_exists('getUserSetting');
    }

    /**
     * Install-wide default. Phase 2 backs this with the module settings table;
     * until then every user falls through to stock unless they have chosen.
     */
    private function getInstallDefault(): ?string
    {
        return null;
    }
}
