<?php

/**
 * ZHR Prefs — per-user preferences for the Zoomly OpenEMR demo (skin selection
 * and, from Phase 2, other per-user display toggles).
 *
 * Registered by the zoomly-module-init container, not the Modules Manager.
 */

use OpenEMR\Core\ModulesClassLoader;

// Guard: only run inside OpenEMR's bootstrap context.
if (!isset($eventDispatcher) || !isset($classLoader)) {
    return;
}

/** @var ModulesClassLoader $classLoader */
$classLoader->registerNamespaceIfNotExists(
    'Zoomly\\ZhrPrefs\\',
    __DIR__ . DIRECTORY_SEPARATOR . 'src'
);

(new \Zoomly\ZhrPrefs\Bootstrap($eventDispatcher, __DIR__))->setup();
