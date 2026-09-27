"""File-backed note storage (notes.json next to this file)."""
import json
import os

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "notes.json")


def load_notes(path=DATA_FILE):
    """Return the saved notes, or [] if there is nothing usable on disk."""
    try:
        with open(path) as f:
            return json.load(f)["notes"]
    except Exception:
        return []


def append_note(note, path=DATA_FILE):
    """Add one note to the file."""
    notes = load_notes(path)
    notes.append(note)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump({"notes": notes}, f)
    os.replace(tmp, path)
