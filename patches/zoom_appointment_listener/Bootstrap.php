<?php

namespace Zoomly\ZoomAppointmentListener;

use OpenEMR\Events\Appointments\AppointmentSetEvent;
use OpenEMR\Events\Appointments\AppointmentDialogCloseEvent;
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
        $appointmentListener = new AppointmentListener();
        $this->eventDispatcher->addListener(
            AppointmentSetEvent::EVENT_HANDLE,
            [$appointmentListener, 'onAppointmentSet'],
            0
        );

        // Listen for appointment dialog close - handles appointment delete action
        $dialogCloseListener = new DialogCloseListener();
        $this->eventDispatcher->addListener(
            AppointmentDialogCloseEvent::EVENT_NAME,
            [$dialogCloseListener, 'onDialogClose'],
            0
        );
    }
}
