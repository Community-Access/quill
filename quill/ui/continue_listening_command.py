"""Opening Continue Listening, and doing what a row says.

Plain functions taking the host frame (QUILL's ``MainFrame``, Quill Cast's
frame, Quill Radio's frame) so one window serves all three and each contributes
only the providers it actually has.

**What a host has decides what it gathers.** Cast has a podcast library and no
radio player; Quill Radio is the reverse; QUILL has both. Rather than each app
carrying its own copy of the list, the sources are discovered from the host's
own attributes -- so an app that gains a provider gains it here with no change,
and one that never had it never shows rows it cannot honour.

**Resuming goes through the app's ordinary path**, never a second one: a podcast
resumes through the same controller and the same ``play_episode`` the Play Queue
uses, so speed, enhancements, chapter marks and position saving all behave
exactly as they do everywhere else.
"""

from __future__ import annotations

from typing import Any

from quill.core.media.continue_listening import (
    Unfinished,
    from_podcast_library,
    from_position_store,
    from_resume_store,
    gather,
)


def _podcast_library(host: Any) -> Any:
    return getattr(host, "_podcast_library", None) or getattr(host, "_library", None)


def _resume_store(host: Any) -> Any:
    """Quill Radio's resume store, if this app has one.

    Constructed here rather than reached for on the host: the store is a thin
    handle over one JSON file, and requiring every host to hold one would mean
    an app gains the feature only after somebody remembers to add an attribute.
    """
    if getattr(host, "_radio_controller", None) is None and not hasattr(host, "_radio_history"):
        return None
    from quill.core.radio.resume import ResumeStore

    return ResumeStore()


def sources(host: Any) -> list:
    """Every gatherer this host can honestly offer."""
    found: list = []
    library = _podcast_library(host)
    if library is not None:
        found.append(lambda: from_podcast_library(library))
    store = _resume_store(host)
    if store is not None:
        found.append(lambda: from_resume_store(store))
    # Local files: a downloaded book, an imported recording, anything played
    # from disk. Offered by every host, because a file is a file wherever it
    # was opened from.
    from quill.core.media.positions import PositionStore
    from quill.core.paths import app_data_dir

    data_dir = app_data_dir()
    found.append(lambda: from_position_store(PositionStore(data_dir), data_dir))
    return found


def can_resume(host: Any, row: Unfinished) -> bool:
    """Whether *this* app can play that row, rather than whether any app can."""
    if row.provider == "podcast":
        return _podcast_library(host) is not None and getattr(host, "_podcast_controller", None)
    if row.provider == "radio":
        return getattr(host, "_radio_controller", None) is not None
    if row.provider == "file":
        # Any host with a radio controller can play a file: a downloaded
        # chapter is an ordinary station whose address happens to be a path.
        return getattr(host, "_radio_controller", None) is not None
    return False


def resume(host: Any, row: Unfinished) -> bool:
    """Start the row where it was left, through the app's ordinary path."""
    if row.provider == "podcast":
        return _resume_podcast(host, row)
    if row.provider in ("radio", "file"):
        return _resume_recording(host, row)
    return False


def _resume_podcast(host: Any, row: Unfinished) -> bool:
    library = _podcast_library(host)
    controller = getattr(host, "_podcast_controller", None)
    if library is None or controller is None or not isinstance(row.key, tuple):
        return False
    show_id, guid = row.key
    show = library.find_show(str(show_id))
    episode = show.find_episode(str(guid)) if show is not None else None
    if show is None or episode is None:
        return False
    from quill.ui.podcasts.show_actions import start_episode_playback

    return bool(
        start_episode_playback(controller, library, show, episode, resume_ms=episode.position_ms)
    )


def _resume_recording(host: Any, row: Unfinished) -> bool:
    """Play a streamed recording again, from where it stopped.

    Handed to the radio controller as an ordinary station: the resume position
    is applied by ``resume_playback`` on load, exactly as it is when the same
    recording is chosen from Browse, so there is one place that decides how a
    recording resumes.
    """
    controller = getattr(host, "_radio_controller", None)
    url = str(row.key or "")
    if controller is None or not url:
        return False
    from quill.core.radio.models import RadioStation

    station = RadioStation(name=row.title or url, stream_url=url)
    try:
        controller.play_station(station)
    except Exception:  # noqa: BLE001 - reported by the caller, never raised at a listener
        return False
    return True


def forget(host: Any, row: Unfinished) -> bool:
    """Drop a saved place, so the row stops coming back."""
    if row.provider == "podcast":
        library = _podcast_library(host)
        if library is None or not isinstance(row.key, tuple):
            return False
        show_id, guid = row.key
        show = library.find_show(str(show_id))
        episode = show.find_episode(str(guid)) if show is not None else None
        if episode is None:
            return False
        # The place is forgotten; the episode is untouched and stays unplayed,
        # because "I am not going back to this" and "I finished it" are
        # different statements and only one of them is being made.
        episode.position_ms = 0
        save = getattr(host, "_save_podcast_library", None) or getattr(
            host, "_on_library_changed", None
        )
        if callable(save):
            save()
        return True
    if row.provider == "radio":
        store = _resume_store(host)
        if store is None:
            return False
        store.forget(str(row.key or ""))
        return True
    if row.provider == "file":
        from pathlib import Path

        from quill.core.media.positions import PositionStore
        from quill.core.paths import app_data_dir

        PositionStore(app_data_dir()).forget(Path(str(row.key)))
        return True
    return False


def open_continue_listening(host: Any) -> None:
    """The command: gather, say what there is, then show it."""
    from quill.core.media.continue_listening import summarise
    from quill.ui.continue_listening_dialog import ContinueListeningDialog

    rows = gather(sources(host))
    announce = getattr(host, "_announce", None)
    if callable(announce):
        announce(summarise(rows))
    ContinueListeningDialog(
        getattr(host, "frame", None) or getattr(host, "dialog", None) or host,
        rows=rows,
        resume=lambda row: resume(host, row),
        forget=lambda row: forget(host, row),
        can_resume=lambda row: bool(can_resume(host, row)),
        announce=announce if callable(announce) else None,
        show_modal_dialog=getattr(host, "_show_modal_dialog", None),
    ).show()
