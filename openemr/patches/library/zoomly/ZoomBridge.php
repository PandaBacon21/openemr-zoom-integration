<?php

/**
 * ZoomBridge.php
 *
 * Shared helper for signing and sending requests from OpenEMR to the
 * Zoom bridge Flask application.
 *
 * Used by:
 *   - interface/patient_file/encounter/fetch_zoom_note.php
 *   - interface/patient_file/encounter/complete_zoom_note.php
 *   - interface/modules/custom_modules/zoom_appointment_listener/AppointmentListener.php
 *   - interface/modules/custom_modules/zoom_appointment_listener/DialogCloseListener.php
 *
 * All requests are signed with HMAC-SHA256 using the OPENEMR_FLASK_SECRET
 * environment variable. The signature is sent in the X-Zoomly-Signature header.
 * Flask verifies this on receipt.
 */

/**
 * Send a signed POST request to the Zoom bridge Flask app.
 *
 * @param string $path        Flask endpoint path, e.g. '/zoom/encounter/18/fetch_zoom_note'
 * @param string $payloadJson JSON string body. Use '{}' when there is no meaningful payload.
 * @param int    $timeout     cURL total timeout in seconds (default 10)
 *
 * @return array{status: int, body: string, error: string}
 *   status — HTTP response code (0 if cURL failed before connecting)
 *   body   — raw response body string
 *   error  — cURL error string, empty on success
 */
function zoomly_bridge_post(string $path, string $payloadJson = '{}', int $timeout = 10): array
{
    $secret = getenv('OPENEMR_FLASK_SECRET');
    if (empty($secret)) {
        error_log('[ZoomBridge] OPENEMR_FLASK_SECRET is not set');
        return ['status' => 0, 'body' => '', 'error' => 'missing secret'];
    }

    $signature = hash_hmac('sha256', $payloadJson, $secret);
    $url = 'http://zoom-bridge:5000' . $path;

    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_POST           => true,
        CURLOPT_POSTFIELDS     => $payloadJson,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT        => $timeout,
        CURLOPT_CONNECTTIMEOUT => 3,
        CURLOPT_HTTPHEADER     => [
            'Content-Type: application/json',
            'X-Zoomly-Signature: ' . $signature,
        ],
    ]);

    $body      = curl_exec($ch);
    $status    = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $curlError = curl_error($ch);
    curl_close($ch);

    return [
        'status' => $status,
        'body'   => (string)$body,
        'error'  => $curlError,
    ];
}