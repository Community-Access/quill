"""The Spotify side-path of the podcast player.

A ``spotify:episode:`` URI is DRM audio that neither mpv nor wx.media can open,
so it is played by the Spotify Web Playback engine instead. That engine is a
hidden WebView, it needs an access token, and it has nothing to do with the
enhancement relay, the playback cache, seeking, or anything else the ordinary
stream path does -- which is exactly why it lives here rather than as three
more methods on the controller.

The controller keeps the mpv/wx engine as ``_stream_engine`` for the whole
session and only *points* ``_engine`` at the Spotify engine for the duration of
a Spotify episode, so leaving one costs no reconstruction.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from quill.ui.spotify.web_player import SpotifyWebEngine


class PodcastSpotifyEngineMixin:
    """Lazily builds and selects the Spotify engine for the player."""

    def _ensure_spotify_engine(self) -> SpotifyWebEngine | None:
        """Lazily create the Spotify engine, or None if no token source (not
        signed in to Spotify)."""
        if self._spotify_engine is not None:
            return self._spotify_engine
        if self._spotify_token_provider is None:
            return None
        from quill.ui.spotify.web_player import SpotifyWebEngine

        self._spotify_engine = SpotifyWebEngine(
            self._parent,
            token_provider=self._spotify_token_provider,
            on_error=self._on_error,
        )
        return self._spotify_engine

    def _select_spotify_engine(self) -> SpotifyWebEngine | None:
        """Make the Spotify engine the active engine (stream engine stays alive
        for the next non-Spotify episode)."""
        spotify = self._ensure_spotify_engine()
        if spotify is not None:
            self._engine = spotify
        return spotify

    def _select_stream_engine(self) -> None:
        """Restore the mpv/wx stream engine as the active engine when leaving a
        Spotify episode. Only swaps back *from* the Spotify engine, so any other
        active engine (including a test-injected fake) is left in place."""
        if self._spotify_engine is not None and self._engine is self._spotify_engine:
            self._engine = self._stream_engine
