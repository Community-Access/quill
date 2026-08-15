"""Song History: recording what a station played, and the window that shows it.

The logic behind the ``radio.song_history`` command lives here rather than in
``main_frame_radio``, for the same reason ``quick_play`` and
``now_playing_commands`` do: that mixin is under a GATE-11 size budget and new
feature bodies belong in their own module.

Every function takes the *host* -- the ``MainFrame``/standalone shell that mixes
in ``RadioMixin`` -- and uses only the small surface it genuinely needs
(``_radio_controller``, ``_radio_history``, ``_announce``, ``_task_manager``,
``_safe_mode``, and the modal/clipboard helpers), so it stays testable and does
not care which of the two hosts it is talking to.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from quill.core.paths import app_data_dir
from quill.core.radio.song_history import (
    SongHistory,
    SongPlay,
    build_song_background_prompt,
    load_song_history,
    save_song_history,
)

#: Named into the ``quill.ui.radio`` subtree so the Preferences "verbose radio
#: logging" toggle (radio_logging.RADIO_LOGGER_NAMES) raises it with the rest of
#: the radio code. A song-log write that quietly failed is exactly the kind of
#: thing that toggle exists to leave a trail of.
_log = logging.getLogger(__name__)


def song_history(host: Any) -> SongHistory:
    """The host's lazily-loaded song log."""
    history = getattr(host, "_radio_song_log", None)
    if history is None:
        history = load_song_history(app_data_dir())
        host._radio_song_log = history
    return history


def save(host: Any) -> None:
    save_song_history(app_data_dir(), song_history(host))


def _current_station(host: Any) -> Any:
    controller = getattr(host, "_radio_controller", None)
    return controller.state.station if controller is not None else None


def record_song(host: Any, title: str) -> None:
    """Log a track-title change against the station that is playing.

    Never raises, and that has to include reading the host's own state: this
    runs from ``_radio_apply_track_title``, immediately before the What's
    Playing announcement, so anything thrown here would silence the very
    announcement the listener is waiting for. Both flags are read through
    ``getattr`` for the same reason -- a host that predates the preference (or a
    lightweight test double standing in for one) must degrade to "log it", never
    to a crash on the announcement path.
    """
    try:
        history_settings = getattr(host, "_radio_history", None)
        if not getattr(history_settings, "song_history_enabled", True):
            return
        if getattr(host, "_safe_mode", False):
            return
        station = _current_station(host)
        if station is None:
            return
        history = song_history(host)
        key = station.station_uuid or station.stream_url
        if history.record(key, station.name or "", title) is not None:
            save(host)
    except Exception:  # noqa: BLE001 - the log is a convenience, never a risk
        _log.debug("Could not record song history", exc_info=True)


def send_to_clip_library(host: Any, text: str, station_name: str) -> bool:
    """Keep one logged song in the Clip Library. True when it was added."""
    try:
        from quill.core.clip_library import ClipLibrary
        from quill.core.fragment import Fragment

        library = ClipLibrary(app_data_dir())
        return library.remember(
            Fragment(
                markup=text,
                title=text,
                source=f"Quill Radio: {station_name}" if station_name else "Quill Radio",
                kind="text",
            )
        )
    except Exception:  # noqa: BLE001 - reported to the caller as "not kept"
        _log.debug("Could not send song to the Clip Library", exc_info=True)
        return False


def request_background(
    host: Any,
    song: SongPlay,
    station_name: str,
    on_done: Callable[[str, str], None],
) -> None:
    """Ask the configured AI provider for background on *song*, off-thread.

    ``on_done(text, error)`` is always called on the UI thread -- exactly one of
    the two is non-empty -- so the dialog can never be left waiting.
    Provider-neutral: whatever the listener configured (a cloud model or a local
    Ollama one) answers. Never available in Safe Mode.
    """
    if host._safe_mode:
        on_done("", "AI background is unavailable in Safe Mode.")
        return
    prompt = build_song_background_prompt(song, station_name)

    def _ask(**_kwargs: object) -> str:
        from quill.core.ai.provider_backend import ProviderChatBackend

        backend = ProviderChatBackend()
        available, reason = backend.is_available()
        if not available:
            raise RuntimeError(reason or "No AI provider is set up yet.")
        return backend.respond(prompt)

    def _ok(_op: str, text: object) -> None:
        host._wx.CallAfter(on_done, str(text or "").strip(), "")

    def _fail(*args: object) -> None:
        detail = str(args[-1]) if args else ""
        host._wx.CallAfter(on_done, "", detail or "The AI provider did not answer.")

    host._task_manager.submit("radio-song-background", _ask, on_success=_ok, on_failure=_fail)


def open_song_history(host: Any) -> None:
    """Open the Song History window for the playing (or last) station."""
    from quill.ui.radio import song_facts
    from quill.ui.radio.song_history_dialog import SongHistoryDialog

    history = song_history(host)
    if not history.known_stations():
        host._announce(
            "No songs logged yet. Play a station that shares track titles "
            "and they will be listed here."
        )
        return
    station = _current_station(host)
    current_key = ""
    if station is not None:
        current_key = station.station_uuid or station.stream_url
    dialog = SongHistoryDialog(
        host.frame,
        history=history,
        current_station_key=current_key,
        show_modal_dialog=host._show_modal_dialog,
        copy_to_clipboard=host._copy_to_clipboard,
        announce=host._announce,
        send_to_clip_library=lambda text, name: send_to_clip_library(host, text, name),
        request_background=lambda song, name, done: request_background(host, song, name, done),
        # Which release, what year, how long: MusicBrainz, keyless, opt-in,
        # off the UI thread. See quill/ui/radio/song_facts.py.
        request_facts=lambda song, show: song_facts.request(host, song, show),
        on_changed=lambda: save(host),
    )
    dialog.show()
