/*
 * Epic-style terminology.
 *
 * The nav entry and workspace tab are renamed server-side by the module's
 * MenuListener (the tab title is taken from the menu label). This handles the
 * in-page copy that the menu cannot reach: the Flow Board's own <h2> and
 * document title.
 *
 * Done in JS rather than by editing the forked patient_tracker.php so that the
 * stock skin keeps OpenEMR's own wording — this file is only injected while
 * the Epic skin is active.
 */
(function () {
    var RENAMES = {
        'Flow Board': 'Schedule'
    };

    function rename() {
        var replacement = RENAMES[document.title.trim()];
        if (replacement) {
            document.title = replacement;
        }

        document.querySelectorAll('h1, h2, h3').forEach(function (heading) {
            var next = RENAMES[heading.textContent.trim()];
            if (next) {
                heading.textContent = next;
            }
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', rename);
    } else {
        rename();
    }
})();
