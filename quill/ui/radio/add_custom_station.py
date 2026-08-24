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

from typing import Any

from quill.core.radio.models import RadioStation
from quill.core.sound_events import SoundEvent
from quill.ui.radio.add_station_dialog import AddStationDialog


def open_add_custom(host: Any, prefill: RadioStation | None) -> None:
    dlg = AddStationDialog(
        host.frame,
        controller=host._radio_controller,
        prefill=prefill,
        announce_cb=host._announce,
        youtube_consent_cb=host._radio_youtube_consent,
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
