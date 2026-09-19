#!/usr/bin/env python3
"""Stop / SubagentStop: a completion claim does not leave the turn without matching evidence.

The whole point is that this is not a skill. A skill has to be chosen, and the
agent that would skip proving is the agent that skips the skill - measured on one
machine: 380 done-claims, 1 verification-skill invocation, and the pudding skill
itself never once. So the harness runs this, not the agent's goodwill.

Cheap by design: a message with no claim in it costs one regex sweep and exits.
"""
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "skills" / "pudding" / "scripts"))

import pudding_core as core          # noqa: E402
from claims import (Claim, Family, UI_FILE, claims_completeness,  # noqa: E402
                    detect, done_items)
from pudding_check import parse_rows, env_of, check, PAIR_WORDS  # noqa: E402

# Runtime artifacts, not the code a claim is about. Without this, a background
# writer (x-account's batch touches pipeline.db-wal every 10 minutes) ages out
# every receipt for reasons unrelated to the work being claimed.
VOLATILE = re.compile(r"\.(?:db|db-shm|db-wal|sqlite3?|log|jsonl|lock|pyc|pid|tmp)$", re.I)

LOCAL_ENV = re.compile(r"localhost|127\.0\.0\.1|0\.0\.0\.0|file://|\blocal(?:host)?\b", re.I)
# ponytail: receipts older than this are ignored when the session start is unknown.
STALE_SECONDS = 6 * 3600
# Blocks allowed per user prompt. The harness force-ends at 8 and prints a warning
# naming the hook, so stay well under it - but bailing on stop_hook_active alone
# (the first design) let every stop after the first one through unchecked.
MAX_BLOCKS_PER_PROMPT = 3


def session_start(session_id, root):
    """When this session armed. Falls back to a window, so a missing log never
    turns stale evidence into fresh evidence."""
    try:
        for line in reversed(core.log_path(root).read_text(encoding="utf-8").splitlines()):
            e = json.loads(line)
            if e.get("event") == "armed" and e.get("session_id") == session_id:
                # fromisoformat keeps the offset; time.mktime would read UTC as local
                # and put session start hours in the future, so nothing is ever fresh.
                return datetime.fromisoformat(e["ts"]).timestamp()
    except Exception:
        pass
    return time.time() - STALE_SECONDS


def blocks_this_prompt(prompt_id, root):
    """How many times this same user prompt has already been blocked."""
    if not prompt_id:
        return 0
    n = 0
    try:
        for line in core.log_path(root).read_text(encoding="utf-8").splitlines()[-300:]:
            try:
                e = json.loads(line)
            except Exception:
                continue
            if e.get("event") == "blocked" and e.get("prompt_id") == prompt_id:
                n += 1
    except Exception:
        pass
    return n


def source_changed(root, since):
    """Did this session touch code? Talking about work is not claiming it."""
    try:
        st = subprocess.run(["git", "-C", str(root), "status", "--porcelain", "-uall"],
                            capture_output=True, text=True, timeout=3)
        if st.returncode == 0 and st.stdout.strip():
            return True
        ct = subprocess.run(["git", "-C", str(root), "log", "-1", "--format=%ct"],
                            capture_output=True, text=True, timeout=3)
        if ct.returncode == 0 and ct.stdout.strip():
            return int(ct.stdout.strip()) >= since
    except Exception:
        pass
    return True  # never let a git failure quietly disarm the gate


PATHY = re.compile(r"[\w./\\-]+\.(?:png|jpe?g|gif|webp|svg|mhtml?|html?|pdf|txt|json|log|md|mov|mp4)")
STOP = {"the", "and", "for", "with", "from", "into", "that", "this", "when", "then",
        "works", "work", "done", "verified", "test", "tests", "page", "user", "new"}


