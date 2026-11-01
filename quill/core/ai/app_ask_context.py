"""What each QuillVille app tells Ask, as named facts (codex.md 10C.3, 10C.4).

Ask takes a small block of facts from the app's own state, rebuilt for every
turn, plus the person's question. Each app has one provider here, wx-free, that
takes the plain data the app already holds and returns :class:`AppFacts`. The
editors' provider is :func:`quill.core.ai.ask_context.ask_context`.

**Never leaves the machine without a yes (10C.3).** Every fact has a kind;
anything but plain is held back until the person agrees to that kind:
pictures and screenshots, audio (never, in practice -- nothing here carries it),
a whole document or transcript beyond the app's scope, Radio listening
history, file paths and folder names, account names and emails, and exact
coordinates. :func:`filter_facts` does the holding back, and plain values are
scrubbed on the way (:func:`scrub`): a path becomes its file name, an email
becomes "an email address", a pair of coordinates becomes "a place".

**Follow-ups (10C.4).** The facts are fresh every turn, and
:func:`change_note` says what moved since the last question: "Now playing
changed since your last question."

wx-free and strict-typed.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING

from quill.core.ai.connection_caps import CONNECTION_NAMES

if TYPE_CHECKING:
    from quill.core.abbreviations import Abbreviation
    from quill.core.audio.media_probe import MediaInfo
    from quill.core.demo_recording import Finding
    from quill.core.demo_recording_verify import Verification
    from quill.core.weather.models import WeatherReport

__all__ = [
    "ACCOUNT",
    "AUDIO",
    "COORDINATES",
    "HISTORY",
    "NEVER_WITHOUT_YES",
    "PATH",
    "PICTURE",
    "PLAIN",
    "WHOLE_TEXT",
    "AppFacts",
    "Fact",
    "asking_line",
    "beacon_context",
    "cast_context",
    "change_note",
    "changed_facts",
    "converter_context",
    "facts_text",
    "filter_facts",
    "inkwell_context",
    "place_name",
    "player_context",
    "radio_context",
    "scrub",
    "studio_context",
    "transcribe_context",
    "weather_context",
]

# -- kinds ------------------------------------------------------------------- #

PLAIN = "plain"
PICTURE = "picture"
AUDIO = "audio"
WHOLE_TEXT = "whole_text"
HISTORY = "history"
PATH = "path"
ACCOUNT = "account"
COORDINATES = "coordinates"

#: The kinds that never leave without the person's yes (10C.3).
NEVER_WITHOUT_YES: frozenset[str] = frozenset({
    PICTURE,
    AUDIO,
    WHOLE_TEXT,
    HISTORY,
    PATH,
    ACCOUNT,
    COORDINATES,
})

#: The longest single fact, in characters. Ask is a conversation, not an upload.
_FACT_CHARS = 6000
#: The longest transcript excerpt sent without a yes.
_TRANSCRIPT_CHARS = 12000


@dataclass(frozen=True, slots=True)
class Fact:
    """One named fact: "Now playing", "Sunny, 72 F"."""

    name: str
    value: str
    kind: str = PLAIN


@dataclass(frozen=True, slots=True)
class AppFacts:
    """One turn's facts for one app, and what was held back for want of a yes."""

    app: str
    facts: tuple[Fact, ...]
    held_back: tuple[str, ...] = field(default_factory=tuple)

    def get(self, name: str) -> str:
        return next((f.value for f in self.facts if f.name == name), "")


# -- scrubbing --------------------------------------------------------------- #

_WIN_PATH = re.compile(r"(?:[A-Za-z]:\\|\\\\)[^\s\"'<>|]*")
_POSIX_PATH = re.compile(r"(?<![\w.])/(?:[\w.-]+/)+[\w.-]*")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_COORDS = re.compile(r"-?\d{1,3}\.\d{2,}\s*,\s*-?\d{1,3}\.\d{2,}")


def _base(match: re.Match[str]) -> str:
    text = match.group(0).rstrip("\\/")
    name = re.split(r"[\\/]", text)[-1]
    return name or "a folder"


def scrub(value: str) -> str:
    """*value* without paths, emails or coordinates (10C.3)."""
    value = _EMAIL.sub("an email address", value)
    value = _COORDS.sub("a place", value)
    value = _WIN_PATH.sub(_base, value)
    return _POSIX_PATH.sub(_base, value)


