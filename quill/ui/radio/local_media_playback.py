"""Playing a Local Media playlist: what plays next, and when.

A playlist plays through Quill Radio's own player, one item at a time, as an
ordinary station whose address is a file -- the same route a downloaded book
chapter takes (``book_playback``), so resume, speed, Sound Enhancements, Show
Video, the sleep timer and every transport key work on it without a second
playback path having to earn each of them again.

What this module adds is the *order*:

* **The queue is the shared one.** :class:`~quill.core.radio.play_queue.PlayQueue`
  already holds the rules the Recordings list plays by -- shuffle is a fixed
  permutation, so Previous goes back to exactly what you heard; repeat-one
  repeats on a natural end, never on Next; stop-after-this outranks repeat and
  clears itself. Here it orders item ids instead of rows, because a playlist is
  rearranged while it plays and an id survives that where a row does not.
* **Up Next comes first.** "Play Next" and "Add to Up Next" queue items ahead
  of the playlist's own order without changing it; when they are done, the
  playlist carries on from where it was.
* **Only a natural end moves on.** Stopping, or choosing a station, never
  starts something new -- the rule ``book_playback`` keeps, for the reason it
  gives: an app that plays a thing you did not ask for at the moment you asked
  it to stop is the most annoying kind.

The session lives on the player controller, because the end of a track is
reported to the controller and nothing else (``track_end``). A file played from
the Browse tree has no session yet; one is made the first time it is needed,
from the playlist that file was listed under.
"""

from __future__ import annotations

import weakref
from dataclasses import dataclass, field
from typing import Any

from quill.core.radio import local_media
from quill.core.radio.local_media import REPEAT_LABELS, MediaItem, Playlist, path_key
from quill.core.radio.play_queue import NO_ROW, REPEAT_ONE, PlayQueue, next_repeat_mode
from quill.ui.radio import local_media_ui as ui

__all__ = [
    "Session",
    "add_up_next",
    "current",
    "cycle_repeat",
    "handle_finished",
    "play_item",
    "play_next",
    "play_playlist",
    "remember_app",
    "reshuffle",
    "step",
    "summary_sentence",
    "sync",
    "toggle_shuffle",
    "toggle_stop_after",
    "where_suffix",
]

SESSION_ATTR = "_local_media_session"

#: The app frame, for a track that ends with no surface open: the end of a
#: track is told to the controller alone, which knows nothing of the library.
_APP_REF: Any = None


def remember_app(host: Any) -> None:
    """Note the app frame, so a track ending in the background can find it."""
    global _APP_REF
    app = ui.app_of(host)
    try:
        _APP_REF = weakref.ref(app)
    except TypeError:
        _APP_REF = lambda: app  # noqa: E731 - an object weakref cannot reach


def _app(fallback: Any = None) -> Any:
    app = _APP_REF() if _APP_REF is not None else None
    return app if app is not None else ui.app_of(fallback)


@dataclass(slots=True)
class Session:
    """One playlist being played: its order, and where it has got to."""

    playlist_id: str
    queue: PlayQueue = field(default_factory=PlayQueue)
    #: The item playing now (0 = none).
    current: int = 0
    #: The last item played *from the playlist's order* -- Up Next detours
    #: leave it alone, so the playlist carries on from here afterwards.
    anchor: int = 0
    up_next: list[int] = field(default_factory=list)


def controller_of(host: Any) -> Any:
    app = ui.app_of(host)
    for owner in (app, host):
        for name in ("_radio_controller", "_controller"):
            controller = getattr(owner, name, None)
            if controller is not None and hasattr(controller, "play_station"):
                return controller
    return None


def session_of(controller: Any) -> Session | None:
    session = getattr(controller, SESSION_ATTR, None)
    return session if isinstance(session, Session) else None


def _state(controller: Any) -> Any:
    return getattr(controller, "_state", None) or getattr(controller, "state", None)


def _playing_path(controller: Any) -> str:
    station = getattr(_state(controller), "station", None)
    if station is None or getattr(station, "source", "") != local_media.SOURCE_LABEL:
        return ""
    return str(getattr(station, "stream_url", "") or "")


def is_live(controller: Any) -> bool:
    """Whether the player holds something (playing, paused, connecting)."""
    from quill.ui.radio.playback_state import RESTARTABLE_STATES

    state = _state(controller)
    return state is not None and getattr(state, "state", None) in RESTARTABLE_STATES


def is_paused(controller: Any) -> bool:
    from quill.ui.radio.playback_state import RadioPlayerState

    return getattr(_state(controller), "state", None) is RadioPlayerState.PAUSED


