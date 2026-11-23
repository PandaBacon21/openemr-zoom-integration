<?php

/**
 * ZHR Demo Preferences.
 *
 * One page, two sections: "My Preferences" for everyone, and "Organization
 * Defaults" for administrators. Saving reloads the top window so the shell and
 * every open workspace tab pick up a skin change together.
 */

namespace Zoomly\ZhrPrefs;

use OpenEMR\Common\Acl\AclMain;
use OpenEMR\Common\Csrf\CsrfUtils;
use OpenEMR\Core\Header;

require_once(__DIR__ . '/../../../../globals.php');

$registry = new SkinRegistry(__DIR__ . '/skins');
$catalog = new PreferenceCatalog($registry);
$preferences = new PreferenceService($catalog);

$userId = (int)($_SESSION['authUserID'] ?? 0);
$isAdmin = AclMain::aclCheckCore('admin', 'super');
$messages = [];

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (!CsrfUtils::verifyCsrfToken($_POST['csrf_token_form'] ?? '')) {
        CsrfUtils::csrfNotVerified();
    }

    $section = $_POST['section'] ?? '';

    if ($section === 'user') {
        foreach ($catalog->userPreferences() as $preference) {
            $key = $preference->getKey();

            // The org lock applies to the skin only; other preferences stay
            // user-controlled regardless.
            if ($key === PreferenceCatalog::SKIN && !$preferences->userChoiceAllowed()) {
                continue;
            }

            // An unchecked checkbox sends nothing, which for a bool means '0'.
            if ($preference->isBool()) {
                $submitted = isset($_POST[$key]) ? '1' : '0';
            } else {
                $submitted = (string)($_POST[$key] ?? '');
            }

            // Empty means "use the organization default" — drop their row
            // rather than storing a copy of today's default.
            if ($submitted === '') {
                $preferences->clearForUser($key, $userId);
                continue;
            }

            if (!$preferences->setForUser($key, $submitted, $userId)) {
                $messages[] = xl('That value is not valid for') . ' ' . $preference->getLabel();
            }
        }
    } elseif ($section === 'org') {
        // Server-side check: the Admin menu entry only hides the link.
        if (!$isAdmin) {
            http_response_code(403);
            exit(xlt('Access denied'));
        }

        if (!$preferences->setOrgDefault(PreferenceCatalog::SKIN, (string)($_POST['org_skin'] ?? ''))) {
            $messages[] = xl('That is not a valid default skin.');
        }
        $preferences->setOrgDefault(
            PreferenceCatalog::ALLOW_USER_SKIN,
            isset($_POST['org_allow_user_skin']) ? '1' : '0'
        );
    }

    if ($messages === []) {
        // Post/Redirect/Get, with a one-shot session flag so the reload fires
        // once per save instead of on every subsequent view.
        $_SESSION['zhr_prefs_saved'] = true;
        header('Location: settings.php');
        exit;
    }
}

$justSaved = !empty($_SESSION['zhr_prefs_saved']);
unset($_SESSION['zhr_prefs_saved']);

$csrf = CsrfUtils::collectCsrfToken();
$userChoiceAllowed = $preferences->userChoiceAllowed();
$skinPreference = $catalog->skin();
$skinOptions = $skinPreference->getOptions();
$ownSkin = $preferences->ownValue(PreferenceCatalog::SKIN, $userId);
$orgSkin = $preferences->orgDefault(PreferenceCatalog::SKIN);
$veradigm = $catalog->showVeradigm();
?>
<!DOCTYPE html>
<html>
<head>
    <?php Header::setupHeader(); ?>
    <title><?php echo xlt('Demo Preferences'); ?></title>
</head>
<body class="body_top container-fluid">
<h2 class="mt-3"><?php echo xlt('Demo Preferences'); ?></h2>

<?php foreach ($messages as $message) : ?>
    <div class="alert alert-danger"><?php echo text($message); ?></div>
<?php endforeach; ?>

<?php if ($justSaved) : ?>
    <div class="alert alert-success"><?php echo xlt('Preferences saved.'); ?></div>
<?php endif; ?>

