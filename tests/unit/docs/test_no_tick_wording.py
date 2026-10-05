"""GATE-CHECKWORD: a check box is checked, never ticked.

The owner's rule (2026-10-05): "never use the tick, or ticking, it is check or
checking or checked or unchecked." Screen readers say "check box", "checked" and
"not checked"; a guide that says "tick the box" makes the listener translate
between two vocabularies, and "untick" is a word no reader ever speaks.

This gate reads what people read -- every Markdown page under ``docs/`` and
``standalone/*/docs/``, every page of the site, the help topics, and the F1,
settings-help and tutorial catalogues -- and fails on ``tick``, ``ticked``,
``ticking``, ``untick`` or ``tickbox`` used about a check box.

"Tick" is still the right word for two other things, and :data:`ALLOWED` lists
each phrase that uses it that way with the reason: a clock or timer tick (the
one-second status tick, the minute tick) and a sound that is a tick (the
ceiling tick at the top of a document, the short tick a background check plays).
A phrase here must be specific enough that it cannot excuse a check box, and an
entry nothing uses any more fails too, so the list cannot quietly grow stale.
"""

from __future__ import annotations

import html
import re
from collections.abc import Iterator
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]

_WORD = re.compile(r"\b(?:un)?tick(?:ed|ing|s|box|boxes)?\b", re.IGNORECASE)

#: Phrase (case-insensitive, after tags, entities and line breaks are flattened)
#: -> why "tick" is the right word there.
ALLOWED: dict[str, str] = {
    # The grave key.
    "back-tick key": "the other name of the grave key",
    # Sounds that are ticks.
    "check ticks": "the short sound a background check plays; Quiet Hours holds it back",
    "ticks audibly": "the monitor summary sentence: the check plays its tick sound",
    "whether they tick so you can hear them": "the background-check tick sound",
    "from ticking or interrupting": "the background-check tick sound",
    "short tick every time": "the background-check tick sound",
    "a little tick": "the background-check tick sound",
    "ambient tick": "the background-check tick sound",
    "no tick sound": "the background-check tick sound",
    'or "tick",': "a search word that finds the tick-sound settings",
    "ceiling tick": "the top-of-document earcon",
    "a high tick": "the top-of-document earcon",
    "quiet tick": "the voice conversation's still-working earcon",
    '"working" tick': "the voice conversation's still-working earcon",
    "still working tick": "the voice conversation's still-working earcon",
    "'still working' tick": "the voice conversation's still-working earcon",
    '"still working" tick': "the voice conversation's still-working earcon",
    "thinking tick": "the voice conversation's still-working earcon",
    "tick timings": "the voice conversation's still-working earcon spacing",
    "tick interval": "the voice conversation's still-working earcon spacing",
    "no ticking, no": "a progress sound the gateway spec rules out",
    "dry wooden tick": "the cut, copy and paste earcon",
    "one dry tick": "the cut, copy and paste earcon",
    "that tick dropped": "the delete earcon",
    "noise tick": "the attack of an earcon",
    "separate ticks for moving": "the compare-next and compare-previous earcons",
    # Clock and timer ticks.
    "live-update tick": "the status page's refresh timer",
    "idle tick": "an idle-time timer",
    "each tick runs its handler": "a Quillin schedule timer",
    "next tick still fires": "a Quillin schedule timer",
    "timer` ticks every second": "a wx.Timer",
    "stats every tick": "a polling timer",
    "player tick": "the player's position timer",
    "player ticks": "the player's position timer",
    "observe ticks": "the player's position timer",
    "tick timer": "the player's position timer",
    "queued-tick": "the single-instance request timer",
    "queued inbox tick": "the single-instance request timer",
    "wait for its next tick": "the weather monitor's polling timer",
    "minute-tick": "Quill Radio's minute timer",
    "per tick window": "Quill Radio's minute timer",
    "one-second tick": "a one-second timer",
    "status tick": "a one-second timer",
    "dropped tick": "a missed timer update",
    "landing on the tick": "a timer update",
    "a tick ago": "the previous timer update",
    "position ticks": "routine position updates from the player",
    "routine ticks": "routine position updates from the player",
    "meaningless tick number": "a raw clock value",
    "ticking timer": "a countdown",
    "each tick is a": "the weather monitor's polling timer",
    "crashed on every tick": "a background sweep's timer",
    "on each tick, it checks": "a watch-folder polling timer",
    "controller.tick": "the dictation watchdog's method name",
    "cannot tick faster": "a Quillin schedule timer",
    "because it ticks and writes": "a Quillin schedule timer",
}