def _cap(value: str, limit: int = _FACT_CHARS) -> str:
    value = value.strip()
    return value if len(value) <= limit else value[:limit].rstrip() + " ..."


def filter_facts(facts: AppFacts, consented: Iterable[str] = ()) -> AppFacts:
    """Hold back every fact whose kind needs a yes the person has not given."""
    allowed = set(consented)
    kept: list[Fact] = []
    held = list(facts.held_back)
    for fact in facts.facts:
        if not fact.value.strip():
            continue
        if fact.kind in NEVER_WITHOUT_YES and fact.kind not in allowed:
            held.append(fact.name)
            continue
        kept.append(replace(fact, value=scrub(fact.value)) if fact.kind == PLAIN else fact)
    return AppFacts(facts.app, tuple(kept), tuple(held))


def facts_text(facts: AppFacts) -> str:
    """The facts block one turn sends, as ``Name: value`` lines (``{context}``)."""
    lines: list[str] = []
    for fact in facts.facts:
        value = fact.value.strip()
        if not value:
            continue
        if "\n" in value:
            lines.append(f"{fact.name}:\n{value}")
        else:
            lines.append(f"{fact.name}: {value}")
    return "\n".join(lines)


def changed_facts(previous: AppFacts | None, current: AppFacts) -> list[str]:
    """The names of facts whose value differs from the last question's."""
    if previous is None:
        return []
    before = {f.name: f.value for f in previous.facts}
    return [f.name for f in current.facts if f.name in before and before[f.name] != f.value]


def change_note(previous: AppFacts | None, current: AppFacts) -> str:
    """ "Now playing changed since your last question.", or nothing."""
    names = changed_facts(previous, current)
    if not names:
        return ""
    if len(names) == 1:
        joined = names[0]
    else:
        joined = ", ".join(names[:-1]) + " and " + names[-1]
    joined = joined[:1].upper() + joined[1:]
    verb = "changed"
    return f"{joined} {verb} since your last question."


def asking_line(connection: str, subject: str) -> str:
    """Ask's first line: "Asking My ChatGPT plan about this station." (10C.2)."""
    who = CONNECTION_NAMES.get(connection, connection)
    return f"Asking {who} about {subject}." if subject else f"Asking {who}."


def _clock(seconds: float) -> str:
    total = max(0, int(seconds))
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"


def _facts(app: str, *facts: Fact) -> AppFacts:
    return AppFacts(app, tuple(f for f in facts if f.value.strip()))


# -- Radio ------------------------------------------------------------------- #

_WANTS_FAVORITES = re.compile(r"\b(favou?rites?|my stations|like mine|recommend)\b", re.I)
_WANTS_SONGS = re.compile(
    r"\b(lately|recent(ly)?|been (hearing|playing)|songs? (heard|played))\b", re.I
)
_WANTS_LISTENING = re.compile(
    r"\b(history|everything i('ve| have) (played|heard)|across my)\b", re.I
)


def radio_context(
    station: str,
    now_playing: str,
    *,
    question: str = "",
    needs: str = "",
    favorites: Sequence[tuple[str, str]] = (),
    recent_songs: Sequence[str] = (),
    listening: Sequence[tuple[str, Sequence[str]]] = (),
) -> AppFacts:
    """Station and now playing, always; favourites and recent songs only when the
    question needs them; listening history only as a HISTORY fact, held back
    until the person says yes. *needs* is a quick question's ``needs``
    (:mod:`quill.core.radio.assistant_prompt`), which overrides the guess."""
    from quill.core.radio.assistant_prompt import (
        NEEDS_FAVORITES,
        NEEDS_LISTENING,
        NEEDS_RECENT_SONGS,
        extra_context,
    )

    wants_fav = needs == NEEDS_FAVORITES or (not needs and bool(_WANTS_FAVORITES.search(question)))
    wants_songs = needs == NEEDS_RECENT_SONGS or (not needs and bool(_WANTS_SONGS.search(question)))
    wants_hist = needs == NEEDS_LISTENING or (not needs and bool(_WANTS_LISTENING.search(question)))
    return _facts(
        "radio",
        Fact("Station", station.strip() or "nothing playing"),
        Fact("Now playing", now_playing.strip()),
        Fact(
            "Favourite stations",
            extra_context(NEEDS_FAVORITES, favorites=favorites) if wants_fav else "",
        ),
        Fact(
            "Songs heard on this station",
            extra_context(NEEDS_RECENT_SONGS, recent_songs=recent_songs) if wants_songs else "",
        ),
        Fact(
            "Listening history",
            extra_context(NEEDS_LISTENING, listening=listening) if wants_hist else "",
            HISTORY,
        ),
    )


