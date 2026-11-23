<?php

namespace Zoomly\ZhrPrefs;

use OpenEMR\Menu\MenuEvent;

/**
 * Adds "Demo Preferences" to the menu rather than editing the menu JSON.
 *
 * Two entries, one page: Miscellaneous for everyone, Admin for administrators.
 * The page itself re-checks the ACL server-side before rendering or saving the
 * organization section, so the Admin entry is signposting, not security.
 */
class MenuListener
{
    private const PARENT_MISC = 'misimg';
    private const PARENT_ADMIN = 'admimg';

    /**
     * Skin-specific menu terminology, keyed by skin id then by a URL fragment
     * identifying the entry.
     *
     * Matching on the URL rather than menu_id is deliberate: standard.json
     * reuses menu_id 'pfb0' for both Flow and Recalls, so the id is ambiguous
     * while the URL is not.
     *
     * Renaming here rather than in the page itself means it also reaches the
     * workspace tab title, which is taken from the menu entry's label.
     */
    private const SKIN_MENU_LABELS = [
        'epic' => [
            'patient_tracker.php' => 'Schedule',
        ],
    ];

    private string $settingsUrl;
    private SkinResolver $resolver;

    public function __construct(string $settingsUrl, SkinResolver $resolver)
    {
        $this->settingsUrl = $settingsUrl;
        $this->resolver = $resolver;
    }

    public function onMenuUpdate(MenuEvent $event): void
    {
        $menu = $event->getMenu();

        $this->attach($menu, self::PARENT_MISC, $this->item('zhrPrefs0', 'msc', []));
        $this->attach($menu, self::PARENT_ADMIN, $this->item('zhrPrefsAdmin0', 'adm', ['admin', 'super']));
        $this->applySkinLabels($menu);

        $event->setMenu($menu);
    }

    /**
     * Rewrites menu labels for the active skin. Stock defines no overrides, so
     * it is untouched.
     */
    private function applySkinLabels(array $menu): void
    {
        $overrides = self::SKIN_MENU_LABELS[$this->resolver->resolve()->getId()] ?? [];
        if ($overrides === []) {
            return;
        }

        foreach ($menu as $entry) {
            foreach ($overrides as $urlFragment => $label) {
                if (str_contains((string)($entry->url ?? ''), $urlFragment)) {
                    $entry->label = xlt($label);
                }
            }

            if (!empty($entry->children)) {
                $this->applySkinLabels($entry->children);
            }
        }
    }

    private function item(string $menuId, string $target, array $aclReq): \stdClass
    {
        $item = new \stdClass();
        $item->requirement = 0;
        $item->target = $target;
        $item->menu_id = $menuId;
        $item->label = xlt('Demo Preferences');
        $item->url = $this->settingsUrl;
        $item->children = [];
        $item->acl_req = $aclReq;
        $item->global_req = [];

        return $item;
    }

    private function attach(array $menu, string $parentMenuId, \stdClass $item): void
    {
        foreach ($menu as $entry) {
            if (($entry->menu_id ?? '') === $parentMenuId) {
                $entry->children[] = $item;
                return;
            }
        }

        error_log("zhr_prefs | menu_listener | status=skipped | reason=parent_not_found | parent={$parentMenuId}");
    }
}