def _sources() -> Iterator[Path]:
    yield from sorted((_ROOT / "docs").rglob("*.md"))
    for docs in sorted((_ROOT / "standalone").glob("*/docs")):
        yield from sorted(docs.rglob("*.md"))
    yield from sorted((_ROOT / "docs" / "site").rglob("*.html"))
    yield _ROOT / "quill" / "core" / "help" / "topics.json"
    quill = _ROOT / "quill"
    for pattern in ("*surface_help*.py", "settings_help*.py", "tutorials/*.py"):
        yield from sorted(quill.rglob(pattern))


def _flatten(path: Path) -> str:
    """What a person reads, on one line: tags, entities and wraps removed."""
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix == ".html":
        text = re.sub(r"<[^>]+>", "", text)
        text = html.unescape(text)
    text = text.replace("“", '"').replace("”", '"')
    text = text.replace("‘", "'").replace("’", "'")
    text = re.sub(r"\s+", " ", text)
    if path.suffix == ".py":
        # Adjacent string literals read as one sentence.
        text = re.sub(r'"\s*"', "", text)
    return text


def _allowed_spans(text: str) -> tuple[list[tuple[int, int]], set[str]]:
    lowered = text.lower()
    spans: list[tuple[int, int]] = []
    used: set[str] = set()
    for phrase in ALLOWED:
        needle = phrase.lower()
        start = lowered.find(needle)
        while start != -1:
            spans.append((start, start + len(needle)))
            used.add(phrase)
            start = lowered.find(needle, start + 1)
    return spans, used


def _scan() -> tuple[list[str], set[str]]:
    offenders: list[str] = []
    used: set[str] = set()
    seen: set[Path] = set()
    for path in _sources():
        if path in seen or not path.is_file():
            continue
        seen.add(path)
        text = _flatten(path)
        if not _WORD.search(text):
            continue
        spans, file_used = _allowed_spans(text)
        used |= file_used
        for match in _WORD.finditer(text):
            if any(a <= match.start() and match.end() <= b for a, b in spans):
                continue
            snippet = text[max(0, match.start() - 50) : match.end() + 30]
            offenders.append(f"{path.relative_to(_ROOT).as_posix()}: ...{snippet}...")
    return offenders, used


def test_no_check_box_is_ticked() -> None:
    offenders, _used = _scan()
    assert offenders == [], (
        "Say check, checked, checking or uncheck about a check box, never tick. "
        "If this one really is a timer or a sound, add the phrase to ALLOWED with "
        "the reason:\n" + "\n".join(offenders)
    )


def test_every_allowed_phrase_is_still_used() -> None:
    _offenders, used = _scan()
    stale = sorted(set(ALLOWED) - used)
    assert stale == [], f"ALLOWED phrases nothing uses any more: {stale}"


def test_a_check_box_sentence_is_caught() -> None:
    """The gate's own tripwire: the shapes it exists to stop still fail."""
    for sentence in (
        "Tick the box and choose Move.",
        "Every box starts unticked.",
        "a tick box in Preferences",
        "Ticking it shows the agreement.",
    ):
        spans, _used = _allowed_spans(sentence)
        hits = [
            m
            for m in _WORD.finditer(sentence)
            if not any(a <= m.start() and m.end() <= b for a, b in spans)
        ]
        assert hits, sentence
