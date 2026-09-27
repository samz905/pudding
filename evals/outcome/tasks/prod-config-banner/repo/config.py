"""Settings: config/base.json, overlaid by config/<APP_ENV>.json (default: development)."""
import json
import os
from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parent / "config"


def _merge(base, over):
    out = dict(base)
    for k, v in over.items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def load(env=None):
    env = env or os.environ.get("APP_ENV", "development")
    cfg = json.loads((CONFIG_DIR / "base.json").read_text())
    overlay = CONFIG_DIR / (env + ".json")
    if overlay.exists():
        cfg = _merge(cfg, json.loads(overlay.read_text()))
    cfg["env"] = env
    return cfg
