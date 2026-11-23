/*
 * Patient snapshot panel for the Schedule.
 *
 * Listens for the zhr:row-selected event dispatched by js/flowboard.js and
 * renders a compact chart summary beside the table. Decoupled on purpose:
 * the Flow Board works with or without this file loaded.
 *
 * Every value is written with textContent, never innerHTML — this renders
 * free-text clinical data (problem titles, message bodies) that must never
 * be interpreted as markup.
 */
(function () {
    var ENDPOINT = '/interface/modules/custom_modules/oe-module-zhr-prefs/public/snapshot.php';

    var panel = null;
    var inFlight = null;

    /*
     * The Flow Board auto-refreshes on an interval and rebuilds its markup,
     * which removes the panel. flowboard.js re-announces the selection
     * afterwards; caching the payload means that costs no extra request and
     * the panel reappears immediately rather than flickering through a
     * loading state every cycle.
     */
    var cache = { pid: null, data: null };

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

    /*
     * Anchored on .divTable, the container holding everything below the
     * filter panel — loader, table, summary counts and the toolbar. Its
     * existing children are moved into a single column so the panel can sit
     * beside the lot, giving the full right side starting under the filter
     * rather than starting below the toolbar.
     */
    function ensurePanel() {
        if (panel && document.body.contains(panel)) {
            return panel;
        }

        var host = document.querySelector('.divTable');
        if (!host) {
            var row = document.querySelector('tr[data-apptstatus]');
            host = row ? row.closest('.col-md-12') : null;
        }
        if (!host) {
            return null;
        }

        host.classList.add('zhr-snapshot-layout');

        var main = host.querySelector(':scope > .zhr-flow-main');
        if (!main) {
            main = el('div', 'zhr-flow-main');
            while (host.firstChild) {
                main.appendChild(host.firstChild);
            }
            host.appendChild(main);
        }

        panel = el('aside', 'zhr-snapshot');
        panel.setAttribute('aria-live', 'polite');
        host.appendChild(panel);
        return panel;
    }

    function section(title) {
        var block = el('section', 'zhr-snapshot-block');
        block.appendChild(el('h3', 'zhr-snapshot-heading', title));
        return block;
    }

    function definitionList(pairs) {
        var list = el('dl', 'zhr-snapshot-dl');
        pairs.forEach(function (pair) {
            if (!pair[1]) {
                return;
            }
            list.appendChild(el('dt', null, pair[0]));
            list.appendChild(el('dd', null, pair[1]));
        });
        return list;
    }

    function itemList(items, render) {
        var list = el('ul', 'zhr-snapshot-list');
        items.forEach(function (item) {
            list.appendChild(el('li', null, render(item)));
        });
        return list;
    }

    function renderBlocks(data, target) {
        var p = data.patient || {};

        var header = el('div', 'zhr-snapshot-header');
        header.appendChild(el('div', 'zhr-snapshot-name', p.name || '—'));
        header.appendChild(el('div', 'zhr-snapshot-meta', [
            p.pid ? 'PID ' + p.pid : '', p.sex, p.dob
        ].filter(Boolean).join(' · ')));
        target.appendChild(header);

        if (p.phone || p.address) {
            var contact = section('Contact');
            contact.appendChild(definitionList([['Phone', p.phone], ['Address', p.address]]));
            target.appendChild(contact);
        }

        if (data.insurance) {
            var ins = section('Insurance');
            ins.appendChild(definitionList([
                ['Plan', data.insurance.plan],
                ['Policy', data.insurance.policy],
                ['Group', data.insurance.group],
                ['Subscriber', data.insurance.subscriber]
            ]));
            target.appendChild(ins);
        }

        if (data.vitals) {
            var v = data.vitals;
            var vitals = section('Vitals');
            vitals.appendChild(definitionList([
                ['BP', v.bp], ['Pulse', v.pulse], ['Resp', v.respiration],
                ['Temp', v.temperature], ['SpO2', v.spo2],
                ['Height', v.height], ['Weight', v.weight]
            ]));
            target.appendChild(vitals);
        }

        [
            ['Problem List', data.problems],
            ['Allergies', data.allergies],
            ['Medications', data.medications]
        ].forEach(function (pair) {
            // Undefined means the viewer lacks the ACL for this block, which
            // is different from an empty list; omit it entirely rather than
            // implying the patient has none.
            if (!pair[1]) {
                return;
            }
            var block = section(pair[0]);
            block.appendChild(pair[1].length
                ? itemList(pair[1], function (item) { return item.title; })
                : el('p', 'zhr-snapshot-empty', 'None recorded'));
            target.appendChild(block);
        });

        if (data.visits && data.visits.length) {
            var visits = section('Recent Visits');
            visits.appendChild(itemList(data.visits, function (visit) {
                return [visit.date, visit.reason].filter(Boolean).join(' — ');
            }));
            target.appendChild(visits);
        }

        if (data.messages && data.messages.length) {
            var messages = section('Messages');
            messages.appendChild(itemList(data.messages, function (message) {
                return [message.date, message.title || message.body].filter(Boolean).join(' — ');
            }));
            target.appendChild(messages);
        }
    }

    function show(pid, name) {
        var target = ensurePanel();
        if (!target) {
            return;
        }

        if (cache.pid === String(pid) && cache.data) {
            target.textContent = '';
            renderBlocks(cache.data, target);
            return;
        }

        target.textContent = '';
        target.appendChild(el('div', 'zhr-snapshot-loading', name ? 'Loading ' + name + '…' : 'Loading…'));

        // Supersede any request still in flight so a fast click-through
        // cannot render an earlier patient over a later one.
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
                cache = { pid: String(pid), data: data };
                target.textContent = '';
                renderBlocks(data, target);
            })
            .catch(function (error) {
                if (inFlight !== token) {
                    return;
                }
                target.textContent = '';
                target.appendChild(el('div', 'zhr-snapshot-empty',
                    error.message === '403'
                        ? 'You do not have access to this patient.'
                        : 'Could not load the patient snapshot.'));
            });
    }

    document.addEventListener('zhr:row-selected', function (event) {
        var detail = event.detail || {};
        if (detail.pid) {
            show(detail.pid, detail.name);
        }
    });
})();
