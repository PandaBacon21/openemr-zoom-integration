<?php

/**
 * openemr.bootstrap.php
 *
 * Module entry point for the Zoomly Appointment Listener.
 *
 * OpenEMR scans /interface/modules/custom_modules/ for files named
 * "openemr.bootstrap.php" during application startup. When found, it
 * requires this file and passes in:
 *
 *   $bootstrap  — OpenEMR\Core\ModuleBootstrap instance (provides getDispatcher())
 *
 * This file is intentionally thin. All logic lives in Bootstrap.php
 * and AppointmentListener.php.
 *
 * Module: zoom_appointment_listener
 * Namespace: Zoomly\ZoomAppointmentListener
 */

// Guard: only run inside OpenEMR's bootstrap context.
if (!defined('SITE_DEFAULT_DOMAIN') && !defined('ABSPATH')) {
    // Not being loaded by OpenEMR — bail silently to avoid exposing internals.
    return;
}

// Register PSR-4 autoloader for this module's namespace.
// OpenEMR's global Composer autoloader won't know about our classes
// unless we register them here.
spl_autoload_register(function (string $class): void {
    $prefix    = 'Zoomly\\ZoomAppointmentListener\\';
    $baseDir   = __DIR__ . '/';

    if (strncmp($prefix, $class, strlen($prefix)) !== 0) {
        // Not our namespace — pass to next autoloader.
        return;
    }

    $relativeClass = substr($class, strlen($prefix));
    $file = $baseDir . str_replace('\\', '/', $relativeClass) . '.php';

    if (file_exists($file)) {
        require $file;
    }
});

// $bootstrap is injected by OpenEMR's module loader.
// It exposes getEventDispatcher() which returns the Symfony dispatcher instance.
if (isset($bootstrap)) {
    $dispatcher = $bootstrap->getEventDispatcher();
    $moduleBootstrap = new \Zoomly\ZoomAppointmentListener\Bootstrap($dispatcher);
    $moduleBootstrap->setup();
}