"""Where an episode should actually start, once both apps have had their say.

The cross-app resume decision (11.11) applied to one episode: Cast's own
stored position against the shared place :mod:`quill.core.podcasts.radio_listens`
holds, resolved by :mod:`quill.core.podcasts.cross_app_resume`'s rule -- last
write wins, not furthest wins.

Extracted from ``show_actions.py`` under GATE-11: that module is the shared
home of every podcast verb and had reached its cap, and "which of two places
is the later word" is a self-contained question with one answer.
"""

from __future__ import annotations

from quill.core.podcasts.models import PodcastEpisode, PodcastShow


def cross_app_start(show: PodcastShow, episode: PodcastEpisode, local_ms: int) -> tuple[int, str]:
    """Where to start, once Quill Radio's opinion is taken into account (11.11).

    Returns ``(position, sentence)`` -- the sentence is what to say when the
    place came from the *other* app, and "" when it did not. Last write wins,
    not furthest wins: somebody who skipped to the outro and came back has
    decided where they are.
    """
    from quill.core.podcasts import cross_app_resume

    audio_url = str(getattr(episode, "audio_url", "") or "")
    if not audio_url:
        return local_ms, ""
    try:
        from quill.core.paths import app_data_dir
        from quill.core.podcasts.radio_listens import latest_place

        shared = latest_place(app_data_dir(), audio_url)
    except Exception:  # noqa: BLE001 - a shared place is a courtesy, never fatal
        return local_ms, ""
    local = cross_app_resume.Place(
        position_ms=max(0, int(local_ms)),
        updated_at=_stamp_seconds(getattr(episode, "position_updated_at", "")),
        finished=bool(getattr(episode, "played", False)),
        app="cast",
    )
    chosen = cross_app_resume.better_place(local, shared)
    if chosen is None or chosen.finished:
        return local_ms, ""
    if not cross_app_resume.should_seek(local_ms, chosen):
        return local_ms, ""
    return chosen.position_ms, cross_app_resume.describe_resume(chosen, this_app="cast")


def _stamp_seconds(stamp: object) -> float:
    """An ISO-8601 stamp as unix seconds; 0.0 when there is none to read."""
    from datetime import datetime

    text = str(stamp or "").strip()
    if not text:
        return 0.0
    try:
        moment = datetime.fromisoformat(text)
    except ValueError:
        return 0.0
    if moment.tzinfo is None:
        from datetime import UTC

        moment = moment.replace(tzinfo=UTC)
    return moment.timestamp()
