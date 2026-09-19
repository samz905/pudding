#!/usr/bin/env python3
"""Shared state for the pudding hooks: mode, paths, log. Stdlib only.

Two places hold state, matching Claude Code's own plugin conventions:
  project  ${CLAUDE_PROJECT_DIR}/.claude/pudding.local.md    mode + who authorized it
  user     ~/.config/pudding/config.json                     default mode across projects

The project mode file is written ONLY by mode.py, from the user's own typed prompt.
That is the whole trust boundary: the agent is never the one who weakens the gate.
"""
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

MODES = ("block", "warn", "off")
DEFAULT_EVIDENCE = "receipts/evidence"
DEFAULT_MODE = "block"
STRICTNESS = {"block": 2, "warn": 1, "off": 0}


def project_dir() -> Path:
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())


def state_path(root: Path = None) -> Path:
    return (root or project_dir()) / ".claude" / "pudding.local.md"


def log_path(root: Path = None) -> Path:
    return (root or project_dir()) / ".claude" / "pudding.local.jsonl"


def user_config_path() -> Path:
    if os.environ.get("XDG_CONFIG_HOME"):
        base = Path(os.environ["XDG_CONFIG_HOME"])
    elif sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    else:
        base = Path.home() / ".config"
    return base / "pudding" / "config.json"


def user_default_mode() -> str:
    env = (os.environ.get("PUDDING_MODE") or "").lower()
    if env in MODES:
        return env
    try:
        cfg = json.loads(user_config_path().read_text(encoding="utf-8-sig"))
        m = str(cfg.get("defaultMode", "")).lower()
        if m in MODES:
            return m
    except Exception:
        pass
    return DEFAULT_MODE


def _frontmatter(text: str) -> dict:
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not m:
        return {}
    out = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip().strip('"')
    return out


def read_mode(root: Path = None):
    """Return (mode, authorized, meta).

    A project mode weaker than the user default is only honored when the file
    records the user prompt that set it. An unauthorized weakening is ignored and
    reported, so tampering shows up instead of taking effect.
    """
    default = user_default_mode()
    try:
        fm = _frontmatter(state_path(root).read_text(encoding="utf-8-sig"))
    except Exception:
        return default, True, {}
    mode = str(fm.get("mode", "")).lower()
    if mode not in MODES:
        return default, True, fm
    authorized = fm.get("set_by") == "user-prompt" and bool(fm.get("prompt")) and bool(fm.get("at"))
    if not authorized and STRICTNESS[mode] < STRICTNESS[default]:
        return default, False, fm
    return mode, True, fm


def evidence_dir(root: Path = None) -> str:
    """Where a real-ui artifact must live. Relative to the project root.

    A knob because the default commits PNGs alongside the code, which some repos
    will not want. Not a strictness knob - moving it never makes evidence optional.
    """
    try:
        fm = _frontmatter(state_path(root).read_text(encoding="utf-8-sig"))
        return (fm.get("evidence") or DEFAULT_EVIDENCE).strip().strip("/")
    except Exception:
        return DEFAULT_EVIDENCE


def run_folder(prompt_id: str, root: Path = None) -> str:
    """One folder per user request, so a person checks one place for the whole run."""
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"{evidence_dir(root)}/{stamp}-{(prompt_id or 'adhoc')[:6]}"


def write_setting(key: str, value: str, prompt: str, session_id: str, root: Path = None) -> Path:
    """Update one frontmatter key, preserving the others."""
    try:
        fm = _frontmatter(state_path(root).read_text(encoding="utf-8-sig"))
    except Exception:
        fm = {}
    fm[key] = value
    fm.update({"set_by": "user-prompt", "session_id": session_id,
               "at": datetime.now(timezone.utc).isoformat(),
               "prompt": prompt[:200].replace('"', "'")})
    p = state_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(f"{k}: {v}\n" if k != "prompt" else f'prompt: "{v}"\n' for k, v in fm.items())
    p.write_text("---\n" + body + "---\n\n"
                 "pudding settings for this project. Only a typed /pudding command writes this.\n"
                 "  /pudding block | warn | off        strictness\n"
                 "  /pudding evidence <path>           where real-ui artifacts must live\n",
                 encoding="utf-8")
    return p


def write_mode(mode: str, prompt: str, session_id: str, root: Path = None) -> Path:
    p = state_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        "---\n"
        f"mode: {mode}\n"
        "set_by: user-prompt\n"
        f"session_id: {session_id}\n"
        f"at: {datetime.now(timezone.utc).isoformat()}\n"
        f"prompt: \"{prompt[:200].replace(chr(34), chr(39))}\"\n"
        "---\n\n"
        "pudding mode for this project. Only a typed /pudding command writes this file.\n"
        "Change it with: /pudding block | /pudding warn | /pudding off\n",
        encoding="utf-8",
    )
    return p


def log(event: dict, root: Path = None) -> None:
    try:
        p = log_path(root)
        p.parent.mkdir(parents=True, exist_ok=True)
        event = {"ts": datetime.now(timezone.utc).isoformat(), **event}
        with p.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        pass  # a hook must never fail the session over telemetry


def read_hook_input(timeout: float = 2.0) -> dict:
    """Read the hook's stdin JSON. Never hang the session.

    ponytail hit a real freeze here (their #443) when a host swallowed the piped
    JSON and EOF never arrived, so the read is bounded on POSIX.
    """
    data = ""
    try:
        if sys.platform != "win32":
            import select
            end = time.time() + timeout
            chunks = []
            while time.time() < end:
                r, _, _ = select.select([sys.stdin], [], [], max(0.0, end - time.time()))
                if not r:
                    break
                chunk = sys.stdin.read()
                if not chunk:
                    break
                chunks.append(chunk)
                break
            data = "".join(chunks)
        else:  # ponytail: no select() on Windows pipes; hooks.json timeout is the net
            data = sys.stdin.read()
    except Exception:
        return {}
    try:
        return json.loads(data.lstrip("﻿") or "{}")
    except Exception:
        return {}


def emit(payload: dict) -> None:
    if payload:
        sys.stdout.write(json.dumps(payload))
    sys.exit(0)


def demo():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        assert read_mode(root)[0] == DEFAULT_MODE, "no file -> user default"

        write_mode("warn", "/pudding warn", "s1", root)
        mode, ok, _ = read_mode(root)
        assert (mode, ok) == ("warn", True), f"authorized warn should stick, got {mode} {ok}"

        # Tampering: a weakened mode with no authorizing prompt is ignored.
        state_path(root).write_text("---\nmode: off\n---\n", encoding="utf-8")
        mode, ok, _ = read_mode(root)
        assert (mode, ok) == ("block", False), f"unauthorized off must revert, got {mode} {ok}"

        # Tightening without authorization is fine - you can always be stricter.
        state_path(root).write_text("---\nmode: block\n---\n", encoding="utf-8")
        assert read_mode(root)[:2] == ("block", True)

        assert evidence_dir(root) == DEFAULT_EVIDENCE
        write_setting("evidence", "docs/proof", "/pudding evidence docs/proof", "s1", root)
        assert evidence_dir(root) == "docs/proof"
        assert read_mode(root)[0] == "block", "changing one setting must not clear the others"
        assert run_folder("abc123def", root).startswith("docs/proof/20")

        log({"event": "test", "n": 1}, root)
        assert json.loads(log_path(root).read_text().strip())["event"] == "test"
    print("pudding_core: ok")


if __name__ == "__main__":
    demo()
