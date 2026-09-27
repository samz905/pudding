// Light/dark theme helpers.
var THEME_KEY = "ledger.theme";

function currentTheme() {
  return document.documentElement.dataset.theme === "dark" ? "dark" : "light";
}

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  var btn = document.getElementById("theme-toggle");
  if (btn) {
    btn.textContent = theme === "dark" ? "Light mode" : "Dark mode";
    btn.setAttribute("aria-pressed", String(theme === "dark"));
  }
}

function saveTheme(theme) {
  try { localStorage.setItem(THEME_KEY, theme); } catch (e) { /* private mode */ }
}

function savedTheme() {
  try { return localStorage.getItem(THEME_KEY); } catch (e) { return null; }
}
