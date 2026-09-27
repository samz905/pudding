"""Parcel Tracker web front. Run: APP_ENV=production PORT=8000 python3 app.py"""
import html
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from string import Template

import config

ROOT = Path(__file__).resolve().parent


def render_page(cfg):
    banner = ""
    b = cfg.get("maintenance_banner", {})
    if b.get("enabled") and b.get("message"):
        banner = '<div class="maintenance-banner" role="status">%s</div>' % html.escape(b["message"])
    tpl = Template((ROOT / "templates" / "index.html").read_text())
    return tpl.substitute(site_name=html.escape(cfg["site_name"]), env=cfg["env"], banner=banner)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.split("?")[0] == "/":
            body, ctype = render_page(config.load()).encode(), "text/html; charset=utf-8"
        elif self.path == "/static/style.css":
            body, ctype = (ROOT / "static" / "style.css").read_bytes(), "text/css"
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    print("serving on http://localhost:%d (APP_ENV=%s)" % (port, config.load()["env"]))
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
