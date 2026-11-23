/*
 * Epic-style Flow Board ("Schedule").
 *
 * Turns OpenEMR's status buttons into pills, replaces the full-row status
 * fill with a left edge accent, greens the video icon when the patient is in
 * the Zoom waiting room, and makes rows selectable.
 *
 * Columns are located by HEADER TEXT, never by index: the PID column is
 * conditional on $GLOBALS['ptkr_show_pid'], so an index-based lookup silently
 * targets the wrong column when that setting differs.
 *
 * Only runs under the Epic skin, so stock keeps OpenEMR's own appearance.
 */
(function () {
    var STATUSES = window.ZHR_STATUSES || {};

    /*
     * Survives the auto-refresh. The Flow Board rebuilds its table on an
     * interval, discarding both the selected row and anything attached
     * alongside it, so the selection is remembered here and re-applied after
     * every rebuild.
     */
    var selected = { pid: null, name: null };

    var STATUS_COLUMN = 'appt status';

    /*
     * Header wording. "Current Status" holds minutes elapsed in the current
     * status, which reads as a duplicate of Appt Status until it is named
     * for what it is. Matched on exact header text — no index involved, so
     * this cannot misalign the table the way hiding a column did.
     */
    var HEADER_LABELS = {
        'Current Status': 'Time in Status',
        'Current': 'Time in Status'
    };

    /*
     * Summary-count wording, aligned with the status pills.
     *
     * The counts come from xl_list_label(), which emits OpenEMR's own
     * phrasing — "None" for what the pills call "Scheduled", and so on. The
     * status code never reaches the DOM (it is the array key server-side),
     * so these are matched on exact label text, scoped to #status_summary.
     * Only labels that differ from our wording are listed.
     */
    var SUMMARY_LABELS = {
        'None': 'Scheduled',
        'In exam room': 'Roomed',
        'Checked out': 'Checked Out',
        'No show': 'No Show',
        'Arrived late': 'Arrived Late',
        'Left w/o visit': 'Left w/o Visit'
    };

    /*
     * Filter field labels. OpenEMR ships this form with no <label> elements
     * at all, so they are created here. Keyed on the control ids, which are
     * stable.
     */
    var FILTER_LABELS = {
        form_apptcat: 'Visit Category',
        form_apptstatus: 'Status',
        form_facility: 'Facility',
        form_provider: 'Provider',
        form_from_date: 'From',
        form_to_date: 'To',
        form_patient_name: 'Patient Name',
        form_patient_id: 'PID'
    };

    function headerCells(table) {
        var head = table.querySelector('thead tr');
        return head ? Array.prototype.slice.call(head.children) : [];
    }

    /*
     * DOM index, matched on header text. This is what the status pill has
     * always used and it works in practice.
     *
     * Do NOT reuse it to hide a column. Hiding needs the header and body
     * sequences to correspond, and they do not: the header carries
     * responsive duplicate cells (d-sm-none) the body lacks, and cells on
     * both sides sit inside $GLOBALS conditionals, so the rendered shapes
     * cannot be predicted. Two attempts at column hiding — one by DOM index,
     * one in visible-column space — both put data under the wrong headings.
     * Removing a column needs a template change, not a DOM lookup.
     */
    function columnIndex(table, label) {
        var cells = headerCells(table);
        for (var i = 0; i < cells.length; i++) {
            if (cells[i].textContent.trim().toLowerCase() === label) {
                return i;
            }
        }
        return -1;
    }

    function relabelHeaders(table) {
        headerCells(table).forEach(function (cell) {
            var next = HEADER_LABELS[cell.textContent.trim()];
            if (next) {
                cell.textContent = next;
            }
        });
    }

    function decorateRow(row, table) {
        if (row.classList.contains('zhr-row')) {
            return;
        }
        row.classList.add('zhr-row');

        var code = row.getAttribute('data-apptstatus');
        var status = STATUSES[code];
        var key = status ? status.key : 'scheduled';

        /*
         * No row-state class is applied and the inline background is left
         * alone: css/pages/flowboard.css suppresses the full-row fill and
         * draws the accent straight from [data-apptstatus], so the row is
         * correct on first paint rather than after this script runs.
         */

        /*
         * The status button must be found in the Appt Status column.
         * querySelector('td .btn') returns the FIRST button in the row, which
         * on telehealth rows is "Start Zoom" — so those rows had the Zoom
         * button restyled as a pill while the status stayed a blue button.
         */
        var statusIndex = columnIndex(table, STATUS_COLUMN);
        var statusCell = statusIndex >= 0 ? row.children[statusIndex] : null;
        var button = statusCell ? statusCell.querySelector('.btn') : null;

        if (button) {
            button.classList.add('zhr-status', 'zhr-status--' + key);

            // The same cell shows a room name instead of the status when a
            // room is assigned, so only replace actual status titles — all of
            // which begin with the status code.
            if (status && button.textContent.trim().indexOf(code) === 0) {
                button.textContent = status.label;
            }

            /*
             * The Epic mockup shows the arrival/checkout time beneath the
             * status pill. That was implemented by reading the Arrive Time or
             * Check Out Time cell via its header index, and it consistently
             * read one column early — picking up the Telehealth cell, so
             * "Start Zoom" (or "—") appeared as the timestamp. The header and
             * body cell sequences evidently do not align the way the template
             * source suggests, and the Flow Board cannot be rendered outside a
             * browser session to diagnose it. Dropped rather than guessed at
             * again; reinstating it needs the time as a data attribute on the
             * row, which is a template change.
             */
        }
    }

    /* ── Filter panel ────────────────────────────────────────────────── */
    function labelFilters() {
        Object.keys(FILTER_LABELS).forEach(function (id) {
            var control = document.getElementById(id);
            if (!control || control.parentNode.querySelector('.zhr-field-label')) {
                return;
            }

            var label = document.createElement('label');
            label.className = 'zhr-field-label';
            label.setAttribute('for', id);
            label.textContent = FILTER_LABELS[id];
            control.parentNode.insertBefore(label, control);
        });
    }

    function selectedText(id) {
        var el = document.getElementById(id);
        if (!el || !el.options) {
            return '';
        }
        var option = el.options[el.selectedIndex];
        return option ? option.textContent.trim() : '';
    }

    /*
     * Subtitle beneath the heading: provider, date, facility. Everything is
     * read from the filter controls, so no server round-trip is needed.
     */
    function buildSubtitle() {
        var heading = document.querySelector('h2');
        if (!heading || heading.parentNode.querySelector('.zhr-subtitle')) {
            return;
        }

        var from = document.getElementById('form_from_date');
        var parts = [selectedText('form_provider'), '', selectedText('form_facility')];

        if (from && from.value) {
            var parsed = new Date(from.value + 'T00:00:00');
            if (!isNaN(parsed)) {
                parts[1] = parsed.toLocaleDateString(undefined, {
                    weekday: 'long', month: 'short', day: 'numeric', year: 'numeric'
                });
            }
        }

        parts = parts.filter(function (part) { return part; });
        if (!parts.length) {
            return;
        }

        var subtitle = document.createElement('div');
        subtitle.className = 'zhr-subtitle';
        subtitle.textContent = parts.join(' \u00b7 ');
        heading.parentNode.insertBefore(subtitle, heading.nextSibling);
    }

    /* The filter action is "Filter"; the mockup calls it Apply. */
    function relabelApply() {
        var apply = document.querySelector('button[type="submit"], input[type="submit"]');
        if (apply && apply.textContent.trim() === 'Filter') {
            apply.classList.add('zhr-apply');
            apply.textContent = 'Apply';
        }
    }

    function relabelSummary() {
        var summary = document.getElementById('status_summary');
        if (!summary) {
            return;
        }

        Array.prototype.forEach.call(summary.querySelectorAll('em'), function (label) {
            // Labels render as "None:" including the colon.
            var text = label.textContent.trim();
            var trailing = text.endsWith(':');
            var key = trailing ? text.slice(0, -1) : text;

            if (SUMMARY_LABELS[key]) {
                label.textContent = SUMMARY_LABELS[key] + (trailing ? ':' : '');
            }
        });
    }

    function wireSelection(table) {
        if (table.classList.contains('zhr-selectable')) {
            return;
        }
        table.classList.add('zhr-selectable');

        table.addEventListener('click', function (event) {
            var row = event.target.closest('tr[data-apptstatus]');
            if (!row) {
                return;
            }

            Array.prototype.forEach.call(
                table.querySelectorAll('tr.zhr-row--selected'),
                function (other) { other.classList.remove('zhr-row--selected'); }
            );
            selected = {
                pid: row.getAttribute('data-pid'),
                name: row.getAttribute('data-pname')
            };
            row.classList.add('zhr-row--selected');

            /*
             * Announce the selection rather than calling the panel directly,
             * so each file owns one surface and the Flow Board works with or
             * without the snapshot panel present.
             */
            document.dispatchEvent(new CustomEvent('zhr:row-selected', {
                detail: {
                    pid: row.getAttribute('data-pid'),
                    name: row.getAttribute('data-pname')
                }
            }));
        });
    }

    /*
     * Re-apply the selection after a rebuild and re-announce it so the
     * snapshot panel, which the rebuild also removed, comes back.
     *
     * Matching is by pid because that is the only patient identifier on the
     * row. A patient with two appointments the same day therefore
     * re-highlights their first row rather than the one originally clicked —
     * cosmetic only, since the panel is per patient, not per appointment.
     */
    function restoreSelection(table) {
        if (!selected.pid) {
            return;
        }

        var row = table.querySelector('tr[data-pid="' + selected.pid + '"]');
        if (!row || row.classList.contains('zhr-row--selected')) {
            return;
        }

        row.classList.add('zhr-row--selected');
        document.dispatchEvent(new CustomEvent('zhr:row-selected', { detail: selected }));
    }

    function run() {
        labelFilters();
        relabelSummary();
        buildSubtitle();
        relabelApply();

        var rows = document.querySelectorAll('tr[data-apptstatus]');
        if (!rows.length) {
            return;
        }

        var table = rows[0].closest('table');
        if (!table) {
            return;
        }

        relabelHeaders(table);
        Array.prototype.forEach.call(rows, function (row) { decorateRow(row, table); });
        wireSelection(table);
        restoreSelection(table);
    }

    /*
     * The Flow Board rewrites its table when Filter is used and on its
     * auto-refresh, so a single pass at DOMContentLoaded is not enough.
     */
    function observe() {
        if (!window.MutationObserver || !document.body) {
            return;
        }

        var pending = null;
        new MutationObserver(function () {
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
