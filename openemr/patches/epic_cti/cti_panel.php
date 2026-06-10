<?php

/**
 * Zoom Contact Center iframe shell for the OpenEMR top nav.
 *
 * The iframe remains mounted when collapsed so an active CTI session survives
 * OpenEMR frame navigation.
 */

$zoomlyEpicCtiClientUrl = getenv('ZOOMLY_EPIC_ZCC_CLIENT_URL') ?: '';
if ($zoomlyEpicCtiClientUrl !== '') :
?>
<div id="zoomly-epic-cti-shell" class="zoomly-epic-cti-shell is-collapsed">
    <button
        id="zoomly-epic-cti-toggle"
        class="btn btn-sm btn-secondary zoomly-epic-cti-toggle"
        type="button"
        aria-label="<?php echo xla('Toggle Zoom Contact Center'); ?>"
        aria-expanded="false"
    >
        <i class="fa fa-phone" aria-hidden="true"></i>
    </button>
    <div class="zoomly-epic-cti-frame-wrap">
        <iframe
            id="zoomly-epic-cti-frame"
            class="zoomly-epic-cti-frame"
            src="<?php echo attr($zoomlyEpicCtiClientUrl); ?>"
            title="<?php echo xla('Zoom Contact Center'); ?>"
            allow="microphone; camera; autoplay; clipboard-read; clipboard-write"
        ></iframe>
    </div>
</div>
<script>
(function () {
    "use strict";
    var shell = document.getElementById("zoomly-epic-cti-shell");
    var toggle = document.getElementById("zoomly-epic-cti-toggle");
    if (!shell || !toggle) {
        return;
    }

    function setCollapsed(collapsed) {
        shell.classList.toggle("is-collapsed", collapsed);
        toggle.setAttribute("aria-expanded", collapsed ? "false" : "true");
        try {
            window.localStorage.setItem("zoomlyEpicCtiCollapsed", collapsed ? "1" : "0");
        } catch (error) {
            console.warn("[ZoomlyEpicCti] Could not persist panel state", error);
        }
    }

    var collapsed = true;
    try {
        collapsed = window.localStorage.getItem("zoomlyEpicCtiCollapsed") !== "0";
    } catch (error) {
        collapsed = true;
    }
    setCollapsed(collapsed);

    toggle.addEventListener("click", function () {
        setCollapsed(!shell.classList.contains("is-collapsed"));
    });
}());
</script>
<?php endif; ?>
