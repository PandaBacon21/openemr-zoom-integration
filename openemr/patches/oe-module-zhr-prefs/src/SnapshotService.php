<?php

namespace Zoomly\ZhrPrefs;

use OpenEMR\Common\Acl\AclMain;
use OpenEMR\Services\InsuranceService;
use OpenEMR\Services\ListService;
use OpenEMR\Services\PatientService;

/**
 * Read-only patient snapshot for the Schedule side panel.
 *
 * Composes OpenEMR's own services where one exists. Three blocks — vitals,
 * recent visits and messages — have no suitable service (VitalsService only
 * exposes a FHIR-shaped search, and there is no service for form_encounter
 * lists or pnotes), so those use sqlQuery() with bound parameters. That is
 * still OpenEMR's data layer, not a new connection.
 *
 * ACL mirrors interface/patient_file/summary/demographics.php exactly:
 * 'patients|demo' to view a patient at all, a per-patient squad check on top
 * of it, 'patients|med' for clinical data and 'patients|rx' for medications.
 * Blocks the caller is not entitled to are OMITTED rather than returned
 * empty, so the panel can never imply "no allergies recorded" when the real
 * answer is "you may not see them".
 */
class SnapshotService
{
    private const RECENT_VISIT_LIMIT = 5;
    private const MESSAGE_LIMIT = 5;

    private PatientService $patients;

    public function __construct()
    {
        $this->patients = new PatientService();
    }

    /**
     * @return array|null null when the caller may not view this patient
     */
    public function forPatient(int $pid): ?array
    {
        if ($pid <= 0 || !AclMain::aclCheckCore('patients', 'demo')) {
            return null;
        }

        $patient = $this->patients->findByPid($pid);
        if (empty($patient)) {
            return null;
        }

        // Per-patient squad restriction, applied on top of the patients ACL
        // just as the patient dashboard does. Without it this endpoint would
        // expose charts the user cannot open normally.
        if (!empty($patient['squad']) && !AclMain::aclCheckCore('squads', $patient['squad'])) {
            error_log("zhr_prefs | snapshot | status=denied | pid={$pid} | reason=squad");
            return null;
        }

        $clinical = AclMain::aclCheckCore('patients', 'med');

        $snapshot = [
            'patient' => $this->demographics($patient),
            'insurance' => $this->insurance($pid),
            'visits' => $this->recentVisits($pid),
            'messages' => $this->messages($pid),
        ];

        if ($clinical) {
            $snapshot['vitals'] = $this->vitals($pid);
            $snapshot['problems'] = $this->listBlock($pid, 'medical_problem');
            $snapshot['allergies'] = $this->listBlock($pid, 'allergy');
        }

        if (AclMain::aclCheckCore('patients', 'rx')) {
            $snapshot['medications'] = $this->listBlock($pid, 'medication');
        }

        return $snapshot;
    }

    private function demographics(array $patient): array
    {
        return [
            'pid' => $patient['pid'] ?? null,
            'name' => trim(($patient['fname'] ?? '') . ' ' . ($patient['lname'] ?? '')),
            'dob' => $patient['DOB'] ?? null,
            'sex' => $patient['sex'] ?? null,
            'phone' => $patient['phone_home'] ?? ($patient['phone_cell'] ?? null),
            'address' => trim(implode(' ', array_filter([
                $patient['street'] ?? '',
                $patient['city'] ?? '',
                $patient['state'] ?? '',
                $patient['postal_code'] ?? '',
            ]))),
        ];
    }

    private function insurance(int $pid): ?array
    {
        $insurance = (new InsuranceService())->getOneByPid($pid, 'primary');
        if (empty($insurance)) {
            return null;
        }

        return [
            'plan' => $insurance['plan_name'] ?? null,
            'policy' => $insurance['policy_number'] ?? null,
            'group' => $insurance['group_number'] ?? null,
            'subscriber' => trim(
                ($insurance['subscriber_fname'] ?? '') . ' ' . ($insurance['subscriber_lname'] ?? '')
            ),
        ];
    }

    /** Most recent vitals row. form_vitals.activity = 1 excludes deleted forms. */
    private function vitals(int $pid): ?array
    {
        $row = sqlQuery(
            "SELECT date, bps, bpd, pulse, respiration, temperature, oxygen_saturation, height, weight
               FROM form_vitals
              WHERE pid = ? AND activity = 1
           ORDER BY date DESC
              LIMIT 1",
            [$pid]
        );

        if (empty($row)) {
            return null;
        }

        return [
            'date' => $row['date'],
            'bp' => ($row['bps'] && $row['bpd']) ? $row['bps'] . '/' . $row['bpd'] : null,
            'pulse' => $row['pulse'] ?: null,
            'respiration' => $row['respiration'] ?: null,
            'temperature' => $row['temperature'] ?: null,
            'spo2' => $row['oxygen_saturation'] ?: null,
            'height' => $row['height'] ?: null,
            'weight' => $row['weight'] ?: null,
        ];
    }

    /**
     * Problems, allergies and medications all live in `lists` and differ only
     * by type, so one method serves all three.
     *
     * @return array<int, array{title: string, date: ?string}>
     */
    private function listBlock(int $pid, string $type): array
    {
        $rows = (new ListService())->getAll($pid, $type);
        $items = [];

        foreach ($rows ?: [] as $row) {
            $title = trim((string)($row['title'] ?? ''));
            if ($title === '') {
                continue;
            }
            $items[] = ['title' => $title, 'date' => $row['date'] ?? null];
        }

        return $items;
    }

    /** @return array<int, array{encounter: int, date: string, reason: ?string}> */
    private function recentVisits(int $pid): array
    {
        $result = sqlStatement(
            "SELECT encounter, date, reason
               FROM form_encounter
              WHERE pid = ?
           ORDER BY date DESC
              LIMIT " . self::RECENT_VISIT_LIMIT,
            [$pid]
        );

        $visits = [];
        while ($row = sqlFetchArray($result)) {
            $visits[] = [
                'encounter' => (int)$row['encounter'],
                'date' => $row['date'],
                'reason' => $row['reason'] ?: null,
            ];
        }

        return $visits;
    }

    /** @return array<int, array{date: string, title: ?string, body: string, user: ?string}> */
    private function messages(int $pid): array
    {
        $result = sqlStatement(
            "SELECT date, title, body, user
               FROM pnotes
              WHERE pid = ? AND deleted = 0 AND activity = 1
           ORDER BY date DESC
              LIMIT " . self::MESSAGE_LIMIT,
            [$pid]
        );

        $messages = [];
        while ($row = sqlFetchArray($result)) {
            $messages[] = [
                'date' => $row['date'],
                'title' => $row['title'] ?: null,
                'body' => (string)$row['body'],
                'user' => $row['user'] ?: null,
            ];
        }

        return $messages;
    }
}
