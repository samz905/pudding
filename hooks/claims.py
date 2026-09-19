#!/usr/bin/env python3
"""Claim detection: which sentences are completion claims, and what earns each one.

Deterministic on purpose. arXiv 2606.09863 measured five LLM judges against this
exact task ("false success") and none exceeded AUROC 0.65 - a model grading a
model is barely better than a coin flip here, so pudding never asks one.

Scope is web and general software. A domain this has never been watched to fail
in is a spec change, not a guess.
"""
import re
from collections import namedtuple

Family = namedtuple("Family", "name pattern methods pair deployed hint")
Claim = namedtuple("Claim", "family phrase sentence")

ANY = None  # satisfied by any verified row

FAMILIES = [
    Family(
        "real-user",
        r"works? (?:as a real user|end.to.end)|(?:tested|verified|working|confirmed)\s+end.to.end"
        r"|end.to.end (?:in|from|through)|as a real user|like a real user"
        r"|in the (?:app|browser|UI)\b|on your (?:real|actual) ",
        {"real-ui"}, False, False,
        "a real-ui artifact: a screenshot, a DOM capture, or the URL you actually drove",
    ),
    Family(
        "design-match",
        r"matches? the (?:design|mock|reference|comp)|likeness|pixel.(?:perfect|honest)|design fidelity",
        {"real-ui"}, True, False,
        "a real-ui screenshot paired against the reference (before/after or shot-vs-design)",
    ),
    Family(
        "deployed",
        r"\b(?:is|are|it's) live\b|\b(?:is |are |now )?deployed\b|in prod(?:uction)?\b|\bit's up\b"
        r"|pushed to prod|on (?:the )?(?:staging|preview|production) (?:url|link|site)",
        {"real-ui"}, False, True,
        "a real-ui artifact captured against the DEPLOYED url, with env naming it - localhost is not the deploy",
    ),
    Family(
        "metric",
        r"the (?:count|number|metric|total|figure)s? (?:is|are) (?:right|correct)"
        r"|counts? correctly|shows? the (?:right|correct) (?:count|number|value)",
        {"db", "real-ui"}, False, False,
        "a db read or a real-ui capture showing the SURFACED value move",
    ),
    Family(
        "persisted",
        r"(?:row|record|event|entry|document)s? (?:is|are|get|gets) (?:written|recorded|saved|created|persisted)"
        r"|persists? correctly|lands? in the (?:db|database|table)",
        {"db"}, False, False,
        "a db artifact: the query and the row it returned",
    ),
    Family(
        "wire",
        r"(?:the|a|its|our) (?:webhook|request|callback|payload|message|event) "r"(?:fires|is sent|goes out|is delivered|arrives)"
        r"|fires correctly",
        {"wire"}, False, False,
        "a wire artifact: the captured request, webhook, or queue payload",
    ),
    Family(
        "bug-fixed",
        r"(?:bug|issue|crash|error|regression) is fixed|no longer (?:repros|reproduces|happens|occurs)"
        r"|(?:doesn't|does not) happen (?:any ?more|again)|fixed the (?:bug|crash|error)",
        ANY, False, False,
        "the reproduction re-run and now failing to reproduce - a fix with no repro row is a guess",
    ),
    Family(
        "faster",
        r"\d+(?:\.\d+)?\s*(?:x|%|times) faster|(?:is |much |now )faster\b"
        r"|(?:performance|latency|load time) (?:improved|is better|dropped)|uses less (?:memory|cpu|ram)",
        ANY, True, False,
        "a before -> after measurement pair, not a single number",
    ),
    Family(
        "installs-clean",
        r"installs? clean|builds? clean(?:ly)?|fresh (?:install|clone|checkout) works|from scratch works"
        r"|works on a clean (?:machine|env)",
        ANY, False, False,
        "an artifact from a fresh environment, not from your warmed-up one",
    ),
    Family(
        "no-break",
        r"(?:doesn't|does not|won't) break (?:existing|anything|any)|backwards? compatible|no regressions?",
        ANY, False, False,
        "the prior consumer still running",
    ),
    Family(
        "completeness",
        r"\ball items\b(?:\s+\w+){0,2}\s+(?:built|done|shipped|implemented|in)\b"
        r"|\ball (?:\d+|the|of the)?\s*(?:items?|asks?|points?|rows?|feedback|fixes)\b"
        r"(?:\s+\w+){0,3}\s+(?:are|is|were)?\s*(?:done|built|shipped|implemented|addressed|verified)"
        r"|everything (?:from|on|in|else|in) [^.]{0,60}?(?:is|are) (?:done|built|verified|addressed|implemented|shipped)"
        r"|everything(?: else)? (?:is|are) (?:done|built|verified|addressed|implemented|shipped)"
        r"|the rest (?:are|is) (?:done|built|verified|addressed)"
        r"|(?:all|every) (?:the )?feedback (?:is|are|has been) (?:done|addressed|implemented|verified)",
        ANY, False, False,
        "one verified row per item you are calling done - not one row standing in for the set",
    ),
    Family(
        "generic",
        r"\bit works\b|\bdone and verified\b|\ball green\b|\bfully tested\b|\beverything works\b"
        r"|\bconfirmed working\b|\bworks now\b|\bnow works\b|\bis working\b|\bworks correctly\b",
        ANY, False, False,
        "at least one verified row with a real artifact",
    ),
]

