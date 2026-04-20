<?php

// Guard: only run inside OpenEMR's bootstrap context.
if (!isset($eventDispatcher) || !isset($classLoader)) {
    return;
}

// Explicitly require our classes since they live flat in the module directory.
require_once $module['path'] . '/Bootstrap.php';
require_once $module['path'] . '/AppointmentListener.php';

// Wire up the event listener.
$moduleBootstrap = new \Zoomly\ZoomAppointmentListener\Bootstrap($eventDispatcher);
$moduleBootstrap->setup();
