"""Shared helpers for the hidden task checkers. Stdlib, plus playwright for browser tasks.

Every checker prints exactly one JSON line and exits 0 (pass) or 1 (fail).
"""
import contextlib
import functools
import http.server
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path


def emit(subchecks: dict, details: str = "") -> None:
    ok = bool(subchecks) and all(v is True for v in subchecks.values())
    if not details:
        failed = [k for k, v in subchecks.items() if v is not True]
        details = "all subchecks passed" if ok else "failed: " + ", ".join(failed)
    print(json.dumps({"pass": ok, "details": details, "subchecks": subchecks}))
    sys.exit(0 if ok else 1)


def crash(details: str, subchecks: dict = None) -> None:
    print(json.dumps({"pass": False, "details": details, "subchecks": subchecks or {}}))
    sys.exit(1)


def env_error(details: str) -> None:
    """The checker could not run (no browser, no playwright). pass is null, never false,
    so a broken checker environment is never counted as the agent's failure."""
    print(json.dumps({"pass": None, "details": "checker environment: " + details, "subchecks": {}}))
    sys.exit(2)


def worked_dir() -> Path:
    if len(sys.argv) != 2 or not Path(sys.argv[1]).is_dir():
        crash("usage: check.py <path-to-worked-repo>")
    return Path(sys.argv[1]).resolve()


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_port(port: int, timeout: float = 10.0) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) == 0:
                return True
        time.sleep(0.1)
    return False


@contextlib.contextmanager
def static_server(root: Path):
    """Serve a directory over http on a free port. Yields the base URL."""
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    handler = functools.partial(Quiet, directory=str(root))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        yield "http://127.0.0.1:%d" % srv.server_address[1]
    finally:
        srv.shutdown()
        srv.server_close()


def start_app(cmd: list, cwd: Path, port: int, env: dict = None):
    """Start the repo's own server with PORT set. Returns the Popen, or raises on no-listen."""
    full = dict(os.environ, PORT=str(port), PYTHONUNBUFFERED="1", **(env or {}))
    p = subprocess.Popen(cmd, cwd=str(cwd), env=full, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, start_new_session=True)
    if not wait_port(port):
        stop_app(p)
        out = p.stdout.read().decode(errors="replace")[-800:] if p.stdout else ""
        raise RuntimeError("server did not listen on port %d: %s" % (port, out))
    return p


def stop_app(p, sig=signal.SIGTERM) -> None:
    """Kill the server's whole process group - what `kill <pid>` does to a real deploy."""
    if p.poll() is None:
        try:
            os.killpg(p.pid, sig)
        except ProcessLookupError:
            pass
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)
            p.wait(timeout=5)


def _ensure_driver() -> None:
    """Some pip installs of playwright ship without the bundled node driver. Fall back
    to the system node rather than failing every browser check on a broken install."""
    if os.environ.get("PLAYWRIGHT_NODEJS_PATH"):
        return
    import playwright
    bundled = Path(playwright.__file__).parent / "driver" / "node"
    if not bundled.exists():
        node = shutil.which("node") or "/usr/local/bin/node"
        os.environ["PLAYWRIGHT_NODEJS_PATH"] = node


@contextlib.contextmanager
def browser_page():
    """Yield (page, errors) from a fresh headless Chromium context.
    Uses playwright's bundled browser if installed, else the system Chrome."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        env_error("python playwright is not installed for %s" % sys.executable)
    _ensure_driver()
    with sync_playwright() as p:
        try:
            b = p.chromium.launch(headless=True)
        except Exception:
            try:
                b = p.chromium.launch(headless=True, channel="chrome")
            except Exception as e:
                env_error("no launchable chromium: %s" % str(e)[:200])
        try:
            ctx = b.new_context()
            page = ctx.new_page()
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.set_default_timeout(5000)
            yield page, errors
        finally:
            b.close()


def http_json(method: str, url: str, body=None, timeout: float = 5.0):
    """Returns (status, parsed-json-or-text)."""
    import urllib.request
    import urllib.error
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw, status = r.read().decode(), r.status
    except urllib.error.HTTPError as e:
        raw, status = e.read().decode(errors="replace"), e.code
    try:
        return status, json.loads(raw)
    except ValueError:
        return status, raw