# Files whose change a person can only judge by looking. Deliberately broad on
# markup and styles, narrower on scripts, since a .ts file is usually not a surface.
UI_FILE = re.compile(
    r"\.(?:tsx|jsx|vue|svelte|css|scss|sass|less|html|htm|astro)$"
    r"|(?:^|/)(?:components?|pages?|views?|ui|screens?|templates?|layouts?|static|public|"
    r"frontend|client|www)/.*\.(?:js|ts|mjs|py)$",
    re.I,
)

# Completeness asserted by PARTITION: a done-list and a not-done heading, which
# together claim exhaustiveness without the word "all" ever appearing. This is the
# form that hid a whole missing feature in a real status report.
DONE_HEAD = re.compile(
    r"^\s*#{1,4}\s*(?:what\s+shipped|done(?:\s+and\s+verified)?|shipped|completed|"
    r"implemented|delivered)\b|^\s*\*\*(?:done|what shipped|done and verified)\b",
    re.I | re.M,
)
NOT_DONE_HEAD = re.compile(
    r"^\s*#{1,4}\s*(?:not\s+done|not\s+tested|deferred|remaining|out\s+of\s+scope|"
    r"still\s+open|left)\b|^\s*\*\*(?:not done|not tested|deferred|you told me to ignore)\b",
    re.I | re.M,
)

# A sentence carrying any of these is not asserting completion - it is hedging,
# planning, or refusing to claim. Measured against real transcripts: without this,
# "Verifying on your real timeline before I tell you it works" gets blocked for
# being careful, which would train exactly the wrong habit.
HEDGE = re.compile(
    r"\b(?:before I|not yet|haven't|have not|hasn't|has not|don't|do not|didn't|did not|can't|cannot|"
    r"won't|will|going to|about to|next I|once I|need to|should work|unverified|untested|"
    r"verifying|checking|testing it|if it works|whether it works|claim(?:ing)? more|no proof|"
    r"without proof|not proven|can I|should I|would|could)\b",
    re.I,
)

# A sentence telling the USER to do something is an instruction, not a claim.
_IMPERATIVE = re.compile(
    r"^\s*(?:and |then |or |now )?(?:run|confirm|check|ensure|make sure|try|open|click|visit|see|tell|let|go|use|add|"
    r"install|type|paste|reload|restart|drive|look)\b",
    re.I,
)

_FENCE = re.compile(r"```.*?```", re.S)
_INLINE = re.compile(r"`[^`\n]*`")
_QUOTED = re.compile("[\"“‘][^\"”’\\n]{0,200}[\"”’]")
_BLOCKQUOTE = re.compile(r"^\s*>.*$", re.M)
_SENTENCE = re.compile(r"[^.!?\n]+[.!?]?")


