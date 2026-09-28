"""Playlists and channels for Convert from URL: read the link, then fetch its audio.

Convert from URL took one video per link (``noplaylist``), so a lecture series
meant pasting forty links. This is the wx-free half of taking the whole thing:

* :func:`read_link` looks at a link *without downloading anything* and says
  what it is -- one video, a playlist (and how many videos), or a channel (and
  which of its sections exist) -- so the window can ask a real question before
  anything is fetched.
* :func:`download_collection` fetches the audio of a playlist or a channel
  section into one folder: numbered in order and tagged with the collection as
  the album and a track number, so the files play in order anywhere; newest N
  or a date window for a channel; a record of what was already fetched, so
  "only what is new since last time" keeps a channel current; a pause between
  videos on long runs, so the site does not block the computer; progress per
  video and inside it; an immediate stop; and a video that fails (private,
  removed, blocked where you are) listed and skipped rather than ending the run.

yt-dlp does the fetching, in-process, exactly as the single-video path does
(:mod:`quill.core.audio.url_import`); the two network hand-offs here are
reviewed in the egress audit. Safe Mode refuses both. Every network call is
injectable, so the tests never touch it.
"""

from __future__ import annotations

import hashlib
import os
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from quill.core.audio.url_import import UrlImportError, looks_like_url
from quill.core.paths import yt_dlp_cache_dir

#: A channel's sections, as (label, URL suffix). Podcasts are left out: that
#: tab holds playlists rather than videos, and each can be pasted on its own.
CHANNEL_SECTIONS: tuple[tuple[str, str], ...] = (
    ("Videos", "/videos"),
    ("Shorts", "/shorts"),
    ("Live streams", "/streams"),
)

#: Longer than this and the run pauses a few seconds between videos.
PAUSE_AFTER = 10

#: ``extract(url, options, download) -> info dict``: yt-dlp's extract_info,
#: injectable.
Extractor = Callable[[str, dict[str, Any], bool], dict[str, Any]]

#: ``(done_items, total_items_or_0, fraction_of_current, title)``
CollectionProgress = Callable[[int, int, float, str], None]

_AUDIO_SUFFIXES = frozenset({
    ".m4a",
    ".webm",
    ".opus",
    ".mp3",
    ".ogg",
    ".aac",
    ".mp4",
    ".mka",
    ".wav",
    ".flac",
})
_UNSAFE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


@dataclass(frozen=True, slots=True)
class LinkInfo:
    """What a pasted link is, read without downloading anything."""

    url: str
    kind: str  # "video", "playlist" or "channel"
    title: str
    #: Videos in a playlist; None for a channel, where counting means paging
    #: through thousands of entries.
    count: int | None = None
    #: The video a ``watch?v=...&list=...`` link points at, or "".
    video_title: str = ""
    #: A channel's sections that exist, as (label, URL).
    sections: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class CollectionChoice:
    """What to fetch from a playlist or a channel section."""

    url: str
    title: str
    is_channel: bool = False
    newest: int | None = None  # None: all of it
    within_days: int | None = None  # None: any date
    only_new: bool = True  # skip what an earlier run already fetched


@dataclass(slots=True)
class CollectionResult:
    """What a collection download produced."""

    folder: Path
    files: list[Path] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    stopped: bool = False


def folder_title(title: str, fallback: str = "YouTube list") -> str:
    """A collection title made safe as a Windows folder name."""
    cleaned = _UNSAFE.sub(" ", title or "").strip(" .")
    cleaned = re.sub(r"\s+", " ", cleaned)[:100]
    return cleaned if cleaned and cleaned != "Untitled List" else fallback


