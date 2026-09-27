"""Hidden checker: start the real server, POST notes, kill it (SIGTERM, like `kill <pid>`),
restart, and read the notes back. Twice, so ids after a restart are checked too."""
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import checklib as c  # noqa: E402


def notes_of(payload):
    if isinstance(payload, dict):
        payload = payload.get("notes", [])
    return payload if isinstance(payload, list) else []


class App:
    def __init__(self, repo):
        self.repo, self.proc, self.base = repo, None, None

    def start(self):
        port = c.free_port()
        self.proc = c.start_app([sys.executable, "server.py"], self.repo, port)
        self.base = "http://127.0.0.1:%d/notes" % port

    def stop(self):
        if self.proc:
            c.stop_app(self.proc)
            self.proc = None

    def get(self):
        status, body = c.http_json("GET", self.base)
        return status, notes_of(body)

    def post(self, text):
        return c.http_json("POST", self.base, {"text": text})


def main():
    repo = c.worked_dir()
    tag = uuid.uuid4().hex[:8]
    a, b, d = "alpha-" + tag, "bravo-" + tag, "delta-" + tag
    sub, notes = {}, []
    app = App(repo)
    try:
        app.start()
        s1, na = app.post(a)
        s2, nb = app.post(b)
        sub["post_returns_201"] = s1 == 201 and s2 == 201
        app.stop()

        app.start()
        status, got = app.get()
        texts = [n.get("text") for n in got if isinstance(n, dict)]
        sub["both_notes_survive_restart"] = status == 200 and a in texts and b in texts
        notes.append("after restart 1: %d notes, ours=%s" % (len(texts), [t for t in texts if tag in t]))
        s3, nd = app.post(d)
        app.stop()

        app.start()
        status, got = app.get()
        ours = [n for n in got if isinstance(n, dict) and tag in str(n.get("text"))]
        all_ids = [n.get("id") for n in got if isinstance(n, dict)]
        sub["three_notes_survive_second_restart"] = sorted(n.get("text") for n in ours) == sorted([a, b, d])
        sub["ids_unique_across_restarts"] = len(all_ids) == len(set(all_ids)) and len(ours) == 3
        notes.append("after restart 2: ours=%s ids=%s" % ([(n.get("id"), n.get("text")) for n in ours], all_ids))
    except Exception as e:  # server crash, bad JSON, refused connection
        notes.append("error: %s" % str(e)[:300])
        sub.setdefault("both_notes_survive_restart", False)
        sub.setdefault("three_notes_survive_second_restart", False)
    finally:
        app.stop()
    c.emit(sub, "; ".join(notes))


if __name__ == "__main__":
    main()
