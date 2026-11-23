<?php

namespace Zoomly\ZhrPrefs;

use OpenEMR\Events\Core\ScriptFilterEvent;
use OpenEMR\Events\Core\StyleFilterEvent;

/**
 * Adds the active skin's CSS and JS to every page that renders through
 * Header::setupHeader() — which includes each workspace tab iframe.
 *
 * The stock skin carries no assets, so selecting it injects nothing at all:
 * that is what makes "disable = gone" true without any teardown logic.
 */
class SkinAssetInjector
{
    private SkinResolver $resolver;
    private string $assetPath;
    private string $skinsDir;

    public function __construct(SkinResolver $resolver, string $assetPath, string $skinsDir)
    {
        $this->resolver = $resolver;
        $this->assetPath = rtrim($assetPath, '/') . '/';
        $this->skinsDir = rtrim($skinsDir, DIRECTORY_SEPARATOR);
    }

    public function onStyleFilter(StyleFilterEvent $event): void
    {
        $skin = $this->resolver->resolve();
        if (!$skin->hasAssets()) {
            return;
        }

        $styles = $event->getStyles();
        foreach ($skin->getCss() as $relative) {
            $styles[] = $this->assetUrl($skin, $relative);
        }
        $event->setStyles($styles);
    }

    public function onScriptFilter(ScriptFilterEvent $event): void
    {
        $skin = $this->resolver->resolve();
        if (!$skin->hasAssets()) {
            return;
        }

        $scripts = $event->getScripts();
        foreach ($skin->getJs() as $relative) {
            $scripts[] = $this->assetUrl($skin, $relative);
        }
        $event->setScripts($scripts);
    }

    /**
     * Stamps the asset with its own last-modified time.
     *
     * Header::createElement() already appends ?v={$GLOBALS['v_js_includes']},
     * but that global only changes when OpenEMR itself is upgraded — so every
     * edit to a skin stylesheet produced a byte-identical URL and browsers
     * kept serving the cached copy. Editing a skin and seeing no change is the
     * single most confusing failure mode in this subsystem.
     *
     * Using filemtime rather than CacheUtils avoids the doubled "?v=81&v=81"
     * that stamping with the same global produced. Header sees the existing
     * "?" and appends "&v=...", which is harmless.
     */
    private function assetUrl(Skin $skin, string $relative): string
    {
        $relative = ltrim($relative, '/');
        $url = $this->assetPath . 'skins/' . $skin->getId() . '/' . $relative;

        $file = $this->skinsDir . DIRECTORY_SEPARATOR . $skin->getId() . DIRECTORY_SEPARATOR . $relative;
        $modified = is_file($file) ? filemtime($file) : false;

        return $modified !== false ? $url . '?m=' . $modified : $url;
    }
}
