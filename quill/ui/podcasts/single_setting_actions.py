"""The three per-show settings worth reaching in one keystroke (list.md 5.7).

``Settings for This Podcast...`` opens two dozen controls. These open one, with
focus on it. The three chosen are the ones people change *per show and often*:
how many downloads to keep for a podcast that publishes daily, how long its
episodes wait in the queue, and how fast a particular host talks.

Each writes through ``PodcastLibrary.apply_show_override``, which clones the
show's effective settings before changing the one field -- so setting a speed
here cannot silently reset a retention rule set there. That is the one correct
way to write a per-show override, and the reason these are three small
functions rather than three places that build a ``PodcastSettings``.
"""

from __future__ import annotations

from typing import Any

from quill.core.podcasts import single_settings as ss

__all__ = ["edit_keep_episodes", "edit_queue_age", "edit_playback_speed"]


def _open(host: Any, show: Any, setting: ss.SingleSetting, **kwargs: Any) -> float | None:
    from quill.ui.podcasts.single_setting_dialog import SingleSettingDialog

    return SingleSettingDialog(
        getattr(host, "dialog", None),
        setting,
        subject=str(getattr(show, "title", "") or ""),
        announce_cb=getattr(host, "_announce", None),
        **kwargs,
    ).show()


def _effective(host: Any, show: Any) -> Any:
    """What is actually in force for this show, override or inherited default."""
    return host._library.effective_settings(show)


def edit_keep_episodes(host: Any, show: Any) -> None:
    """How many downloaded episodes of this show to keep.

    Written as ``retention``/``retention_count`` together, because a count on
    its own means nothing while the rule says "keep all" -- a listener who set
    5 and saw nothing deleted would reasonably conclude the setting is broken.
    Zero here is "keep everything", which is what the rule already says.
    """
    setting = ss.setting(ss.KEEP_EPISODES)
    if setting is None:
        return
    current = _effective(host, show)
    shown = current.retention_count if current.retention == "keep_last_n" else 0
    chosen = _open(host, show, setting, value=float(shown), minimum=0, maximum=500)
    if chosen is None:
        return
    count = int(chosen)
    host._library.apply_show_override(
        show,
        retention="keep_last_n" if count > 0 else "keep_all",
        retention_count=max(1, count),
    )
    host._on_library_changed()
    host._announce(ss.describe_keep(count))


def edit_queue_age(host: Any, show: Any) -> None:
    """How long this show's episodes wait in the Play Queue."""
    setting = ss.setting(ss.QUEUE_AGE)
    if setting is None:
        return
    current = _effective(host, show)
    chosen = _open(
        host, show, setting, value=float(current.queue_age_limit_days), minimum=0, maximum=365
    )
    if chosen is None:
        return
    days = int(chosen)
    host._library.apply_show_override(show, queue_age_limit_days=days)
    host._on_library_changed()
    host._announce(ss.describe_queue_age(days))


def edit_playback_speed(host: Any, show: Any) -> None:
    """How fast this show plays, remembered between episodes."""
    from quill.core.podcasts.models_settings import SPEED_MAX, SPEED_MIN, clamp_speed

    setting = ss.setting(ss.PLAYBACK_SPEED)
    if setting is None:
        return
    current = _effective(host, show)
    chosen = _open(
        host,
        show,
        setting,
        value=float(current.speed),
        # The app's own range, not a second opinion about it: a dialog that
        # stopped at 3 would refuse a speed the rest of Cast accepts, and the
        # listener would have to go to the full settings window for it.
        minimum=SPEED_MIN,
        maximum=SPEED_MAX,
        decimals=2,
    )
    if chosen is None:
        return
    speed = clamp_speed(chosen)
    host._library.apply_show_override(show, speed=speed)
    host._on_library_changed()
    host._announce(ss.describe_speed(speed))
