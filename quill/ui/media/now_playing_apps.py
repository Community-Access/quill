"""What each QuillVille app puts on Windows' now-playing card.

:mod:`quill.ui.audio.now_playing` owns the card; this owns what goes on it --
which is a different question per app, and the same three lines of plumbing
every time. They live together for the reason the output-device bindings do
(:mod:`quill.ui.media.output_device_apps`): a capability written once per app is
a capability that drifts, and writing it in the app pushed three modules past
their GATE-11 ceilings at once.

### What goes where, and why

Windows lays the card out with a headline and a second line. Every app here
puts **the thing being listened to** on the headline and **the detail** below
it, never the reverse:

* Quill Radio -- the station, then the song. Somebody who opens the volume
  flyout is far more often asking "what is this?" than "what is this track?",
  and the station is also the part that is always known: plenty of streams
  never send a title at all.
* QUILL Cast -- the episode, then the show.
* Quill Media Player -- the book or file, then the chapter.

### It says nothing out loud

The screen reader reads the flyout when it opens, and Windows' own surfaces
answer from this card. Announcing the same words again is the over-announcing
GATE-13 exists to stop, so nothing in this module speaks; it only makes the
machine able to answer.
"""

from __future__ import annotations

from typing import Any

from quill.ui.audio.now_playing import clear_now_playing, set_playback_status, update_now_playing

__all__ = [
    "clear_card",
    "refresh_cast_card",
    "refresh_player_card",
    "refresh_radio_card",
    "set_card_status",
]


def refresh_radio_card(host: Any) -> bool:
    """Quill Radio: the station on the headline, the song under it."""
    controller = getattr(host, "_radio_controller", None)
    if controller is None:
        return False
    station = getattr(getattr(controller, "state", None), "station", None)
    if station is None:
        return False
    song = ""
    ask = getattr(host, "_radio_now_playing_text", None)
    if callable(ask):
        try:
            song = str(ask() or "")
        except Exception:  # noqa: BLE001 - no song is a card with just a station
            song = ""
    return update_now_playing(
        controller.current_engine(),
        app_name="Quill Radio",
        title=str(getattr(station, "name", "") or "Quill Radio"),
        artist=song,
    )


def refresh_cast_card(host: Any, state: Any = None) -> bool:
    """QUILL Cast: the episode on the headline, the show under it.

    Takes the whole playback state when it has one, so the card is taken down
    on a stop and marked paused on a pause rather than going on claiming to
    play. A card that lies about that is the small thing that makes people stop
    trusting the surface.
    """
    controller = getattr(host, "_podcast_controller", None)
    if controller is None:
        return False
    if state is None:
        state = getattr(controller, "state", None)
    engine = controller.output_engine()
    title = str(getattr(state, "title", "") or "")
    status = getattr(getattr(state, "state", None), "name", "")
    if status == "STOPPED" or not title:
        return clear_now_playing(engine)
    show = ""
    library = getattr(host, "_podcast_library", None)
    show_id = getattr(state, "show_id", None)
    if library is not None and show_id:
        try:
            found = library.find_show(show_id)
            show = str(getattr(found, "title", "") or "")
        except Exception:  # noqa: BLE001 - a card without the show still helps
            show = ""
    shown = update_now_playing(
        engine,
        app_name="QUILL Cast",
        title=title,
        artist=show,
    )
    set_playback_status(engine, "paused" if status == "PAUSED" else "playing")
    return shown


def refresh_player_card(app: Any, *, title: str, chapter: str = "") -> bool:
    """Quill Media Player: the book or file, then the chapter."""
    player = getattr(app, "_player", None)
    if player is None or not str(title).strip():
        return False
    return update_now_playing(
        player.output_engine(),
        app_name="Quill Media Player",
        title=str(title),
        artist=str(chapter),
    )


def set_card_status(engine: Any, status: str) -> bool:
    """Keep the card honest about playing / paused / stopped.

    Without it the card goes on saying "playing" after a pause, which is the
    small kind of lie that makes people stop trusting a surface.
    """
    return set_playback_status(engine, status)


def clear_card(engine: Any) -> bool:
    """Take the card down: nothing is playing any more."""
    return clear_now_playing(engine)
