<?php

namespace Zoomly\ZhrPrefs;

/**
 * The registered preferences.
 *
 * Adding a preference means adding it here and rendering nothing extra — the
 * settings page builds itself from userPreferences().
 */
class PreferenceCatalog
{
    public const SKIN = 'zhr_skin';
    public const ALLOW_USER_SKIN = 'zhr_allow_user_skin';
    public const SHOW_VERADIGM = 'zhr_show_veradigm';

    private SkinRegistry $registry;

    public function __construct(SkinRegistry $registry)
    {
        $this->registry = $registry;
    }

    /**
     * Preferences shown in the "My Preferences" section, in display order.
     *
     * @return Preference[]
     */
    public function userPreferences(): array
    {
        return [$this->skin(), $this->showVeradigm()];
    }

    public function get(string $key): ?Preference
    {
        foreach ([$this->skin(), $this->showVeradigm(), $this->allowUserSkin()] as $preference) {
            if ($preference->getKey() === $key) {
                return $preference;
            }
        }

        return null;
    }

    /**
     * Skin options come from the registry, so a newly dropped-in skin folder
     * appears on the settings page with no code change.
     */
    public function skin(): Preference
    {
        $options = [];
        foreach ($this->registry->all() as $id => $skin) {
            $options[$id] = $skin->getName();
        }

        return new Preference(
            self::SKIN,
            Preference::TYPE_CHOICE,
            xl('Skin'),
            xl('Changes how OpenEMR looks. Stock renders exactly as it does today.'),
            SkinRegistry::STOCK_SKIN_ID,
            $options
        );
    }

    public function showVeradigm(): Preference
    {
        return new Preference(
            self::SHOW_VERADIGM,
            Preference::TYPE_BOOL,
            xl('Show the Veradigm launch icon'),
            xl('Shows the "V" icon in the top navigation bar. Only ever visible to provider-mapped users.'),
            '1'
        );
    }

    /** Organization-scoped: there is no per-user value for this one. */
    public function allowUserSkin(): Preference
    {
        return new Preference(
            self::ALLOW_USER_SKIN,
            Preference::TYPE_BOOL,
            xl('Allow users to choose their own skin'),
            xl('When off, everyone sees the organization default skin and cannot change it.'),
            '1'
        );
    }
}
