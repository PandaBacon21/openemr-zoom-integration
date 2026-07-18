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

if (!empty($_SESSION['zoomly_is_provider'])):
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
