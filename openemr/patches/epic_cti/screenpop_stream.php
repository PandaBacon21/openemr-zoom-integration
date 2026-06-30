<?php
/**
 * Same-origin SSE proxy for Epic-ZCC screen-pop events.
 *
 * OpenEMR's CSP restricts connect-src to the same origin, so the browser
 * cannot open an EventSource directly to the Flask bridge host. This proxy
 * relays the SSE stream from Flask over Docker-internal networking so the
 * browser connects to the OpenEMR host (same origin, no CSP issue).
 *
 * Auth is delegated to Flask — token, expires, account_id, and
 * openemr_user_id are passed through unchanged and verified by Flask's
 * screenpop_stream endpoint.
 */

// Release any output buffering before setting SSE headers.
while (ob_get_level() > 0) {
    ob_end_clean();
}

header('Content-Type: text/event-stream; charset=utf-8');
header('Cache-Control: no-cache');
header('X-Accel-Buffering: no');

$accountId = trim((string)($_GET['account_id'] ?? ''));
$userId    = trim((string)($_GET['openemr_user_id'] ?? ''));
$expires   = trim((string)($_GET['expires'] ?? ''));
$token     = trim((string)($_GET['token'] ?? ''));

if ($accountId === '' || $userId === '' || $expires === '' || $token === '') {
    echo "event: error\ndata: {\"error\":\"missing_params\"}\n\n";
    flush();
    exit;
}

$params = http_build_query([
    'openemr_user_id' => $userId,
    'expires'         => $expires,
    'token'           => $token,
]);

$url = 'http://zoom-bridge:5000/zoomly/'
    . rawurlencode($accountId)
    . '/interconnect-amcurprd-oauth/screenpop/stream?'
    . $params;

// Keep PHP alive after browser disconnects so cURL can clean up.
ignore_user_abort(true);

$ch = curl_init($url);
curl_setopt_array($ch, [
    CURLOPT_RETURNTRANSFER => false,
    CURLOPT_WRITEFUNCTION  => function ($ch, $data) {
        if (connection_aborted()) {
            return 0; // tells cURL to abort the transfer
        }
        echo $data;
        flush();
        return strlen($data);
    },
    CURLOPT_TIMEOUT        => 0,   // no timeout — SSE is long-lived
    CURLOPT_CONNECTTIMEOUT => 5,
    CURLOPT_FOLLOWLOCATION => false,
]);

curl_exec($ch);
curl_close($ch);
