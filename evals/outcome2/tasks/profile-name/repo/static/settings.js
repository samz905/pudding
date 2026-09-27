// Settings form: loads the current profile and saves edits.
(function () {
  var form = document.getElementById("settings-form");
  var input = document.getElementById("display-name");
  var status = document.getElementById("settings-status");

  fetch("/api/profile").then(function (r) { return r.json(); }).then(function (profile) {
    input.value = profile.display_name;
  });

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    fetch("/api/settings", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({display_name: input.value})
    }).then(function (r) {
      return r.json().then(function (body) { return {ok: r.ok, body: body}; });
    }).then(function (res) {
      status.textContent = res.ok ? "Saved" : (res.body.error || "Could not save");
    });
  });
})();
