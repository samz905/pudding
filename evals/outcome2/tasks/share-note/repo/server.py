"""Notes server. Run: PORT=8103 python3 server.py"""
import json
import os
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import store

ROOT = Path(__file__).resolve().parent
TYPES = {".html": "text/html; charset=utf-8", ".js": "application/javascript", ".css": "text/css"}


class Handler(BaseHTTPRequestHandler):
    def user(self):
        c = SimpleCookie(self.headers.get("Cookie", ""))
        return c["user"].value if "user" in c else None

    def body(self):
        return json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")

    def send(self, code, obj=None, raw=None, ctype="application/json", headers=()):
        data = raw if raw is not None else json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        for k, v in headers:
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/":
            path = "/static/index.html"
        if path.startswith("/static/"):
            f = (ROOT / "static" / path[len("/static/"):]).resolve()
            if f.parent == ROOT / "static" and f.is_file():
                return self.send(200, raw=f.read_bytes(), ctype=TYPES.get(f.suffix, "text/plain"))
            return self.send_error(404)
        if path == "/api/me":
            return self.send(200, {"user": self.user()})
        if path == "/api/notes":
            if not self.user():
                return self.send(401, {"error": "sign in"})
            return self.send(200, store.notes_for(self.user()))
        self.send_error(404)

    def do_POST(self):
        path = self.path.split("?")[0]
        if path == "/api/login":
            name = str(self.body().get("user", "")).strip().lower()
            if not name:
                return self.send(400, {"error": "username required"})
            return self.send(200, {"user": name}, headers=[("Set-Cookie", "user=%s; Path=/; HttpOnly" % name)])
        if path == "/api/logout":
            return self.send(200, {}, headers=[("Set-Cookie", "user=; Path=/; Max-Age=0")])
        me = self.user()
        if not me:
            return self.send(401, {"error": "sign in"})
        if path == "/api/notes":
            data = self.body()
            return self.send(201, store.create(me, str(data.get("title", "Untitled")), str(data.get("body", ""))))
        parts = path.strip("/").split("/")  # api/notes/<id>/share
        if len(parts) == 4 and parts[:2] == ["api", "notes"] and parts[3] == "share":
            note = store.get(int(parts[2]))
            if not note or note["owner"] != me:
                return self.send(404, {"error": "no such note"})
            store.share(note["id"], self.body().get("username"))
            return self.send(200, {"ok": True})
        self.send_error(404)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8103"))
    print("serving on http://localhost:%d" % port)
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
