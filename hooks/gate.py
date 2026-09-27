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
from pudding_check import METHODS, PAIR_WORDS, env_of, parse_rows  # noqa: E402

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


IN_PROGRESS = re.compile(
    r"\b(?:still working|work in progress|\bWIP\b|in progress|next,? I'll|I'll (?:continue|keep going|finish|"
    r"pick (?:this|it) up)|continuing (?:with|on)|not done yet|not finished|halfway|part \d+ of \d+|"
    r"(?:first|next) (?:step|pass|half)|waiting (?:on|for) (?:you|your))\b", re.I)


def is_report(message):
    """Is the agent handing work back, rather than asking or still going?

    A report is anything that isn't a question and doesn't say it's unfinished -
    deliberately broad, because the point of this rule is not to depend on how the
    report is phrased.
    """
    text = (message or "").strip()
    if len(text) < 8:
        return False
    last = [ln.strip() for ln in text.splitlines() if ln.strip()][-1]
    if last.endswith("?") or IN_PROGRESS.search(text):
        return False
    return True


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
    """Did THIS session touch code? Talking about work is not claiming it.

    Pudding's own writes don't count (its .gitignore lines, receipts, log), and
    neither do changes that predate the session.
    """
    try:
        inside = subprocess.run(["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"],
                                capture_output=True, text=True, timeout=3)
        if inside.returncode != 0:
            return True  # not a repo we can read: stay armed rather than guess
    except Exception:
        return True
    if any(f != ".gitignore" for f in session_files(root, since)):
        return True
    return newest_source_commit(root, since) >= since > 0


PATHY = re.compile(r"[\w./\\-]+\.(?:png|jpe?g|gif|webp|svg|mhtml?|html?|pdf|txt|json|log|md|mov|mp4)")
STOP = {"the", "and", "for", "with", "from", "into", "that", "this", "when", "then",
        "works", "work", "done", "verified", "test", "tests", "page", "user", "new"}


MAGIC = {".png": (b"\x89PNG",), ".jpg": (b"\xff\xd8\xff",), ".jpeg": (b"\xff\xd8\xff",),
         ".gif": (b"GIF87a", b"GIF89a"), ".webp": (b"RIFF",)}


def looks_real(path):
    """An image has to be an image. `touch shot.png` is the cheapest possible fake,
    and it should not be the one that works.

    ponytail: header bytes only. A real screenshot of the wrong screen still passes;
    that one is caught by the person opening the file, which is the point of saving it.
    """
    try:
        if path.stat().st_size == 0:
            return False
        sigs = MAGIC.get(path.suffix.lower())
        if not sigs:
            return True
        head = path.open("rb").read(12)
        return any(head.startswith(sig) for sig in sigs)
    except OSError:
        return False


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
        if full.exists() and ev in full.parents and looks_real(full):
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


def session_files(root, since):
    """Files changed in THIS session: dirty now and modified after it started.

    A tree with old uncommitted changes is normal. Counting those made every turn of a
    new session look like it had done work - a /pudding-stats call got hijacked into
    re-verifying a file the previous session had edited.
    """
    out = []
    for rel in changed_files(root):
        try:
            if (root / rel).stat().st_mtime >= since:
                out.append(rel)
        except OSError:
            out.append(rel)  # deleted this session - that is a change too
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
        # Not --since: git's date parser intermittently reads "@0" as "now", so with a
        # clean tree (floor 0) it dropped every commit older than the current second.
        # Recent history, filtered here, is exact.
        out = subprocess.run(
            ["git", "-C", str(root), "log", "-n", "200", "--format=%ct", "--name-only"],
            capture_output=True, text=True, timeout=5)
        for line in out.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.isdigit():
                ts = float(line)
            elif ts >= (floor or 0) and not (line.startswith(("receipts/", ".claude/")) or VOLATILE.search(line)):
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


def evidence_findings(text):
    """What the gate insists on: rows exist, and every verified row names a real
    method and a real artifact. Receipt hygiene (tier, cleanup, a Not-tested
    section) is the linter's business, not a reason to hold a turn - an agent that
    wrote honest rows with a slightly different header was blocked three times and
    escaped, which is the paperwork failure this tool must not have.
    """
    rows = parse_rows(text)
    if not rows:
        return ["the receipt has no rows"]
    out = []
    for claim, method, artifact, status in rows:
        if status.lower().startswith("verified"):
            if method not in METHODS:
                out.append(f"row '{claim[:40]}': method '{method}' is not one of {', '.join(sorted(METHODS))}")
            if artifact.strip() in ("", "-"):
                out.append(f"row '{claim[:40]}': verified with no artifact")
    return out


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


def excerpt(sentence, phrase, width=90):
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
    # snap to word boundaries so the quote never starts or ends mid-word
    if start:
        sp = sentence.find(" ", start)
        start = sp + 1 if 0 <= sp < i else start
    if end < len(sentence):
        sp = sentence.rfind(" ", i + len(phrase), end)
        end = sp if sp > 0 else end
    return ("..." if start else "") + sentence[start:end].strip() + ("..." if end < len(sentence) else "")


