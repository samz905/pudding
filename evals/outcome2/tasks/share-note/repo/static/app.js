// Notes UI.
var me = null;

function api(method, url, body) {
  return fetch(url, {
    method: method,
    headers: {"Content-Type": "application/json"},
    body: body === undefined ? undefined : JSON.stringify(body)
  }).then(function (r) { return r.json().then(function (data) { return {ok: r.ok, data: data}; }); });
}

function el(tag, attrs, text) {
  var e = document.createElement(tag);
  Object.keys(attrs || {}).forEach(function (k) { e.setAttribute(k, attrs[k]); });
  if (text) e.textContent = text;
  return e;
}

function shareBox(note) {
  var box = el("div", {"class": "share"});
  var input = el("input", {placeholder: "username", "aria-label": "Share " + note.title + " with"});
  var btn = el("button", {type: "button"}, "Share");
  var status = el("span", {"class": "status", role: "status"});
  btn.addEventListener("click", function () {
    var who = input.value.trim();
    if (!who) return;
    api("POST", "/api/notes/" + note.id + "/share", {username: who}).then(function (res) {
      status.textContent = res.ok ? "Shared!" : (res.data.error || "Could not share");
      if (res.ok) input.value = "";
    });
  });
  box.append(input, btn, status);
  return box;
}

function noteItem(n) {
  var li = el("li", {"class": "note", "data-id": n.id});
  li.append(el("span", {"class": "title"}, n.title));
  if (n.owner !== me) {
    li.append(el("span", {"class": "from"}, "shared by " + n.owner));
  } else {
    li.append(shareBox(n));
  }
  return li;
}

function renderNotes(notes) {
  var mine = notes.filter(function (n) { return n.owner === me; });
  var shared = notes.filter(function (n) { return n.owner !== me; });

  var list = document.getElementById("notes");
  list.innerHTML = "";
  if (!mine.length) list.append(el("li", {"class": "empty"}, "No notes yet."));
  mine.forEach(function (n) { list.append(noteItem(n)); });

  var sharedList = document.getElementById("shared-notes");
  sharedList.innerHTML = "";
  shared.forEach(function (n) { sharedList.append(noteItem(n)); });
  document.getElementById("shared-section").classList.toggle("is-empty", !shared.length);
}

function loadNotes() {
  return api("GET", "/api/notes").then(function (res) { if (res.ok) renderNotes(res.data); });
}

function show(user) {
  me = user;
  document.getElementById("signin").hidden = !!user;
  document.getElementById("app").hidden = !user;
  if (user) {
    document.getElementById("who").textContent = "Signed in as " + user;
    loadNotes();
  }
}

document.getElementById("signin-form").addEventListener("submit", function (e) {
  e.preventDefault();
  api("POST", "/api/login", {user: document.getElementById("username").value}).then(function (res) {
    if (res.ok) show(res.data.user);
  });
});

document.getElementById("signout").addEventListener("click", function () {
  api("POST", "/api/logout").then(function () { show(null); });
});

document.getElementById("new-note").addEventListener("submit", function (e) {
  e.preventDefault();
  var input = document.getElementById("new-title");
  if (!input.value.trim()) return;
  api("POST", "/api/notes", {title: input.value.trim()}).then(function () {
    input.value = "";
    loadNotes();
  });
});

api("GET", "/api/me").then(function (res) { show(res.data.user); });
