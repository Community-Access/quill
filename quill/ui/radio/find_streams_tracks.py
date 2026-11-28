"""Enter plays the selected tracks in the order shown (wx).

A mixin for :class:`quill.ui.radio.link_finder_dialog.LinkFinderDialog`, kept
apart under GATE-11. A podcast feed, an Internet Archive item or an open
directory lists audio **files**, and a list of files is meant to be played
through. With two or more file rows selected, Enter (and the Test button) starts
the first and queues the rest, in the order the rows are shown, through Radio's
own player: the same queue a Lineup uses, so every transport key works on a
track, a track that ends is followed by the next, and Next
(Ctrl+Shift+Period) moves on at once. With one row, or with live streams
selected, Enter keeps testing the focused row as before.
"""

from __future__ import annotations

from typing import Any

from quill.ui.radio import find_streams_actions as actions

LIST_NAME = "Found tracks"


class TracksMixin:
    """Play several found files, in order."""

    def _play_selected_tracks(self) -> bool:
        """True when several selected rows were files and are now playing."""
        rows = self._list.targets()
        if len(rows) < 2 or any(row.check != "file" for row in rows):
            return False
        return self._play_tracks(rows)

    def _play_tracks(self, rows: list[Any]) -> bool:
        from quill.core.lineups.refs import KIND_RECORDING, ItemRef
        from quill.ui.radio import lineups_playback as lp
        from quill.ui.radio.local_media_playback import remember_app

        host = self._host
        controller = lp._controller(host)
        if controller is None:
            self._announce("The player is not ready.")
            return False
        entries = []
        for row in rows:
            station = actions.station_for(row, self._page_title)
            station.is_recording = True  # a finished file: seek, speed and resume apply
            entries.append(lp.Entry(ItemRef(KIND_RECORDING, row.url), station.name, station))
        session = lp.Session("find-streams", LIST_NAME, entries)
        try:
            setattr(controller, lp.SESSION_ATTR, session)
        except AttributeError:
            self._announce("The player cannot play a list of tracks.")
            return False
        remember_app(host)  # a track ending in the background must find the app
        lp._forget_local_media_session(controller)
        if self._testing:
            self._set_testing(False)
        sentence = lp._play_from(host, session, 0, skipped=[])
        first = f"Playing {len(entries)} tracks in the order shown."
        self._say_after(f"{first} {sentence}")
        return True
