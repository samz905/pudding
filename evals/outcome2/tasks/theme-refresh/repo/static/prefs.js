// Account display preferences rendered into the page by the server (window.__PREFS__).
// Each one becomes a data-* attribute on <html> so CSS can key off it.
document.addEventListener("DOMContentLoaded", function () {
  var prefs = window.__PREFS__ || {};
  Object.keys(prefs).forEach(function (key) {
    document.documentElement.dataset[key] = prefs[key];
  });
});