def artifact_is_real(artifact, root):
    """A real-ui row must point at a file the user can open, where they look for it.

    Existence alone is too weak a rule. A real session produced
    /var/folders/nm/.../claude-chrome-screenshots-RecJyX/screenshot-1789691621795-0.jpg
    - a genuine file, in a temp dir the user will never open. And before that:
    "You can't see them - I've been reading images into my own context, not
    rendering them in your terminal. My fault entirely; that's twice now."

    So the artifact has to be inside the project's evidence dir.
    """
    root = root.resolve()
    ev = (root / core.evidence_dir(root)).resolve()
    for cand in PATHY.findall(artifact or ""):
        try:
            full = (root / cand.lstrip("./")).resolve()
        except OSError:
            continue
        if full.exists() and ev in full.parents:
            return True
    return False


def words(text):
    return {w for w in re.findall(r"[a-z0-9]{4,}", (text or "").lower()) if w not in STOP}


def uncovered(items, rows):
    """Items called done that no verified row speaks to."""
    covered = [words(r[0]) for r in rows]
    return [it for it in items if not any(words(it) & c for c in covered)]


def changed_files(root):
    """Paths git reports dirty, minus runtime artifacts and pudding's own files."""
    out = []
    try:
        # -uall: without it git collapses a wholly-untracked directory to "components/",
        # so a brand new folder of components is invisible to every check below.
        res = subprocess.run(["git", "-C", str(root), "status", "--porcelain", "-uall"],
                             capture_output=True, text=True, timeout=3)
        for line in res.stdout.splitlines():
            rel = line[3:].strip().strip('"').split(" -> ")[-1]
            if rel and not (rel.startswith(("receipts/", ".claude/")) or VOLATILE.search(rel)):
                out.append(rel)
    except Exception:
        pass
    return out


def newest_source_mtime(root):
    """When the code last changed. Evidence written before the code it describes is
    evidence for different work - the first live session accepted a four-minute-old
    receipt about run.sh as proof for a claim about tunnel.sh.

    ponytail: reads only files git already reports as dirty, so ignored build output
    and data churn cannot age a receipt out. A background writer committing tracked
    files mid-session can still do it; per-path exclusions if that bites.
    """
    newest = 0.0
    try:
        out = subprocess.run(["git", "-C", str(root), "status", "--porcelain"],
                             capture_output=True, text=True, timeout=3)
        for line in out.stdout.splitlines():
            rel = line[3:].strip().strip('"').split(" -> ")[-1]
            if rel.startswith(("receipts/", ".claude/")) or VOLATILE.search(rel):
                continue
            try:
                newest = max(newest, (root / rel).stat().st_mtime)
            except OSError:
                continue
    except Exception:
        pass
    return max(newest, newest_source_commit(root, newest))


def newest_source_commit(root, floor):
    """When code was last COMMITTED. x-account's batch commits the agent's edits
    within ten minutes, so a status-only check goes blind the moment it runs.

    Only commits touching non-volatile paths count, so the same batch writing
    data/pipeline.db every tick does not age a receipt out on its own cadence.
    """
    newest, ts = 0.0, 0.0
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "log", "--since=@%d" % int(floor or 0),
             "--format=%ct", "--name-only"],
            capture_output=True, text=True, timeout=5)
        for line in out.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.isdigit():
                ts = float(line)
            elif not (line.startswith(("receipts/", ".claude/")) or VOLATILE.search(line)):
                # ponytail: %ct truncates to the second, so a receipt written in the
                # same second as a commit reads as fresh. Rounding up fixes that and
                # breaks the common case (write code, commit, write receipt, same
                # second), which is the worse trade. Sub-second source if it matters.
                newest = max(newest, ts)
    except Exception:
        pass
    return newest


def fresh_receipt(root, since):
    """The newest receipt that is both from this session and not older than the code."""
    floor = max(since, newest_source_mtime(root))
    try:
        cands = [p for p in (root / "receipts").glob("*.md") if p.stat().st_mtime >= floor]
    except Exception:
        return None
    return max(cands, key=lambda p: p.stat().st_mtime) if cands else None


def verified_rows(text):
    return [r for r in parse_rows(text) if r[3].lower().startswith("verified")]


