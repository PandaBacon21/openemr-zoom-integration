/*
 * Appointment status wording — the single source of truth.
 *
 * OpenEMR's apptstat list titles embed the status code ("- None",
 * "> Checked out"), which reads poorly in a demo. Every status in the list is
 * mapped here so the Flow Board and the calendar present them identically;
 * leaving the long tail unmapped meant most statuses kept OpenEMR's raw title
 * while a handful looked different.
 *
 * `key` selects a colour family from css/status.css. The five families are
 * reused across all eighteen statuses rather than inventing new colours:
 * grey for pre-visit states, blue for arrived, purple for roomed, green for
 * completed, warm for cancelled / problem states.
 *
 * Loaded before its consumers (js/flowboard.js, js/calendar_blocks.js).
 */
window.ZHR_STATUSES = {
    '-':     { key: 'scheduled',   label: 'Scheduled' },
    '*':     { key: 'scheduled',   label: 'Reminder Done' },
    '+':     { key: 'scheduled',   label: 'Chart Pulled' },
    '^':     { key: 'scheduled',   label: 'Pending' },
    'AVM':   { key: 'scheduled',   label: 'AVM Confirmed' },
    'SMS':   { key: 'scheduled',   label: 'SMS Confirmed' },
    'EMAIL': { key: 'scheduled',   label: 'Email Confirmed' },
    'CALL':  { key: 'scheduled',   label: 'Callback Requested' },

    '@':     { key: 'arrived',     label: 'Arrived' },
    '~':     { key: 'arrived',     label: 'Arrived Late' },

    '<':     { key: 'roomed',      label: 'Roomed' },

    '>':     { key: 'checked-out', label: 'Checked Out' },
    '$':     { key: 'checked-out', label: 'Coding Done' },

    '?':     { key: 'no-show',     label: 'No Show' },
    'x':     { key: 'no-show',     label: 'Cancelled' },
    '%':     { key: 'no-show',     label: 'Cancelled < 24h' },
    '!':     { key: 'no-show',     label: 'Left w/o Visit' },
    '#':     { key: 'no-show',     label: 'Ins/Fin Issue' }
};
