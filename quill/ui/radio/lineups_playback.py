"""Playing a Lineup through in Quill Radio: one item after another, any kind.

A session lives on the player controller (like Local Media's), holding the
Lineup's items in the order they were started. ``track_end`` asks
:func:`handle_finished` after the live-reconnect and book checks: when the item
that ended is the session's current one, the next playable item starts.

Three rules, all about what the listener cannot see:

* **Live things never end**, so a live station or stream in a play-through
  plays until the listener moves on; the first live item of each run says how
  ("Live. Press Ctrl+Right for the next item.").
* **What is skipped is said** -- an item that has gone missing, or a place,
  which is somewhere to browse rather than something to play.
* **The end is said** ("End of Morning."), because silence is ambiguous.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from quill.core.lineups.fields import ItemFacts
from quill.core.lineups.model import Lineup
from quill.core.lineups.refs import (
    KIND_LOCAL,
    KIND_PLACE,
    KIND_YT_CHANNEL,
    ItemRef,
)
from quill.core.radio.models import RadioStation

SESSION_ATTR = "_lineup_session"
#: The app-wide next key (the transport's Next Chapter, which steps a Lineup
#: playing through even on a live stream): it works in every Radio window,
#: where the Lineups window's own Ctrl+Right works only in there (review M8).
NEXT_KEY = "Ctrl+Shift+Period"


@dataclass(slots=True)
class Entry:
    ref: ItemRef
    name: str
    station: RadioStation | None
    live: bool = False
    #: Why it cannot play here, said when it is skipped ("a place to browse").
    unplayable: str = ""


@dataclass(slots=True)
class Session:
    lineup_id: str
    lineup_name: str
    entries: list[Entry] = field(default_factory=list)
    current: int = -1
    stop_after_current: bool = False
    live_noted: bool = False
    up_next: list[Entry] = field(default_factory=list)


def station_of(
    ref: ItemRef, facts: ItemFacts | None, payload: dict[str, object] | None
) -> RadioStation | None:
    """The ``RadioStation`` Radio plays for one item, or ``None`` when it is not playable."""
    if ref.kind in (KIND_PLACE, KIND_YT_CHANNEL):
        return None
    data = dict(payload or (facts.payload if facts is not None and facts.payload else {}) or {})
    if ref.kind == KIND_LOCAL and "path" in data:
        name = facts.name if facts is not None else str(data.get("name", ""))
        return RadioStation(
            name=name or str(data["path"]),
            stream_url=str(data["path"]),
            source="Local Media",
            is_recording=True,
        )
    if not data.get("stream_url"):
        return None
    if not data.get("name") and facts is not None:
        data["name"] = facts.name
    try:
        return RadioStation.from_dict(data)
    except Exception:  # noqa: BLE001 - a malformed record is simply not playable
        return None


def entries_for(
    lineup: Lineup, refs: Sequence[ItemRef], facts: Sequence[ItemFacts | None]
) -> list[Entry]:
    entries = []
    for ref, item in zip(refs, facts, strict=True):
        row = lineup.row_for(ref)
        payload = dict(row.payload) if row is not None and row.payload else None
        station = station_of(ref, item, payload)
        name = (
            (item.name if item is not None else "")
            or (row.name if row is not None else "")
            or "Unnamed item"
        )
        unplayable = ""
        if station is None:
            unplayable = (
                "a place to browse, not something to play"
                if ref.kind in (KIND_PLACE, KIND_YT_CHANNEL)
                else "missing"
            )
        live = (
            bool(item.live)
            if item is not None
            else bool(station is not None and not station.is_recording)
        )
        entries.append(Entry(ref, name, station, live=live, unplayable=unplayable))
    return entries


def _controller(app: Any) -> Any:
    from quill.ui.radio.local_media_playback import controller_of

    return controller_of(app)


def session_of(controller: Any) -> Session | None:
    session = getattr(controller, SESSION_ATTR, None)
    return session if isinstance(session, Session) else None


def _announce(app: Any, text: str) -> None:
    speak = getattr(app, "_announce", None)
    if callable(speak) and text:
        speak(text)


def start(
    app: Any, lineup: Lineup, refs: Sequence[ItemRef], index: int, facts: Sequence[ItemFacts | None]
) -> str:
    """Play *refs* from *index* through to the end. Returns what to say first."""
    controller = _controller(app)
    if controller is None:
        return "The player is not ready."
    entries = entries_for(lineup, refs, facts)
    if not entries:
        return f"{lineup.name} has nothing to play."
    session = Session(lineup.id, lineup.name, entries)
    try:
        setattr(controller, SESSION_ATTR, session)
    except AttributeError:
        return "The player cannot play lineups."
    from quill.ui.radio.local_media_playback import remember_app

    remember_app(app)  # so an item ending in the background can find the app
    _forget_local_media_session(controller)
    if len(entries) == 1 and entries[0].station is None:
        return f"{entries[0].name} is {entries[0].unplayable}."
    return _play_from(app, session, index, skipped=[])


def _forget_local_media_session(controller: Any) -> None:
    """A Lineup and a Local Media playlist cannot both decide what comes next."""
    from quill.ui.radio import local_media_playback

    if getattr(controller, local_media_playback.SESSION_ATTR, None) is not None:
        try:
            setattr(controller, local_media_playback.SESSION_ATTR, None)
        except AttributeError:
            pass


def next_key(app: Any) -> str:
    """The app-wide next key as it is bound now, spelled the way it is said."""
    binding = ""
    finder = getattr(app, "_binding_for", None)
    if callable(finder):
        try:
            binding = str(finder("radio.transport.next_chapter") or "")
        except Exception:  # noqa: BLE001 - the default is still right
            binding = ""
    chord = binding or "Ctrl+Shift+."
    return chord.replace("+.", "+Period").replace("+,", "+Comma")


def _playable_from(session: Session, index: int, step: int) -> tuple[int | None, list[str]]:
    """The first playable entry from *index* in *step*'s direction, and what it skips."""
    skipped: list[str] = []
    position = index
    while 0 <= position < len(session.entries):
        entry = session.entries[position]
        if entry.station is not None:
            return position, skipped
        skipped.append(f"Skipped {entry.name}, {entry.unplayable}.")
        position += step
    return None, skipped


