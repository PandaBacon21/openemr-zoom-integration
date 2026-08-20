<?php

/**
 * Veradigm nav-icon bootstrap.
 *
 * Runs inside OpenEMR's authenticated main.php <head>. Sends the logged-in
 * OpenEMR user id to Flask via the HMAC-signed ZoomBridge helper. Flask replies
 * whether that user has an active provider-role UserMapping; if so, the
 * top-right Veradigm nav icon renders (see veradigm_nav_button.php).
 *
 * Mirrors the epic_cti/cti_subscriber_inject.php bootstrap pattern.
 */

require_once(__DIR__ . '/../../library/zoomly/ZoomBridge.php');

$zoomlyVeradigmIsProvider = false;
$zoomlyVeradigmUserId = isset($_SESSION['authUserID']) ? (string)$_SESSION['authUserID'] : '';

if ($zoomlyVeradigmUserId !== '') {
    $payloadJson = json_encode(['openemr_user_id' => $zoomlyVeradigmUserId]);
    if ($payloadJson === false) {
        error_log('[ZoomlyVeradigm] Failed to encode nav bootstrap payload');
    } else {
        $result = zoomly_bridge_post('/veradigm/nav-bootstrap', $payloadJson, 3);
        if ((int)$result['status'] === 200) {
            $decoded = json_decode($result['body'], true);
            if (is_array($decoded) && !empty($decoded['is_provider'])) {
                $zoomlyVeradigmIsProvider = true;
            }
        } elseif ((int)$result['status'] > 0) {
            error_log('[ZoomlyVeradigm] Nav bootstrap failed with HTTP ' . (int)$result['status']);
        } else {
            error_log('[ZoomlyVeradigm] Nav bootstrap request failed: ' . ($result['error'] ?: 'unknown error'));
        }
    }
}

$_SESSION['zoomly_is_provider'] = $zoomlyVeradigmIsProvider ? 1 : 0;
