<?php

/**
 * AppointmentListener.php
 *
 * Handles the AppointmentSetEvent fired by OpenEMR whenever an appointment
 * is created or updated via add_edit_event.php.
 *
 * On event fire:
 *   1. Extracts appointment data from the event's $_POST payload
 *   2. Builds a structured JSON payload
 *   3. POSTs signed request to the Flask bridge webhook endpoint
 *
 * Module: zoom_appointment_listener
 */

namespace Zoomly\ZoomAppointmentListener;

use OpenEMR\Events\Appointments\AppointmentSetEvent;

require_once('/var/www/localhost/htdocs/openemr/library/zoomly/ZoomBridge.php');

class AppointmentListener
{
    /**
     * Event handler — called by Symfony when 'appointment.set' fires.
     *
     * @param AppointmentSetEvent $event
     */
    public function onAppointmentSet(AppointmentSetEvent $event): void
    {
        // --- 1. Extract data from the event ---
        // givenAppointmentData() returns the $_POST array captured at dispatch time.
        $postData = $event->givenAppointmentData();

        // $event->eid is the appointment ID, set explicitly in add_edit_event.php
        // after the DB insert/update resolves.
        $eid = $event->eid ?? null;

        if (empty($eid)) {
            // No appointment ID means the save failed upstream — nothing to do.
            error_log('[ZoomAppointmentListener] Event fired but eid is empty, skipping.');
            return;
        }

        // form_allday signals an all-day block (vacation, holiday, etc.).
        // These are never telehealth appointments — drop immediately.
        $isAllDay = !empty($postData['form_allday']) && $postData['form_allday'] === '1';
        if ($isAllDay) {
            error_log('[ZoomAppointmentListener] All-day event, skipping eid=' . $eid);
            return;
        }

        // form_provider can be a scalar or array (multi-provider appointments).
        // Normalize to array and take the first value for our 1:1 meeting model.
        $rawProvider = $postData['form_provider'] ?? null;
        if (is_array($rawProvider)) {
            $providerId = !empty($rawProvider) ? (int)$rawProvider[0] : null;
        } else {
            $providerId = !empty($rawProvider) ? (int)$rawProvider : null;
        }

        // form_date is already normalized to YYYYMMDD by add_edit_event.php line 81.
        $appointmentDate = $postData['form_date'] ?? null;

        // form_hour + form_minute give us the start time.
        // Both are padded to 2 digits and combined into HH:MM.
        $hour   = isset($postData['form_hour'])   ? str_pad((int)$postData['form_hour'],   2, '0', STR_PAD_LEFT) : '00';
        $minute = isset($postData['form_minute']) ? str_pad((int)$postData['form_minute'], 2, '0', STR_PAD_LEFT) : '00';
        $appointmentTime = "{$hour}:{$minute}";

        // form_duration is in minutes. Falls back to 30 if not set.
        // OpenEMR stores as seconds (duration * 60) but the form field is minutes.
        $durationMinutes = !empty($postData['form_duration']) ? abs((int)$postData['form_duration']) : 30;

        // --- 2. Build the payload ---
        $payload = [
            'event'            => 'appointment.set',
            'eid'              => (int)$eid,
            'pid'              => !empty($postData['form_pid'])        ? (int)$postData['form_pid']        : null,
            'provider_id'      => $providerId,
            'category_id'      => !empty($postData['form_category'])   ? (int)$postData['form_category']   : null,
            'appointment_date' => $appointmentDate,
            'appointment_time' => $appointmentTime,
            'duration_minutes' => $durationMinutes,
            'appt_status'      => $postData['form_apptstatus']         ?? null,
            'facility_id'      => !empty($postData['facility'])        ? (int)$postData['facility']        : null,
            // form_title is the appointment reason/chief complaint.
            // Used to populate the Zoom meeting topic.
            'title'            => !empty($postData['form_title'])      ? trim($postData['form_title'])      : null,
            // form_room is the exam room assignment.
            // Useful for the rooming workflow (MA/nurse alternative host flow).
            'room'             => !empty($postData['form_room'])       ? trim($postData['form_room'])       : null,
            'comments'         => !empty($postData['form_comments'])   ? trim($postData['form_comments'])   : null,
            // Timestamp lets Flask detect stale/replayed events if needed.
            'fired_at'         => (new \DateTime('now', new \DateTimeZone('UTC')))->format(\DateTime::ATOM),
        ];

        $payloadJson = json_encode($payload);
        if ($payloadJson === false) {
            error_log('[ZoomAppointmentListener] Failed to JSON-encode payload for eid=' . $eid);
            return;
        }

        // --- 3. POST to Flask bridge ---
        $result = zoomly_bridge_post('/webhooks/openemr', $payloadJson, 5);

        if ($result['error']) {
            error_log(sprintf(
                '[ZoomAppointmentListener] cURL error for eid=%d: %s',
                $eid,
                $result['error']
            ));
            return;
        }

        if ($result['status'] < 200 || $result['status'] >= 300) {
            error_log(sprintf(
                '[ZoomAppointmentListener] Flask returned HTTP %d for eid=%d. Response: %s',
                $result['status'],
                $eid,
                substr($result['body'], 0, 500)
            ));
            return;
        }

        error_log(sprintf(
            '[ZoomAppointmentListener] Successfully delivered event for eid=%d (HTTP %d)',
            $eid,
            $result['status']
        ));
    }
}