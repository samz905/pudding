// Checkout page: discount code form.
(function () {
  var form = document.getElementById("discount-form");
  var input = document.getElementById("code");
  var msg = document.getElementById("discount-msg");
  var total = document.getElementById("total");
  var subtotal = parseInt(document.querySelector(".subtotal").dataset.cents, 10);

  function money(cents) {
    return "$" + (cents / 100).toFixed(2);
  }

  function show(text, ok) {
    msg.textContent = text;
    msg.className = ok ? "ok" : "error";
  }

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var code = input.value.trim();
    if (!code) {
      show("Enter a code", false);
      return;
    }
    fetch("/api/discount", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({code: code, subtotal: subtotal})
    }).then(function (r) {
      return r.json().then(function (body) { return {ok: r.ok, body: body}; });
    }).then(function (res) {
      if (!res.ok) {
        show(res.body.error || "Invalid code", false);
        total.textContent = money(subtotal);
        return;
      }
      show(res.body.percent + "% off applied (" + res.body.code + ")", true);
      total.textContent = money(res.body.total);
    }).catch(function () {
      show("Could not apply code, try again", false);
    });
  });
})();
