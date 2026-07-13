(function () {
    "use strict";

    var config = window.ZoomlyEpicCti || {};
    var streams = Array.isArray(config.streams) ? config.streams : [];
    var sources = [];

    function webroot() {
        return window.webroot_url || "";
    }

    function navigate(url, tabName) {
        if (!url) {
            return;
        }
        if (typeof window.restoreSession === "function") {
            window.restoreSession();
        }
        if (typeof window.navigateTab === "function") {
            window.navigateTab(url, tabName, function () {
                if (typeof window.activateTabByName === "function") {
                    window.activateTabByName(tabName, true);
                }
            });
            return;
        }
        if (window.top && window.top.RTop) {
            window.top.RTop.location = url;
        }
    }

    function buildNavigation(payload) {
        if (payload.matched_on === "no_match") {
            return {
                tabName: "fin",
                url: webroot() + "/interface/new/new.php"
            };
        }
        if (payload.openemr_patient_id) {
            return {
                tabName: "pat",
                url: webroot() + "/interface/patient_file/summary/demographics.php?set_pid="
                    + encodeURIComponent(payload.openemr_patient_id)
            };
        }
        if (payload.caller_number) {
            return {
                tabName: "fin",
                url: webroot() + "/interface/main/finder/dynamic_finder.php?search_any="
                    + encodeURIComponent(payload.caller_number)
            };
        }
        return {
            tabName: "fin",
            url: webroot() + "/interface/main/finder/dynamic_finder.php"
        };
    }

    // Address Book screen-pop for provider callers. Opens (or focuses) the
    // Address Book tab — the same "adm" target OpenEMR's own menu uses — and,
    // on a single provider match, opens that provider's entry in OpenEMR's
    // native Address Book editor modal. Mirrors addrbook_list.php's
    // doedclick_edit() dlgopen call, invoked here from the top frame with an
    // absolute webroot URL.
    function handleAddressBookPop(payload) {
        navigate(webroot() + "/interface/usergroup/addrbook_list.php", "adm");
        var userId = payload.openemr_provider_user_id;
        if (userId) {
            openAddrbookEditModal(userId);
        }
    }

    function openAddrbookEditModal(userId) {
        var url = webroot()
            + "/interface/usergroup/addrbook_edit.php?userid="
            + encodeURIComponent(userId);
        var height = Math.round(((window.screen && window.screen.availHeight) || 800) * 0.75);
        if (typeof window.restoreSession === "function") {
            window.restoreSession();
        }
        if (typeof window.dlgopen === "function") {
            window.dlgopen(url, "_blank", 650, height);
        } else if (window.top && typeof window.top.dlgopen === "function") {
            window.top.dlgopen(url, "_blank", 650, height);
        } else {
            // No dialog framework available — degrade to loading the editor
            // into the Address Book tab itself.
            navigate(url, "adm");
        }
    }

    function closeActiveModal() {
        var jq = window.jQuery || window.$;
        if (jq && typeof jq.fn.modal === "function") {
            jq(".dialogModal.show").modal("hide");
        }
    }

    function expandCtiPanel() {
        var shell = document.getElementById("zoomly-epic-cti-shell");
        if (!shell) { return; }
        shell.classList.remove("is-collapsed");
        var toggle = document.getElementById("zoomly-epic-cti-toggle");
        if (toggle) { toggle.setAttribute("aria-expanded", "true"); }
        try { window.localStorage.setItem("zoomlyEpicCtiCollapsed", "0"); } catch (e) {}
    }

    function formatPhone(raw) {
        var d = String(raw || "").replace(/\D/g, "");
        if (d.length === 11 && d.charAt(0) === "1") { d = d.slice(1); }
        if (d.length === 10) {
            return d.slice(0, 3) + "-" + d.slice(3, 6) + "-" + d.slice(6);
        }
        return String(raw || "");
    }

    // Outbound click-to-dial confirmation. ZCC echoes an RC3 with
    // ContactType=Outgoing after placing the call; Flask pushes an
    // {target:"outbound_call"} event and we show a small "Ring, ring!" dialog
    // (mirrors Epic). Deliberately tiny — just the number — unlike the inbound
    // multi-match picker.
    function showCallingModal(number) {
        var existing = document.getElementById("zoomly-cti-calling");
        if (existing && existing.parentNode) { existing.parentNode.removeChild(existing); }

        var overlay = document.createElement("div");
        overlay.id = "zoomly-cti-calling";
        overlay.setAttribute("role", "dialog");
        overlay.setAttribute("aria-modal", "true");
        overlay.style.cssText = [
            "position:fixed", "inset:0",
            "background:rgba(0,0,0,0.5)",
            "z-index:9999",
            "display:flex", "align-items:center", "justify-content:center",
            "font-family:inherit",
        ].join(";");

        var modal = document.createElement("div");
        modal.style.cssText = [
            "background:#fff", "border-radius:8px", "padding:20px 24px",
            "min-width:240px", "max-width:320px",
            "box-shadow:0 4px 24px rgba(0,0,0,0.25)",
        ].join(";");

        var title = document.createElement("div");
        title.textContent = "Ring, ring!";
        title.style.cssText = "font-weight:600;font-size:15px;margin-bottom:10px;";
        modal.appendChild(title);

        var body = document.createElement("div");
        body.textContent = "Calling " + formatPhone(number) + "…";
        body.style.cssText = "font-size:14px;color:#333;margin-bottom:16px;";
        modal.appendChild(body);

        var footer = document.createElement("div");
        footer.style.cssText = "text-align:right;";
        var ok = document.createElement("button");
        ok.type = "button";
        ok.textContent = "OK";
        ok.style.cssText = [
            "background:#0B5CFF", "color:#fff", "border:none", "border-radius:4px",
            "padding:4px 18px", "font-size:13px", "cursor:pointer",
        ].join(";");
        function dismiss() { if (overlay.parentNode) { overlay.parentNode.removeChild(overlay); } }
        ok.addEventListener("click", dismiss);
        footer.appendChild(ok);
        modal.appendChild(footer);

        overlay.appendChild(modal);
        document.body.appendChild(overlay);
        overlay.addEventListener("click", function (e) { if (e.target === overlay) { dismiss(); } });
    }

    function handleNavigate(event) {
        var payload;
        try {
            payload = JSON.parse(event.data);
        } catch (error) {
            console.error("[ZoomlyEpicCti] Invalid navigate event", error);
            return;
        }
        expandCtiPanel();
        closeActiveModal();
        if (payload.target === "outbound_call") {
            showCallingModal(payload.caller_number);
            return;
        }
        if (payload.target === "address_book") {
            handleAddressBookPop(payload || {});
            return;
        }
        if (payload.matched_on === "multi_match" && Array.isArray(payload.candidates) && payload.candidates.length > 0) {
            showPickerModal(payload.candidates);
            return;
        }
        var target = buildNavigation(payload || {});
        navigate(target.url, target.tabName);
    }

    function showPickerModal(candidates) {
        var existing = document.getElementById("zoomly-cti-picker");
        if (existing && existing.parentNode) { existing.parentNode.removeChild(existing); }

        var ZOOM_BLUE = "#0B5CFF";
        var hasSsn = candidates.some(function (c) { return c.ssn; });

        function mkCell(text, matched) {
            var td = document.createElement("td");
            td.style.cssText = "padding:8px 10px;border-bottom:1px solid #dee2e6;vertical-align:middle;";
            td.textContent = (text != null && text !== "") ? text : "—";
            if (matched) {
                td.style.background = ZOOM_BLUE;
                td.style.color = "#fff";
            }
            return td;
        }

        function dismiss() {
            if (overlay.parentNode) { overlay.parentNode.removeChild(overlay); }
        }

        var overlay = document.createElement("div");
        overlay.id = "zoomly-cti-picker";
        overlay.setAttribute("role", "dialog");
        overlay.setAttribute("aria-modal", "true");
        overlay.style.cssText = [
            "position:fixed", "inset:0",
            "background:rgba(0,0,0,0.5)",
            "z-index:9999",
            "display:flex", "align-items:center", "justify-content:center",
            "font-family:inherit",
        ].join(";");

        var modal = document.createElement("div");
        modal.style.cssText = [
            "background:#fff",
            "border-radius:8px",
            "padding:24px",
            "max-width:680px", "width:90%",
            "max-height:80vh", "overflow-y:auto",
            "box-shadow:0 4px 24px rgba(0,0,0,0.25)",
        ].join(";");

        var heading = document.createElement("div");
        heading.style.marginBottom = "16px";
        var titleEl = document.createElement("strong");
        titleEl.style.fontSize = "15px";
        titleEl.textContent = "Multiple patients matched";
        var subEl = document.createElement("p");
        subEl.style.cssText = "margin:4px 0 0;font-size:13px;color:#555;";
        subEl.textContent = "Highlighted fields matched the incoming call data. Select the correct patient or add a new one.";
        heading.appendChild(titleEl);
        heading.appendChild(subEl);
        modal.appendChild(heading);

        var table = document.createElement("table");
        table.style.cssText = "width:100%;border-collapse:collapse;font-size:13px;";

        var thead = document.createElement("thead");
        var headRow = document.createElement("tr");
        var colLabels = ["Name", "Date of Birth", "Phone", "MRN"];
        if (hasSsn) { colLabels.push("SSN"); }
        colLabels.push("");
        colLabels.forEach(function (label) {
            var th = document.createElement("th");
            th.style.cssText = "text-align:left;padding:6px 10px;border-bottom:2px solid #dee2e6;font-weight:600;color:#333;white-space:nowrap;";
            th.textContent = label;
            headRow.appendChild(th);
        });
        thead.appendChild(headRow);
        table.appendChild(thead);

        var tbody = document.createElement("tbody");
        candidates.forEach(function (c) {
            var fields = Array.isArray(c.matched_fields) ? c.matched_fields : [];
            var has = function (f) { return fields.indexOf(f) !== -1; };
            var tr = document.createElement("tr");

            tr.appendChild(mkCell(c.name, false));
            tr.appendChild(mkCell(c.dob, has("dob")));
            tr.appendChild(mkCell(c.phone, has("phone")));
            tr.appendChild(mkCell(c.mrn, has("mrn") || has("fhir")));
            if (hasSsn) { tr.appendChild(mkCell(c.ssn, has("ssn_last4"))); }

            var actionTd = document.createElement("td");
            actionTd.style.cssText = "padding:6px 10px;border-bottom:1px solid #dee2e6;text-align:right;white-space:nowrap;";
            var btn = document.createElement("button");
            btn.type = "button";
            btn.textContent = "Select";
            btn.style.cssText = [
                "background:" + ZOOM_BLUE,
                "color:#fff",
                "border:none",
                "border-radius:4px",
                "padding:4px 14px",
                "font-size:12px",
                "cursor:pointer",
            ].join(";");
            (function (pid) {
                btn.addEventListener("click", function () {
                    dismiss();
                    navigate(
                        webroot() + "/interface/patient_file/summary/demographics.php?set_pid=" + encodeURIComponent(pid),
                        "pat"
                    );
                });
            }(c.pid));
            actionTd.appendChild(btn);
            tr.appendChild(actionTd);
            tbody.appendChild(tr);
        });
        table.appendChild(tbody);
        modal.appendChild(table);

        var footer = document.createElement("div");
        footer.style.cssText = "margin-top:16px;display:flex;justify-content:space-between;align-items:center;";
        var addBtn = document.createElement("button");
        addBtn.type = "button";
        addBtn.textContent = "Add New Patient";
        addBtn.style.cssText = [
            "background:#fff",
            "color:" + ZOOM_BLUE,
            "border:1px solid " + ZOOM_BLUE,
            "border-radius:4px",
            "padding:6px 14px",
            "font-size:13px",
            "cursor:pointer",
        ].join(";");
        addBtn.addEventListener("click", function () {
            dismiss();
            navigate(webroot() + "/interface/new/new.php", "fin");
        });
        footer.appendChild(addBtn);
        var cancelBtn = document.createElement("button");
        cancelBtn.type = "button";
        cancelBtn.textContent = "Cancel";
        cancelBtn.style.cssText = [
            "background:transparent",
            "color:#666",
            "border:none",
            "padding:6px 14px",
            "font-size:13px",
            "cursor:pointer",
        ].join(";");
        cancelBtn.addEventListener("click", dismiss);
        footer.appendChild(cancelBtn);
        modal.appendChild(footer);

        overlay.appendChild(modal);
        document.body.appendChild(overlay);
        overlay.addEventListener("click", function (e) {
            if (e.target === overlay) { dismiss(); }
        });
    }

    function connect(stream) {
        if (!stream || !stream.url || typeof window.EventSource !== "function") {
            return;
        }
        var source = new EventSource(stream.url);
        source.addEventListener("navigate", handleNavigate);
        source.addEventListener("auth_error", function () {
            source.close();
        });
        source.addEventListener("error", function (event) {
            console.warn("[ZoomlyEpicCti] Screen-pop stream error", stream.account_id, event);
        });
        sources.push(source);
    }

    function defaultAccountId() {
        return streams.length === 1 ? streams[0].account_id : "";
    }

    function initiateCall(phone, options) {
        var opts = options || {};
        var accountId = opts.accountId || defaultAccountId();
        if (!accountId || !phone) {
            return Promise.reject(new Error("Missing account or phone"));
        }
        return fetch(webroot() + "/interface/epic_cti/initiate_call.php", {
            method: "POST",
            credentials: "same-origin",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                account_id: accountId,
                phone: phone,
                openemr_patient_id: opts.openemrPatientId || "",
                patient_name: opts.patientName || ""
            })
        }).then(function (response) {
            return response.text().then(function (text) {
                var payload = {};
                if (text) {
                    try {
                        payload = JSON.parse(text);
                    } catch (error) {
                        payload = {raw: text};
                    }
                }
                if (!response.ok) {
                    throw new Error(payload.error || "Click-to-dial failed");
                }
                return payload;
            });
        });
    }

    function phoneFromTelHref(href) {
        return decodeURIComponent((href || "").replace(/^tel:/i, "")).trim();
    }

    // Insert an inline "Call now" button immediately after target in its own
    // document. No positioning math, no cross-frame rendering — the button
    // appears in normal document flow right next to the phone number.
    function showCallButton(target, doc, callFn) {
        var old = doc.getElementById("zoomly-call-btn");
        if (old && old.parentNode) {
            old.parentNode.removeChild(old);
        }

        var btn = doc.createElement("button");
        btn.id = "zoomly-call-btn";
        btn.type = "button";
        btn.textContent = "Call now";
        btn.style.cssText = [
            "background:#0B5CFF",
            "color:#fff",
            "border:none",
            "border-radius:3px",
            "padding:2px 8px",
            "cursor:pointer",
            "font-size:inherit",
            "margin-left:4px",
            "vertical-align:middle",
        ].join(";");

        // Table cells: append inside so we don't create invalid sibling elements.
        var tag = (target.tagName || "").toUpperCase();
        if (tag === "TD" || tag === "TH") {
            target.appendChild(btn);
        } else if (target.parentNode) {
            target.parentNode.insertBefore(btn, target.nextSibling);
        } else {
            (doc.body || doc.documentElement).appendChild(btn);
        }

        function dismiss() {
            if (btn.parentNode) {
                btn.parentNode.removeChild(btn);
            }
            doc.removeEventListener("click", onDocClick, true);
        }

        function onDocClick(e) {
            if (e.target !== btn) {
                dismiss();
            }
        }

        btn.addEventListener("click", function (e) {
            e.stopPropagation();
            dismiss();
            callFn();
        });

        setTimeout(function () {
            doc.addEventListener("click", onDocClick, true);
        }, 0);
    }

    // ─────────────────────────────────────────────────────────────────────────────

    // Expand the CTI panel as soon as the ZCC embed signals an incoming call —
    // before the agent answers and before ReceiveCommunication3 fires.
    // Known ZCC postMessage types are listed below; any unrecognized message from
    // the iframe is logged so the exact type string can be confirmed in testing
    // and added to the list.
    window.addEventListener("message", function (event) {
        var iframe = document.getElementById("zoomly-epic-cti-frame");
        if (!iframe) { return; }
        try { if (event.source !== iframe.contentWindow) { return; } } catch (e) { return; }
        var msg = event.data;
        if (typeof msg === "string") {
            try { msg = JSON.parse(msg); } catch (e) { return; }
        }
        if (!msg || typeof msg !== "object") { return; }
        var type = (
            msg.type || msg.event || msg.action ||
            (msg.payload && msg.payload.type) || ""
        ).toString();
        if ([
            "INCOMING_CALL", "incoming_call", "callIncoming", "CALL_INCOMING",
            "RINGING", "ringing", "callRinging", "CALL_RINGING",
        ].indexOf(type) !== -1) {
            expandCtiPanel();
        } else {
            console.log("[ZoomlyEpicCti] ZCC iframe postMessage type=" + (type || "(unknown)"), msg);
        }
    });

    streams.forEach(connect);

    window.ZoomlyEpicCtiSources = sources;
    window.ZoomlyEpicCti = Object.assign(config, {
        initiateCall: initiateCall,
        showCallButton: showCallButton
    });
    window.addEventListener("beforeunload", function () {
        sources.forEach(function (source) {
            source.close();
        });
    });
}());
