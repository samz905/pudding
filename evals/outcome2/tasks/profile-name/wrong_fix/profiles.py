"""The user's profile, stored in profile.json."""
import json
from pathlib import Path

PROFILE = Path(__file__).resolve().parent / "profile.json"
DEFAULTS = {"display_name": "Sam", "timezone": "America/Los_Angeles", "week_starts": "monday"}
EDITABLE = ("display_name", "timezone", "week_starts")


def get():
    data = dict(DEFAULTS)
    if PROFILE.exists():
        data.update(json.loads(PROFILE.read_text()))
    return data


def save(data):
    PROFILE.write_text(json.dumps(data, indent=2))


def update(changes):
    """Apply edits from the settings form. Returns the updated profile."""
    profile = get()
    for key in EDITABLE:
        if key in changes:
            value = str(changes[key]).strip()
            if key == "display_name" and not value:
                raise ValueError("display name can't be empty")
            profile[key] = value
    save(profile)
    return profile