def read_link(url: str, *, extract: Extractor | None = None) -> LinkInfo:
    """Say what *url* is -- one video, a playlist, or a channel -- fetching no media."""
    _refuse_in_safe_mode(url)
    run = extract or _default_extract
    quiet = _Collector([])  # a missing section is an answer, not an error to print
    flat = {"extract_flat": "in_playlist", "playlistend": 1, "logger": quiet}
    try:
        info = run(url, dict(flat), False)
    except Exception as exc:  # noqa: BLE001 - said in words
        raise UrlImportError(f"Could not read that link: {_first_line(exc)}") from exc
    if info.get("_type") != "playlist":
        return LinkInfo(url=url, kind="video", title=str(info.get("title") or "this video"))
    title = str(info.get("title") or "")
    if _is_channel(info):
        base = str(info.get("channel_url") or info.get("uploader_url") or url).rstrip("/")
        base = re.sub(r"/(videos|shorts|streams|featured|podcasts)$", "", base)
        sections = tuple(
            (label, base + suffix)
            for label, suffix in CHANNEL_SECTIONS
            if _has_entries(run, base + suffix, flat)
        )
        name = str(info.get("channel") or info.get("uploader") or title.split(" - ")[0])
        return LinkInfo(url=url, kind="channel", title=name, sections=sections)
    count = info.get("playlist_count")
    if not isinstance(count, int):
        try:
            whole = run(url, {"extract_flat": "in_playlist", "logger": quiet}, False)
            count = len(list(whole.get("entries") or []))
        except Exception:  # noqa: BLE001 - the count is a courtesy, not a need
            count = None
    video_title = ""
    if "v" in parse_qs(urlparse(url).query):
        try:
            single = run(url, {"noplaylist": True, "logger": quiet}, False)
            video_title = str(single.get("title") or "")
        except Exception:  # noqa: BLE001 - then the question omits its name
            video_title = ""
    return LinkInfo(
        url=url,
        kind="playlist",
        title=folder_title(title),
        count=count,
        video_title=video_title,
    )


def archive_path(archive_dir: Path, url: str) -> Path:
    """Where the record of what *url* has already fetched is kept."""
    digest = hashlib.sha1(url.strip().encode("utf-8")).hexdigest()[:16]  # noqa: S324 - a name
    return archive_dir / f"{digest}.txt"


def download_collection(
    choice: CollectionChoice,
    dest_dir: Path,
    *,
    archive_dir: Path | None = None,
    ffmpeg: str | None = None,
    progress: CollectionProgress | None = None,
    cancelled: Callable[[], bool] | None = None,
    extract: Extractor | None = None,
) -> CollectionResult:
    """Fetch the audio of every chosen video into ``dest_dir/<title>/``."""
    _refuse_in_safe_mode(choice.url)
    folder = dest_dir / folder_title(choice.title)
    folder.mkdir(parents=True, exist_ok=True)
    before = set(folder.iterdir())
    result = CollectionResult(folder=folder)
    total = choice.newest or 0
    done = [0]
    current = [""]

    def hook(status: dict[str, Any]) -> None:
        if cancelled is not None and cancelled():
            raise _stop_error()("Stopped.")
        info = status.get("info_dict") or {}
        current[0] = str(info.get("title") or current[0])
        n = info.get("n_entries")
        count = n if isinstance(n, int) and n > 0 else total
        if status.get("status") == "downloading" and progress is not None:
            size = status.get("total_bytes") or status.get("total_bytes_estimate") or 0
            got = status.get("downloaded_bytes") or 0
            fraction = min(1.0, float(got) / float(size)) if size else 0.0
            progress(done[0], count, fraction, current[0])
        elif status.get("status") == "finished":
            done[0] += 1
            if progress is not None:
                progress(done[0], count, 0.0, current[0])

    options = collection_options(choice, folder, archive_dir=archive_dir, ffmpeg=ffmpeg)
    options["progress_hooks"] = [hook]
    options["logger"] = _Collector(result.failed)
    run = extract or _default_extract
    try:
        run(choice.url, options, True)
    except Exception as exc:  # noqa: BLE001 - a stop, or a whole-list failure
        if type(exc).__name__ in ("DownloadCancelled", "_Stopped") or (
            cancelled is not None and cancelled()
        ):
            result.stopped = True
        else:
            raise UrlImportError(f"Could not download that list: {_first_line(exc)}") from exc
    result.files = sorted(
        p
        for p in set(folder.iterdir()) - before
        if p.is_file() and p.suffix.lower() in _AUDIO_SUFFIXES
    )
    return result


