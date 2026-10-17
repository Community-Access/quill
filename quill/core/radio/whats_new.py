"""What's New: one key that says what changed since you last looked.

Todo P3 "Radio extras" 8. The notification centre already keeps everything
Quill Radio found while you were away -- new podcast episodes, new videos from
followed channels, reminders that went off -- but reading it means opening a
window and arrowing a list. This is the one-sentence version: press the key,
hear the counts and the names, and carry on listening.

"Since you last looked" is the centre's own unread mark, the only record of
what you have and have not been told. Saying the summary marks those entries
read, so the next press says "Nothing new" rather than the same news again;
the entries themselves stay in the centre.

Only Quill Radio's own entries are summarised: a QUILL dictation notice is not
news about your listening.

wx-free, strict-typed.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from quill.core import notification_targets
from quill.core.counted import plural
from quill.core.notifications import Notification

__all__ = ["APP", "NOTHING_NEW", "WhatsNew", "gather", "summary"]

APP = "Quill Radio"
NOTHING_NEW = "Nothing new since you last looked."

#: How many names are read before "and N more": enough to recognise, short
#: enough that the sentence finishes before the listener's attention does.
_NAMES = 3


@dataclass(slots=True)
class WhatsNew:
    """Radio's unread notices, sorted into what they are about."""

    episodes: int = 0
    shows: list[str] = field(default_factory=list)
    videos: int = 0
    channels: list[str] = field(default_factory=list)
    reminders: int = 0
    other: int = 0
    ids: list[str] = field(default_factory=list)

    @property
    def empty(self) -> bool:
        return not self.ids


def _episode_count(title: str) -> int:
    head = title.split(" ", 1)[0]
    return int(head) if head.isdigit() else 1


def gather(entries: Iterable[Notification], *, app: str = APP) -> WhatsNew:
    """Sort *app*'s unread entries into episodes, videos, reminders and the rest."""
    news = WhatsNew()
    for entry in entries:
        if entry.read or entry.app != app:
            continue
        news.ids.append(entry.id)
        kind, _value = notification_targets.parse(entry.target) if entry.target else ("", "")
        if entry.title == "Reminder":
            news.reminders += 1
        elif kind == notification_targets.KIND_SHOW:
            news.episodes += _episode_count(entry.title)
            if entry.body and entry.body not in news.shows:
                news.shows.append(entry.body)
        elif kind == notification_targets.KIND_STREAM:
            news.videos += 1
            if entry.body and entry.body not in news.channels:
                news.channels.append(entry.body)
        else:
            news.other += 1
    return news


def _names(names: list[str]) -> str:
    shown = names[:_NAMES]
    rest = len(names) - len(shown)
    text = ", ".join(shown)
    return f"{text}, and {rest} more" if rest else text


def summary(news: WhatsNew) -> str:
    """The sentence the key says. Every clause carries its number."""
    if news.empty:
        return NOTHING_NEW
    clauses: list[str] = []
    if news.episodes:
        where = f" in {_names(news.shows)}" if news.shows else ""
        clauses.append(f"{plural(news.episodes, 'new episode')}{where}.")
    if news.videos:
        where = f" from {_names(news.channels)}" if news.channels else ""
        clauses.append(f"{plural(news.videos, 'new video')}{where}.")
    if news.reminders:
        clauses.append(f"{plural(news.reminders, 'reminder')} went off.")
    if news.other:
        clauses.append(f"{plural(news.other, 'other notification')}.")
    return "Since you last looked: " + " ".join(clauses)
