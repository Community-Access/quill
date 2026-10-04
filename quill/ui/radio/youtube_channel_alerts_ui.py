"""Running Notify Me About New Videos, and following a notice back to its video.

The check rides Quill Radio's podcast schedule: every time the subscribed-feed
timer fires (and at launch, if feeds are checked at launch), the channels with
the bell on are looked at once, off the UI thread
(:func:`quill.core.radio.youtube_channel_alerts.check_channels`). Each new
upload becomes one entry in Notifications -- "New on <channel>: <title>" --
and, quiet hours allowing, one desktop notice and one sound for the whole
check, the same as new podcast episodes.

Opening one of those notices from Help > Notifications plays the video.
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


def check_in_background(
    task_manager: Any, *, safe_mode: bool, minutes: int, consented: bool
) -> bool:
    """Start one polite check of the ringing channels. True when one started."""
    if safe_mode or task_manager is None or not consented:
        return False
    from quill.core.radio.youtube_channel_alerts import AlertStore

    if not AlertStore().notifying():
        return False  # no bell anywhere: no thread, no request

    def _work(**_kwargs: Any) -> object:
        from quill.core.radio.youtube_channel_alerts import check_channels
        from quill.core.radio.youtube_channels import ChannelStore

        names = {channel.url: channel.display_name for channel in ChannelStore().all()}
        return check_channels(names=names, now=time.time(), every_minutes=minutes)

    def _ok(_op: str, result: object) -> None:
        found, failures = result if isinstance(result, tuple) else ([], [])
        raise_notices(list(found))
        for channel, why in failures:
            _record(f"New videos on {channel}", why)

    def _failed(_op: str, error: BaseException) -> None:
        _record("New videos on YouTube channels", str(error) or error.__class__.__name__)

    task_manager.submit("radio-youtube-channel-check", _work, on_success=_ok, on_failure=_failed)
    return True


def raise_notices(found: list[Any]) -> int:
    """One Notifications entry per new video; one toast and sound per check."""
    if not found:
        return 0
    from quill.core import notification_targets
    from quill.core.notifications import add_notice

    for video in found:
        try:
            add_notice(
                app="Quill Radio",
                title=video.headline,
                body=video.channel,
                target=notification_targets.for_stream(video.url),
            )
        except Exception:  # noqa: BLE001 - the video is still there to find
            logger.debug("Could not record a new-video notice", exc_info=True)
    _notify_loudly(found)
    return len(found)


def _notify_loudly(found: list[Any]) -> None:
    from quill.core.quiet_hours import Kind
    from quill.ui.quiet_hours_ui import held_back

    try:
        if held_back(Kind.NEW_EPISODE):
            return
    except Exception:  # noqa: BLE001 - unknown quiet hours never lose the news
        pass
    if len(found) == 1:
        heading, body = f"New on {found[0].channel}", found[0].title
    else:
        heading = f"{len(found)} new videos"
        body = ", ".join(sorted({video.channel for video in found}))
    try:
        from quill.core.sound_events import SoundEvent
        from quill.ui.companion_cues import post_cue

        post_cue(SoundEvent.CAST_NEW_EPISODES)
    except Exception:  # noqa: BLE001 - a missing clip is not a failure
        pass
    try:
        from quill.ui.toast import show_toast

        show_toast(heading, body)
    except Exception:  # noqa: BLE001 - recorded in Notifications either way
        logger.debug("New-video toast could not be shown", exc_info=True)


def open_stream_notice(host: Any, url: str) -> bool:
    """Enter on a new-video notice: play the video. False when it is not one."""
    from quill.core.radio.youtube_urls import is_youtube_url

    if not is_youtube_url(url):
        return False
    controller = getattr(host, "_radio_controller", None)
    if controller is None:
        return False
    from quill.core.radio.models import RadioStation

    controller.play_station(
        RadioStation(
            name="YouTube video", stream_url=url, homepage=url, source="YouTube", is_recording=True
        )
    )
    return True


def _record(subject: str, reason: str) -> None:
    try:
        from quill.core import problem_log
        from quill.core.paths import app_data_dir

        problem_log.record_problem(app_data_dir(), problem_log.KIND_FEED, subject, reason)
    except Exception:  # noqa: BLE001 - a problem list is never worth a crash
        return


__all__ = ["check_in_background", "open_stream_notice", "raise_notices"]
