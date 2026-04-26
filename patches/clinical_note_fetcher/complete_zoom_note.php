<?php

/**
 * complete_zoom_note.php
 *
 * PHP proxy called when a SOAP or Clinical Notes form is eSigned and locked.
 * Notifies the Flask bridge to mark the associated Zoom clinical note as completed.
 *
 * Fire-and-forget — no response is shown to the user.
 * Called automatically on page load when a form is in locked state.
 *
 * Uses the same HMAC-SHA256 signing pattern as fetch_zoom_note.php and
 * AppointmentListener.php — secret pulled from OPENEMR_ZOOM_SECRET env var,
 * never exposed to the browser.
 *
 * Usage:
 *   POST /interface/patient_file/encounter/complete_zoom_note.php?encounter=123
 */

require_once(__DIR__ . "/../../globals.php");
require_once(__DIR__ . '/../../../library/zoomly/ZoomBridge.php');

use OpenEMR\Common\Acl\AclMain;

// --- 1. Verify OpenEMR session ---
if (!isset($_SESSION['authUserID'])) {
    http_response_code(401);
    exit;
}

// --- 2. Validate encounter parameter ---
$encounterNumber = isset($_GET['encounter']) ? (int)$_GET['encounter'] : 0;
if ($encounterNumber <= 0) {
    http_response_code(400);
    exit;
}

// --- 3. ACL check ---
if (!AclMain::aclCheckCore('clinical', 'notes', '', 'write')) {
    http_response_code(403);
    exit;
}

// --- 4. POST to Flask bridge ---
$result = zoomly_bridge_post('/zoom/encounter/' . $encounterNumber . '/complete_zoom_note');
 
if ($result['error']) {
    error_log('[complete_zoom_note] cURL error for encounter=' . $encounterNumber . ': ' . $result['error']);
}
 
if ($result['status'] > 0 && ($result['status'] < 200 || $result['status'] >= 300)) {
    error_log('[complete_zoom_note] Flask returned HTTP ' . $result['status'] . ' for encounter=' . $encounterNumber . '. Response: ' . substr($result['body'], 0, 500));
}
 
// Fire and forget — always return 200 to the browser regardless of Flask response.
// The provider has already eSigned; we don't want any error to disrupt their workflow.
http_response_code(200);