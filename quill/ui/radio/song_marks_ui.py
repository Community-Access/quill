"""The song-mark commands: jump between songs, ask where you are, save songs.

Every title change while the time-shift buffer runs marks where that song
starts (:mod:`quill.core.radio.song_marks`, kept by the mpv engine in
:mod:`quill.ui.radio.mpv_live_extras`). These are the commands that use the
marks, plus the per-station time-shift length. The ideas -- segment
bookmarks, writing current, previous, next or all segments to their own
files, and a time-shift length per station -- come from BlindRadio by
serrebidev (MIT).

What is spoken follows GATE-13: after a jump, the song's title and how far
behind live you now are, because nothing else on screen can tell you; after
a save, what was saved or why not. Nothing about focus, and nothing the
screen reader already says.

Plain functions taking the app as ``app`` (the ``tiered_seek_ui`` shape), so
the main frame gains no handler bodies and each one is testable with a fake
controller and a fake engine.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from quill.core.radio import song_marks
from quill.core.radio.song_marks import Song, Which

_log = logging.getLogger(__name__)

NO_MARKS = (
    "No songs are marked in the buffer yet. They are marked as the station sends song titles."
)
RECORDING_REFUSAL = "This is a recording, not live radio, so it has no song marks."

_MISSING = {
    Which.CURRENT: "No song is marked where you are listening.",
    Which.PREVIOUS: "There is no earlier song in the buffer.",
    Which.NEXT: "There is no next song yet; you are at the newest one.",
}


# -- reaching the buffer ---------------------------------------------------------


def _extras(app: Any) -> Any | None:
    """The playing mpv engine's live extras, or None after saying why not."""
    controller = getattr(app, "_radio_controller", None)
    station = getattr(getattr(controller, "state", None), "station", None)
    if controller is None or station is None:
        app._announce("Nothing is playing.")
        return None
    engine = getattr(controller, "_mpv_engine", None)
    if not controller._is_mpv_active() or engine is None or not getattr(engine, "_loaded", False):
        app._announce(app._radio_dvr_unavailable_message())
        return None
    if engine.is_bounded():
        app._announce(RECORDING_REFUSAL)
        return None
    return engine.live_extras


def _snapshot(extras: Any) -> tuple[list[Song], float, float] | None:
    """``(songs, playhead, live edge)``, or None when mpv cannot say."""
    playhead = extras.playhead()
    live = extras.live_edge()
    if playhead is None or live is None:
        return None
    start = extras.buffer_start()
    if start is None:
        start = 0.0
    return extras.marks.songs(start, max(live, playhead)), playhead, live


def _title(raw: str) -> str:
    from quill.core.radio.now_playing import render_now_playing

    return render_now_playing(raw) or raw


# -- jumping ---------------------------------------------------------------------


def previous_song(app: Any) -> None:
    """Back to the start of this song, or the one before when it has just begun."""
    _jump(app, forward=False)


def next_song(app: Any) -> None:
    """On to the start of the next song; after the last one, back to live."""
    _jump(app, forward=True)


def _jump(app: Any, *, forward: bool) -> None:
    extras = _extras(app)
    if extras is None:
        return
    snap = _snapshot(extras)
    if snap is None or not snap[0]:
        app._announce(NO_MARKS)
        return
    songs, playhead, live = snap
    behind = max(0.0, live - playhead)
    target = song_marks.jump(songs, playhead, forward=forward, behind_live=behind >= 5.0)
    if target.live:
        app.radio_jump_to_live()
        return
    if target.song is None:
        app._announce(
            "You are listening live; there is no next song yet."
            if forward
            else "This is the oldest song in the buffer."
        )
        return
    if not extras.seek_to(target.song.start):
        app._announce("Could not move in the buffer.")
        return
    phrase = app._radio_behind_live_phrase(max(0.0, live - target.song.start))
    # The behind-live phrase always ends in a full stop ("Live." or "N seconds
    # behind live.").
    # announce-punctuation: exempt
    app._announce(f"{_title(target.song.title)}. {phrase}")


