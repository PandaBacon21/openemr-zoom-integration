<?php

/**
 * Same-origin OpenEMR bridge for Epic-ZCC click-to-dial.
 *
 * Browser JavaScript cannot hold OPENEMR_FLASK_SECRET, so it posts here; this
 * PHP endpoint adds the logged-in OpenEMR user id and forwards the request to
 * Flask via ZoomBridge's HMAC-signed server-to-server helper.
 */

require_once(__DIR__ . '/../globals.php');
require_once(__DIR__ . '/../../library/zoomly/ZoomBridge.php');

header('Content-Type: application/json');

$rawBody = file_get_contents('php://input');
$payload = json_decode((string)$rawBody, true);
if (!is_array($payload)) {
    http_response_code(400);
    echo json_encode(['error' => 'invalid JSON']);
    exit;
}

$accountId = trim((string)($payload['account_id'] ?? ''));
$phone = trim((string)($payload['phone'] ?? ''));
$openemrUserId = isset($_SESSION['authUserID']) ? (string)$_SESSION['authUserID'] : '';

if ($accountId === '') {
    http_response_code(400);
    echo json_encode(['error' => 'missing account_id']);
    exit;
}
if ($phone === '') {
    http_response_code(400);
    echo json_encode(['error' => 'missing phone']);
    exit;
}
if ($openemrUserId === '') {
    http_response_code(401);
    echo json_encode(['error' => 'missing OpenEMR user']);
    exit;
}

$bridgePayload = [
    'phone' => $phone,
    'openemr_user_id' => $openemrUserId,
];

$openemrPatientId = trim((string)($payload['openemr_patient_id'] ?? ($_SESSION['pid'] ?? '')));
if ($openemrPatientId !== '') {
    $bridgePayload['openemr_patient_id'] = $openemrPatientId;
    $bridgePayload['patient_id_type'] = 'OPENEMR';
}

$patientName = trim((string)($payload['patient_name'] ?? ''));
if ($patientName !== '') {
    $bridgePayload['patient_name'] = $patientName;
}

$payloadJson = json_encode($bridgePayload);
if ($payloadJson === false) {
    http_response_code(500);
    echo json_encode(['error' => 'failed to encode payload']);
    exit;
}

$path = '/zoomly/' . rawurlencode($accountId) . '/interconnect-amcurprd-oauth/cti/initiate-call';
$result = zoomly_bridge_post($path, $payloadJson, 10);

if ((int)$result['status'] <= 0) {
    http_response_code(502);
    echo json_encode(['error' => 'bridge request failed']);
    exit;
}

http_response_code((int)$result['status']);
echo $result['body'] !== '' ? $result['body'] : json_encode(['status' => 'empty']);
