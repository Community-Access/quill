"""The three windows that answer "what is this installation doing?".

Station Catalog Status, Audio Health, and the Keyboard Shortcuts Sheet: three
surfaces that report rather than change anything. Split out of
``main_frame_radio`` under GATE-11, and along a real seam -- every method here
opens a read-only status window and nothing else in the mixin does.

They belong together for a reason beyond line count. All three exist because
the app tells you things at the moment *it* decides -- the catalog announces a
refresh, ``media_preflight`` speaks once at launch, the menus name their keys
as you pass them -- and none of that helps somebody who wants to ask. These are
the asked half.
"""

from __future__ import annotations

from quill.core.radio.now_playing_source import NowPlayingFacts


class RadioStatusWindowsMixin:
    """Read-only status surfaces for the Radio frame."""

    def _radio_now_playing_facts(self) -> NowPlayingFacts:
        """The current title, what the station actually sent, and which route
        supplied it -- everything the details window needs to say how much of
        what it is showing is a quotation and how much is a reading.

        ``shown`` and ``raw`` are deliberately both captured here rather than
        stored apart: the rendering is a pure function of the raw text, so
        holding the input beside the output is what lets the window compare them
        instead of trusting a flag set at one of three call sites.
        """
        return NowPlayingFacts(
            shown=self._radio_now_playing_text(),
            raw=self._radio_track_title,
            source=self._radio_track_source,
        )

    def radio_catalog_status(self) -> None:
        """View > Station Catalog Status... See catalog_status_dialog."""
        from quill.ui.radio.catalog_status_dialog import show_catalog_status

        show_catalog_status(self)

    def radio_keyboard_cheat_sheet(self) -> None:
        """Help > Keyboard Shortcuts Sheet... See cheat_sheet_dialog.

        Built by walking this window's own menu bar, so it lists the keys the
        listener actually has -- rebindings included -- and cannot drift from
        the menus the way a hand-kept list in the guide always eventually does.
        """
        from quill.ui.radio.cheat_sheet_dialog import show_cheat_sheet

        show_cheat_sheet(self)

    def radio_audio_health(self) -> None:
        """View > Audio Health... See audio_health_dialog.

        The asked half of what ``media_preflight`` tells you once at launch:
        which engine is playing, whether mpv and FFmpeg are here, where audio is
        going, what the enhancements are doing, and whether a recording started
        now could actually be written.
        """
        from quill.ui.radio.audio_health_dialog import show_audio_health

        show_audio_health(self)