def _build(playlist: Playlist) -> Session:
    session = Session(playlist_id=playlist.id)
    session.queue = PlayQueue(shuffle=playlist.shuffle, repeat=playlist.repeat)
    session.queue.set_rows(playlist.ids())
    return session


def _attach(controller: Any, session: Session) -> None:
    try:
        setattr(controller, SESSION_ATTR, session)
    except AttributeError:
        pass


def current(host: Any, *, ending: bool = False) -> tuple[Playlist | None, MediaItem | None]:
    """The playlist and item the player holds now, if it is Local Media's.

    Builds the session for a file played from the Browse tree, from the
    playlist it was listed under there. *ending* is the end-of-track path,
    where the player may already be on its way to Stopped.
    """
    controller = controller_of(host)
    path = _playing_path(controller)
    if not path or not (ending or is_live(controller)):
        return None, None
    lib = ui.library(_app(host))
    session = session_of(controller)
    if session is not None:
        playlist = lib.find(session.playlist_id)
        item = playlist.find(session.current) if playlist is not None else None
        if item is not None and path_key(item.path) == path_key(path):
            return playlist, item
    from quill.core.radio.browse_local_media import PLAYLIST_OF

    hinted = lib.find(PLAYLIST_OF.get(path_key(path), ""))
    candidates = [hinted] if hinted is not None else lib.playlists_with(path)
    for playlist in candidates:
        for item in playlist.items:
            if path_key(item.path) == path_key(path):
                session = _build(playlist)
                session.current = session.anchor = item.id
                _attach(controller, session)
                return playlist, item
    return None, None


# --- starting things ---------------------------------------------------------------


def _start(host: Any, session: Session, playlist: Playlist, item: MediaItem) -> bool:
    from quill.core.radio.browse_local_media import station_for

    controller = controller_of(host)
    if controller is None:
        ui.announce(host, "The player is not ready yet.")
        return False
    if not item.exists():
        ui.announce(
            host,
            f"{item.display_title} is missing: {item.path} is not there any more. "
            "Locate... on its menu finds it again.",
        )
        return False
    try:
        controller.play_station(station_for(item))
    except Exception as error:  # noqa: BLE001 - reported, never raised at a listener
        ui.announce(host, f"{item.display_title} could not be played: {error}.")
        return False
    session.current = item.id
    _attach(controller, session)
    playlist.last_item_id = item.id
    try:
        local_media.save_library(ui.library(_app(host)))
    except OSError:
        pass  # where you left off is a courtesy; failing to note it is not news
    return True


def _position(playlist: Playlist, item: MediaItem) -> str:
    return f"{playlist.index_of(item.id) + 1} of {len(playlist.items)}"


def play_item(host: Any, playlist_id: str, item_id: int, *, quiet: bool = False) -> bool:
    """Play one item, and carry on through the playlist from there."""
    lib = ui.library(host)
    playlist = lib.find(playlist_id)
    item = playlist.find(item_id) if playlist is not None else None
    if playlist is None or item is None:
        return False
    controller = controller_of(host)
    session = session_of(controller)
    if session is None or session.playlist_id != playlist_id:
        session = _build(playlist)
    else:
        sync_session(session, playlist)
    session.anchor = item.id
    if not _start(host, session, playlist, item):
        return False
    if not quiet:
        ui.announce(host, f"Playing {item.spoken()}, {_position(playlist, item)}.")
    return True


def play_playlist(host: Any, playlist_id: str, *, shuffle: bool | None = None) -> bool:
    """Play a playlist from its start -- or from a fresh shuffle of it."""
    playlist = ui.library(host).find(playlist_id)
    if playlist is None:
        return False
    if not playlist.items:
        ui.announce(host, f"{playlist.name} is empty. Add Media Files puts something in it.")
        return False
    if shuffle is not None and shuffle != playlist.shuffle:
        playlist.shuffle = shuffle
    session = _build(playlist)
    _attach(controller_of(host), session)
    for item_id in session.queue.order:
        item = playlist.find(item_id)
        if item is not None and item.exists():
            session.anchor = item.id
            if not _start(host, session, playlist, item):
                return False
            lead = "Shuffling" if playlist.shuffle else "Playing"
            ui.announce(host, f"{lead} {playlist.name}. {item.spoken()}.")
            return True
    ui.announce(host, f"Every file in {playlist.name} is missing. Locate... finds them again.")
    return False


