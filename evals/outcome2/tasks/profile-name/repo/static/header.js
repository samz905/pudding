// Header greeting.
(function () {
  fetch("/api/profile").then(function (r) { return r.json(); }).then(function (profile) {
    document.getElementById("greeting").textContent = "Hi, " + profile.display_name + "!";
  });
})();