def which_song(app: Any) -> None:
    """Say which song you are in, how far into it, and how far behind live."""
    extras = _extras(app)
    if extras is None:
        return
    snap = _snapshot(extras)
    if snap is None:
        app._announce(NO_MARKS)
        return
    songs, playhead, live = snap
    behind = app._radio_behind_live_phrase(max(0.0, live - playhead))
    current = song_marks.pick(songs, playhead, Which.CURRENT)
    if not current:
        # announce-punctuation: exempt (the behind-live phrase ends in a full stop)
        app._announce(f"No song is marked here yet. {behind}")
        return
    song = current[0]
    into = song_marks.describe_offset(playhead - song.start)
    count = len(songs)
    place = f"song {songs.index(song) + 1} of {count} in the buffer"
    # announce-punctuation: exempt (the behind-live phrase ends in a full stop)
    app._announce(f"{_title(song.title)}, {into} in, {place}. {behind}")


# -- saving ----------------------------------------------------------------------


def save_current(app: Any) -> None:
    save_songs(app, Which.CURRENT)


def save_previous(app: Any) -> None:
    save_songs(app, Which.PREVIOUS)


def save_next(app: Any) -> None:
    save_songs(app, Which.NEXT)


def save_all(app: Any) -> None:
    save_songs(app, Which.ALL)


def plan_files(
    songs: list[Song],
    *,
    folder: Path,
    pattern: str,
    station: str,
    extension: str,
    live_edge: float,
    now: datetime,
) -> list[tuple[Song, Path]]:
    """Name a file for each song, none of which exists or repeats (pure apart
    from checking the folder).

    Named the recorder's way -- its filename pattern for the station and the
    time the song went out, then the song as the song splitter names it --
    so a saved song sits beside your recordings and sorts with them.
    """
    from quill.core.radio.recording_commands import build_filename, uniquify
    from quill.core.radio.recording_split import song_file_name

    reserved: set[Path] = set()
    out: list[tuple[Song, Path]] = []
    for song in songs:
        when = now - timedelta(seconds=max(0.0, live_edge - song.start))
        stem = build_filename(pattern, station=station, when=when)
        path = uniquify(folder / f"{stem} - {song_file_name(song.title)}{extension}", reserved)
        reserved.add(path)
        out.append((song, path))
    return out


def _destination(app: Any) -> Path:
    from quill.core.radio import recording

    settings = getattr(app, "_radio_recording_settings", None)
    root = str(getattr(settings, "destination_root", "") or "")
    return Path(root) if root else recording._default_dir()


def save_songs(app: Any, which: Which) -> None:
    """Write the chosen song (or every buffered song) to its own file.

    The audio is copied out of the buffer exactly as the station sent it --
    no decoding, no re-encoding -- on a worker thread, so the window stays
    free while a long buffer writes.
    """
    extras = _extras(app)
    if extras is None:
        return
    snap = _snapshot(extras)
    if snap is None or not snap[0]:
        app._announce(NO_MARKS)
        return
    songs, playhead, live = snap
    chosen = song_marks.pick(songs, playhead, which)
    if not chosen:
        app._announce(_MISSING.get(which, NO_MARKS))
        return
    from quill.core.radio.local_clock import local_now

    station = getattr(app._radio_controller.state.station, "display_name", "") or "Radio"
    folder = _destination(app)
    settings = getattr(app, "_radio_recording_settings", None)
    from quill.core.radio import recording

    pattern = str(getattr(settings, "filename_pattern", "") or recording._DEFAULT_FILENAME_PATTERN)
    planned = plan_files(
        chosen,
        folder=folder,
        pattern=pattern,
        station=station,
        extension=song_marks.extension_for_codec(extras.codec()),
        live_edge=live,
        now=local_now(),
    )

    def _write(**_kwargs: object) -> list[Path]:
        folder.mkdir(parents=True, exist_ok=True)
        written: list[Path] = []
        for song, path in planned:
            if not extras.dump(song.start, song.end, str(path)):
                break
            written.append(path)
        return written

    def _done(_op: str, written: object) -> None:
        paths = written if isinstance(written, list) else []
        app._wx.CallAfter(app._announce, describe_saved(planned, paths, folder))

    def _failed(_op: str, error: BaseException) -> None:
        _log.warning("saving songs from the buffer failed: %s", error)
        app._wx.CallAfter(app._announce, describe_saved(planned, [], folder))

    app._task_manager.submit("radio-save-songs", _write, on_success=_done, on_failure=_failed)