def collection_options(
    choice: CollectionChoice,
    folder: Path,
    *,
    archive_dir: Path | None = None,
    ffmpeg: str | None = None,
) -> dict[str, Any]:
    """The yt-dlp options for one collection download (pure, and tested)."""
    interpret = _interpret_action()
    # A playlist keeps its order; a channel section is newest first, so its
    # files are named by date, which sorts the same way in any folder.
    name = (
        "%(upload_date>%Y-%m-%d|)s - %(title)s.%(ext)s"
        if choice.is_channel
        else "%(playlist_index|0)03d - %(title)s.%(ext)s"
    )
    album = folder_title(choice.title)
    options: dict[str, Any] = {
        "cachedir": yt_dlp_cache_dir(),
        "format": "bestaudio/best",
        "outtmpl": str(folder / name),
        "noplaylist": False,
        "ignoreerrors": True,
        "quiet": True,
        "no_warnings": True,
        "windowsfilenames": True,
        "postprocessors": [
            {
                "key": "MetadataParser",
                "when": "pre_process",
                "actions": [
                    # A template whose field never exists, so its default --
                    # the collection's own name -- becomes the album.
                    (interpret, _literal(album), "%(album)s"),
                    (interpret, "playlist_index", "%(track_number)s"),
                ],
            },
            {"key": "FFmpegMetadata", "add_metadata": True},
        ],
    }
    if ffmpeg:
        options["ffmpeg_location"] = ffmpeg
    if choice.newest:
        options["playlistend"] = int(choice.newest)
    if choice.within_days:
        from datetime import date, timedelta

        since = (date.today() - timedelta(days=int(choice.within_days))).strftime("%Y%m%d")
        from yt_dlp.utils import match_filter_func

        # Newest first on a channel, so the first older video ends the run
        # instead of paging through years of uploads to reject each one.
        options["match_filter"] = match_filter_func(None, [f"upload_date>={since}"])
    if choice.only_new and archive_dir is not None:
        archive_dir.mkdir(parents=True, exist_ok=True)
        options["download_archive"] = str(archive_path(archive_dir, choice.url))
    if not choice.newest or choice.newest > PAUSE_AFTER:
        options["sleep_interval"] = 2
        options["max_sleep_interval"] = 6
    return options


class _Collector:
    """yt-dlp's logger: keeps the per-video failures, drops the chatter."""

    def __init__(self, failed: list[str]) -> None:
        self._failed = failed

    def debug(self, msg: str) -> None:
        return None

    def info(self, msg: str) -> None:
        return None

    def warning(self, msg: str) -> None:
        return None

    def error(self, msg: str) -> None:
        text = re.sub(r"^ERROR:\s*", "", str(msg)).strip()
        if text:
            self._failed.append(text.splitlines()[0])


def _stop_error() -> type[Exception]:
    """yt-dlp's own "stop now" exception, which it lets through its error handling."""
    try:
        from yt_dlp.utils import DownloadCancelled
    except ImportError:  # the unit tests' machine; nothing downloads there
        return _Stopped
    return DownloadCancelled  # type: ignore[no-any-return]


class _Stopped(UrlImportError):
    """Stands in for yt-dlp's DownloadCancelled when yt-dlp is absent."""

    code = "QUILL-AUDIO-URLLIST-STOPPED"


def _interpret_action() -> Any:
    try:
        from yt_dlp.postprocessor.metadataparser import MetadataParserPP
    except ImportError:  # the unit tests' machine; nothing downloads there
        return "INTERPRET"
    return MetadataParserPP.Actions.INTERPRET


def _literal(text: str) -> str:
    """*text* as a yt-dlp output template that always renders as itself."""
    safe = re.sub(r"[()|%&,>]", " ", text).strip() or "YouTube list"
    return f"%(quill_collection_name|{safe})s"


def _is_channel(info: dict[str, Any]) -> bool:
    # A channel's id is its UC... id, or its @handle when the link used one (and
    # then yt-dlp lists the channel's tabs rather than its videos). A playlist
    # has a PL..., OL... or TL... id even when a channel owns it.
    ident = str(info.get("id") or "")
    tab = str(info.get("extractor_key") or "") == "YoutubeTab"
    return tab and (ident.startswith("UC") or ident.startswith("@"))


def _has_entries(run: Extractor, url: str, options: dict[str, Any]) -> bool:
    try:
        info = run(url, dict(options), False)
    except Exception:  # noqa: BLE001 - a section the channel does not have
        return False
    return any(True for _ in (info.get("entries") or []))


def _refuse_in_safe_mode(url: str) -> None:
    if os.environ.get("QUILL_SAFE_MODE") == "1":
        raise UrlImportError("Importing audio from a URL is disabled in Safe Mode.")
    if not looks_like_url(url):
        raise UrlImportError(
            "That does not look like a web address. Paste a full http:// or https:// link."
        )


def _first_line(exc: BaseException) -> str:
    text = re.sub(r"^ERROR:\s*", "", str(exc)).strip()
    return text.splitlines()[0] if text else type(exc).__name__


def _default_extract(url: str, options: dict[str, Any], download: bool) -> dict[str, Any]:
    """yt-dlp's extract_info (the reviewed egress site)."""
    import yt_dlp

    from quill.core.js_runtime import yt_dlp_js_options

    params: dict[str, Any] = {
        "cachedir": yt_dlp_cache_dir(),
        "quiet": True,
        "no_warnings": True,
        **yt_dlp_js_options(),  # the bundled deno, for YouTube's challenges
        **options,
    }
    with yt_dlp.YoutubeDL(params) as ydl:
        info = ydl.extract_info(url, download=download)
    return dict(info or {})
