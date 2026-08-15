"""The radio's Spotify commands: connect, browse, and the search-blend client.

Extracted from ``main_frame_radio`` under GATE-11 (extract, never rebaseline),
and a coherent seam: all three answer *how the radio talks to Spotify*, refuse
in Safe Mode with Spotify's own words, and read the same token store. The host
passes itself in, exactly like ``settings_commands`` and ``download_runner``.
"""

from __future__ import annotations

from typing import Any


def connect(host: Any) -> None:
    """Open the accessible Spotify sign-in dialog (Radio)."""
    from quill.core.spotify import auth

    try:
        auth.refuse_in_safe_mode(host._safe_mode)
    except auth.SpotifyAuthError as error:
        host._announce(str(error))
        return
    from quill.ui.spotify.connect_dialog import SpotifyConnectDialog

    dialog = SpotifyConnectDialog(
        host.frame,
        announce=host._announce,
        task_runner=getattr(host, "_task_manager", None),
        safe_mode=host._safe_mode,
    )
    host._show_modal_dialog(dialog, "Connect to Spotify")


def search_client(host: Any) -> object | None:
    """A signed-in Spotify client for blending Spotify into Find Stations.

    ``None`` -- so the source is simply absent -- in Safe Mode, when nobody
    has connected Spotify, or when no Client ID is configured. Called from
    the browser's off-thread search worker, so it touches no wx: it only
    reads the stored token bundle.
    """
    if host._safe_mode:
        return None
    from quill.core.spotify import token_store
    from quill.core.spotify.client import SpotifyClient

    tokens = token_store.load_tokens()
    client_id = token_store.load_client_id()
    if tokens.is_empty or not client_id:
        return None
    return SpotifyClient(tokens, client_id, on_tokens_refreshed=token_store.save_tokens)


def browse(host: Any) -> None:
    """Open the accessible Spotify browse dialog and play the chosen track."""
    from quill.core.spotify import auth, token_store

    try:
        auth.refuse_in_safe_mode(host._safe_mode)
    except auth.SpotifyAuthError as error:
        host._announce(str(error))
        return
    tokens = token_store.load_tokens()
    if tokens.is_empty:
        host._announce("Connect to Spotify first (Spotify: Connect to Spotify).")
        return
    from quill.core.radio.models import RadioStation
    from quill.core.spotify.client import SpotifyClient
    from quill.ui.spotify.browse_dialog import BrowseItem, SpotifyBrowseDialog

    client = SpotifyClient(
        tokens,
        token_store.load_client_id(),
        on_tokens_refreshed=token_store.save_tokens,
    )

    def _play(item: BrowseItem) -> None:
        station = RadioStation(name=item.label, stream_url=item.uri, source="Spotify")
        host._radio_controller.play_station(station)

    dialog = SpotifyBrowseDialog(
        host.frame, client=client, on_play=_play, announce=host._announce, kind="radio"
    )
    host._show_modal_dialog(dialog, "Browse Spotify")