<form method="POST" action="settings.php" class="mb-4">
    <input type="hidden" name="csrf_token_form" value="<?php echo attr($csrf); ?>" />
    <input type="hidden" name="section" value="user" />

    <h4><?php echo xlt('My Preferences'); ?></h4>
    <p class="text-muted"><?php echo xlt('These apply only to you.'); ?></p>

    <fieldset class="mb-3">
        <legend class="h6"><?php echo text($skinPreference->getLabel()); ?></legend>
        <p class="text-muted"><?php echo text($skinPreference->getDescription()); ?></p>

        <?php if (!$userChoiceAllowed) : ?>
            <div class="alert alert-info">
                <?php echo xlt('Your administrator has set the skin for everyone:'); ?>
                <strong><?php echo text($skinOptions[$orgSkin] ?? $orgSkin); ?></strong>
            </div>
        <?php else : ?>
            <div class="form-check">
                <input class="form-check-input" type="radio" name="<?php echo attr(PreferenceCatalog::SKIN); ?>"
                       id="skin_default" value="" <?php echo $ownSkin === null ? 'checked' : ''; ?> />
                <label class="form-check-label" for="skin_default">
                    <?php echo xlt('Use organization default'); ?>
                    <span class="text-muted">(<?php echo text($skinOptions[$orgSkin] ?? $orgSkin); ?>)</span>
                </label>
            </div>
            <?php foreach ($skinOptions as $skinId => $skinName) : ?>
                <?php $skin = $registry->get($skinId); ?>
                <div class="form-check">
                    <input class="form-check-input" type="radio" name="<?php echo attr(PreferenceCatalog::SKIN); ?>"
                           id="skin_<?php echo attr($skinId); ?>" value="<?php echo attr($skinId); ?>"
                           <?php echo $ownSkin === $skinId ? 'checked' : ''; ?> />
                    <label class="form-check-label" for="skin_<?php echo attr($skinId); ?>">
                        <strong><?php echo text($skinName); ?></strong>
                        <?php if ($skin !== null && $skin->getDescription() !== '') : ?>
                            <span class="text-muted">&mdash; <?php echo text($skin->getDescription()); ?></span>
                        <?php endif; ?>
                    </label>
                </div>
            <?php endforeach; ?>
        <?php endif; ?>
    </fieldset>

    <fieldset class="mb-3">
        <div class="form-check">
            <input class="form-check-input" type="checkbox" value="1"
                   name="<?php echo attr($veradigm->getKey()); ?>" id="pref_veradigm"
                   <?php echo $preferences->effectiveValue($veradigm->getKey(), $userId) !== '0' ? 'checked' : ''; ?> />
            <label class="form-check-label" for="pref_veradigm">
                <strong><?php echo text($veradigm->getLabel()); ?></strong>
                <span class="text-muted">&mdash; <?php echo text($veradigm->getDescription()); ?></span>
            </label>
        </div>
    </fieldset>

    <button type="submit" class="btn btn-primary"><?php echo xlt('Save my preferences'); ?></button>
</form>

<?php if ($isAdmin) : ?>
    <hr />
    <form method="POST" action="settings.php">
        <input type="hidden" name="csrf_token_form" value="<?php echo attr($csrf); ?>" />
        <input type="hidden" name="section" value="org" />

        <h4><?php echo xlt('Organization Defaults'); ?></h4>
        <p class="text-muted"><?php echo xlt('These apply to everyone who has not chosen for themselves.'); ?></p>

        <div class="form-group">
            <label for="org_skin"><?php echo xlt('Default skin'); ?></label>
            <select class="form-control w-auto" name="org_skin" id="org_skin">
                <?php foreach ($skinOptions as $skinId => $skinName) : ?>
                    <option value="<?php echo attr($skinId); ?>" <?php echo $orgSkin === $skinId ? 'selected' : ''; ?>>
                        <?php echo text($skinName); ?>
                    </option>
                <?php endforeach; ?>
            </select>
        </div>

        <div class="form-check mb-3">
            <input class="form-check-input" type="checkbox" value="1"
                   name="org_allow_user_skin" id="org_allow_user_skin"
                   <?php echo $userChoiceAllowed ? 'checked' : ''; ?> />
            <label class="form-check-label" for="org_allow_user_skin">
                <?php echo text($catalog->allowUserSkin()->getLabel()); ?>
            </label>
        </div>

        <button type="submit" class="btn btn-secondary"><?php echo xlt('Save organization defaults'); ?></button>
    </form>
<?php endif; ?>

<?php if ($justSaved) : ?>
    <script>
        // Reload the whole shell so the top bar and every open tab pick up a
        // skin change together. Fires once: the session flag is consumed above.
        if (window.top) {
            window.top.location.reload();
        }
    </script>
<?php endif; ?>
</body>
</html>