def describe_saved(planned: list[tuple[Song, Path]], written: list[Path], folder: Path) -> str:
    """What one save says when it finishes (pure)."""
    if not written:
        if len(planned) == 1:
            return f"{_title(planned[0][0].title)} could not be saved."
        return "The songs could not be saved."
    if len(planned) == 1:
        return f"Saved {_title(planned[0][0].title)} to {folder.name}."
    if len(written) < len(planned):
        return f"Saved {len(written)} of {len(planned)} songs to {folder.name}; the rest failed."
    return f"Saved {len(written)} songs to {folder.name}."


# -- the station's own time-shift length ------------------------------------------


def _favorite_for(app: Any, station: Any) -> Any | None:
    if station is None:
        return None
    key = getattr(station, "station_uuid", "") or getattr(station, "stream_url", "")
    favorites = getattr(app, "_radio_favorites", None)
    return favorites.find(key) if favorites is not None and key else None


def resolve_timeshift_minutes(app: Any, station: Any) -> int:
    """The buffer length *station* plays with: its favorite's own, else Preferences."""
    from quill.core.radio import timeshift

    favorite = _favorite_for(app, station)
    own = getattr(favorite, "timeshift_minutes", timeshift.FOLLOW_PREFERENCES)
    return timeshift.resolve_minutes(own, getattr(app._radio_history, "timeshift_minutes", 60))


def _target_favorite(app: Any) -> Any | None:
    """The playing station's favorite, else the favorite selected in the tree."""
    controller = getattr(app, "_radio_controller", None)
    playing = _favorite_for(app, getattr(getattr(controller, "state", None), "station", None))
    if playing is not None:
        return playing
    pick_selected = getattr(app, "_selected_favorite", None)
    return pick_selected() if callable(pick_selected) else None


def choose_station_timeshift(app: Any) -> None:
    """Pick this station's own time-shift length, or follow Preferences."""
    from quill.core.radio import timeshift

    favorite = _target_favorite(app)
    if favorite is None:
        app._announce(
            "Add this station to your favorites first; its time-shift length is kept with it."
        )
        return
    rows = timeshift.station_choices(getattr(app._radio_history, "timeshift_minutes", 60))
    current = timeshift.normalise_station_minutes(favorite.timeshift_minutes)
    index = next((i for i, (minutes, _label) in enumerate(rows) if minutes == current), 0)
    chosen = _ask_choice(
        app,
        f"How much of {favorite.display_label} should the time-shift buffer keep?",
        f"Time-Shift Length for {favorite.display_label}",
        [label for _minutes, label in rows],
        index,
    )
    if chosen is None or rows[chosen][0] == current:
        return
    favorite.timeshift_minutes = rows[chosen][0]
    app._persist_radio_favorites()
    app._announce(
        f"{favorite.display_label}: {rows[chosen][1]}. "
        "It takes effect the next time this station starts."
    )


def _ask_choice(app: Any, prompt: str, title: str, labels: list[str], index: int) -> int | None:
    """The platform's own single-choice list. The chosen row, or None on cancel."""
    import wx

    from quill.ui import modal_stack

    with wx.SingleChoiceDialog(modal_stack.parent_window(app), prompt, title, labels) as dialog:
        dialog.SetSelection(index)
        if dialog.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
            return None
        return int(dialog.GetSelection())


# -- the second source of titles ---------------------------------------------------


def note_title(app: Any, title: str) -> None:
    """A title read from outside mpv (ICY tap, status page): mark the live edge.

    Never raises and never speaks: it is bookkeeping on the way to the
    announcement the title already gets.
    """
    try:
        controller = getattr(app, "_radio_controller", None)
        engine = getattr(controller, "_mpv_engine", None)
        if controller is None or engine is None or not controller._is_mpv_active():
            return
        if getattr(engine, "_loaded", False) and not engine.is_bounded():
            engine.live_extras.mark_live_edge(title)
    except Exception:  # noqa: BLE001
        _log.exception("could not mark a song in the buffer")


__all__ = [
    "choose_station_timeshift",
    "describe_saved",
    "next_song",
    "note_title",
    "plan_files",
    "previous_song",
    "resolve_timeshift_minutes",
    "save_all",
    "save_current",
    "save_next",
    "save_previous",
    "save_songs",
    "which_song",
]
