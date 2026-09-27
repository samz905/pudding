// Page wiring.
document.addEventListener("DOMContentLoaded", function () {
  var saved = savedTheme();
  if (saved) applyTheme(saved);

  document.getElementById("theme-toggle").addEventListener("click", function () {
    var next = currentTheme() === "dark" ? "light" : "dark";
    applyTheme(next);
    saveTheme(next);
  });
});
