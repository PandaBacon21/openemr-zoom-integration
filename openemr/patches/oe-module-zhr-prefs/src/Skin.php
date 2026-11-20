<?php

namespace Zoomly\ZhrPrefs;

/**
 * Immutable description of one skin, built from its skin.json manifest.
 *
 * Asset paths are stored relative to the skin's own folder; SkinAssetInjector
 * turns them into browser URLs.
 */
class Skin
{
    public function __construct(
        private readonly string $id,
        private readonly string $name,
        private readonly string $description,
        private readonly string $version,
        private readonly array $css,
        private readonly array $js,
        private readonly ?string $preview
    ) {
    }

    public function getId(): string
    {
        return $this->id;
    }

    public function getName(): string
    {
        return $this->name;
    }

    public function getDescription(): string
    {
        return $this->description;
    }

    public function getVersion(): string
    {
        return $this->version;
    }

    /** @return string[] paths relative to the skin folder */
    public function getCss(): array
    {
        return $this->css;
    }

    /** @return string[] paths relative to the skin folder */
    public function getJs(): array
    {
        return $this->js;
    }

    public function getPreview(): ?string
    {
        return $this->preview;
    }

    /**
     * The stock skin is the "render exactly as today" control case: it carries
     * no assets, so nothing is injected and no skin attribute is set.
     */
    public function hasAssets(): bool
    {
        return $this->css !== [] || $this->js !== [];
    }
}
