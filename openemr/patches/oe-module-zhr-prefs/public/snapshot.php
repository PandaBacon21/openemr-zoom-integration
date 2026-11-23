<?php

/**
 * Patient snapshot for the Schedule side panel.
 *
 * GET ?pid=<int> -> JSON. Read-only; no state is changed, so there is no CSRF
 * token. Authentication comes from the OpenEMR session that globals.php
 * establishes, and authorisation is enforced inside SnapshotService, which
 * mirrors the patient dashboard's ACL rules.
 */

namespace Zoomly\ZhrPrefs;

require_once(__DIR__ . '/../../../../globals.php');

header('Content-Type: application/json');

// Deliberately strict: anything that is not a positive integer is rejected
// rather than coerced, so "0", "abc" and "12 OR 1=1" all fail here.
$pid = filter_input(INPUT_GET, 'pid', FILTER_VALIDATE_INT, ['options' => ['min_range' => 1]]);
if ($pid === false || $pid === null) {
    http_response_code(400);
    echo json_encode(['error' => 'invalid_pid']);
    exit;
}

$snapshot = (new SnapshotService())->forPatient($pid);

// A null result means the caller may not view this patient. The response is
// identical whether the patient does not exist or is merely out of reach, so
// the endpoint cannot be used to probe which PIDs are real.
if ($snapshot === null) {
    http_response_code(403);
    echo json_encode(['error' => 'forbidden']);
    exit;
}

echo json_encode($snapshot);
