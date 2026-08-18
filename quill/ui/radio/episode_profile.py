"""What the shared podcast library knows, applied to Radio's player.

Extracted-by-birth rather than grown inside ``player_controller`` (that module
is at its GATE-11 ceiling), in the same plain-functions-taking-``host`` shape
as :mod:`quill.ui.radio.resume_playback` and friends.

Three pulls from Quill Cast, all read-only against the shared library so a
Radio write can never clobber Cast's open store:

* **The show's playback speed.** Cast stores a speed per show; when Radio
  plays that show's episodes it is applied -- but only while the session rate
  is untouched (1.0), so Play Faster/Slower always wins, exactly like the
  controller's own silent speed re-apply after a load. Radio grows no
  settings UI: the setting simply follows the show.
* **Podcasting 2.0 chapters.** The feed's chapters file is fetched in the
  background (the play token guards against a stale fetch) and served through
  the same ``chapters()`` surface YouTube chapters use, so chapter
  next/previous and the chapter announcements work on podcast episodes with
  no new UI at all.
* Resume positions ride :mod:`resume_playback` (see
  ``saved_position_ms``), which now also consults the library -- so twenty
  minutes into an episode in Cast, Enter on the same row here continues.
"""

from __future__ import annotations

import threading
from typing import Any


def apply_profile(host: Any) -> None:
    """Fold the library's knowledge into the just-loaded playback.

    Called right after the controller declares the source bounded. A row that
    is not a podcast episode (or is not followed) costs one source-string
    check and nothing else.
    """
    state = getattr(host, "_state", None)
    station = getattr(state, "station", None)
    host._episode_chapters = []
    from quill.core.podcasts.radio_listens import PODCAST_EPISODE_SOURCES

    if station is None or str(getattr(station, "source", "")) not in PODCAST_EPISODE_SOURCES:
        return
    from quill.core.paths import app_data_dir
    from quill.core.podcasts.radio_listens import episode_playback_profile

    profile = episode_playback_profile(
        app_data_dir(),
        feed_url=str(getattr(station, "homepage", "") or ""),
        audio_url=str(getattr(station, "stream_url", "") or ""),
    )
    # The show's saved speed, unless the listener already chose a session
    # speed -- Play Faster/Slower always wins, and re-applying a chosen state
    # silently is this controller's own precedent (_declare_source_shape).
    if profile.speed != 1.0 and float(getattr(host, "_playback_rate", 1.0)) == 1.0:
        host.set_speed(profile.speed)
    if profile.chapters_url:
        _fetch_chapters_async(host, profile.chapters_url, profile.chapters_auth_header)


def _fetch_chapters_async(host: Any, url: str, auth_header: str) -> None:
    """Fetch the chapters file off-thread; discard the result if playback moved on."""
    token = getattr(host, "_play_token", 0)

    def _work() -> None:
        try:
            from quill.core.podcasts.chapters import fetch_and_parse_chapters

            chapters = fetch_and_parse_chapters(url, auth_header=auth_header)
        except Exception:  # noqa: BLE001 - chapters are a bonus, never a failure
            return
        if getattr(host, "_play_token", 0) == token and chapters:
            host._episode_chapters = chapters

    # The playback controller deliberately carries no TaskManager (it is
    # constructed before the app's manager exists and outlives dialogs that
    # have one). This is a single bounded HTTPS GET on a daemon thread,
    # token-guarded against stale application, catching everything, and it
    # never touches a widget -- the result lands in a plain list attribute.
    thread = threading.Thread(  # GATE-40-OK: controller has no TaskManager
        target=_work, name="radio-episode-chapters", daemon=True
    )
    thread.start()


def chapters_for(host: Any) -> list[Any]:
    """The published chapters of what is playing, or an empty list.

    A resolved YouTube video's own markers first (captured during the resolve
    at no extra cost); otherwise the podcast episode's Podcasting 2.0
    chapters, fetched by :func:`apply_profile`. Both shapes expose
    ``start_ms``/``title``, so the bounded-playback commands cannot tell them
    apart -- which is the point.
    """
    if not host.is_seekable():
        return []
    stream = getattr(host, "_youtube_stream", None)
    if stream is not None:
        return list(getattr(stream, "chapters", ()) or ())
    return list(getattr(host, "_episode_chapters", ()) or ())