def _start_entry(app: Any, session: Session, position: int, skipped: list[str]) -> str:
    from quill.core.radio.youtube_urls import is_youtube_url

    entry = session.entries[position]
    session.current = position
    assert entry.station is not None
    _controller(app).play_station(entry.station)
    # A YouTube item is resolved first, and may yet be refused (no consent, no
    # network): "Starting" promises less than "Playing" (review M10).
    verb = "Starting" if is_youtube_url(entry.station.stream_url) else "Playing"
    notes = [*skipped, f"{verb} {entry.name}."]
    if entry.live and not session.live_noted:
        session.live_noted = True
        notes.append(f"Live. Press {next_key(app)} for the next item.")
    return " ".join(notes)


def _play_from(app: Any, session: Session, index: int, *, skipped: list[str], step: int = 1) -> str:
    """Play from *index*; at the natural end of the Lineup, end the session and say so."""
    position, passed = _playable_from(session, index, step)
    if position is not None:
        return _start_entry(app, session, position, [*skipped, *passed])
    session.current = -1
    setattr(_controller(app), SESSION_ATTR, None)
    return " ".join([*skipped, *passed, f"End of {session.lineup_name}."])


def _playing_matches(controller: Any, session: Session) -> bool:
    if not (0 <= session.current < len(session.entries)):
        return False
    station = getattr(getattr(controller, "state", None), "station", None)
    expected = session.entries[session.current].station
    return (
        station is not None and expected is not None and station.stream_url == expected.stream_url
    )


def handle_finished(controller: Any) -> bool:
    """An item ended by itself. True when the next one was started (or the end said)."""
    session = session_of(controller)
    if session is None or not _playing_matches(controller, session):
        return False
    app = _app_of_controller(controller)
    if app is None:
        return False
    if session.stop_after_current:
        session.stop_after_current = False
        name = session.entries[session.current].name
        setattr(controller, SESSION_ATTR, None)
        _announce(app, f"Stopped after {name}.")  # never silent (review N9)
        return False
    if session.up_next:
        entry = session.up_next.pop(0)
        session.entries.insert(session.current + 1, entry)
    _announce(app, _play_from(app, session, session.current + 1, skipped=[]))
    return True


def _app_of_controller(controller: Any) -> Any:
    from quill.ui.radio import local_media_playback

    return local_media_playback._app() or getattr(controller, "_app", None)


def step(app: Any, delta: int) -> str:
    """Next or Previous within the Lineup playing; the sentence to say."""
    controller = _controller(app)
    session = session_of(controller) if controller is not None else None
    if session is None:
        return "Nothing from a lineup is playing."
    step_by = 1 if delta > 0 else -1
    position, skipped = _playable_from(session, session.current + step_by, step_by)
    if position is None:
        # At either end the item playing carries on: Next and Previous never end
        # the play-through, they say where it is (review M9).
        return "This is the last item." if delta > 0 else "This is the first item."
    return _start_entry(app, session, position, skipped)


def queue(
    app: Any,
    lineup: Lineup,
    refs: Sequence[ItemRef],
    facts: Sequence[ItemFacts | None],
    *,
    at_end: bool,
) -> str:
    """Play Next or Add to Up Next, within the Lineup playing (or starting one)."""
    controller = _controller(app)
    session = session_of(controller) if controller is not None else None
    entries = [entry for entry in entries_for(lineup, refs, facts) if entry.station is not None]
    if not entries:
        return "Nothing selected can be played."
    if session is None or session.lineup_id != lineup.id:
        return start(app, lineup, refs, 0, facts)
    if at_end:
        session.up_next.extend(entries)
        return f"Added {len(entries)} to Up Next." if len(entries) != 1 else "Added to Up Next."
    session.entries[session.current + 1 : session.current + 1] = entries
    return "Plays next."


def stop_after(app: Any) -> str:
    controller = _controller(app)
    session = session_of(controller) if controller is not None else None
    if session is None:
        return "Nothing from a lineup is playing."
    session.stop_after_current = not session.stop_after_current
    return "Stops after this item." if session.stop_after_current else "Carries on after this item."


__all__ = [
    "SESSION_ATTR",
    "Entry",
    "Session",
    "entries_for",
    "handle_finished",
    "queue",
    "session_of",
    "start",
    "station_of",
    "step",
    "stop_after",
]
