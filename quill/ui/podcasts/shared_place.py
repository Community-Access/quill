"""Writing an episode's place where the other app can read it (11.11).

The write half of cross-app resume. Best effort and quiet: a shared place is
a courtesy, and losing one must never cost somebody their playback. Only
episodes with a feed and an audio address are shareable -- a locally imported
file has no identity the other app could match.

Extracted from ``main_frame_podcasts.py`` under GATE-11.
"""

from __future__ import annotations


def share_place(show: object, episode: object, ms: int, *, finished: bool) -> None:
    """Record this episode's place in the store Quill Radio also writes."""

    feed_url = str(getattr(show, "feed_url", "") or "")
    audio_url = str(getattr(episode, "audio_url", "") or "")
    if not feed_url or not audio_url:
        return
    try:
        from quill.core.paths import app_data_dir
        from quill.core.podcasts.radio_listens import record_listen

        record_listen(
            app_data_dir(),
            feed_url=feed_url,
            audio_url=audio_url,
            title=str(getattr(episode, "title", "") or ""),
            position_ms=max(0, int(ms)),
            finished=finished,
            app="cast",
        )
    except Exception:  # noqa: BLE001 - a shared place is never worth a crash
        return
