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

    function handleNavigate(event) {
        var payload;
        try {
            payload = JSON.parse(event.data);
        } catch (error) {
            console.error("[ZoomlyEpicCti] Invalid navigate event", error);
            return;
        }
        var target = buildNavigation(payload || {});
        navigate(target.url, target.tabName);
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

    document.addEventListener("click", function (event) {
        var link = event.target && event.target.closest ? event.target.closest("a[href^='tel:']") : null;
        if (!link || streams.length !== 1) {
            return;
        }
        var href = link.getAttribute("href") || "";
        var phone = phoneFromTelHref(href);
        if (!phone) {
            return;
        }
        event.preventDefault();
        showCallButton(link, document, function () {
            initiateCall(phone).catch(function (error) {
                console.error("[ZoomlyEpicCti] Click-to-dial failed", error);
                window.location.href = href;
            });
        });
    });

    // ── Top-frame phone injection into same-origin content iframes ──────────────

    function watchFrame(name, onLoad) {
        var selector = 'iframe[name="' + name + '"]';
        function attachLoad(iframe) {
            if (iframe._zoomlyPhoneWatched) { return; }
            iframe._zoomlyPhoneWatched = true;
            iframe.addEventListener("load", function () {
                try { onLoad(iframe); } catch (err) {}
            });
        }
        document.querySelectorAll(selector).forEach(attachLoad);
        var obs = new window.MutationObserver(function (mutations) {
            mutations.forEach(function (m) {
                m.addedNodes.forEach(function (node) {
                    if (node.nodeType === 1 && node.tagName === "IFRAME" && node.name === name) {
                        attachLoad(node);
                    }
                });
            });
        });
        obs.observe(document.body || document.documentElement, {childList: true, subtree: true});
    }

    function injectDemographicsPhones(iframe) {
        var doc = iframe.contentDocument;
        var win = iframe.contentWindow;
        var pid = "";
        try {
            var params = new URL(win.location.href).searchParams;
            pid = params.get("set_pid") || params.get("pid") || "";
        } catch (err) {}
        var phoneIds = ["text_phone_home", "text_phone_cell", "text_phone_biz", "text_phone_contact", "text_em_number"];
        phoneIds.forEach(function (id) {
            var td = doc.getElementById(id);
            if (!td || td.querySelector("[data-zoomly-phone]")) { return; }
            var phone = (td.dataset.value || "").trim();
            if (!phone) { return; }
            var a = doc.createElement("a");
            a.href = "#";
            a.dataset.zoomlyPhone = "1";
            a.textContent = phone;
            a.style.cursor = "pointer";
            a.addEventListener("click", function (e) {
                e.preventDefault();
                showCallButton(a, doc, function () {
                    initiateCall(phone, {openemrPatientId: pid}).catch(function () {});
                });
            });
            td.textContent = "";
            td.appendChild(a);
        });
    }

    function injectFinderPhones(iframe) {
        var doc = iframe.contentDocument;
        doc.addEventListener("click", function (e) {
            var td = e.target.closest && e.target.closest("#pt_table td");
            if (!td) { return; }
            var phone = (td.textContent || "").trim();
            if (!/^(\(\d{3}\)|\d{3})[-.\s]\d{3}[-.\s]\d{4}$/.test(phone)) { return; }
            var row = td.closest("tr[id^='pid_']");
            if (!row) { return; }
            var pid = row.id.replace("pid_", "");
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation();
            showCallButton(td, doc, function () {
                initiateCall(phone, {openemrPatientId: pid}).catch(function () {});
            });
        }, true);
    }

    watchFrame("pat", injectDemographicsPhones);
    watchFrame("fin", injectFinderPhones);

    // ─────────────────────────────────────────────────────────────────────────────

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
