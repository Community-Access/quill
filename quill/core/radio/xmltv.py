"""XMLTV: the programme-guide format, read from a file the listener placed.

XMLTV is the lingua franca of TV listings -- a plain XML document of
``<programme channel="BBCOne.uk" start="..." stop="...">`` elements -- and the
iptv.org catalog's channel ids *are* XMLTV ids, so a guide and the TV branch
join on nothing more than a string.

WHERE THE GUIDE COMES FROM, and why it is a file
------------------------------------------------
There is no one XMLTV feed to fetch: guides are a choose-your-own ecosystem
(national broadcasters publish some, the ``iptv-org/epg`` project generates
them per site, paid services sell them). So this module reads exactly one
place -- ``<data dir>/tv_guide.xml`` -- and fetches nothing from anywhere. A
file the listener put there is consent in its plainest form, it works offline,
and it adds no egress site to the audit. The user guide says where the file
goes and where guides come from.

Parsed through :func:`quill.core.safe_xml.fromstring`, because a programme
guide is exactly the kind of large attacker-supplied XML a billion-laughs
payload arrives in. A malformed guide degrades to "no guide", never to an
exception reaching a browse tree.

The parsed guide is cached in-process keyed by the file's mtime, so annotating
ten thousand channel rows costs one parse per file change, not one per row.

wx-free, strict-typed, no network.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

#: XMLTV instant: ``20260827123000 +0000`` -- seconds and offset both optional.
_INSTANT_RE = re.compile(r"^(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})?\s*([+-]\d{4})?$")

#: Guides bigger than this are refused rather than parsed: a week of a big
#: lineup fits comfortably, and an unbounded parse of attacker-supplied XML is
#: the exact thing this cap exists to prevent.
MAX_GUIDE_BYTES = 64_000_000

GUIDE_FILE_NAME = "tv_guide.xml"


@dataclass(frozen=True, slots=True)
class Programme:
    """One scheduled programme."""

    channel: str
    start: datetime
    stop: datetime
    title: str


def parse_instant(value: str) -> datetime | None:
    """An XMLTV timestamp as an aware UTC datetime (pure), or ``None``.

    A guide without offsets is read as UTC -- the format's own default -- which
    keeps a naive guide *consistently* shifted rather than half-parsed, and a
    consistently shifted guide is visibly wrong where a half-parsed one lies.
    """
    match = _INSTANT_RE.match(str(value or "").strip())
    if match is None:
        return None
    year, month, day, hour, minute = (int(match.group(i)) for i in range(1, 6))
    second = int(match.group(6) or 0)
    offset = match.group(7)
    try:
        instant = datetime(year, month, day, hour, minute, second, tzinfo=UTC)
    except ValueError:
        return None
    if offset:
        sign = 1 if offset[0] == "+" else -1
        delta = timedelta(hours=int(offset[1:3]), minutes=int(offset[3:5]))
        instant -= sign * delta
    return instant


def parse_guide(text: str) -> dict[str, list[Programme]]:
    """Programmes by channel id from an XMLTV document (pure).

    Tolerant of everything except hostile XML: a programme missing a channel,
    a time, or a title is skipped; a document that will not parse yields an
    empty guide. Programmes come back sorted by start time per channel, which
    is what :func:`now_next` binary-searches against.
    """
    from quill.core.safe_xml import ParseError, UnsafeXMLError, fromstring

    try:
        root = fromstring(text)
    except (ParseError, UnsafeXMLError, ValueError):
        return {}
    guide: dict[str, list[Programme]] = {}
    for element in root.iter("programme"):
        channel = str(element.get("channel") or "").strip()
        start = parse_instant(element.get("start") or "")
        stop = parse_instant(element.get("stop") or "")
        title_el = element.find("title")
        title = str(title_el.text or "").strip() if title_el is not None else ""
        if not channel or start is None or stop is None or not title:
            continue
        guide.setdefault(channel, []).append(
            Programme(channel=channel, start=start, stop=stop, title=title)
        )
    for programmes in guide.values():
        programmes.sort(key=lambda p: p.start)
    return guide


def now_next(
    guide: dict[str, list[Programme]], channel: str, at: datetime
) -> tuple[Programme | None, Programme | None]:
    """The programme on *channel* at *at*, and the one after it (pure)."""
    programmes = guide.get(channel, [])
    current: Programme | None = None
    upcoming: Programme | None = None
    for programme in programmes:
        if programme.start <= at < programme.stop:
            current = programme
        elif programme.start > at:
            upcoming = programme
            break
    return current, upcoming


def note_for(guide: dict[str, list[Programme]], channel: str, at: datetime) -> str:
    """One row note: ``"Now: X. Next: Y."`` -- empty when the guide is silent."""
    current, upcoming = now_next(guide, channel, at)
    parts = []
    if current is not None:
        parts.append(f"Now: {current.title}.")
    if upcoming is not None:
        parts.append(f"Next: {upcoming.title}.")
    return " ".join(parts)


# --- the listener's own guide file -------------------------------------------

_loaded: tuple[Path, float, dict[str, list[Programme]]] | None = None


def guide_path() -> Path:
    """Where the guide lives: ``<data dir>/tv_guide.xml``."""
    from quill.core.paths import app_data_dir

    return app_data_dir() / GUIDE_FILE_NAME


def load_guide() -> dict[str, list[Programme]]:
    """The listener's guide, parsed once per file change. ``{}`` without one.

    Keyed by the file's mtime and size: annotating ten thousand rows costs one
    parse per edit, and a listener who deletes the file gets silence on the
    next read rather than a ghost of it.
    """
    global _loaded
    path = guide_path()
    try:
        stat = path.stat()
    except OSError:
        _loaded = None
        return {}
    if stat.st_size > MAX_GUIDE_BYTES:
        return {}
    stamp = float(stat.st_mtime_ns) + float(stat.st_size)
    if _loaded is not None and _loaded[0] == path and _loaded[1] == stamp:
        return _loaded[2]
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    guide = parse_guide(text)
    _loaded = (path, stamp, guide)
    return guide


def now_next_note(channel: str, at: datetime | None = None) -> str:
    """The "Now / Next" note for *channel* from the listener's guide, or ``""``."""
    if not channel:
        return ""
    guide = load_guide()
    if not guide:
        return ""
    return note_for(guide, channel, at or datetime.now(UTC))


def reset_for_tests() -> None:
    """Forget the cached parse, so tests can swap files under one path."""
    global _loaded
    _loaded = None
