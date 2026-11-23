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

    private string $settingsUrl;

    public function __construct(string $settingsUrl)
    {
        $this->settingsUrl = $settingsUrl;
    }

    public function onMenuUpdate(MenuEvent $event): void
    {
        $menu = $event->getMenu();

        $this->attach($menu, self::PARENT_MISC, $this->item('zhrPrefs0', 'msc', []));
        $this->attach($menu, self::PARENT_ADMIN, $this->item('zhrPrefsAdmin0', 'adm', ['admin', 'super']));

        $event->setMenu($menu);
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
