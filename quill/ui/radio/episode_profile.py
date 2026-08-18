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
  settings UI: the setting simply follows the show. On top of the Cast
  setting, a speed the listener chooses *in Radio* while an episode plays is
  remembered per show (:func:`remember_speed_choice`, a Radio-side store that
  never touches the shared library) and wins over Cast's; auto-apply is gated
  by :func:`_speed_applies_here` so a network stream on the WMP fallback
  engine is never asked to time-stretch.
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
    from quill.core.podcasts.radio_listens import episode_playback_profile, remembered_show_speed

    feed_url = str(getattr(station, "homepage", "") or "")
    profile = episode_playback_profile(
        app_data_dir(),
        feed_url=feed_url,
        audio_url=str(getattr(station, "stream_url", "") or ""),
    )
    # The speed this show should play at: a speed the listener set IN RADIO
    # (remembered per show, Radio-side store) wins over Cast's library
    # setting; either applies only while the session rate is untouched --
    # Play Faster/Slower always wins, matching the controller's own silent
    # speed re-apply precedent.
    speed = remembered_show_speed(app_data_dir(), feed_url) or profile.speed
    if (
        speed != 1.0
        and float(getattr(host, "_playback_rate", 1.0)) == 1.0
        and _speed_applies_here(host, station)
    ):
        host.set_playback_rate(speed)
    if profile.chapters_url:
        _fetch_chapters_async(host, profile.chapters_url, profile.chapters_auth_header)


def _speed_applies_here(host: Any, station: Any) -> bool:
    """Whether a saved speed should auto-apply to this playback.

    Always for a downloaded episode (a local file has no network to fall
    behind), and for streamed episodes only on the mpv engine, which
    time-stretches a bounded remote file cleanly. The WMP fallback engine
    honours rates unreliably on network streams, so there the saved speed
    stays saved and Play Faster remains one keypress away -- never a
    stuttering surprise.
    """
    stream_url = str(getattr(station, "stream_url", "") or "")
    if not stream_url.lower().startswith(("http://", "https://")):
        return True  # a downloaded file: speed is purely local arithmetic
    engine = getattr(host, "_engine", None)
    mpv = getattr(host, "_mpv_engine", None)
    return engine is not None and engine is mpv


def remember_speed_choice(host: Any) -> str:
    """Persist a listener's speed change for the playing show, per show.

    Called by the Play Faster/Slower/Normal Speed commands. Returns the
    suffix to append to their announcement -- "" when the playing row is not
    a podcast episode, so ordinary videos and recordings speak exactly as
    before. Setting normal speed forgets the entry: normal is the default,
    not a preference worth storing.
    """
    state = getattr(host, "_state", None)
    station = getattr(state, "station", None)
    from quill.core.podcasts.radio_listens import PODCAST_EPISODE_SOURCES

    if station is None or str(getattr(station, "source", "")) not in PODCAST_EPISODE_SOURCES:
        return ""
    from quill.core.paths import app_data_dir
    from quill.core.podcasts.radio_listens import remember_show_speed

    rate = float(getattr(host, "_playback_rate", 1.0))
    remember_show_speed(app_data_dir(), str(getattr(station, "homepage", "") or ""), rate)
    if rate == 1.0:
        return " This show will play at normal speed."
    return " Remembered for this show."


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
