<?php

namespace Zoomly\ZhrPrefs;

/**
 * One user-settable preference. Immutable description only — reading and
 * writing values is PreferenceService's job.
 */
class Preference
{
    public const TYPE_CHOICE = 'choice';
    public const TYPE_BOOL = 'bool';

    public function __construct(
        private readonly string $key,
        private readonly string $type,
        private readonly string $label,
        private readonly string $description,
        private readonly string $default,
        /** @var array<string, string> value => label; choice type only */
        private readonly array $options = []
    ) {
    }

    public function getKey(): string
    {
        return $this->key;
    }

    public function getType(): string
    {
        return $this->type;
    }

    public function getLabel(): string
    {
        return $this->label;
    }

    public function getDescription(): string
    {
        return $this->description;
    }

    public function getDefault(): string
    {
        return $this->default;
    }

    /** @return array<string, string> */
    public function getOptions(): array
    {
        return $this->options;
    }

    public function isBool(): bool
    {
        return $this->type === self::TYPE_BOOL;
    }

    /**
     * Anything arriving from a form is untrusted; a value that fails here is
     * rejected rather than coerced, so a bad POST cannot persist junk.
     */
    public function accepts(string $value): bool
    {
        if ($this->isBool()) {
            return $value === '0' || $value === '1';
        }

        return isset($this->options[$value]);
    }
}
