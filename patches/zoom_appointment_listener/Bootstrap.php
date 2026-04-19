<?php

/**
 * Bootstrap.php
 *
 * Registers the ZoomAppointmentListener with OpenEMR's Symfony EventDispatcher.
 * OpenEMR calls Bootstrap::setup() when it loads this module during startup.
 *
 * Module: zoom_appointment_listener
 */

namespace Zoomly\ZoomAppointmentListener;

use OpenEMR\Events\Appointments\AppointmentSetEvent;
use Symfony\Component\EventDispatcher\EventDispatcherInterface;

class Bootstrap
{
    /**
     * @var EventDispatcherInterface
     */
    private $eventDispatcher;

    public function __construct(EventDispatcherInterface $eventDispatcher)
    {
        $this->eventDispatcher = $eventDispatcher;
    }

    /**
     * Called by OpenEMR's module loader.
     * Attaches our listener to the appointment.set event.
     */
    public function setup(): void
    {
        $listener = new AppointmentListener();

        $this->eventDispatcher->addListener(
            AppointmentSetEvent::EVENT_HANDLE,  // 'appointment.set'
            [$listener, 'onAppointmentSet'],
            // Priority 0 — run after OpenEMR's own listeners (higher number = earlier)
            0
        );
    }
}