def continue_playlist(host: Any, playlist_id: str) -> bool:
    """Continue Where I Left Off: the item that last played, at its place."""
    playlist = ui.library(host).find(playlist_id)
    if playlist is None:
        return False
    if playlist.find(playlist.last_item_id) is None:
        return play_playlist(host, playlist_id)
    return play_item(host, playlist_id, playlist.last_item_id)


# --- moving through it ---------------------------------------------------------------


def sync_session(session: Session, playlist: Playlist) -> None:
    """Bring a session's order up to date with an edited playlist."""
    ids = playlist.ids()
    session.queue.shuffle = playlist.shuffle
    session.queue.repeat = playlist.repeat
    session.queue.follow(ids)
    present = set(ids)
    session.up_next = [item_id for item_id in session.up_next if item_id in present]


def sync(host: Any, playlist_id: str) -> None:
    """After an edit: the playing session, if it is this playlist's, follows it."""
    session = session_of(controller_of(host))
    playlist = ui.library(host).find(playlist_id)
    if session is not None and playlist is not None and session.playlist_id == playlist_id:
        sync_session(session, playlist)


def _next_id(session: Session, playlist: Playlist, *, natural: bool) -> tuple[int, bool]:
    """``(item id, from Up Next)`` for what follows, or ``(NO_ROW, False)``."""
    present = set(playlist.ids())
    if natural and session.queue.repeat == REPEAT_ONE and session.current in present:
        return session.current, session.current != session.anchor
    while session.up_next:
        candidate = session.up_next.pop(0)
        if candidate in present:
            return candidate, True
    base = session.anchor or session.current
    if natural:
        return session.queue.row_after_finishing(base), False
    return session.queue.next_row(base), False


def _advance(host: Any, session: Session, playlist: Playlist, *, natural: bool) -> bool:
    """Move to the next playable item. Missing files are skipped, said once."""
    if natural and session.queue.stop_after_current:
        session.queue.stop_after_current = False  # a one-shot: it clears as it fires
        ui.announce(host, "Stopped after that item, as you asked.")
        return False
    skipped = 0
    for _attempt in range(len(playlist.items) + len(session.up_next) + 1):
        item_id, detour = _next_id(session, playlist, natural=natural)
        if item_id == NO_ROW:
            break
        item = playlist.find(item_id)
        if item is None:
            break
        if not detour:
            session.anchor = item.id
        if not item.exists():
            skipped += 1
            natural = False  # repeat-one must not spin on a missing file
            continue
        if not _start(host, session, playlist, item):
            return False
        lead = f"Skipped {skipped} missing. " if skipped else ""
        tail = "Up next" if detour else _position(playlist, item)
        ui.announce(host, f"{lead}{item.spoken()}, {tail}.")
        return True
    if natural:
        ui.announce(host, f"That was the end of {playlist.name}.")
    else:
        ui.announce(host, f"That is the last item in {playlist.name}.")
    return False


def step(host: Any, direction: int) -> bool:
    """Next (1) or Previous (-1) in the playlist playing now. False if none.

    Previous goes back through the playlist's own order -- Up Next is a detour
    forwards, not a history -- and stops at the first item rather than wrapping
    unless the playlist repeats.
    """
    playlist, item = current(host)
    if playlist is None or item is None:
        return False
    session = session_of(controller_of(host))
    if session is None:
        return False
    sync_session(session, playlist)
    if direction > 0:
        _advance(host, session, playlist, natural=False)
        return True
    base = session.anchor or item.id
    for _attempt in range(len(playlist.items)):
        previous = session.queue.previous_row(base)
        found = playlist.find(previous) if previous != NO_ROW else None
        if found is None:
            ui.announce(host, f"That is the first item in {playlist.name}.")
            return True
        base = found.id
        if found.exists():
            session.anchor = found.id
            if _start(host, session, playlist, found):
                ui.announce(host, f"{found.spoken()}, {_position(playlist, found)}.")
            return True
    return True


def handle_finished(controller: Any) -> bool:
    """A file ended by itself. True when the next one was started.

    Called from ``track_end`` after the live-reconnect and book-chapter checks
    and before the player settles on Stopped, so the end of a song in a
    playlist is the start of the next rather than silence.
    """
    path = _playing_path(controller)
    if not path:
        return False
    app = _app()
    if app is None:
        return False
    playlist, item = current(app, ending=True)
    session = session_of(controller)
    if playlist is None or item is None or session is None:
        return False
    sync_session(session, playlist)
    return _advance(app, session, playlist, natural=True)


# --- the queue's switches ------------------------------------------------------------------


