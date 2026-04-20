<?php

namespace Zoomly\ZoomAppointmentListener;

use OpenEMR\Events\Appointments\AppointmentSetEvent;
use Symfony\Component\EventDispatcher\EventDispatcherInterface;

class Bootstrap
{
    private $eventDispatcher;

    public function __construct(EventDispatcherInterface $eventDispatcher)
    {
        $this->eventDispatcher = $eventDispatcher;
    }

    public function setup(): void
    {
        $listener = new AppointmentListener();
        $this->eventDispatcher->addListener(
            AppointmentSetEvent::EVENT_HANDLE,
            [$listener, 'onAppointmentSet'],
            0
        );
    }
}