def satisfies(fam, rows, env, root):
    """Does any verified row earn this claim? The gate table, mechanically."""
    for claim, method, artifact, _ in rows:
        if fam.methods is not None and method not in fam.methods:
            continue
        if method == "real-ui" and not artifact_is_real(artifact, root):
            continue  # a named screenshot that is not on disk is a promise, not proof
        if fam.pair and not PAIR_WORDS.search(artifact + " " + claim):
            continue
        if fam.deployed and (LOCAL_ENV.search(env) or not env.strip()):
            continue
        return True
    return False


def have_summary(rows):
    if not rows:
        return "no verified rows"
    counts = {}
    for _, method, _, _ in rows:
        counts[method] = counts.get(method, 0) + 1
    return ", ".join(f"{n} {m}" for m, n in sorted(counts.items(), key=lambda kv: -kv[1]))


def excerpt(sentence, phrase, width=76):
    """Show the claim, not its preamble. Clipping the head once ate the only words
    that mattered: "Test stimulus, as requested (deliberately unearned - no receipt
    exists): ..." with `it works end to end` cut off the end."""
    if len(sentence) <= width:
        return sentence
    i = sentence.lower().find(phrase.lower())
    if i < 0:
        return sentence[:width - 3] + "..."
    start = max(0, i - (width - len(phrase)) // 2)
    end = min(len(sentence), start + width)
    start = max(0, end - width)
    return ("..." if start else "") + sentence[start:end].strip() + ("..." if end < len(sentence) else "")


def render(unmet, receipt, rows, root):
    """Who sees what, measured in a real terminal rather than read off the schema:

    warn   -> systemMessage renders as "Stop says: ...". stopReason never appears.
    block  -> reason renders as "Stop hook error: ..." AND goes to the model.
              stopReason never appeared either.

    So `reason` is the only channel that reaches a human on the block path, and it
    leads with the mascot for that reason; the machine instructions follow it.
    """
    c = unmet[0]
    said = excerpt(c.sentence, c.phrase)
    have = have_summary(rows)
    where = str(receipt) if receipt else "none written this session"

    stop_reason = (
        "\n\U0001F36E  no pudding, no done.\n\n"
        f"  you said     {said}\n"
        f"  you have     {have}\n"
        f"  you need     {c.family.hint}\n\n"
        "  go look at it. then come back.\n"
        "  (or write it down honestly:\n"
        f"   | {c.phrase} | - | - | blocked: <why> |)\n"
    )

    lines = [
        stop_reason.rstrip(),
        "",
        f"receipt read: {where}",
        f"receipts are read from exactly one place: {root / 'receipts'}/",
        f"real-ui artifacts must live under: {root / core.evidence_dir(root)}/",
        "a receipts/ folder anywhere else in the tree is not read.",
        "",
    ]
    for c in unmet:
        lines += [f'claim   "{c.sentence.strip()}"',
                  f"family  {c.family.name}",
                  f"needs   {c.family.hint}",
                  ""]
    lines += [
        "Do one of these, then say it again:",
        "  1. Go get the evidence, drive it the way the user does, and add the row.",
        "  2. If you cannot reach it, record that honestly as a row with",
        "     status `blocked: <why - user decision needed>` and say so in your report.",
        "  3. If the user already waived it, record `waived: <who/when>`.",
        "",
        "Do not restate the claim without doing one of those. A softer sentence with",
        "the same unearned meaning is the failure this exists to catch.",
    ]
    return stop_reason, "\n".join(lines)


def decide(data, root):
    """The whole verdict, as a pure function of the hook input and the repo. Returns
    the JSON payload to print ({} means: let the turn end)."""
    prompt_id = data.get("prompt_id") or ""
    spent = blocks_this_prompt(prompt_id, root)
    if spent >= MAX_BLOCKS_PER_PROMPT:
        # Budget spent. The claim gets through - the harness would force-end at 8
        # anyway - but it does NOT get through quietly. A live probe repeated one
        # unearned claim four times and escaped on the fourth, and the log showed
        # three blocks and nothing else, reading exactly like enforcement had held.
        core.log({"event": "escaped", "session_id": data.get("session_id", ""),
                  "prompt_id": prompt_id, "event_kind": data.get("hook_event_name", "Stop"),
                  "blocks_spent": spent}, root)
        return {"systemMessage": (
            "\U0001F36E  pudding gave up after %d blocks on this prompt.\n"
            "  the claim ships UNPROVEN. persistence beat the gate - that is a\n"
            "  recorded fact, not a pass: .claude/pudding.local.jsonl, event=escaped."
            % spent)}
    if not prompt_id and data.get("stop_hook_active"):
        return {}  # no prompt_id to count against, so fall back to the coarse guard

    message = data.get("last_assistant_message") or ""
    claims = detect(message)
    whole_set = claims_completeness(message)
    ui = [f for f in changed_files(root) if UI_FILE.search(f)]
    if not (claims or whole_set or ui):
        return {}  # the common case: a regex sweep and one git status

    session_id = data.get("session_id", "")
    since = session_start(session_id, root)
    if not source_changed(root, since):
        return {}

    mode, authorized, _ = core.read_mode(root)
    if mode == "off":
        return {}

    receipt = fresh_receipt(root, since)
    text = receipt.read_text(encoding="utf-8-sig") if receipt else ""
    rows, env = verified_rows(text), env_of(text)
    findings = check(receipt) if receipt else ["no receipt written this session"]
    receipt_ok = bool(receipt) and not findings

    unmet = [c for c in claims if not (receipt_ok and satisfies(c.family, rows, env, root))]

    # A claim about a SET needs a row per member. One row standing in for fifteen
    # items is how a whole unbuilt feature stayed inside a "done" list.
    if whole_set:
        items = done_items(message)
        missing = uncovered(items, rows) if receipt_ok else items
        # No enumerable list is worse, not better: "All items built" names nothing a
        # reader can check, and the list it refers to is a thousand lines upstream.
        if missing or not receipt_ok or not items:
            named = ", ".join(missing[:6]) or "the items you are calling done - name them"
            unmet.append(Claim(Family(
                "completeness", "", None, False, False,
                "one verified row per item. No row speaks to: " + named), "", 
                "you called a whole set done"))

    # UI you changed is UI someone has to look at, claim or no claim.
    if ui and not any(m == "real-ui" and artifact_is_real(a, root)
                      for _, m, a, _ in (rows if receipt_ok else [])):
        unmet.append(Claim(Family(
            "ui-unseen", "", {"real-ui"}, False, False,
            "a screenshot for the UI you changed (" + ", ".join(ui[:3]) + ") saved in " +
            core.run_folder(prompt_id, root) + "/ - not a temp dir, not your own context"),
            "", "you changed UI this turn"))
    base = {"session_id": session_id, "prompt_id": prompt_id,
            "event_kind": data.get("hook_event_name", "Stop"),
            "claims": [c.family.name for c in claims],
            "receipt": receipt.name if receipt else None, "mode": mode}

    if not unmet:
        core.log({"event": "earned", **base}, root)
        return {}

    stop_reason, reason = render(unmet, receipt, rows, root)
    if receipt and findings:
        reason += "\n\nThe receipt is also invalid:\n" + "\n".join(f"  - {f}" for f in findings)

    if mode == "warn":
        core.log({"event": "unearned", **base}, root)
        return {"systemMessage": stop_reason}

    core.log({"event": "blocked", **base}, root)
    out = {"decision": "block", "reason": reason, "systemMessage": stop_reason,
           "stopReason": "a done-claim with no matching evidence"}
    if not authorized:
        out["systemMessage"] += ("\n  note: the mode file was weakened without a /pudding "
                                 "command, so the gate reverted to block.")
    return out


def main():
    core.emit(decide(core.read_hook_input(), core.project_dir()))


if __name__ == "__main__":
    main()
