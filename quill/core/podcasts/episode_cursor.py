"""Where you were in each podcast's episode list, by who the episode is.

Item 43 of the 2026-10-16 checklist ("feed-list position"). Opening a podcast
used to land on its first row every time, so a listener working down a long
back catalogue had to find their place again by ear on every visit -- and on
every refresh, sort change or filter change that rebuilt the list. This keeps,
for each feed, **which episode** was selected:

* **Stable identity, never the row number or the playback time.** The feed is
  keyed by its feed URL (lower-cased, without a trailing slash), or by the
  show's id for a local show with no feed; the episode by its GUID, with its
  audio URL, published date and title kept beside it as fallbacks. A row index
  means nothing after a new episode arrives at the top or the sort flips.
* **A sensible neighbour when the episode has gone.** Feeds drop old episodes,
  and a filter can hide one. Then the cursor lands on the remaining episode
  published closest to the one that disappeared (the newer of two equally
  close), so the listener resumes in the same stretch of the catalogue rather
  than at the top. With no dates at all it is the first row.
* **Kept across restarts.** One small JSON file in the app's data folder,
  written atomically; a missing or damaged file is an empty memory, never an
  error.

wx-free and strict-typed. The two surfaces that use it are QUILL's Podcast
Manager (:mod:`quill.ui.podcasts.manager_dialog`) and QUILL Cast's one window
(:mod:`quill.ui.podcasts.places_host`).
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

__all__ = ["CURSOR_FILE", "EpisodeCursor", "EpisodeMark", "feed_key", "neighbour_index"]

CURSOR_FILE = "podcast_episode_cursor.json"

#: Enough feeds for any real library; the oldest-touched are dropped past it.
_MAX_FEEDS = 2000


def feed_key(show: Any) -> str:
    """A feed's stable identity: its URL, or ``id:<show id>`` for a local show."""
    url = str(getattr(show, "feed_url", "") or "").strip().rstrip("/").lower()
    return url if url else f"id:{getattr(show, 'id', '')}"


@dataclass(frozen=True, slots=True)
class EpisodeMark:
    """Who the selected episode was, in every way it can be recognised again."""

    guid: str
    audio_url: str = ""
    published: str = ""
    title: str = ""

    @classmethod
    def of(cls, episode: Any) -> EpisodeMark:
        return cls(
            guid=str(getattr(episode, "guid", "") or ""),
            audio_url=str(getattr(episode, "audio_url", "") or ""),
            published=str(getattr(episode, "published", "") or ""),
            title=str(getattr(episode, "title", "") or ""),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "guid": self.guid,
            "audio_url": self.audio_url,
            "published": self.published,
            "title": self.title,
        }

    @classmethod
    def from_dict(cls, data: object) -> EpisodeMark | None:
        if not isinstance(data, dict):
            return None
        mark = cls(
            guid=str(data.get("guid", "") or ""),
            audio_url=str(data.get("audio_url", "") or ""),
            published=str(data.get("published", "") or ""),
            title=str(data.get("title", "") or ""),
        )
        return mark if (mark.guid or mark.audio_url) else None


def _timestamp(published: str) -> float | None:
    from quill.core.podcasts.sorting import _parse_published

    if not published:
        return None
    value = _parse_published(published)
    return value if value else None


def neighbour_index(mark: EpisodeMark, episodes: Sequence[Any]) -> int:
    """The row to land on for *mark* in *episodes* (as currently sorted/filtered).

    The same episode when it is there (by GUID, then by audio URL); otherwise
    the one published closest to it, the newer of two equally close; otherwise
    the first row. ``0`` for an empty list.
    """
    for index, episode in enumerate(episodes):
        if mark.guid and str(getattr(episode, "guid", "")) == mark.guid:
            return index
    for index, episode in enumerate(episodes):
        if mark.audio_url and str(getattr(episode, "audio_url", "")) == mark.audio_url:
            return index
    target = _timestamp(mark.published)
    if target is None:
        return 0
    best: tuple[float, float, int] | None = None
    for index, episode in enumerate(episodes):
        when = _timestamp(str(getattr(episode, "published", "") or ""))
        if when is None:
            continue
        candidate = (abs(when - target), -when, index)
        if best is None or candidate < best:
            best = candidate
    return best[2] if best is not None else 0


@dataclass(slots=True)
class EpisodeCursor:
    """Per-feed selected episode, persisted in one JSON file."""

    path: Path | None = None
    marks: dict[str, EpisodeMark] = field(default_factory=dict)

    @classmethod
    def load(cls, data_dir: Path) -> EpisodeCursor:
        path = Path(data_dir) / CURSOR_FILE
        cursor = cls(path=path)
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return cursor
        feeds = raw.get("feeds") if isinstance(raw, dict) else None
        if isinstance(feeds, dict):
            for key, value in feeds.items():
                mark = EpisodeMark.from_dict(value)
                if mark is not None and str(key):
                    cursor.marks[str(key)] = mark
        return cursor

    def save(self) -> None:
        if self.path is None:
            return
        from quill.core.storage import write_json_atomic

        try:
            write_json_atomic(
                self.path,
                {"version": 1, "feeds": {k: m.to_dict() for k, m in self.marks.items()}},
            )
        except OSError:
            return  # a read-only profile forgets the place; it never breaks the list

    def remember(self, show: Any, episode: Any) -> bool:
        """Record *episode* as *show*'s selected episode; True when it changed."""
        mark = EpisodeMark.of(episode)
        if not (mark.guid or mark.audio_url):
            return False
        key = feed_key(show)
        if self.marks.get(key) == mark:
            return False
        self.marks.pop(key, None)
        self.marks[key] = mark  # most recently touched last
        while len(self.marks) > _MAX_FEEDS:
            self.marks.pop(next(iter(self.marks)))
        return True

    def row_for(self, show: Any, episodes: Sequence[Any]) -> int | None:
        """Where to land in *show*'s list, or ``None`` when nothing is remembered."""
        mark = self.marks.get(feed_key(show))
        if mark is None or not episodes:
            return None
        return neighbour_index(mark, episodes)
