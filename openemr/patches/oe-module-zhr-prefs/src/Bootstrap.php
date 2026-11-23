<?php

namespace Zoomly\ZhrPrefs;

use OpenEMR\Events\Core\ScriptFilterEvent;
use OpenEMR\Events\Core\StyleFilterEvent;
use OpenEMR\Menu\MenuEvent;
use Symfony\Component\EventDispatcher\EventDispatcherInterface;

/**
 * Wires the module's listeners. Kept deliberately thin — it owns no logic
 * beyond assembling collaborators and subscribing them.
 */
class Bootstrap
{
    public const MODULE_DIRECTORY_NAME = 'oe-module-zhr-prefs';

    private const MODULE_INSTALLATION_PATH = '/interface/modules/custom_modules/';

    private EventDispatcherInterface $eventDispatcher;
    private string $moduleRoot;

    public function __construct(EventDispatcherInterface $eventDispatcher, string $moduleRoot)
    {
        $this->eventDispatcher = $eventDispatcher;
        $this->moduleRoot = rtrim($moduleRoot, DIRECTORY_SEPARATOR);
    }

    public function setup(): void
    {
        $skinsDir = $this->moduleRoot . '/public/skins';
        $registry = new SkinRegistry($skinsDir);
        $catalog = new PreferenceCatalog($registry);
        $preferences = new PreferenceService($catalog);
        $resolver = new SkinResolver($registry, $preferences);
        $injector = new SkinAssetInjector($resolver, $this->getAssetPath(), $skinsDir);

        $this->eventDispatcher->addListener(
            StyleFilterEvent::EVENT_NAME,
            [$injector, 'onStyleFilter']
        );
        $this->eventDispatcher->addListener(
            ScriptFilterEvent::EVENT_NAME,
            [$injector, 'onScriptFilter']
        );

        $menuListener = new MenuListener($this->getSettingsUrl(), $resolver);
        $this->eventDispatcher->addListener(
            MenuEvent::MENU_UPDATE,
            [$menuListener, 'onMenuUpdate']
        );
    }

    /** Browser-facing URL of the Demo Preferences page. */
    private function getSettingsUrl(): string
    {
        return self::MODULE_INSTALLATION_PATH
            . self::MODULE_DIRECTORY_NAME
            . '/public/settings.php';
    }

    /**
     * Browser-facing base URL for this module's public assets.
     */
    private function getAssetPath(): string
    {
        return ($GLOBALS['webroot'] ?? '')
            . self::MODULE_INSTALLATION_PATH
            . self::MODULE_DIRECTORY_NAME
            . '/public/';
    }
}
