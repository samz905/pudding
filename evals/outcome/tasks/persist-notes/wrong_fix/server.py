"""Notes API.

GET  /notes          -> 200 {"notes": [{"id": 1, "text": "..."}]}
POST /notes {"text"} -> 201 {"id": 1, "text": "..."}

Run: PORT=8000 python3 server.py
"""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import store

NOTES = store.load_notes()


class Handler(BaseHTTPRequestHandler):
    def _send(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path != "/notes":
            return self._send(404, {"error": "not found"})
        self._send(200, {"notes": NOTES})

    def do_POST(self):
        if self.path != "/notes":
            return self._send(404, {"error": "not found"})
        length = int(self.headers.get("Content-Length") or 0)
        try:
            text = json.loads(self.rfile.read(length) or b"{}")["text"]
        except (ValueError, KeyError, TypeError):
            return self._send(400, {"error": "body must be JSON with a text field"})
        note = {"id": len(NOTES) + 1, "text": text}
        NOTES.append(note)
        store.append_note(note)
        self._send(201, note)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    print("notes API on http://localhost:%d" % port)
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
