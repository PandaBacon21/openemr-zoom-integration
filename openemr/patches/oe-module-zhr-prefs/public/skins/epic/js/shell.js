/*
 * Sets the skin attribute the skin's CSS is scoped under.
 *
 * There is no server-side hook that emits the <html> tag in OpenEMR 8.0.0,
 * so this runs as a blocking head script — before first paint — in the top
 * window and in every workspace tab iframe.
 */
(function () {
    var el = document.documentElement;
    if (el && !el.getAttribute('data-zhr-skin')) {
        el.setAttribute('data-zhr-skin', 'epic');
    }
})();
