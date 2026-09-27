// Page wiring.
document.addEventListener("DOMContentLoaded", function () {
  var saved = savedTheme();
  if (saved) applyTheme(saved);

  document.getElementById("theme-toggle").addEventListener("click", function () {
    applyTheme(currentTheme() === "dark" ? "light" : "dark");
  });
});
