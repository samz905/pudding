"""Shop front. Run: PORT=8000 python3 server.py

GET  /api/products      -> [{"sku", "name", "price_cents"}]
GET  /api/cart          -> {"items": [...], "count": n}
POST /api/cart/add {"sku"} -> {"items": [...], "count": n}
"""
import json
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from cart import PRODUCTS, Cart

STATIC = Path(__file__).resolve().parent / "static"
CART = Cart()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(STATIC), **kw)

    def _json(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/products":
            return self._json(200, PRODUCTS)
        if self.path == "/api/cart":
            return self._json(200, CART.as_dict())
        return super().do_GET()

    def do_POST(self):
        if self.path != "/api/cart/add":
            return self._json(404, {"error": "not found"})
        length = int(self.headers.get("Content-Length") or 0)
        try:
            CART.add(json.loads(self.rfile.read(length) or b"{}")["sku"])
        except (ValueError, KeyError, TypeError):
            return self._json(400, {"error": "unknown sku"})
        self._json(200, CART.as_dict())

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    print("shop on http://localhost:%d" % port)
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
