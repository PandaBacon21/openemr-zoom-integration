<?php

/**
 * Veradigm nav icon (top-right of the OpenEMR nav bar, next to the CTI panel).
 *
 * Renders only for provider-mapped users ($_SESSION['zoomly_is_provider'] set
 * by veradigm_nav_inject.php). Links to Flask's /veradigm/launch with signed
 * params (openemr_user_id + timestamp, HMAC-SHA256 over "<user>:<ts>" with
 * OPENEMR_FLASK_SECRET). The link is cross-origin (browser -> public bridge
 * host), so it uses ZOOMLY_BRIDGE_PUBLIC_URL. /veradigm/launch verifies the
 * signature, sets the veradigm_session cookie, and redirects to the external
 * appointment page in the new tab.
 */

// zhr_show_veradigm is the per-user toggle on the Demo Preferences page
// (Zoomly\ZhrPrefs\PreferenceCatalog::SHOW_VERADIGM). The literal key is used
// rather than the class constant so this patch keeps working if the ZHR Prefs
// module is ever disabled; a test asserts the two strings stay in sync.
// An absent row means "show", so only an explicit '0' hides the icon.
$veradigmPrefValue = \OpenEMR\Services\Globals\UserSettingsService::getUserSetting(
    'zhr_show_veradigm',
    (int)($_SESSION['authUserID'] ?? 0),
    0
);

if (!empty($_SESSION['zoomly_is_provider']) && $veradigmPrefValue !== '0'):
    $veradigmBridgeBase = rtrim(getenv('ZOOMLY_BRIDGE_PUBLIC_URL') ?: '', '/');
    $veradigmUserId = isset($_SESSION['authUserID']) ? (string)$_SESSION['authUserID'] : '';
    $veradigmSecret = getenv('OPENEMR_FLASK_SECRET') ?: '';

    if ($veradigmBridgeBase !== '' && $veradigmUserId !== '' && $veradigmSecret !== ''):
        $veradigmTs = (string)time();
        $veradigmSig = hash_hmac('sha256', $veradigmUserId . ':' . $veradigmTs, $veradigmSecret);
        $veradigmLaunchUrl = $veradigmBridgeBase . '/veradigm/launch'
            . '?u=' . urlencode($veradigmUserId)
            . '&ts=' . urlencode($veradigmTs)
            . '&sig=' . urlencode($veradigmSig);
        ?>
        <a href="<?php echo attr($veradigmLaunchUrl); ?>"
           target="_blank" rel="noopener noreferrer"
           class="btn btn-secondary"
           style="width:2rem;height:2rem;padding:0;margin-left:0.5rem;display:inline-flex;align-items:center;justify-content:center;font-weight:700;line-height:1;"
           title="<?php echo xla('Veradigm Appointments'); ?>"
           aria-label="<?php echo xla('Veradigm Appointments'); ?>">
            <span aria-hidden="true">V</span>
        </a>
        <?php
    endif;
endif;