def strip_quoted(text: str) -> str:
    """Remove code and quotation, where claim language is mentioned rather than made.

    Measured on 190 real messages: without this, explaining pudding itself trips
    the gate, because the explanation contains the sentences it is about.
    """
    for rx in (_FENCE, _INLINE, _BLOCKQUOTE, _QUOTED):
        text = rx.sub(" . ", text)
    return text


def done_items(message: str):
    """The items a message is calling done, from the list it presents them in.

    Real reports enumerate with middle dots, bullets or commas under a Done heading.
    Whatever comes back here is what a receipt has to cover, one row each.
    """
    m = DONE_HEAD.search(message or "")
    if not m:
        return []
    tail = message[m.end():]
    tail = re.split(r"^\s*(?:#{1,4}\s|\*\*[A-Z])", tail, maxsplit=1, flags=re.M)[0]
    items = []
    for line in tail.splitlines():
        line = line.strip().lstrip("-*\u2022 ").strip()
        if not line:
            continue
        parts = re.split(r"\s*[\u00b7\u2022;]\s*|,\s+(?=[a-z@\"])", line)
        for part in parts:
            part = re.sub(r"[*`_]", "", part).strip(" .:")
            if 3 <= len(part) <= 90:
                items.append(part)
        if len(items) > 40:
            break
    return items[:40]


def claims_completeness(message: str):
    """True when a message claims a whole set is handled - by saying so, or by
    partitioning everything into a done list and a not-done list."""
    if not message:
        return False
    body = strip_quoted(message)
    if any(re.search(f.pattern, body, re.I) for f in FAMILIES if f.name == "completeness"):
        return True
    return bool(DONE_HEAD.search(message) and NOT_DONE_HEAD.search(message))


def detect(message: str):
    """Return the Claims asserted in `message`. Empty list is the common case."""
    if not message:
        return []
    found, seen = [], set()
    for sentence in _SENTENCE.findall(strip_quoted(message)):
        if HEDGE.search(sentence) or _IMPERATIVE.match(sentence):
            continue
        for fam in FAMILIES:
            m = re.search(fam.pattern, sentence, re.I)
            if m and fam.name not in seen:
                seen.add(fam.name)
                found.append(Claim(fam, m.group(0).strip(), sentence.strip()))
    # A specific family always outranks the generic one.
    if len(found) > 1:
        found = [c for c in found if c.family.name != "generic"]
    return found


def demo():
    def fams(msg):
        return {c.family.name for c in detect(msg)}

    assert fams("The server chunk is done and verified against the live server.") >= {"generic"}
    assert "real-user" in fams("It works end to end in the browser.")
    assert "deployed" in fams("The fix is deployed and the dashboard is live.")
    assert "bug-fixed" in fams("The crash no longer repros.")
    assert "design-match" in fams("It matches the design at both widths.")
    assert "persisted" in fams("The row is written to the database on every unlock.")
    assert "wire" in fams("The webhook fires correctly with the right payload.")
    assert "faster" in fams("The page is 3x faster now.")

    # Hedged and future-tense sentences are honest, not claims.
    assert fams("Verifying on your real timeline before I tell you it works.") == set()
    assert fams("It should work but I have not run it.") == set()
    assert fams("I will check whether it works end to end.") == set()
    assert fams("I won't claim it is verified end to end: the gate lets it through.") == set()

    # Talking about claims is not making one.
    assert fams('When I say "it works" pudding asks for the receipt.') == set()
    assert fams("Run `npm test` and confirm it works correctly.") == set()
    assert fams("> it works end to end") == set()

    # A specific family wins over generic.
    assert fams("It works end to end and everything works.") == {"real-user"}

    assert detect("") == [] and detect("Here is the plan for tomorrow.") == []
    print("claims: ok")


if __name__ == "__main__":
    demo()