def render(unmet, receipt, rows, root, run_dir):
    """One block, read by both the human and the model.

    Measured in a real terminal: on a block, `reason` renders as "Stop hook error"
    and hookSpecificOutput.additionalContext renders as "Stop hook feedback" - there
    is no model-only channel. Two blocks meant ~25 lines of instructions and absolute
    temp paths on the user's screen. So: one short block, relative paths, written so
    the human understands it and the model can act on it.
    """
    c = unmet[0]
    said = excerpt(c.sentence, c.phrase) if c.sentence else c.phrase
    lines = [
        "\U0001F36E  no pudding, no done.",
        "",
        f"  you said     {said}",
        f"  you have     {have_summary(rows)}" + ("" if receipt else "  (no receipt this session)"),
        f"  you need     {c.family.hint}",
    ]
    for extra in unmet[1:4]:
        lines.append(f"  and          {extra.family.hint}")
    lines += [
        "",
        f"  go look at it. save what you capture in {run_dir}/",
        "  add a row to receipts/<feature>-<date>.md, then say it again.",
        "  can't reach it? write it down honestly and say so:",
        f"   | {c.phrase or c.family.name} | - | - | blocked: <why> |",
        "  (a softer sentence with the same meaning is not a way out.)",
    ]
    return "\n".join(lines)


def decide(data, root):
    """The whole verdict, as a pure function of the hook input and the repo. Returns
    the JSON payload to print ({} means: let the turn end)."""
    prompt_id = data.get("prompt_id") or ""
    if not prompt_id and data.get("stop_hook_active"):
        return {}  # no prompt_id to count against, so fall back to the coarse guard

    message = data.get("last_assistant_message") or ""
    session_id = data.get("session_id", "")
    since = session_start(session_id, root)
    claims = detect(message)
    whole_set = claims_completeness(message)
    files = session_files(root, since)
    ui = [f for f in files if UI_FILE.search(f)]
    reporting = is_report(message)
    if not (claims or whole_set or ui or reporting):
        return {}  # a question or a turn still in progress: nothing to prove yet

    if not source_changed(root, since):
        return {}

    mode, authorized, _ = core.read_mode(root)
    if mode == "off":
        return {}

    receipt = fresh_receipt(root, since)
    text = receipt.read_text(encoding="utf-8-sig") if receipt else ""
    rows, env = verified_rows(text), env_of(text)
    findings = evidence_findings(text) if receipt else ["no receipt written this session"]
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

    # Work reported back with no claim phrase the detector recognised still needs proof.
    # Measured: on text it had never seen, the claim detector caught about two thirds
    # of real claims. This rule doesn't depend on phrasing at all - the session
    # changed code and the agent is handing back, so there has to be a row.
    if reporting and not claims and not whole_set and not (receipt_ok and rows):
        touched = [f for f in files if f != ".gitignore"][:3]
        unmet.append(Claim(Family(
            "work-unproven", "", None, False, False,
            "one verified row for the work you did" + (" (" + ", ".join(touched) + ")" if touched else "") +
            ": what you ran, and what you saw"),
            "", "you changed code and reported back"))

    # UI you changed is UI someone has to look at, claim or no claim.
    if ui and not any(m == "real-ui" and artifact_is_real(a, root)
                      for _, m, a, _ in (rows if receipt_ok else [])):
        unmet.append(Claim(Family(
            "ui-unseen", "", {"real-ui"}, False, False,
            "a screenshot of the UI you changed (" + ", ".join(ui[:3]) + ")"),
            "", "you changed UI this turn"))
    base = {"session_id": session_id, "prompt_id": prompt_id,
            "event_kind": data.get("hook_event_name", "Stop"),
            "claims": [c.family.name for c in claims],
            "receipt": receipt.name if receipt else None, "mode": mode}

    if not unmet:
        core.log({"event": "earned", **base}, root)
        return {}

    text = render(unmet, receipt, rows, root, core.run_folder(prompt_id, root))
    if receipt and findings:
        text += "\n\n  " + receipt.name + " doesn't hold up yet:\n" + \
                "\n".join(f"   - {f}" for f in findings[:4])

    if mode == "warn":
        core.log({"event": "unearned", **base}, root)
        return {"systemMessage": text}

    # The budget applies only to a turn that is still unearned. Checking it first -
    # the first version did - logged an agent as having escaped on the very stop where
    # its receipt had finally become valid.
    spent = blocks_this_prompt(prompt_id, root)
    if spent >= MAX_BLOCKS_PER_PROMPT:
        core.log({"event": "escaped", **base, "blocks_spent": spent}, root)
        return {"systemMessage": (
            "\U0001F36E  pudding gave up after %d blocks on this prompt.\n"
            "  this ships UNPROVEN. persistence beat the gate - that is a recorded\n"
            "  fact, not a pass: .claude/pudding.local.jsonl, event=escaped." % spent)}

    core.log({"event": "blocked", **base}, root)
    # Measured in a real terminal: `reason` renders to the human as "Stop hook error"
    # AND reaches the model; additionalContext reaches only the model. So the human
    # gets the short mascot block and the model gets the full instructions.
    out = {"decision": "block", "reason": text}
    if not authorized:
        out["systemMessage"] = ("\U0001F36E pudding: the mode file was weakened without a /pudding "
                                "command, so the gate reverted to block.")
    return out


def main():
    core.emit(decide(core.read_hook_input(), core.project_dir()))


if __name__ == "__main__":
    main()
