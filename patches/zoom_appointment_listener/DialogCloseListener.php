<?php

/**
 * DialogCloseListener.php
 *
 * Handles the AppointmentDialogCloseEvent fired by OpenEMR when the
 * appointment dialog closes after any action (save, duplicate, delete).
 *
 * We only care about the 'delete' action — save/duplicate are handled
 * by AppointmentListener via AppointmentSetEvent.
 *
 * On delete:
 *   1. Extracts eid from the event
 *   2. Builds a signed delete payload
 *   3. POSTs to Flask bridge webhook endpoint
 *
 * Module: zoom_appointment_listener
 */

namespace Zoomly\ZoomAppointmentListener;

use OpenEMR\Events\Appointments\AppointmentDialogCloseEvent;

class DialogCloseListener
{
    private const WEBHOOK_URL = 'http://zoom-bridge:5000/webhooks/openemr';

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
     * Event handler — called by Symfony when appointment dialog closes.
     *
     * @param AppointmentDialogCloseEvent $event
     */
    public function onDialogClose(AppointmentDialogCloseEvent $event): void
    {
        // Only handle delete actions — ignore save/duplicate
        if ($event->getDialogAction() !== 'delete') {
            return;
        }

        $eid = $event->getAppointmentId();
        if (empty($eid)) {
            error_log('[ZoomAppointmentListener] Delete event fired but eid is empty, skipping.');
            return;
        }

        $payload = [
            'event'    => 'appointment.deleted',
            'eid'      => (int)$eid,
            'fired_at' => (new \DateTime('now', new \DateTimeZone('UTC')))->format(\DateTime::ATOM),
        ];

        $payloadJson = json_encode($payload);
        if ($payloadJson === false) {
            error_log('[ZoomAppointmentListener] Failed to JSON-encode delete payload for eid=' . $eid);
            return;
        }

        $secret = $this->getWebhookSecret();
        if (empty($secret)) {
            error_log('[ZoomAppointmentListener] Cannot send delete webhook: missing secret. eid=' . $eid);
            return;
        }

        $signature = hash_hmac('sha256', $payloadJson, $secret);
        $this->postToFlask($payloadJson, $signature, $eid);
    }

    private function postToFlask(string $payloadJson, string $signature, int $eid): void
    {
        $ch = curl_init(self::WEBHOOK_URL);

        curl_setopt_array($ch, [
            CURLOPT_POST           => true,
            CURLOPT_POSTFIELDS     => $payloadJson,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_TIMEOUT        => 5,
            CURLOPT_CONNECTTIMEOUT => 3,
            CURLOPT_HTTPHEADER     => [
                'Content-Type: application/json',
                'X-Zoomly-Signature: ' . $signature,
            ],
        ]);

        $response   = curl_exec($ch);
        $httpStatus = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $curlError  = curl_error($ch);
        curl_close($ch);

        if ($curlError) {
            error_log(sprintf(
                '[ZoomAppointmentListener] cURL error for delete eid=%d: %s',
                $eid, $curlError
            ));
            return;
        }

        if ($httpStatus < 200 || $httpStatus >= 300) {
            error_log(sprintf(
                '[ZoomAppointmentListener] Flask returned HTTP %d for delete eid=%d. Response: %s',
                $httpStatus, $eid, substr((string)$response, 0, 500)
            ));
            return;
        }

        error_log(sprintf(
            '[ZoomAppointmentListener] Successfully delivered delete event for eid=%d (HTTP %d)',
            $eid, $httpStatus
        ));
    }
}