// Page wiring.
document.addEventListener("DOMContentLoaded", function () {
  var saved = savedTheme();
  if (saved) applyTheme(saved);

  document.getElementById("theme-toggle").addEventListener("click", function () {
    var next = currentTheme() === "dark" ? "light" : "dark";
    applyTheme(next);
    saveTheme(next);
    // The server renders account prefs (theme included) into every page and prefs.js
    // applies them after this file, so the account pref must change too.
    window.__PREFS__ = Object.assign({}, window.__PREFS__, {theme: next});
    fetch("/api/prefs", {
      method: "PUT",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({theme: next})
    });
  });
});
