"""QUILL Cast's Now Playing window: open it, and switch to it when asked (qc.md 5).

The window itself is :mod:`quill.ui.podcasts.now_playing_window`; this mixin
is the frame's side of it: the command, the Episode menu row's handler, the
status bar's Play cell row, and the Preferences switch **Switch to Now Playing
when playback starts** (off by default -- Jeff, 2026-09-30 -- because a window
that steals focus every time a podcast starts is a window somebody turns off
and never turns back on).

Made at start-up and hidden rather than destroyed on close, so it is always
window 2 in the Window menu and Ctrl+2 always reaches it.
"""

from __future__ import annotations

from typing import Any


class CastNowPlayingMixin:
    """open_now_playing, and the playback hook that may bring it forward."""

    def _init_now_playing(self) -> None:
        """Make the window once, hidden, so its number in the Window menu is fixed."""
        from quill.ui.podcasts.now_playing_window import NowPlayingWindow, _install_peer

        window = NowPlayingWindow(self)
        self._now_playing_window = window
        _install_peer(self, window)
        self.commands.try_register(  # type: ignore[attr-defined]
            "podcasts.now_playing",
            "Now Playing",
            self.open_now_playing,
            self._binding_for("podcasts.now_playing"),  # type: ignore[attr-defined]
        )

    def open_now_playing(self) -> None:
        """Window > Now Playing, Ctrl+2, the Episode menu, the Play cell."""
        from quill.ui.podcasts.now_playing_window import open_now_playing

        open_now_playing(self)

    def _on_podcast_state_changed(self, state: Any) -> None:
        super()._on_podcast_state_changed(state)  # type: ignore[misc]
        window = getattr(self, "_now_playing_window", None)
        if window is None:
            return
        from quill.ui.podcasts.player_controller import PodcastPlayerState

        if window.frame.IsShown():
            window.refresh()
        elif state.state is PodcastPlayerState.PLAYING and bool(
            getattr(self._podcast_history, "switch_to_now_playing", False)  # type: ignore[attr-defined]
        ):
            key = (state.show_id, state.episode_guid)
            if key != getattr(self, "_now_playing_switched_for", None):
                self._now_playing_switched_for = key
                window.show(focus=True)


__all__ = ["CastNowPlayingMixin"]