# -- Cast -------------------------------------------------------------------- #


def cast_context(
    show: str,
    episode: str,
    *,
    notes: str = "",
    chapters: Sequence[tuple[str, float]] = (),
    position_s: float | None = None,
    duration_s: float | None = None,
) -> AppFacts:
    """The episode, its show notes, chapters and the listener's position.

    *chapters* are ``(title, start in seconds)``, in order.
    """
    where = ""
    current = ""
    if position_s is not None:
        where = _clock(position_s)
        if duration_s:
            where += f" of {_clock(duration_s)}"
        before = [title for title, start in chapters if start <= position_s]
        current = before[-1] if before else ""
    listing = "\n".join(f"{_clock(start)} {title}" for title, start in chapters[:60])
    return _facts(
        "cast",
        Fact("Show", show),
        Fact("Episode", episode),
        Fact("Position", where),
        Fact("Current chapter", current),
        Fact("Chapters", listing),
        Fact("Show notes", _cap(notes)),
    )


# -- Studio ------------------------------------------------------------------ #


def studio_context(
    *,
    plan_summary: str = "",
    findings: Sequence[Finding] = (),
    capture: Mapping[str, str] | None = None,
    verification: Verification | None = None,
) -> AppFacts:
    """The plan (``demo_recording.summary``), the pre-flight findings, the capture
    facts ``gather_facts`` measured, and the last recording check's result."""
    found = "\n".join(f"{f.severity}: {f.text}" for f in findings) if findings else ""
    if not findings and plan_summary:
        found = "No problems found."
    measured = "\n".join(f"{k}: {v}" for k, v in (capture or {}).items() if str(v).strip())
    last = ""
    if verification is not None:
        problems = [f"{c.name}: {c.detail}" for c in verification.checks if not c.passed]
        last = f"{verification.state}. {verification.sentence}"
        if problems:
            last += "\n" + "\n".join(problems)
    return _facts(
        "studio",
        Fact("Recording plan", plan_summary),
        Fact("Pre-flight check", found),
        Fact("Capture facts", measured),
        Fact("Last recording check", last),
    )


# -- Transcribe -------------------------------------------------------------- #


def transcribe_context(
    transcript: str, *, title: str = "", speakers: Sequence[str] | None = None
) -> AppFacts:
    """The transcript open, up to a limit, and its speakers. Anything past the
    limit is a WHOLE_TEXT fact, held back without a yes."""
    from quill.core.ai.transcript_actions import _SPEAKER_LINE

    if speakers is None:
        seen: list[str] = []
        for match in _SPEAKER_LINE.finditer(transcript):
            label = match.group(1).strip("[] ")
            if label and label not in seen:
                seen.append(label)
        speakers = seen if len(seen) >= 2 else []
    text = transcript.strip()
    head, rest = text[:_TRANSCRIPT_CHARS], text[_TRANSCRIPT_CHARS:]
    return _facts(
        "transcribe",
        Fact("Transcript title", title),
        Fact("Speakers", ", ".join(speakers)),
        Fact("Transcript", head),
        Fact("Rest of the transcript", rest, WHOLE_TEXT),
    )


# -- Converter --------------------------------------------------------------- #


def converter_context(files: Sequence[MediaInfo], *, limit: int = 20) -> AppFacts:
    """The queued files, as the File Properties text ``media_probe.describe`` makes."""
    from quill.core.audio.media_probe import describe

    blocks = ["\n".join(describe(info)) for info in files[:limit]]
    more = len(files) - limit
    if more > 0:
        blocks.append(f"And {more} more files.")
    return _facts(
        "converter",
        Fact("Files queued", str(len(files)) if files else ""),
        Fact("File details", "\n\n".join(blocks)),
    )


# -- Player ------------------------------------------------------------------ #


