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

    public function __construct(SkinResolver $resolver, string $assetPath)
    {
        $this->resolver = $resolver;
        $this->assetPath = rtrim($assetPath, '/') . '/';
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
     * Returns an un-versioned URL on purpose.
     *
     * Header::createElement() already appends ?v={$GLOBALS['v_js_includes']}
     * to every module script and style it renders, so stamping here as well
     * produces a doubled "?v=81&v=81" query string.
     */
    private function assetUrl(Skin $skin, string $relative): string
    {
        return $this->assetPath . 'skins/' . $skin->getId() . '/' . ltrim($relative, '/');
    }
}
