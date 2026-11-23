<?php

namespace Zoomly\ZhrPrefs;

/**
 * Picks the active skin for the current request.
 *
 * Order: the user's own choice -> the install-wide default -> stock.
 * PreferenceService owns the first two rungs (and the org-level lock on user
 * choice); this class owns only the fall back to stock.
 */
class SkinResolver
{
    private SkinRegistry $registry;
    private PreferenceService $preferences;

    public function __construct(SkinRegistry $registry, PreferenceService $preferences)
    {
        $this->registry = $registry;
        $this->preferences = $preferences;
    }

    public function resolve(?int $userId = null): Skin
    {
        $userId ??= (int)($_SESSION['authUserID'] ?? 0);

        $skinId = $this->preferences->effectiveSkinId($userId);
        $skin = $this->registry->get($skinId);
        if ($skin !== null) {
            return $skin;
        }

        // A skin folder can be removed after someone has selected it.
        error_log("zhr_prefs | skin_resolver | status=fallback | user={$userId} | reason=unknown_skin | requested={$skinId}");

        return $this->registry->getStock();
    }
}