def play_next(host: Any, playlist_id: str, item_ids: list[int]) -> None:
    """Play Next: these items right after the one playing, in this order."""
    session = _session_for(host, playlist_id)
    if session is None:
        return
    session.up_next[:0] = [item_id for item_id in item_ids if item_id not in session.up_next]
    count = len(item_ids)
    ui.announce(host, "Will play next." if count == 1 else f"{count} items will play next.")


def add_up_next(host: Any, playlist_id: str, item_ids: list[int]) -> None:
    """Add to Up Next: after anything already queued, before the playlist resumes."""
    session = _session_for(host, playlist_id)
    if session is None:
        return
    session.up_next.extend(item_id for item_id in item_ids if item_id not in session.up_next)
    ui.announce(host, f"Added to Up Next. {len(session.up_next)} waiting.")


def _session_for(host: Any, playlist_id: str) -> Session | None:
    """The session for *playlist_id*, starting one when nothing of it plays."""
    controller = controller_of(host)
    playlist = ui.library(host).find(playlist_id)
    if playlist is None:
        return None
    current(host)  # adopt a file played from Browse
    session = session_of(controller)
    if session is None or session.playlist_id != playlist_id:
        session = _build(playlist)
        _attach(controller, session)
        ui.announce(host, f"Nothing from {playlist.name} is playing; it will play when it starts.")
    return session


def toggle_shuffle(host: Any, playlist_id: str) -> bool:
    playlist = ui.library(host).find(playlist_id)
    if playlist is None:
        return False
    playlist.shuffle = not playlist.shuffle
    session = session_of(controller_of(host))
    if session is not None and session.playlist_id == playlist_id:
        session.queue.shuffle = playlist.shuffle
        session.queue.set_rows(playlist.ids())
        _keep_current_first(session)
    ui.commit(host)
    ui.announce(host, "Shuffle on." if playlist.shuffle else "Shuffle off. Playing in list order.")
    return playlist.shuffle


def reshuffle(host: Any, playlist_id: str) -> None:
    """Shuffle Again: a new order, starting after what is playing now."""
    playlist = ui.library(host).find(playlist_id)
    if playlist is None:
        return
    if not playlist.shuffle:
        toggle_shuffle(host, playlist_id)
        return
    session = session_of(controller_of(host))
    if session is not None and session.playlist_id == playlist_id:
        session.queue.set_rows(playlist.ids())
        _keep_current_first(session)
    ui.announce(host, "Shuffled again. A new order starts after this item.")


def _keep_current_first(session: Session) -> None:
    """Put what is playing at the front of a new order, so Next is all new."""
    order = session.queue.order
    keep = session.anchor or session.current
    if keep in order:
        order.remove(keep)
        order.insert(0, keep)


def cycle_repeat(host: Any, playlist_id: str) -> str:
    playlist = ui.library(host).find(playlist_id)
    if playlist is None:
        return ""
    playlist.repeat = next_repeat_mode(playlist.repeat)
    sync(host, playlist_id)
    ui.commit(host)
    ui.announce(host, REPEAT_LABELS[playlist.repeat] + ".")
    return playlist.repeat


def toggle_stop_after(host: Any) -> None:
    """Stop After This Item: a one-shot, cleared when it fires."""
    playlist, _item = current(host)
    session = session_of(controller_of(host))
    if playlist is None or session is None:
        ui.announce(host, "Nothing from Local Media is playing.")
        return
    on = session.queue.toggle_stop_after_current()
    ui.announce(host, "Will stop after this item." if on else "Will keep playing after this item.")


# --- saying where things are ------------------------------------------------------------


def where_suffix(host: Any) -> str:
    """ "3 of 12 in Road Trip" for Where Am I, when a playlist is playing."""
    playlist, item = current(host)
    if playlist is None or item is None:
        return ""
    return f"{_position(playlist, item)} in {playlist.name}"


def summary_sentence(host: Any, playlist: Playlist) -> str:
    """The playlist in a breath, and what of it is playing (pure apart from the player)."""
    parts = [f"{playlist.name}: {local_media.summary(playlist)}."]
    playing_list, item = current(host)
    if playing_list is not None and item is not None and playing_list.id == playlist.id:
        verb = "Paused at" if is_paused(controller_of(host)) else "Playing"
        parts.append(f"{verb} {_position(playlist, item)}: {item.spoken()}.")
        session = session_of(controller_of(host))
        if session is not None and session.up_next:
            parts.append(f"{len(session.up_next)} up next.")
    parts.append("Shuffle on." if playlist.shuffle else "Shuffle off.")
    parts.append(REPEAT_LABELS[playlist.repeat] + ".")
    return " ".join(parts)
