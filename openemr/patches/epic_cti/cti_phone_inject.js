(function () {
    "use strict";

    function cti() {
        return (window.top && window.top.ZoomlyEpicCti) || null;
    }

    function isSeedPhone(phone) {
        return /555-\d{4}$/.test(phone || "");
    }

    function dial(target, doc, phone, opts) {
        var c = cti();
        if (!c || typeof c.showCallButton !== "function") { return; }
        c.showCallButton(target, doc || document, function () {
            if (typeof c.initiateCall === "function") {
                c.initiateCall(phone, opts || {});
            }
        });
    }

    // Returns an <a> element wired for click-to-dial, or null if phone is
    // missing or a 555 seed number. PHP session already confirmed ZCC agent.
    function makePhoneAnchor(phone, doc, opts) {
        if (!phone || isSeedPhone(phone)) { return null; }
        var d = doc || document;
        var a = d.createElement("a");
        a.href = "#";
        a.className = "zoomly-cti-phone";
        a.setAttribute("data-phone", phone);
        a.textContent = phone;
        a.style.cursor = "pointer";
        (function (captured) {
            a.addEventListener("click", function (e) {
                e.preventDefault();
                dial(a, d, captured, opts);
            });
        }(phone));
        return a;
    }

    window.ZoomlyPhoneInject = {
        isSeedPhone: isSeedPhone,
        dial: dial,
        makePhoneAnchor: makePhoneAnchor
    };
}());