def player_context(
    book: str,
    *,
    author: str = "",
    chapter_title: str = "",
    chapter_number: int = 0,
    chapter_count: int = 0,
    position_s: float | None = None,
    duration_s: float | None = None,
) -> AppFacts:
    """The book, the chapter and the place in it."""
    chapter = chapter_title
    if chapter_number and chapter_count:
        chapter = f"{chapter} (chapter {chapter_number} of {chapter_count})".strip()
    where = ""
    if position_s is not None:
        where = _clock(position_s) + (f" of {_clock(duration_s)}" if duration_s else "")
    return _facts(
        "player",
        Fact("Book", book),
        Fact("Author", author),
        Fact("Chapter", chapter),
        Fact("Position", where),
    )


# -- Weather ----------------------------------------------------------------- #

_LOOKS_LIKE_COORDS = re.compile(r"^\s*-?\d{1,3}(\.\d+)?\s*,\s*-?\d{1,3}(\.\d+)?\s*$")


def place_name(name: str, *, fallback: str = "the saved place") -> str:
    """A place's name, never its coordinates: a bare ``lat,lon`` becomes *fallback*."""
    name = (name or "").strip()
    if not name or _LOOKS_LIKE_COORDS.match(name):
        return fallback
    return _COORDS.sub(fallback, name)


def weather_context(report: WeatherReport, *, hours: int = 12, periods: int = 4) -> AppFacts:
    """The place's name (never coordinates), conditions, forecast and alerts.

    Alerts are named as the Weather Service wrote them, so a model is told they
    exist but is never the one who words them (10E.9).
    """
    loc = report.location
    name = place_name(loc.resolved_name or loc.display_name)
    now = ""
    cur = report.current
    if cur is not None:
        bits = [cur.text_description]
        if cur.temperature_f is not None:
            bits.append(f"{cur.temperature_f:.0f} F")
        if cur.feels_like_f is not None:
            bits.append(f"feels like {cur.feels_like_f:.0f} F")
        if cur.wind_speed_mph is not None:
            wind = f"wind {cur.wind_direction} {cur.wind_speed_mph:.0f} mph".replace("  ", " ")
            bits.append(wind)
        if cur.humidity_percent is not None:
            bits.append(f"humidity {cur.humidity_percent:.0f} percent")
        now = ", ".join(b for b in bits if b)
    hourly = "\n".join(
        f"{h.time}: {h.temperature} {h.temperature_unit}, {h.short_forecast}"
        + (f", {h.precipitation_percent} percent chance of rain" if h.precipitation_percent else "")
        + (f", wind {h.wind_speed}" if h.wind_speed else "")
        for h in report.hourly[:hours]
    )
    forecast = "\n".join(
        f"{p.name}: {p.detailed_forecast or p.short_forecast}" for p in report.periods[:periods]
    )
    alerts = "\n".join(
        f"{a.event}" + (f" -- {a.headline}" if a.headline else "") for a in report.alerts
    )
    return _facts(
        "weather",
        Fact("Place", name),
        Fact("Current conditions", now),
        Fact("Next hours", hourly),
        Fact("Forecast", forecast),
        Fact("Active alerts, as the Weather Service wrote them", alerts),
    )


# -- Inkwell ----------------------------------------------------------------- #


def inkwell_context(abbreviations: Sequence[Abbreviation], *, limit: int = 80) -> AppFacts:
    """The abbreviations, by name and expansion, most used first."""
    ranked = sorted(abbreviations, key=lambda a: (-a.usage_count, a.abbreviation.lower()))
    rows = [
        f"{a.abbreviation} -> {_cap(a.expansion, 200)}"
        + (f" (used {a.usage_count} times)" if a.usage_count else "")
        for a in ranked[:limit]
        if a.enabled
    ]
    return _facts(
        "inkwell",
        Fact("Abbreviations", str(len(abbreviations)) if abbreviations else ""),
        Fact("Abbreviation list", "\n".join(rows)),
    )


# -- Beacon ------------------------------------------------------------------ #


def beacon_context(
    *,
    note_title: str = "",
    note_text: str = "",
    tags: Sequence[str] = (),
    search: str = "",
    results: Sequence[tuple[str, str]] = (),
    limit: int = 20,
) -> AppFacts:
    """The note open, or the search results open (``(title, snippet)`` pairs)."""
    listing = "\n".join(
        f"- {title}" + (f": {_cap(snippet, 300)}" if snippet else "")
        for title, snippet in results[:limit]
    )
    return _facts(
        "beacon",
        Fact("Note", note_title),
        Fact("Tags", ", ".join(tags)),
        Fact("Note text", _cap(note_text)),
        Fact("Search", search),
        Fact("Search results", listing),
    )
