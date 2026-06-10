<?php

/**
 * Emits the browser bootstrap payload for Epic-ZCC screen-pop subscriptions.
 *
 * This file runs inside OpenEMR's authenticated main.php. It sends the current
 * OpenEMR user id to Flask using the existing HMAC-signed ZoomBridge helper.
 * Flask returns one SSE stream URL per active ZCC-agent account mapping.
 */

require_once(__DIR__ . '/../../library/zoomly/ZoomBridge.php');

$zoomlyEpicCtiStreams = [];
$zoomlyEpicCtiUserId = isset($_SESSION['authUserID']) ? (string)$_SESSION['authUserID'] : '';

if ($zoomlyEpicCtiUserId !== '') {
    $payloadJson = json_encode(['openemr_user_id' => $zoomlyEpicCtiUserId]);
    if ($payloadJson === false) {
        error_log('[ZoomlyEpicCti] Failed to encode screen-pop bootstrap payload');
    } else {
        $result = zoomly_bridge_post('/zoomly/epic-zcc/screenpop/bootstrap', $payloadJson, 3);
        if ((int)$result['status'] === 200) {
            $decoded = json_decode($result['body'], true);
            if (is_array($decoded) && is_array($decoded['streams'] ?? null)) {
                $zoomlyEpicCtiStreams = $decoded['streams'];
            } else {
                error_log('[ZoomlyEpicCti] Bootstrap response did not contain streams');
            }
        } elseif ((int)$result['status'] > 0) {
            error_log('[ZoomlyEpicCti] Bootstrap failed with HTTP ' . (int)$result['status']);
        } else {
            error_log('[ZoomlyEpicCti] Bootstrap request failed: ' . ($result['error'] ?: 'unknown error'));
        }
    }
}

$zoomlyEpicCtiConfig = [
    'openemrUserId' => $zoomlyEpicCtiUserId,
    'streams' => $zoomlyEpicCtiStreams,
];
?>
<script>
window.ZoomlyEpicCti = <?php echo json_encode($zoomlyEpicCtiConfig, JSON_HEX_TAG | JSON_HEX_AMP | JSON_HEX_APOS | JSON_HEX_QUOT | JSON_UNESCAPED_SLASHES); ?>;
</script>
