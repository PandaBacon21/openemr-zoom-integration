<?php

/**
 * fetch_zoom_note.php
 *
 * PHP proxy for the "Retrieve Zoom Note" button on the encounter page.
 *
 * Called by the browser via fetch() in forms.php.
 * Signs the request with HMAC-SHA256 and forwards it to the Flask bridge.
 * Returns the Flask response as JSON to the browser.
 * *
 * Usage:
 *   GET /interface/patient_file/encounter/fetch_zoom_note.php?encounter=123
 */

// OpenEMR bootstrap — required for session auth and globals.
// The path is standard across OpenEMR installs.
require_once(__DIR__ . "/../../globals.php");
require_once(__DIR__ . '/../../../library/zoomly/ZoomBridge.php');


// --- 1. Verify OpenEMR session ---
// Ensures only logged-in OpenEMR users can trigger this.
// top.restoreSession() in the JS keeps the session alive across form interactions.
if (!isset($_SESSION['authUserID'])) {
    http_response_code(401);
    echo json_encode(['error' => 'Not authenticated']);
    exit;
}

// --- 2. Validate encounter parameter ---
$encounterNumber = isset($_GET['encounter']) ? (int)$_GET['encounter'] : 0;
if ($encounterNumber <= 0) {
    http_response_code(400);
    echo json_encode(['error' => 'Invalid or missing encounter number']);
    exit;
}


// --- 3. POST to Flask bridge ---
$result = zoomly_bridge_post('/zoom/encounter/' . $encounterNumber . '/fetch_zoom_note');
 
// --- 4. Handle cURL errors ---
if ($result['error']) {
    error_log('[fetch_zoom_note] cURL error for encounter=' . $encounterNumber . ': ' . $result['error']);
    http_response_code(502);
    echo json_encode(['error' => 'Could not reach Zoom bridge: ' . $result['error']]);
    exit;
}
 
// --- 5. Forward Flask response to browser ---
// Pass the status code and body through directly.
// The JS in forms.php checks response.ok and reads data.error on failure.
http_response_code($result['status']);
header('Content-Type: application/json');
echo $result['body'];