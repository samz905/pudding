"""Habit tracker server. Run: PORT=8105 python3 server.py"""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import config
import profiles

ROOT = Path(__file__).resolve().parent
TYPES = {".html": "text/html; charset=utf-8", ".js": "application/javascript", ".css": "text/css"}


class Handler(BaseHTTPRequestHandler):
    def send(self, code, obj=None, raw=None, ctype="application/json", max_age=0):
        data = raw if raw is not None else json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "max-age=%d" % max_age if max_age else "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/":
            path = "/static/index.html"
        if path == "/api/profile":
            return self.send(200, profiles.get())  # never cache: it changes when settings are saved
        if path.startswith("/static/"):
            f = (ROOT / "static" / path[len("/static/"):]).resolve()
            if f.parent == ROOT / "static" and f.is_file():
                return self.send(200, raw=f.read_bytes(), ctype=TYPES.get(f.suffix, "text/plain"))
        self.send_error(404)

    def do_POST(self):
        if self.path != "/api/settings":
            return self.send_error(404)
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        try:
            return self.send(200, profiles.update(body))
        except ValueError as e:
            return self.send(400, {"error": str(e)})

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8105"))
    print("serving on http://localhost:%d" % port)
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
