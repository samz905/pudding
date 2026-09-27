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

# Word lists shared by several patterns.
_STATE = (r"(?:fixed|done|working|built|merged|shipped|passing|green|complete|completed|in place|"
          r"wired(?: up)?|resolved|up and running|persisting|firing)")

FAMILIES = [
    Family(
        "real-user",
        r"works? (?:as a real user|end.to.end)|(?:tested|verified|working|confirmed|checked)\s+end.to.end"
        r"|end.to.end (?:in|from|through|pass)|as a (?:real|brand.new|new|first.time) (?:user|signup|customer)"
        r"|like a real user|clicked through|walked through the (?:whole|full|entire)"
        r"|(?:works?|working|tested|verified|checked|confirmed|tried|renders?|shows? up|loads?)\b.{0,30}\bin the "
        r"(?:app|browser|UI)\b"
        r"|on your (?:real|actual) |signed up (?:with|as) a|installing this for the first time"
        r"|the way a (?:real |new )?user would|as a user would",
        {"real-ui"}, False, False,
        "a real-ui artifact: a screenshot, a DOM capture, or the URL you actually drove",
    ),
    Family(
        "design-match",
        r"match(?:es|ed)? the (?:design|mock(?:up)?|reference|comp|figma|spec(?: doc)?)|against the "
        r"(?:figma|mock(?:up)?|design|spec)|pixel by pixel|pixel.(?:perfect|honest)|design fidelity|likeness"
        r"|confirmed against the spec",
        {"real-ui"}, True, False,
        "a real-ui screenshot paired against the reference (before/after or shot-vs-design)",
    ),
    Family(
        "deployed",
        r"\b(?:is|are|it's|now) live\b|\blive on\b|\b(?:is|are|now|been|got) deployed\b|\bdeployed to\b"
        r"|\bin prod(?:uction)? now\b|\bit's up\b|pushed to prod|rolled out|rollout is (?:done|complete)"
        r"|on (?:the )?(?:staging|preview|production) (?:url|link|site)|released to|published to (?:npm|pypi)"
        r"|\bv\d+\.\d+(?:\.\d+)? is (?:out|live|published)|running on the new"
        r"|serving (?:live|production|real) traffic|every\b.{0,40}\b(?:pod|instance|server|node|host)s? (?:is|are) "
        r"(?:now )?running",
        {"real-ui"}, False, True,
        "a real-ui artifact captured against the DEPLOYED url, with env naming it - localhost is not the deploy",
    ),
    Family(
        "metric",
        r"the (?:count|number|metric|total|figure|rate|tile|counter|badge)s? (?:is|are|now) (?:right|correct|"
        r"accurate)|counts? (?:correctly|match)|numbers? (?:match|line up)|now (?:reads|shows|reports|displays) "
        r"[\d,.$%]|(?:lines up|match(?:es)?) exactly|matches reality|cross.?checked\b.{0,80}\b(?:match|line up)",
        {"db", "real-ui"}, False, False,
        "a db read or a real-ui capture showing the SURFACED value move",
    ),
    Family(
        "persisted",
        r"(?:row|record|event|entry|document)s? (?:is |are |get |gets )?(?:written|recorded|saved|created|"
        r"persisted|lands?)\b|persist(?:s|ing)? correctly|lands? in the (?:db|database|\w+ table|table)"
        r"|(?:is|are) (?:now )?persist(?:ed|ing)|now (?:holds|has|contains) (?:all )?[\d,]+ (?:rows|records)",
        {"db"}, False, False,
        "a db artifact: the query and the row it returned",
    ),
    Family(
        "wire",
        r"(?:the|a|its|our) (?:webhook|request|callback|payload|message|event|download|notification|ping) "
        r"(?:now )?(?:fires|is sent|goes out|is delivered|arrives|lands)|fires (?:correctly|on every)|now fires"
        r"|(?:actually|now) fires|hit our endpoint|posts to (?:the )?#|triggers? on every"
        r"|(?:message|ping|notification|email|alert|event)s? (?:showed up|landed|lands?|arrived|appeared) in"
        r"|watched (?:the|it|them)\b.{0,30}\b(?:land|arrive|show up|come through)",
        {"wire"}, False, False,
        "a wire artifact: the captured request, webhook, or queue payload",
    ),
    Family(
        "bug-fixed",
        r"(?:bug|issue|crash|error|regression|leak|race(?: condition)?|hang|off.by.one|timeout)s? (?:is |are )?"
        r"(?:now )?(?:fixed|gone|resolved)|\bno longer (?:\w+)|(?:doesn't|does not) (?:happen|occur|reproduce) "
        r"(?:any ?more|again)|^\s*fixed(?: it| that| this)?\b|fixed the (?:bug|crash|error|leak|race|hang)"
        r"|\b(?:zero|no more) (?:duplicate|errors|failures|crashes)|repro(?:duction)?(?: script)?\b.{0,60}"
        r"\b(?:now|and it|zero|no longer)|isn't (?:there|happening) any ?more|stay(?:s|ed) flat"
        r"|completed cleanly|(?:ran|completed|finished) clean(?:ly)? (?:each|every) time|no (?:more )?hangs\b"
        r"|(?:hasn't|has not) (?:recurred|come back|happened (?:again|since))",
        None, False, False,
        "the reproduction re-run and now failing to reproduce - a fix with no repro row is a guess",
    ),
    Family(
        "faster",
        r"\d+(?:\.\d+)?\s*(?:x|%|times) (?:faster|smaller|less)|(?:is |much |now )faster\b|(?:performance|"
        r"latency|load time|p9\d) (?:improved|is better|dropped|down)|uses less (?:memory|cpu|ram)"
        r"|takes? [\d.]+\s*\w* (?:now )?instead of|(?:down|dropped) (?:from|to) [\d.]+\s*(?:kb|mb|ms|s\b|seconds|"
        r"minutes)|now takes [\d.]+|\btook [\dhms:.]+\b.{0,60}\b(?:lands at|now takes|this one|now) [\dhms:.]+",
        None, True, False,
        "a before -> after measurement pair, not a single number",
    ),
    Family(
        "installs-clean",
        r"installs? clean|builds? (?:clean(?:ly)?|and starts)|fresh (?:install|clone|checkout|machine)"
        r"|cloned (?:the repo )?fresh|from scratch works|clean (?:machine|env|home directory|checkout)"
        r"|zero manual steps|works on a clean|brand.new (?:vm|machine|box|laptop|container)|came up (?:healthy|clean(?:ly)?)"
        r"|nothing (?:else )?(?:installed )?on it",
        None, False, False,
        "an artifact from a fresh environment, not from your warmed-up one",
    ),
    Family(
        "no-break",
        r"(?:doesn't|does not|won't|didn't) break|backwards? compatible|no regressions?|nothing (?:downstream )?"
        r"broke|no breaking changes|(?:all )?existing (?:consumers|clients|callers|users) still"
        r"|still (?:parse|pass|work)s?\b.{0,40}\b(?:old|existing|v1)|exactly as before|byte.identical"
        r"|identical output|has(?:n't| not)? anything to change|nobody\b.{0,50}\bhas anything to change",
        None, False, False,
        "the prior consumer still running",
    ),
    Family(
        "completeness",
        r"\ball items\b(?:\s+\w+){0,2}\s+(?:built|done|shipped|implemented|in)\b"
        r"|\ball (?:\d+|the|of the|two|three|four|five|six|seven|eight)?\s*(?:\w+ ){0,3}(?:items?|asks?|points?"
        r"|rows?|feedback|fixes|endpoints?|subcommands?|tickets?|tasks?|issues?|changes|pieces)\b[^.]{0,80}?"
        r"\b(?:are|were|is)?\s*(?:now )?(?:done|built|fixed|shipped|implemented|addressed|verified|in|merged)\b"
        r"|everything (?:from|on|in|else) [^.]{0,60}?(?:is|are) (?:done|built|verified|addressed|implemented|"
        r"shipped)|everything(?:'s| else)? (?:is |are )?(?:done|built|verified|addressed|implemented|shipped|in)\b"
        r"|the rest (?:are|is) (?:done|built|verified|addressed)|(?:all|every) (?:the )?feedback (?:is|are|has "
        r"been) (?:done|addressed|implemented|verified)|nothing left on (?:that|the|your) list"
        r"|went through (?:the whole|the full|the entire|every)\b.{0,60}\b(?:list|checklist|ticket)",
        None, False, False,
        "one verified row per item you are calling done - not one row standing in for the set",
    ),
    Family(
        "generic",
        r"\bit works\b|\bdone and verified\b|\ball green\b|\bfully tested\b|\beverything works\b"
        r"|\bconfirmed working\b|\bworks now\b|\bnow works\b|\bis working\b|\bworks correctly\b"
        r"|^\s*(?:done|shipped|merged|sorted|all set|good to go|ready to (?:merge|ship|go))\b"
        r"|you're all set|that's (?:done|sorted|fixed|in|shipped)|\ball (?:\d+ )?(?:tests? )?pass(?:ing)?\b"
        r"|\b(?:tests?|suite|checks?|ci|build) (?:is |are )?(?:all )?(?:green|passing)\b"
        r"|\b(?:is|are|'s) (?:now )?" + _STATE + r"\b"
        r"|\b(?:built|tested|merged|shipped|verified|confirmed)(?:,| and) (?:tested|merged|verified|deployed|shipped)\b"
        r"|\ball \d+ \w+ (?:pass|match|succeed)|\beverything'?s in\b|\bnothing left\b"
        r"|\b(?:tracked|worked|behaved|rendered|loaded|synced|saved|formatted) correctly\b"
        r"|\b(?:core|whole|main|happy) (?:flow|path) (?:is|was) (?:solid|clean|good)\b|\bthey line up\b"
        r"|^\s*(?:confirmed|verified|tested|checked|double.checked|clicked through|ran|compared|pulled)\b.{0,160}"
        r"\b(?:match(?:es|ed)?|pass(?:es|ed)?|works?|lands?|fires?|hit|returns?|green|stays?|succeed(?:s|ed)?"
        r"|zero|clean(?:ly)?)\b",
        None, False, False,
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
    r"\b(?:before I|not yet|so far|still running|in progress|pending|waiting on|once I|once it|next I|"
    r"I'll|I will|we'll|will (?:fix|work|be)|going to|about to|need to|needs to|should|"
    r"might|may (?:fix|work)|probably|likely|I think|I believe|hopefully|unverified|untested|"
    r"haven't (?:run|tested|verified|checked|tried|confirmed)|have not (?:run|tested|verified|checked|tried|"
    r"confirmed)|didn't (?:run|test|verify|check|try|get to)|did not (?:run|test|verify|check|try)|"
    r"can't (?:confirm|verify|test|reproduce|say)|cannot (?:confirm|verify|test|say)|"
    r"not (?:yet )?(?:tested|verified|confirmed|run)|not sure|unclear|verifying|checking|"
    r"if it works|whether it works|should I|could you|would you|let me know|"
    r"(?:won't|will not|can't|cannot|not going to|wouldn't|shouldn't) (?:claim|call|say)|not claiming)\b",
    re.I,
)
# Negation alone is not a hedge: "it didn't break anything" is a claim. Only negated
# VERIFICATION is ("didn't test", "can't confirm") - the first version dropped every
# sentence with "didn't" or "can't" in it and missed a whole family of real claims.

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
        if HEDGE.search(sentence) or _IMPERATIVE.match(sentence) or sentence.strip().endswith("?"):
            continue
        for fam in FAMILIES:
            m = re.search(fam.pattern, sentence, re.I)
            if m and fam.name not in seen:
                seen.add(fam.name)
                found.append(Claim(fam, m.group(0).strip(), sentence.strip()))
    for head in re.findall(r"^\s*#{1,4}\s*(.+?)\s*$", message, re.M):
        if re.search(r"(?:\u2014|\u2013|-|:)\s*(?:done|complete|shipped|fixed|merged|live)\s*[.!]?$", head, re.I) \
                and "generic" not in seen:
            seen.add("generic")
            gen = next(f for f in FAMILIES if f.name == "generic")
            found.append(Claim(gen, head.strip(), head.strip()))
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
