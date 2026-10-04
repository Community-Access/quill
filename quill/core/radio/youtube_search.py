"""Search YouTube for videos, playlists and channels, each row saying which.

Search Stations has blended YouTube *videos* into its results for a while,
through yt-dlp's keyless ``ytsearch``. That route only ever returns videos, and
the most useful answers to "Rick Steves" or "BBC Radio 4" are often not a video
at all: they are the channel, or the playlist that holds the whole series.
Asked for by a listener who searches YouTube more than any radio directory.

So this asks YouTube's own results page three times, once per type, with the
type filter YouTube's own Filters menu applies (the ``sp`` parameter). yt-dlp
reads that page with its ``YoutubeSearchURL`` extractor, flatly -- one request
per type, nothing resolved -- and the three answers become ordinary browse
rows:

* a **video** is a playable row, exactly like a saved YouTube video;
* a **playlist** is a folder that opens into its videos, through the same
  ``youtubevideos`` branch a channel's playlists already use;
* a **channel** is a folder (``ytchannel``) that opens into its uploads, its
  live broadcasts and its playlists, and offers Follow on its menu.

Every row's note leads with what it is -- "video, 12 minutes, Rick Steves",
"playlist, Rick Steves", "channel, 1.2 million subscribers" -- because a mixed
list is unreadable by ear without it.

**What YouTube does not say.** A playlist result on YouTube's current results
page carries no video count that yt-dlp reads, so a playlist row names its
channel and, only when the page happens to carry it, its size. The count is
honest when present and absent rather than guessed otherwise.

wx-free, strict-typed. No network in this module beyond
:func:`quill.core.radio.youtube_requests.run`.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import quote_plus

from quill.core.radio.browse_nodes import BrowseNode, folder, leaf, make_id
from quill.core.radio.models import RadioStation
from quill.core.radio.youtube_requests import Fetch, YouTubeRequestError, plain, run

if TYPE_CHECKING:  # federated_browse reaches browse_sources, which imports us
    from quill.core.radio.federated_browse import FederatedBrowse

VIDEO = "video"
PLAYLIST = "playlist"
CHANNEL = "channel"

#: YouTube's own result-type filters (the ``sp`` value its Filters menu sets).
TYPE_FILTERS: dict[str, str] = {
    VIDEO: "EgIQAQ%3D%3D",
    CHANNEL: "EgIQAg%3D%3D",
    PLAYLIST: "EgIQAw%3D%3D",
}

#: How many of each type one search asks for. Videos are what most searches
#: want, so they get the most room; a page of twenty is still one request.
LIMITS: dict[str, int] = {VIDEO: 20, PLAYLIST: 10, CHANNEL: 10}

#: The order the merged list groups them in, and the word each type reads as.
TYPE_ORDER: tuple[str, ...] = (VIDEO, PLAYLIST, CHANNEL)
TYPE_LABELS: dict[str, str] = {VIDEO: "Video", PLAYLIST: "Playlist", CHANNEL: "Channel"}


@dataclass(frozen=True, slots=True)
class YouTubeResult:
    """One search answer, before it becomes a browse row."""

    kind: str
    url: str
    title: str
    uploader: str = ""
    duration_ms: int = 0
    is_live: bool = False
    #: Videos in a playlist, when the results page said. 0 = not said.
    video_count: int = 0
    #: A channel's subscribers, when the results page said. 0 = not said.
    followers: int = 0
    #: A channel's ``@handle`` page, when known -- the friendlier address to follow.
    handle_url: str = ""


def results_url(query: str, kind: str) -> str:
    """YouTube's own results page for *query*, filtered to one type (pure)."""
    return (
        f"https://www.youtube.com/results?search_query={quote_plus(query.strip())}"
        f"&sp={TYPE_FILTERS[kind]}"
    )


def short_duration(milliseconds: int) -> str:
    """A length as a list row says it: "12 minutes", "1 hour 5 minutes" (pure).

    Rounded to the minute on purpose. A search row is for deciding whether to
    open something, and "12 minutes 41 seconds" is precision nobody needed
    there, read aloud on every row.
    """
    seconds = max(0, int(milliseconds) // 1000)
    if seconds < 60:
        return f"{seconds} second{'' if seconds == 1 else 's'}" if seconds else ""
    minutes = int(round(seconds / 60))
    hours, minutes = divmod(minutes, 60)
    if not hours:
        return f"{minutes} minute{'' if minutes == 1 else 's'}"
    said = f"{hours} hour{'' if hours == 1 else 's'}"
    return f"{said} {minutes} minute{'' if minutes == 1 else 's'}" if minutes else said


def count_words(value: int) -> str:
    """1234567 -> "1.2 million" (pure). Counts are read, not inspected."""
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}".rstrip("0").rstrip(".") + " million"
    if value >= 10_000:
        return f"{value // 1000} thousand"
    return f"{value:,}"


def note_for(result: YouTubeResult) -> str:
    """What the row says after its title, type first (pure).

    ``"video, 12 minutes, Rick Steves"`` / ``"playlist, 40 videos, Rick
    Steves"`` / ``"channel, 1.2 million subscribers"``.
    """
    parts = [result.kind]
    if result.kind == VIDEO:
        if result.is_live:
            parts.append("live now")
        elif result.duration_ms > 0:
            parts.append(short_duration(result.duration_ms))
        if result.uploader:
            parts.append(result.uploader)
    elif result.kind == PLAYLIST:
        if result.video_count > 0:
            parts.append(f"{result.video_count} video{'' if result.video_count == 1 else 's'}")
        if result.uploader:
            parts.append(result.uploader)
    elif result.followers > 0:
        parts.append(
            f"{count_words(result.followers)} subscriber{'' if result.followers == 1 else 's'}"
        )
    return ", ".join(part for part in parts if part)


