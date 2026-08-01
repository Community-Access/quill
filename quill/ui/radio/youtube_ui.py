"""Host-side wiring for YouTube stations (#1268): consent, and the resolver.

Two host concerns that do not belong in the playback controller or in a dialog:

* **Consent.** Playing or recording a YouTube link reaches YouTube through
  yt-dlp, which QUILL installs on demand and never bundles. The listener is
  asked once -- when a YouTube link is first *added* as a station, not when it
  plays -- and the answer is remembered in ``RadioHistory.youtube_consented``.
  Asking at add time is deliberate: a scheduled recording can fire while nobody
  is at the computer, and that must never be the first time QUILL touches
  YouTube.
* **Resolving.** The controller calls this on a worker thread for every play,
  because YouTube's stream addresses expire within hours and a cached one would
  simply stop working mid-listen.

The frame keeps two thin delegating methods; the policy lives here, next to the
text the listener actually reads.
"""

from __future__ import annotations

from typing import Any

#: The one-time consent + rights notice. Mirrors the converter's URL-import
#: notice (#1255 §4.6): same component, same rights reminder, same "never
#: bundled, installed on demand" posture.
YOUTUBE_CONSENT = (
    "Adding a YouTube link lets Quill Radio play and record it like any other "
    "station. To do that it uses yt-dlp to find the audio stream behind the "
    "page, every time the station plays -- YouTube's own stream addresses "
    "expire after a few hours.\n\n"
    "The first time, QUILL will download and install the yt-dlp component "
    "(about 3 MB, from PyPI).\n\n"
    "Only record content you have the right to record. QUILL sends no account "
    "or credential to YouTube, and this is unavailable in Safe Mode.\n\n"
    "Continue?"
)

YOUTUBE_TITLE = "YouTube station"


def ask_youtube_consent(host: Any) -> bool:
    """Ask once, remember the answer, and report whether YouTube may be used."""
    wx = host._wx
    if bool(getattr(host, "_safe_mode", False)):
        host._show_message_box(
            "YouTube stations are unavailable in Safe Mode.",
            YOUTUBE_TITLE,
            wx.ICON_INFORMATION | wx.OK,
        )
        return False
    history = host._radio_history
    if bool(getattr(history, "youtube_consented", False)):
        return True
    if (
        host._show_message_box(YOUTUBE_CONSENT, YOUTUBE_TITLE, wx.ICON_QUESTION | wx.YES_NO)
        != wx.YES
    ):
        host._announce("YouTube station cancelled.")
        return False
    history.youtube_consented = True
    try:
        from quill.core.paths import app_data_dir
        from quill.core.radio import history as radio_history

        radio_history.save_history(app_data_dir(), history)
    except Exception:  # noqa: BLE001 - a failed save must never block playback
        pass
    return True


def resolve_youtube_for_host(host: Any, page_url: str) -> str:
    """Turn a saved YouTube link into a playable stream URL (worker thread).

    Installs yt-dlp on first use -- consent was already given when the station
    was added. Raises :class:`quill.core.radio.youtube.YouTubeError` with a
    speakable reason, which the controller announces as the play failure.
    """
    from quill.core.radio.youtube import YouTubeError, ensure_and_resolve

    if bool(getattr(host, "_safe_mode", False)):
        raise YouTubeError("YouTube stations are unavailable in Safe Mode.")
    if not bool(getattr(host._radio_history, "youtube_consented", False)):
        raise YouTubeError(
            "This YouTube station needs the one-time yt-dlp consent. "
            "Add it again from Add Custom Station to accept it."
        )
    return ensure_and_resolve(page_url).stream_url
