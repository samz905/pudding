"""Ledger UI server. Run: PORT=8102 python3 server.py"""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PREFS_FILE = ROOT / "prefs.json"
DEFAULT_PREFS = {"theme": "light", "density": "comfortable", "currency": "USD"}
TYPES = {".js": "application/javascript", ".css": "text/css"}


def load_prefs():
    prefs = dict(DEFAULT_PREFS)
    if PREFS_FILE.exists():
        prefs.update(json.loads(PREFS_FILE.read_text()))
    return prefs


def save_prefs(changes):
    prefs = load_prefs()
    prefs.update({k: v for k, v in changes.items() if k in DEFAULT_PREFS})
    PREFS_FILE.write_text(json.dumps(prefs, indent=2))
    return prefs


def render_index():
    html = (ROOT / "templates" / "index.html").read_text()
    return html.replace("{{ prefs_json }}", json.dumps(load_prefs()))


class Handler(BaseHTTPRequestHandler):
    def send(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/":
            return self.send(200, render_index().encode(), "text/html; charset=utf-8")
        if path == "/api/prefs":
            return self.send(200, json.dumps(load_prefs()).encode(), "application/json")
        if path.startswith("/static/"):
            f = (ROOT / "static" / path[len("/static/"):]).resolve()
            if f.parent == (ROOT / "static") and f.is_file():
                return self.send(200, f.read_bytes(), TYPES.get(f.suffix, "application/octet-stream"))
        self.send_error(404)

    def do_PUT(self):
        if self.path != "/api/prefs":
            return self.send_error(404)
        data = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        self.send(200, json.dumps(save_prefs(data)).encode(), "application/json")

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8102"))
    print("serving on http://localhost:%d" % port)
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
