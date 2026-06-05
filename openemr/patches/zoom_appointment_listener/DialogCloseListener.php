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
 *   2. Builds a delete payload
 *   3. POSTs signed request to Flask bridge webhook endpoint
 *
 * Module: zoom_appointment_listener
 */

namespace Zoomly\ZoomAppointmentListener;

use OpenEMR\Events\Appointments\AppointmentDialogCloseEvent;

require_once('/var/www/localhost/htdocs/openemr/library/zoomly/ZoomBridge.php');

class DialogCloseListener
{
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

        // --- POST to Flask bridge ---
        $result = zoomly_bridge_post('/webhooks/openemr', $payloadJson, 5);

        if ($result['error']) {
            error_log(sprintf(
                '[ZoomAppointmentListener] cURL error for delete eid=%d: %s',
                $eid,
                $result['error']
            ));
            return;
        }

        if ($result['status'] < 200 || $result['status'] >= 300) {
            error_log(sprintf(
                '[ZoomAppointmentListener] Flask returned HTTP %d for delete eid=%d. Response: %s',
                $result['status'],
                $eid,
                substr($result['body'], 0, 500)
            ));
            return;
        }

        error_log(sprintf(
            '[ZoomAppointmentListener] Successfully delivered delete event for eid=%d (HTTP %d)',
            $eid,
            $result['status']
        ));
    }
}