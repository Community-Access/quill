"""Resolve a currently-valid Spotify access token for the player engine.

The Web Playback SDK asks the host for an access token on load and again
whenever it needs to refresh. :class:`SpotifySession` is that host side: it
reads the persisted :class:`~quill.core.spotify.token_store.TokenBundle`,
returns the stored access token while it is still fresh, and transparently
refreshes it (persisting the new one) when it is near or past expiry. wx-free
and strict-typed; the clock and network opener are injectable so the whole
refresh path is unit-testable with no real network and no wall clock.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

from quill.core.spotify import auth, token_store
from quill.core.spotify.token_store import TokenBundle

#: Refresh a little before the true expiry so a token handed to the SDK does
#: not expire mid-request.
_REFRESH_MARGIN_SECONDS = 60.0


class SpotifySession:
    """Hands out a valid Spotify access token, refreshing as needed."""

    def __init__(
        self,
        *,
        opener: auth.Opener | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._opener = opener
        self._clock = clock
        self._lock = threading.Lock()

    def access_token(self) -> str:
        """A currently-valid access token, or ``""`` when not signed in or a
        refresh failed (the caller degrades gracefully -- the SDK simply cannot
        play until the user connects)."""
        with self._lock:
            bundle = token_store.load_tokens()
            if bundle.is_empty:
                return ""
            now = self._clock()
            if bundle.access_token and (bundle.expires_at - now) > _REFRESH_MARGIN_SECONDS:
                return bundle.access_token
            if not bundle.refresh_token:
                return bundle.access_token
            client_id = token_store.load_client_id()
            if not client_id:
                return bundle.access_token
            try:
                response = auth.refresh(bundle.refresh_token, client_id, opener=self._opener)
            except auth.SpotifyAuthError:
                return ""
            refreshed = TokenBundle.from_token_response(response, now=now)
            token_store.save_tokens(refreshed)
            return refreshed.access_token

    def provider(self) -> Callable[[], str]:
        """The bound token callable to hand a player engine as its
        ``spotify_token_provider``."""
        return self.access_token
