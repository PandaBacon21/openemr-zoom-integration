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
 *   3. Signs the payload with HMAC-SHA256 using a shared secret
 *   4. POSTs to the Flask bridge webhook endpoint
 *
 * Module: zoom_appointment_listener
 */

namespace Zoomly\ZoomAppointmentListener;

use OpenEMR\Events\Appointments\AppointmentSetEvent;

class AppointmentListener
{
    /**
     * Endpoint on the Flask bridge service.
     * Uses internal Docker DNS — zoom-bridge is the compose service name.
     */
    private const WEBHOOK_URL = 'http://zoom-bridge:5000/webhooks/openemr';

    /**
     * Shared secret for HMAC-SHA256 request signing.
     * Must match WEBHOOK_SECRET in Flask app config.
     * Pulled from environment so it never lives in source code.
     */
    private function getWebhookSecret(): string
    {
        $secret = getenv('OPENEMR_WEBHOOK_SECRET');
        if (empty($secret)) {
            error_log('[ZoomAppointmentListener] OPENEMR_WEBHOOK_SECRET is not set');
            return '';
        }
        return $secret;
    }

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

        // form_hour is the hour component; form_minute is the minute.
        // Combine into HH:MM for readability.
        $hour   = isset($postData['form_hour'])   ? str_pad((int)$postData['form_hour'],   2, '0', STR_PAD_LEFT) : '00';
        $minute = isset($postData['form_minute']) ? str_pad((int)$postData['form_minute'], 2, '0', STR_PAD_LEFT) : '00';
        $appointmentTime = "{$hour}:{$minute}";

        // --- 2. Build the payload ---
        $payload = [
            'event'            => 'appointment.set',
            'eid'              => (int)$eid,
            'pid'              => !empty($postData['form_pid'])      ? (int)$postData['form_pid']      : null,
            'provider_id'      => $providerId,
            'category_id'      => !empty($postData['form_category']) ? (int)$postData['form_category'] : null,
            'appointment_date' => $appointmentDate,
            'appointment_time' => $appointmentTime,
            'appt_status'      => $postData['form_apptstatus'] ?? null,
            'facility_id'      => !empty($postData['facility'])      ? (int)$postData['facility']      : null,
            'comments'         => $postData['form_comments']         ?? null,
            // Timestamp lets Flask detect stale/replayed events if needed.
            'fired_at'         => (new \DateTime('now', new \DateTimeZone('UTC')))->format(\DateTime::ATOM),
        ];

        $payloadJson = json_encode($payload);
        if ($payloadJson === false) {
            error_log('[ZoomAppointmentListener] Failed to JSON-encode payload for eid=' . $eid);
            return;
        }

        // --- 3. Sign the payload ---
        $secret = $this->getWebhookSecret();
        if (empty($secret)) {
            // Log and bail — sending an unsigned request to Flask would be rejected anyway.
            error_log('[ZoomAppointmentListener] Cannot send webhook: missing secret. eid=' . $eid);
            return;
        }

        // HMAC-SHA256 over the raw JSON body.
        // Flask will recompute this from the received body and compare.
        $signature = hash_hmac('sha256', $payloadJson, $secret);

        // --- 4. POST to Flask ---
        $this->postToFlask($payloadJson, $signature, $eid);
    }

    /**
     * Sends the signed JSON payload to the Flask bridge using cURL.
     *
     * @param string $payloadJson  Raw JSON string
     * @param string $signature    HMAC-SHA256 hex digest
     * @param int    $eid          Appointment ID (for log context only)
     */
    private function postToFlask(string $payloadJson, string $signature, int $eid): void
    {
        $ch = curl_init(self::WEBHOOK_URL);

        curl_setopt_array($ch, [
            CURLOPT_POST           => true,
            CURLOPT_POSTFIELDS     => $payloadJson,
            CURLOPT_RETURNTRANSFER => true,
            // Generous timeout — Flask is on the same Docker network so this should
            // never be needed, but avoids hanging OpenEMR's request if bridge is down.
            CURLOPT_TIMEOUT        => 5,
            CURLOPT_CONNECTTIMEOUT => 3,
            CURLOPT_HTTPHEADER     => [
                'Content-Type: application/json',
                // Flask reads this header to verify the request origin.
                'X-Zoomly-Signature: ' . $signature,
            ],
        ]);

        $response   = curl_exec($ch);
        $httpStatus = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $curlError  = curl_error($ch);
        curl_close($ch);

        if ($curlError) {
            error_log(sprintf(
                '[ZoomAppointmentListener] cURL error for eid=%d: %s',
                $eid,
                $curlError
            ));
            return;
        }

        if ($httpStatus < 200 || $httpStatus >= 300) {
            error_log(sprintf(
                '[ZoomAppointmentListener] Flask returned HTTP %d for eid=%d. Response: %s',
                $httpStatus,
                $eid,
                substr((string)$response, 0, 500)  // cap log length
            ));
            return;
        }

        error_log(sprintf(
            '[ZoomAppointmentListener] Successfully delivered event for eid=%d (HTTP %d)',
            $eid,
            $httpStatus
        ));
    }
}