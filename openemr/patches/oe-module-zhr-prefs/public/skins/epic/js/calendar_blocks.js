/*
 * Epic-style calendar event blocks.
 *
 * OpenEMR paints the appointment category colour as the block's inline
 * background, which makes the dark patient-name text unreadable on darker
 * categories. This moves that colour onto a chip behind the visit type and
 * lets the block itself go neutral, then adds the meta line the mockup shows
 * (PID, visit type, duration).
 *
 * Existing child nodes — the patient anchor, the Zoom button — are left in
 * place and never re-serialised. Rebuilding the block with innerHTML would be
 * simpler but would destroy their click handlers.
 *
 * The calendar replaces its grid via AJAX on nearly every interaction (day
 * navigation, view switch, provider change), so running once on
 * DOMContentLoaded is not enough — on a first visit the grid often does not
 * exist yet, which is why details only appeared after navigating away and
 * back. A MutationObserver re-decorates whatever arrives later.
 *
 * Only runs under the Epic skin, so stock keeps OpenEMR's own appearance.
 */
(function () {
    var STATUSES = window.ZHR_STATUSES || {};

    /* Blocks shorter than this cannot carry a meta line without overflowing
     * their slot; week and month views are deliberately left denser. */
    var MIN_HEIGHT_FOR_META = 34;

    /*
     * Relative luminance per WCAG, used to decide whether a chip needs light
     * or dark text. Without this, a dark category colour simply reproduces the
     * unreadability one level down, on the chip instead of the block.
     */
    function readableTextOn(color) {
        var probe = document.createElement('span');
        probe.style.color = color;
        document.body.appendChild(probe);
        var rgb = getComputedStyle(probe).color.match(/\d+/g);
        document.body.removeChild(probe);

        if (!rgb) {
            return '#1F2430';
        }

        var channels = rgb.slice(0, 3).map(function (value) {
            var c = value / 255;
            return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
        });
        var luminance = 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];

        return luminance > 0.45 ? '#1F2430' : '#FFFFFF';
    }

    function minutesFrom(durationSeconds) {
        var seconds = parseInt(durationSeconds, 10);
        if (!seconds || seconds <= 0) {
            return null;
        }
        return Math.round(seconds / 60) + ' min';
    }

    function buildMeta(block) {
        var meta = document.createElement('span');
        meta.className = 'zhr-event-meta';

        var pid = block.getAttribute('data-pid');
        if (pid) {
            var pidNode = document.createElement('span');
            pidNode.className = 'zhr-event-pid';
            pidNode.textContent = 'PID ' + pid;
            meta.appendChild(pidNode);
        }

        var visitType = block.getAttribute('data-visittype');
        if (visitType) {
            var chip = document.createElement('span');
            chip.className = 'zhr-event-type';
            chip.textContent = visitType;

            // The category colour lives here now instead of on the block.
            var color = block.getAttribute('data-cat-color');
            if (color) {
                chip.style.backgroundColor = color;
                chip.style.color = readableTextOn(color);
            }
            meta.appendChild(chip);
        }

        var duration = minutesFrom(block.getAttribute('data-duration'));
        if (duration) {
            var durationNode = document.createElement('span');
            durationNode.className = 'zhr-event-duration';
            durationNode.textContent = duration;
            meta.appendChild(durationNode);
        }

        return meta.childNodes.length ? meta : null;
    }

    function decorate(block) {
        if (block.classList.contains('zhr-event')) {
            return;
        }

        // Marks the block as reskinned; css/pages/calendar.css keys the
        // neutral background and flex layout off this class, so a block we
        // could not process keeps OpenEMR's original styling rather than
        // ending up half-converted. It also makes this function idempotent,
        // which matters because the observer may see the same node twice.
        block.classList.add('zhr-event');

        // The inline category colour is now redundant and would otherwise win
        // over the stylesheet.
        block.style.removeProperty('background-color');

        if (block.offsetHeight < MIN_HEIGHT_FOR_META) {
            return;
        }

        var meta = buildMeta(block);
        if (meta) {
            block.appendChild(meta);
        }

        // Appended last so the pill's margin-left:auto pushes it to the right
        // edge with the meta line to its left, as in the mockup.
        var status = STATUSES[block.getAttribute('data-apptstatus')];
        if (status) {
            var pill = document.createElement('span');
            pill.className = 'zhr-event-pill';
            pill.textContent = status.label;
            block.appendChild(pill);
        }
    }

    /*
     * Day / Week / Month ship as three separate anchors with literal
     * whitespace between them, so border tricks alone leave visible gaps.
     * Wrapping them in a flex container is the only way to make them read as
     * one segmented control; the anchors themselves are moved, not recreated,
     * so their handlers survive.
     */
    function groupViewSwitch() {
        var day = document.getElementById('dayview');
        var week = document.getElementById('weekview');
        var month = document.getElementById('monthview');

        if (!day || !week || !month || day.parentNode.classList.contains('zhr-viewswitch')) {
            return;
        }

        var group = document.createElement('span');
        group.className = 'zhr-viewswitch';
        day.parentNode.insertBefore(group, day);
        group.appendChild(day);
        group.appendChild(week);
        group.appendChild(month);
    }

    /*
     * Stock renders the primary action as a bare "+" icon, which reads as
     * nothing in a demo. The label is added here rather than in the template
     * so the stock skin keeps OpenEMR's own toolbar.
     */
    function labelNewAppointment() {
        var icon = document.querySelector('.btn > .fa-plus');
        if (!icon || icon.parentNode.querySelector('.zhr-btn-label')) {
            return;
        }

        var label = document.createElement('span');
        label.className = 'zhr-btn-label';
        label.textContent = 'New Appointment';
        icon.parentNode.appendChild(label);
    }

    function run() {
        document.querySelectorAll('.event[data-apptstatus]').forEach(decorate);
        groupViewSwitch();
        labelNewAppointment();
    }

    function observe() {
        if (!window.MutationObserver || !document.body) {
            return;
        }

        var pending = null;
        new MutationObserver(function () {
            // Coalesce bursts: the calendar rewrites the whole grid at once.
            window.clearTimeout(pending);
            pending = window.setTimeout(run, 50);
        }).observe(document.body, { childList: true, subtree: true });
    }

    function start() {
        run();
        observe();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', start);
    } else {
        start();
    }
})();
