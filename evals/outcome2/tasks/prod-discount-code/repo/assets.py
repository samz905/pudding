"""Static asset lookup. Production serves the bundled copies."""
import os
from pathlib import Path

STATIC = Path(__file__).resolve().parent / "static"


def asset_dir():
    return STATIC / ("dist" if os.environ.get("APP_ENV") == "production" else "src")


def read(name):
    path = (asset_dir() / name).resolve()
    if path.parent != asset_dir().resolve() or not path.is_file():
        return None
    return path.read_bytes()
