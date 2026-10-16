"""Add Custom Station: the dialog, the duplicate check, the tree refresh.

Extracted from ``main_frame_radio.py`` under GATE-11 when duplicate detection
(11.6) pushed that module past its ceiling -- and the duplicate check is the
reason this is worth its own file rather than four lines in a mixin. The
store's ``add`` used to answer ``None`` whether or not it had added anything,
so this path announced "Added ... to Favorites" over a station that was
already there, which is precisely the thing a listener who cannot see the
list has no other way to catch.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.radio.models import RadioStation
from quill.core.sound_events import SoundEvent
from quill.ui.radio.add_station_dialog import AddStationDialog


def page_resolver(host: Any) -> Callable[[str, Callable[[Any, Any], None]], None] | None:
    """The dialog's way to look behind a pasted web page (#36), or None.

    The Find Streams scan, run on the host's task manager, answering on the UI
    thread. None in Safe Mode (every network service is off) and for a host
    without a task manager, which leaves the dialog network-free as before.
    """
    task_manager = getattr(host, "_task_manager", None)
    if getattr(host, "_safe_mode", False) or task_manager is None:
        return None

    def resolve(url: str, done: Callable[[Any, Any], None]) -> None:
        from quill.core.radio.link_finder import scan_page_for_streams

        def work(**_kwargs: Any) -> Any:
            return scan_page_for_streams(url)

        # The task manager delivers both callbacks on the UI thread already.
        task_manager.submit(
            "radio-add-station-resolve",
            work,
            on_success=lambda _op, result: done(result, None),
            on_failure=lambda _op, error: done(None, error),
        )

    return resolve


def open_add_custom(host: Any, prefill: RadioStation | None) -> None:
    dlg = AddStationDialog(
        host.frame,
        controller=host._radio_controller,
        prefill=prefill,
        announce_cb=host._announce,
        youtube_consent_cb=host._radio_youtube_consent,
        resolve_page_cb=page_resolver(host),
    )
    station = dlg.show()
    if station is None:
        return
    from quill.core import duplicate_add

    if not host._radio_favorites.add(station, custom=True):
        # 11.6: the store used to answer None either way, so this said
        # "Added ... to Favorites" over a station that was already there.
        host._announce(duplicate_add.already_have("station", station.name))
        return
    host._save_radio_favorites()
    # Refresh the favorites tree and the favorite toggle so the just-added
    # custom station appears immediately, instead of only after a restart
    # (#1205). These live on the standalone RadioAppFrame; embedded QUILL
    # has no favorites tree, so guard for their absence.
    reload_tree = getattr(host, "_reload_favorites_tree", None)
    if callable(reload_tree):
        reload_tree()
    refresh_toggle = getattr(host, "_refresh_favorite_toggle", None)
    if callable(refresh_toggle):
        refresh_toggle()
    host._announce(f"Added {station.name} to Favorites.", sound=SoundEvent.RADIO_FAVORITE_ADDED)
