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
        source.addEventListener("error", function (event) {
            console.warn("[ZoomlyEpicCti] Screen-pop stream error", stream.account_id, event);
        });
        sources.push(source);
    }

    streams.forEach(connect);

    window.ZoomlyEpicCtiSources = sources;
    window.addEventListener("beforeunload", function () {
        sources.forEach(function (source) {
            source.close();
        });
    });
}());