def _int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0
    return int(value) if value > 0 else 0


def parse_entry(entry: dict[str, object], kind: str) -> YouTubeResult | None:
    title = str(entry.get("title") or entry.get("channel") or "").strip()
    raw_url = str(entry.get("url") or entry.get("webpage_url") or "").strip()
    entry_id = str(entry.get("id") or "").strip()
    uploader = str(entry.get("uploader") or entry.get("channel") or "").strip()
    if kind == VIDEO:
        url = raw_url or (f"https://www.youtube.com/watch?v={entry_id}" if entry_id else "")
        if "/watch" not in url and "/shorts/" not in url and "youtu.be" not in url:
            return None
        live = str(entry.get("live_status") or "") == "is_live" or bool(entry.get("is_live"))
        duration = entry.get("duration")
        millis = (
            int(float(duration) * 1000)
            if isinstance(duration, (int, float)) and not isinstance(duration, bool)
            else 0
        )
        return (
            YouTubeResult(VIDEO, url, title, uploader=uploader, duration_ms=millis, is_live=live)
            if title
            else None
        )
    if kind == PLAYLIST:
        url = raw_url or (f"https://www.youtube.com/playlist?list={entry_id}" if entry_id else "")
        if "list=" not in url or not title:
            return None
        count = _int(entry.get("playlist_count")) or _int(entry.get("video_count"))
        return YouTubeResult(PLAYLIST, url, title, uploader=uploader, video_count=count)
    channel_id = str(entry.get("channel_id") or entry_id).strip()
    url = str(entry.get("channel_url") or raw_url or "").strip()
    if not url and channel_id.startswith("UC"):
        url = f"https://www.youtube.com/channel/{channel_id}"
    if "youtube.com/" not in url or not title:
        return None
    handle = str(entry.get("uploader_url") or "").strip()
    return YouTubeResult(
        CHANNEL,
        url,
        title,
        followers=_int(entry.get("channel_follower_count")),
        handle_url=handle if "/@" in handle else "",
    )


def parse_results(info: dict[str, object], kind: str, *, cap: int = 0) -> list[YouTubeResult]:
    """One type's answer out of a flat results-page listing (pure).

    Entries of the wrong shape are dropped rather than guessed at: a channel
    filter sometimes still yields a promoted video, and a row claiming to be a
    channel that opens into nothing is worse than a shorter list.
    """
    entries = info.get("entries")
    if not isinstance(entries, list):
        return []
    found: list[YouTubeResult] = []
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        result = parse_entry(entry, kind)
        if result is None or result.url in seen:
            continue
        seen.add(result.url)
        found.append(result)
    return found[: cap or LIMITS.get(kind, 20)]


def to_node(result: YouTubeResult) -> BrowseNode:
    """The browse row for one result -- a real row, with a real menu."""
    note = note_for(result)
    if result.kind == VIDEO:
        return leaf(
            RadioStation(
                name=result.title,
                stream_url=result.url,
                homepage=result.url,
                source="YouTube",
                tags=("video", *((result.uploader,) if result.uploader else ())),
                # A finished video seeks and resumes; a live one is simply on.
                is_recording=not result.is_live,
            ),
            note=note,
        )
    if result.kind == PLAYLIST:
        return folder(make_id("youtubevideos", result.url, "1"), result.title, note=note)
    return folder(make_id("ytchannel", result.url, result.handle_url), result.title, note=note)


def search(
    query: str,
    *,
    kinds: tuple[str, ...] = TYPE_ORDER,
    fetch: Fetch | None = None,
    safe_mode: bool = False,
) -> FederatedBrowse:
    """Ask YouTube for each type at once and merge the answers into rows.

    One type failing does not lose the others: it is named in ``failed`` and
    the spoken summary says so. Only when every type fails is it an error,
    because then there is genuinely nothing to show.
    """
    from quill.core.radio.federated_browse import FederatedBrowse

    result = FederatedBrowse()
    text = query.strip()
    if not text:
        return result
    if safe_mode:
        raise YouTubeRequestError("YouTube is not available in Safe Mode.")

    def _one(kind: str) -> tuple[str, list[YouTubeResult], str]:
        options = {"extract_flat": "in_playlist", "playlistend": LIMITS[kind]}
        try:
            info = run(results_url(text, kind), options, fetch=fetch)
        except YouTubeRequestError as error:
            return kind, [], plain(error)
        return kind, parse_results(info, kind), ""

    with ThreadPoolExecutor(max_workers=len(kinds) or 1) as pool:
        answers = list(pool.map(_one, kinds))
    errors = [why for _kind, _rows, why in answers if why]
    if errors and len(errors) == len(answers):
        raise YouTubeRequestError(errors[0])
    by_kind = {kind: rows for kind, rows, _why in answers}
    for kind, _rows, why in answers:
        result.asked.append(f"YouTube {kind}s")
        if why:
            result.failed.append((f"YouTube {kind}s", why))
    for kind in TYPE_ORDER:
        rows = by_kind.get(kind, [])
        if rows:
            result.counts[TYPE_LABELS[kind]] = len(rows)
        result.rows.extend(to_node(row) for row in rows)
    return result


__all__ = [
    "CHANNEL",
    "PLAYLIST",
    "TYPE_FILTERS",
    "VIDEO",
    "YouTubeResult",
    "note_for",
    "parse_entry",
    "parse_results",
    "results_url",
    "search",
    "short_duration",
    "to_node",
]
