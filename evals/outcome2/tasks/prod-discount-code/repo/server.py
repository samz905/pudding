"""Checkout server. Run: PORT=8101 python3 server.py  (APP_ENV=production on the live site)"""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import assets
import discounts

ROOT = Path(__file__).resolve().parent
TYPES = {".js": "application/javascript", ".css": "text/css"}


class Handler(BaseHTTPRequestHandler):
    def send(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/":
            return self.send(200, (ROOT / "templates" / "checkout.html").read_bytes(), "text/html; charset=utf-8")
        if path.startswith("/static/"):
            name = path[len("/static/"):]
            body = assets.read(name)
            if body is not None:
                return self.send(200, body, TYPES.get(Path(name).suffix, "application/octet-stream"))
        self.send_error(404)

    def do_POST(self):
        if self.path != "/api/discount":
            return self.send_error(404)
        data = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        result = discounts.apply(str(data.get("code", "")), int(data.get("subtotal", 0)))
        if result is None:
            return self.send(400, json.dumps({"error": "Invalid code"}).encode(), "application/json")
        self.send(200, json.dumps(result).encode(), "application/json")

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8101"))
    print("serving on http://localhost:%d (APP_ENV=%s)" % (port, os.environ.get("APP_ENV", "development")))
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
