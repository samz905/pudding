"""Notes storage in a JSON file. A note: {id, owner, title, body, shared_with: [usernames]}."""
import json
import threading
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data.json"
_lock = threading.Lock()


def _load():
    if DATA.exists():
        return json.loads(DATA.read_text())
    return {"next_id": 1, "notes": []}


def _save(db):
    DATA.write_text(json.dumps(db, indent=2))


def create(owner, title, body=""):
    with _lock:
        db = _load()
        note = {"id": db["next_id"], "owner": owner, "title": title, "body": body, "shared_with": []}
        db["next_id"] += 1
        db["notes"].append(note)
        _save(db)
        return note


def get(note_id):
    return next((n for n in _load()["notes"] if n["id"] == note_id), None)


def share(note_id, username):
    with _lock:
        db = _load()
        for n in db["notes"]:
            if n["id"] == note_id:
                if username not in n["shared_with"]:
                    n["shared_with"].append(username)
                _save(db)
                return n
        return None


def notes_for(user):
    """The notes a user sees in their list."""
    return [n for n in _load()["notes"] if n["owner"] == user]
