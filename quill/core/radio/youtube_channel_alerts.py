"""Notify Me About New Videos, for a channel Quill Radio follows.

YouTube's own bell cannot be rung from outside YouTube without its account API,
which Quill Radio deliberately does not use. So this is Quill's own bell, built
the way the podcast one is: you turn it on per channel from the channel's row,
Quill Radio looks at that channel when it checks your podcasts -- the same
schedule, the same quiet hours, the same Notifications list -- and every new
upload becomes one notice, "New on <channel>: <title>".

Three rules keep it polite:

* **Only channels you asked about, and only their newest few.** One flat
  listing of the channel's uploads per check, :data:`NEWEST` rows long. Nothing
  is resolved and nothing is played.
* **The first look is a baseline, not news.** Turning the bell on for a channel
  with four thousand videos must not announce the five on top as new, so the
  first check only remembers what is there.
* **Off by default for every channel.** Following a channel puts it in the
  tree; asking to be interrupted about it is a separate, explicit choice.

The store is one small JSON file of channel addresses, on/off flags and the ids
of the videos already seen. wx-free, strict-typed; the single request goes
through :func:`quill.core.radio.youtube_requests.run`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from quill.core.paths import app_data_dir
from quill.core.radio.youtube_channels import normalize_channel_url
from quill.core.radio.youtube_requests import Fetch, YouTubeRequestError, plain, run
from quill.core.storage import read_json, write_json_atomic

_FILE_NAME = "radio-youtube-channel-alerts.json"

#: How many of a channel's newest uploads one check reads.
NEWEST = 5

#: How many seen ids are remembered per channel. Comfortably more than one
#: check can return, so a video is never announced twice.
SEEN_LIMIT = 60


@dataclass(frozen=True, slots=True)
class NewVideo:
    """One upload the listener has not been told about yet."""

    channel: str
    title: str
    url: str

    @property
    def headline(self) -> str:
        return f"New on {self.channel}: {self.title}"


def _key(url: str) -> str:
    return normalize_channel_url(url) or url.strip()


class AlertStore:
    """Which followed channels ring, and which videos each has already shown."""

    def __init__(self, data_dir: Path | None = None) -> None:
        self._dir = data_dir

    def _path(self) -> Path:
        return (self._dir or app_data_dir()) / _FILE_NAME

    def _read(self) -> dict[str, dict[str, object]]:
        try:
            raw = read_json(self._path(), {})
        except OSError:
            return {}
        channels = raw.get("channels") if isinstance(raw, dict) else None
        if not isinstance(channels, dict):
            return {}
        return {str(k): v for k, v in channels.items() if isinstance(v, dict)}

    def _write(self, channels: dict[str, dict[str, object]]) -> None:
        try:
            write_json_atomic(self._path(), {"channels": channels, "last_check": self.last_check()})
        except (OSError, TypeError, ValueError):  # pragma: no cover - environmental
            return

    def is_notifying(self, url: str) -> bool:
        return bool(self._read().get(_key(url), {}).get("notify", False))

    def set_notifying(self, url: str, on: bool) -> None:
        """Turn the bell on or off. Turning it on starts a fresh baseline."""
        channels = self._read()
        entry = dict(channels.get(_key(url), {}))
        entry["notify"] = bool(on)
        if on:
            entry.pop("seen", None)  # the next look is a baseline, not news
        channels[_key(url)] = entry
        self._write(channels)

    def notifying(self) -> list[str]:
        """Every channel address with the bell on, in a stable order."""
        return sorted(url for url, entry in self._read().items() if entry.get("notify"))

    def seen(self, url: str) -> list[str] | None:
        """Ids already seen, or ``None`` before the first (baseline) look."""
        value = self._read().get(_key(url), {}).get("seen")
        return [str(item) for item in value] if isinstance(value, list) else None

    def remember(self, url: str, ids: list[str]) -> None:
        channels = self._read()
        entry = dict(channels.get(_key(url), {}))
        previous = entry.get("seen")
        old = [str(i) for i in previous] if isinstance(previous, list) else []
        merged = [*ids, *(i for i in old if i not in ids)][:SEEN_LIMIT]
        entry["seen"] = merged
        channels[_key(url)] = entry
        self._write(channels)

    def last_check(self) -> float:
        try:
            raw = read_json(self._path(), {})
        except OSError:
            return 0.0
        value = raw.get("last_check") if isinstance(raw, dict) else None
        return float(value) if isinstance(value, (int, float)) else 0.0

    def stamp(self, now: float) -> None:
        try:
            raw = read_json(self._path(), {})
        except OSError:
            raw = {}
        data = raw if isinstance(raw, dict) else {}
        data["last_check"] = float(now)
        try:
            write_json_atomic(self._path(), data)
        except (OSError, TypeError, ValueError):  # pragma: no cover - environmental
            return

    def forget(self, url: str) -> None:
        """Drop a channel entirely -- what Stop Following does."""
        channels = self._read()
        if channels.pop(_key(url), None) is not None:
            self._write(channels)


def newest_uploads(url: str, *, fetch: Fetch | None = None) -> tuple[str, list[tuple[str, str]]]:
    """``(channel name, [(video id, title), ...])``, newest first. One request."""
    target = f"{_key(url)}/videos"
    info = run(target, {"extract_flat": "in_playlist", "playlistend": NEWEST}, fetch=fetch)
    name = str(info.get("channel") or info.get("uploader") or info.get("title") or "").strip()
    name = name.removesuffix(" - Videos").strip()
    rows: list[tuple[str, str]] = []
    entries = info.get("entries")
    for entry in entries if isinstance(entries, list) else []:
        if not isinstance(entry, dict):
            continue
        video_id = str(entry.get("id") or "").strip()
        title = str(entry.get("title") or "").strip()
        if video_id and title:
            rows.append((video_id, title))
    return name, rows[:NEWEST]


def check_channels(
    *,
    store: AlertStore | None = None,
    names: dict[str, str] | None = None,
    fetch: Fetch | None = None,
    safe_mode: bool = False,
    now: float | None = None,
    every_minutes: int = 0,
) -> tuple[list[NewVideo], list[tuple[str, str]]]:
    """Look at every ringing channel once. ``(new videos, failures)``.

    One channel at a time, never in parallel: this runs in the background on a
    schedule, and politeness costs nothing nobody is waiting for. A channel
    that cannot be read is reported and the rest are still checked. Newest
    first within a channel, so the notices read in the order they appeared.
    """
    if safe_mode:
        return [], []
    alerts = store or AlertStore()
    if now is not None:
        # The same cadence as the podcast check, and never faster: a launch
        # check and a timer tick close together must not ask YouTube twice.
        last = alerts.last_check()
        if every_minutes > 0 and last and now - last < every_minutes * 60 - 30:
            return [], []
        alerts.stamp(now)
    labels = names or {}
    found: list[NewVideo] = []
    failures: list[tuple[str, str]] = []
    for url in alerts.notifying():
        try:
            name, rows = newest_uploads(url, fetch=fetch)
        except YouTubeRequestError as error:
            failures.append((labels.get(url) or url, plain(error)))
            continue
        channel = labels.get(url) or name or url
        seen = alerts.seen(url)
        ids = [video_id for video_id, _title in rows]
        if seen is not None:
            for video_id, title in reversed(rows):
                if video_id not in seen:
                    found.append(
                        NewVideo(channel, title, f"https://www.youtube.com/watch?v={video_id}")
                    )
        alerts.remember(url, ids)
    return found, failures


__all__ = ["NEWEST", "AlertStore", "NewVideo", "check_channels", "newest_uploads"]
