"""Small spoken answers about what is playing (qc.md section 18, items 3 and 4).

* :func:`time_left` -- Ctrl+Shift+T: "12:04 of 31:50, 19 minutes left", with
  the time it really takes at the speed in force and the sleep timer.
* :func:`up_next_due` / :func:`up_next_sentence` -- "Next: Episode 412 from
  Accidental Tech Podcast", said once, about ten seconds before the end.
* :func:`play_this_next` -- Shift+Space: an episode goes straight after the
  one that is playing, not ahead of it.

wx-free, strict-typed.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "UP_NEXT_LEAD_MS",
    "clock",
    "play_this_next",
    "time_left",
    "up_next_due",
    "up_next_sentence",
]

#: How long before the end "up next" is said.
UP_NEXT_LEAD_MS = 10_000


def clock(ms: int) -> str:
    """12:04, or 1:02:09 past an hour."""
    seconds = max(0, int(ms) // 1000)
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def _minutes(seconds: float) -> str:
    whole = round(seconds / 60)
    if seconds < 60 or whole < 1:
        return "under a minute"
    if whole >= 60:
        hours, minutes = divmod(whole, 60)
        hour_words = f"{hours} hour{'s' if hours != 1 else ''}"
        return hour_words if not minutes else f"{hour_words} {minutes} minutes"
    return f"{whole} minute{'s' if whole != 1 else ''}"


def time_left(
    position_ms: int,
    length_ms: int,
    *,
    speed: float = 1.0,
    sleep_seconds: int = 0,
    sleep_at_end: bool = False,
) -> str:
    """The sentence Ctrl+Shift+T says. *length_ms* 0 means the length is unknown."""
    if length_ms <= 0:
        sentence = f"{clock(position_ms)} in; the length is not known yet"
    else:
        remaining_ms = max(0, length_ms - position_ms)
        sentence = (
            f"{clock(position_ms)} of {clock(length_ms)}, {_minutes(remaining_ms / 1000)} left"
        )
        if speed and abs(speed - 1.0) > 1e-6 and remaining_ms >= 60_000:
            real = remaining_ms / 1000 / speed
            sentence += f", {_minutes(real)} at {speed:g} times"
    if sleep_at_end:
        sentence += "; sleep at the end of this episode"
    elif sleep_seconds > 0:
        sentence += f"; sleep in {_minutes(sleep_seconds)}"
    return sentence + "."


def up_next_due(position_ms: int, length_ms: int, *, speed: float = 1.0) -> bool:
    """Whether the end is close enough, in real time, to say what comes next."""
    if length_ms <= 0 or position_ms <= 0:
        return False
    remaining_real = (length_ms - position_ms) / max(speed or 1.0, 0.1)
    return 0 < remaining_real <= UP_NEXT_LEAD_MS


def up_next_sentence(show: Any, episode: Any, *, same_show: bool) -> str:
    title = str(getattr(episode, "title", "") or "")
    if same_show or not show:
        return f"Next: {title}."
    return f"Next: {title} from {getattr(show, 'title', '')}."


def play_this_next(
    library: Any,
    show_id: str,
    episode_guid: str,
    *,
    playing: tuple[str, str] | None = None,
) -> int:
    """Put an episode straight after the playing one; return its queue index.

    The playing episode stays in the queue while it plays (ear.md R4), so the
    front of the queue is *behind* it; "next" is the slot after it. With
    nothing playing, or the playing episode not queued, next is the front.
    An episode already queued is moved, keeping its added time.
    """
    from quill.core.podcasts.models import QueueItem, now_iso

    queue: list[Any] = library.queue
    wanted = (show_id, episode_guid)
    existing = next(
        (i for i, item in enumerate(queue) if (item.show_id, item.episode_guid) == wanted), -1
    )
    item = (
        queue.pop(existing)
        if existing != -1
        else QueueItem(show_id=show_id, episode_guid=episode_guid, added_at=now_iso())
    )
    at = 0
    if playing is not None:
        for index, queued in enumerate(queue):
            if (queued.show_id, queued.episode_guid) == playing:
                at = index + 1
                break
    queue.insert(at, item)
    return at
