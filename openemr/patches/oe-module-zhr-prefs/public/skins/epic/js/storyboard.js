/*
 * Epic-style patient storyboard rail.
 *
 * A persistent left rail showing the active patient, visible across every
 * workspace tab — the Epic model, per the handoff spec.
 *
 * Runs ONLY in the top-level shell (interface/main/tabs/main.php). The skin's
 * assets are injected into every document including tab iframes, so the guard
 * on #mainFrames_div and left_nav is what keeps this out of the iframes,
 * where it would render a second rail inside each tab.
 *
 * No template change is needed: #mainFrames_div is already d-flex flex-row
 * with #framesDisplay inside it, so prepending an <aside> puts the rail to
 * the left of the tab content.
 *
 * Data comes from the same public/snapshot.php endpoint as the Schedule
 * panel, so the ACL rules are identical and enforced server-side.
 */
(function () {
    var ENDPOINT = '/interface/modules/custom_modules/oe-module-zhr-prefs/public/snapshot.php';

    var rail = null;
    var inFlight = null;

    function isShell() {
        return !!document.getElementById('mainFrames_div');
    }

    function el(tag, className, text) {
        var node = document.createElement(tag);
        if (className) {
            node.className = className;
        }
        if (text !== undefined && text !== null && text !== '') {
            node.textContent = text;
        }
        return node;
    }

    function ensureRail() {
        if (rail && document.body.contains(rail)) {
            return rail;
        }

        var frames = document.getElementById('mainFrames_div');
        if (!frames) {
            return null;
        }

        rail = el('aside', 'zhr-storyboard');
        rail.setAttribute('aria-label', 'Patient storyboard');

        /*
         * Two regions. The card region holds OpenEMR's own patient card,
         * moved here from the top of the shell, and is NEVER cleared —
         * emptying it would tear out live Knockout bindings and the
         * encounter controls would stop working. The body region is ours to
         * re-render freely.
         */
        rail.appendChild(el('div', 'zhr-storyboard-card'));
        rail.appendChild(el('div', 'zhr-storyboard-body'));

        frames.insertBefore(rail, frames.firstChild);
        return rail;
    }

    /*
     * Moves the shell's patient card into the rail rather than hiding it and
     * rebuilding its contents. The card carries the patient picture and the
     * encounter selector / new-encounter actions, all Knockout-bound — moving
     * the element preserves those bindings and handlers; recreating them
     * would not.
     */
    function adoptPatientCard(target) {
        var card = document.getElementById('attendantData');
        var slot = target.querySelector('.zhr-storyboard-card');
        if (card && slot && card.parentNode !== slot) {
            slot.appendChild(card);
        }
        return !!card;
    }

    /*
     * The card's encounter actions are icon-only with a title attribute,
     * which reads as nothing in a demo. Labels are appended rather than the
     * markup rebuilt, so the Knockout click bindings survive.
     */
    function labelCardActions(target) {
        var card = target.querySelector('.zhr-storyboard-card');
        if (!card) {
            return;
        }

        var newEncounter = card.querySelector('[data-bind*="clickNewEncounter"]');
        if (newEncounter && !newEncounter.querySelector('.zhr-btn-label')) {
            var label = document.createElement('span');
            label.className = 'zhr-btn-label';
            label.textContent = 'New Encounter';
            newEncounter.appendChild(label);
        }
    }

    function initials(name) {
        return (name || '')
            .split(/[\s,]+/)
            .filter(Boolean)
            .slice(0, 2)
            .map(function (part) { return part.charAt(0).toUpperCase(); })
            .join('');
    }

    function block(title) {
        var section = el('section', 'zhr-storyboard-block');
        section.appendChild(el('h3', 'zhr-storyboard-heading', title));
        return section;
    }

    function pairs(list) {
        var dl = el('dl', 'zhr-storyboard-dl');
        list.forEach(function (pair) {
            if (!pair[1]) {
                return;
            }
            dl.appendChild(el('dt', null, pair[0]));
            dl.appendChild(el('dd', null, pair[1]));
        });
        return dl;
    }

    function render(data, target) {
        var p = data.patient || {};

        /*
         * The adopted card already renders the patient name and picture, so
         * our own identity header is only used as a fallback when the card
         * is absent — showing both would print the name twice.
         */
        var hasCard = document.getElementById('attendantData');
        var header = hasCard ? null : el('div', 'zhr-storyboard-header');
        if (header) {
            header.appendChild(el('div', 'zhr-storyboard-avatar', initials(p.name)));

            var identity = el('div', 'zhr-storyboard-identity');
            identity.appendChild(el('div', 'zhr-storyboard-name', p.name || '—'));
            identity.appendChild(el('div', 'zhr-storyboard-meta',
                [p.sex, p.dob].filter(Boolean).join(' · ')));
            identity.appendChild(el('div', 'zhr-storyboard-meta',
                p.pid ? 'PID ' + p.pid : ''));
            header.appendChild(identity);
            target.appendChild(header);
        } else {
            // Card supplies the name; add the details it does not show.
            target.appendChild(el('div', 'zhr-storyboard-meta',
                [p.sex, p.dob, p.pid ? 'PID ' + p.pid : ''].filter(Boolean).join(' · ')));
        }

        /*
         * Allergies lead, as in the spec — it is the one block a clinician
         * must not miss. An undefined value means the viewer lacks the
         * clinical ACL, which is different from having none on file, so the
         * box is omitted entirely rather than reading "No known allergies".
         */
        if (data.allergies) {
            var allergyBox = el('div', 'zhr-storyboard-allergies');
            allergyBox.appendChild(el('div', 'zhr-storyboard-heading', 'Allergies'));
            if (data.allergies.length) {
                var list = el('ul', 'zhr-storyboard-list');
                data.allergies.forEach(function (item) {
                    list.appendChild(el('li', null, item.title));
                });
                allergyBox.appendChild(list);
            } else {
                allergyBox.appendChild(el('div', 'zhr-storyboard-none', 'No known allergies'));
            }
            target.appendChild(allergyBox);
        }

        if (p.phone || p.address) {
            var contact = block('Contact');
            contact.appendChild(pairs([['Phone', p.phone], ['Address', p.address]]));
            target.appendChild(contact);
        }

        if (data.insurance) {
            var coverage = block('Coverage');
            coverage.appendChild(pairs([
                ['Plan', data.insurance.plan],
                ['Policy', data.insurance.policy]
            ]));
            target.appendChild(coverage);
        }

        if (data.visits && data.visits.length) {
            var visits = block('Recent Visits');
            var vlist = el('ul', 'zhr-storyboard-list');
            data.visits.slice(0, 3).forEach(function (visit) {
                vlist.appendChild(el('li', null,
                    [visit.date, visit.reason].filter(Boolean).join(' — ')));
            });
            visits.appendChild(vlist);
            target.appendChild(visits);
        }
    }

    function show(pid, name) {
        var target = ensureRail();
        if (!target) {
            return;
        }

        target.classList.add('zhr-storyboard--open');
        adoptPatientCard(target);
        labelCardActions(target);

        var body = target.querySelector('.zhr-storyboard-body');
        body.textContent = '';
        body.appendChild(el('div', 'zhr-storyboard-loading', name || 'Loading…'));

        // Supersede any in-flight request so switching patients quickly
        // cannot render an earlier one over a later one.
        var token = {};
        inFlight = token;

        fetch(ENDPOINT + '?pid=' + encodeURIComponent(pid), { credentials: 'same-origin' })
            .then(function (response) {
                if (!response.ok) {
                    throw new Error(String(response.status));
                }
                return response.json();
            })
            .then(function (data) {
                if (inFlight !== token) {
                    return;
                }
                body.textContent = '';
                render(data, body);
            })
            .catch(function () {
                if (inFlight !== token) {
                    return;
                }
                body.textContent = '';
                body.appendChild(el('div', 'zhr-storyboard-none',
                    'Patient summary unavailable.'));
            });
    }

    function hide() {
        inFlight = null;
        if (rail) {
            var body = rail.querySelector('.zhr-storyboard-body');
            if (body) {
                body.textContent = '';
            }
            rail.classList.remove('zhr-storyboard--open');
        }
    }

    /*
     * left_nav.setPatient is the shell's single entry point for "a patient
     * became active", and clearPatient closes the chart. Both are globals, so
     * they are wrapped rather than reimplemented — the original is always
     * called first and its return value preserved, so shell behaviour is
     * unchanged whether or not this rail is present.
     */
    function wrap() {
        if (!isShell()) {
            return;
        }

        if (window.left_nav && typeof window.left_nav.setPatient === 'function'
            && !window.left_nav.setPatient.zhrWrapped) {
            var originalSet = window.left_nav.setPatient;
            window.left_nav.setPatient = function (pname, pid) {
                var result = originalSet.apply(this, arguments);
                if (pid) {
                    show(pid, pname);
                }
                return result;
            };
            window.left_nav.setPatient.zhrWrapped = true;
        }

        if (typeof window.clearPatient === 'function' && !window.clearPatient.zhrWrapped) {
            var originalClear = window.clearPatient;
            window.clearPatient = function () {
                hide();
                return originalClear.apply(this, arguments);
            };
            window.clearPatient.zhrWrapped = true;
        }
    }

    function start() {
        if (!isShell()) {
            return;
        }

        wrap();

        /*
         * The shell's own scripts may not have defined these globals yet
         * depending on injection order, so retry briefly rather than assume.
         */
        var attempts = 0;
        var timer = window.setInterval(function () {
            wrap();
            attempts += 1;
            if (attempts > 20 || (window.left_nav && window.left_nav.setPatient
                && window.left_nav.setPatient.zhrWrapped)) {
                window.clearInterval(timer);
            }
        }, 250);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', start);
    } else {
        start();
    }
})();
