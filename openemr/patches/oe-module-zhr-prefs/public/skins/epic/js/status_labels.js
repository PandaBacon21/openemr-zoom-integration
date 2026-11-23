/*
 * Epic-style appointment status pills.
 *
 * OpenEMR's apptstat list titles embed the status code ("- None",
 * "> Checked out"), which reads poorly in a demo. This rewrites the five
 * statuses the spec names and tags every status element with a normalised
 * class so css/pages/flowboard.css can colour it.
 *
 * Deliberately JS rather than PHP: the stock skin must render exactly as
 * today, and this file is only injected while the Epic skin is active, so
 * stock is unaffected without any skin-awareness in OpenEMR's own code.
 *
 * STATUSES is the single source of truth for status presentation and is
 * shared with the calendar.
 */
(function () {
    var STATUSES = {
        '-': { key: 'scheduled',   label: 'Scheduled' },
        '@': { key: 'arrived',     label: 'Arrived' },
        '<': { key: 'roomed',      label: 'Roomed' },
        '>': { key: 'checked-out', label: 'Checked Out' },
        '?': { key: 'no-show',     label: 'No Show' }
    };

    function decorate(row) {
        var code = row.getAttribute('data-apptstatus');
        var cell = row.querySelector('td .btn');
        if (!cell) {
            return;
        }

        var status = STATUSES[code];

        // Unmapped codes keep OpenEMR's own title and the Scheduled styling,
        // per the spec.
        cell.classList.add('zhr-status', 'zhr-status--' + (status ? status.key : 'scheduled'));

        if (!status) {
            return;
        }

        // The same cell shows the room name instead of the status when a room
        // is assigned, so only replace text that is actually the status title
        // (OpenEMR's titles all begin with the code character).
        if (cell.textContent.trim().indexOf(code) === 0) {
            cell.textContent = status.label;
        }
    }

    function run() {
        document.querySelectorAll('tr[data-apptstatus]').forEach(decorate);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', run);
    } else {
        run();
    }
})();
