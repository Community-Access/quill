"""Play and record YouTube as if it were a radio station (#1268).

A YouTube link is a *web page*, not a stream, so nothing in the radio stack can
play one directly. yt-dlp turns that page into a real audio stream URL, and from
there YouTube behaves like any other station: the same player, the same
recorder, the same favorites, the same scheduled recordings.

Two things shape the design:

* **The playable URL expires.** YouTube signs its media URLs and they die after
  a few hours, so a favorite must store the *page* URL (stable, shareable, what
  the listener actually has) and re-resolve at the moment of play or record.
  :func:`resolve_youtube_stream` is therefore called on every play, not once at
  save time. That is also why a resolved URL is never persisted.
* **yt-dlp is bundled, but stays replaceable.** It used to install on demand;
  it now ships with the app (~3 MB wheel), because meeting a consent dialog and
  a download before your first YouTube link ever plays is a poor trade for the
  disk it saves. The one-time consent + rights notice at the UI call site
  (``RadioHistory.youtube_consented``) remains -- it covers *contacting
  YouTube*, which is still true, not the download, which no longer happens.
  Because yt-dlp goes stale whenever YouTube changes its player, the installer
  survives as an update path
  (:func:`quill.core.speech.engine_install.install_yt_dlp`), and an installed
  copy takes precedence over the bundled one even in a frozen build
  (:mod:`quill.core.speech.engine_pack_imports`).

Safety: refused in Safe Mode; the single network hand-off is constructing
``yt_dlp.YoutubeDL`` in :func:`_default_resolver`, recorded in the network-egress
audit. The resolver is injectable so tests never touch the network.

wx-free, strict-typed.
"""

from __future__ import annotations

import os
import re
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

from quill.core.error_codes import CodedError

#: ``progress(fraction_0_to_1, message)`` -- the shape every on-demand install uses.
ProgressCallback = Callable[[float, str], None]

#: Hosts whose links this module knows how to turn into a stream. ``www.`` and a
#: leading ``m.`` (mobile) are stripped before the comparison.
_YOUTUBE_HOSTS: frozenset[str] = frozenset({
    "youtube.com",
    "music.youtube.com",
    "youtu.be",
    "youtube-nocookie.com",
})

#: A YouTube video id: 11 characters of the URL-safe base64 alphabet.
_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")

#: Path shapes that carry the video id as the last path segment.
_ID_PATH_PREFIXES: tuple[str, ...] = ("/live/", "/shorts/", "/embed/", "/v/")


class YouTubeError(CodedError):
    """Raised when a YouTube link cannot be turned into a playable stream."""

    code = "QUILL-RADIO-YOUTUBE-RESOLVE"


@dataclass(frozen=True, slots=True)
class YouTubeChapter:
    """One chapter marker YouTube itself published for a video."""

    start_ms: int
    title: str


@dataclass(frozen=True, slots=True)
class YouTubeStream:
    """One resolved YouTube audio stream.

    ``stream_url`` is the short-lived media URL the player/recorder loads;
    ``page_url`` is the durable link a favorite stores. ``title`` seeds the
    station name so a saved YouTube station reads as its video/broadcast name
    rather than a URL, and ``is_live`` lets a caller say "live" out loud.

    Everything below ``is_live`` comes out of the *same* yt-dlp response that
    produced the stream URL, so it costs no extra network call -- it was simply
    being discarded before. ``duration_ms`` is what makes a finished video
    seekable (a live broadcast reports 0, which is honest: it has no timeline);
    ``chapters`` are YouTube's own, authored markers; ``caption_url`` points at
    a timed caption track, which is both a transcript and, fed through the
    podcast chapter segmenter, a source of sections for a video that published
    none.
    """

    stream_url: str
    page_url: str
    title: str = ""
    is_live: bool = False
    duration_ms: int = 0
    uploader: str = ""
    description: str = ""
    chapters: tuple[YouTubeChapter, ...] = ()
    #: A timed caption track (WebVTT/SRT/JSON), preferring a real one over an
    #: automatic one. Empty when the video published no captions at all.
    caption_url: str = ""
    caption_is_automatic: bool = False


@dataclass(frozen=True, slots=True)
class YouTubePlaylistEntry:
    """One video inside a resolved playlist."""

    page_url: str
    title: str = ""
    duration_ms: int = 0
    uploader: str = ""


def is_youtube_playlist_url(url: str) -> bool:
    """True when *url* is a YouTube playlist rather than a single video.

    A ``/playlist?list=`` link is unambiguous. A watch link that *also* carries
    ``list=`` is deliberately **not** treated as a playlist: the listener asked
    for that video, and silently expanding it into fifty stations because the
    link happened to be copied from within a playlist would be a nasty surprise.
    """
    # Checked independently of is_youtube_url: a playlist link carries no video
    # id, so that function rejects it by design.
    candidate = (url or "").strip()
    if not candidate.lower().startswith(("http://", "https://")):
        return False
    try:
        parsed = urlparse(candidate)
    except ValueError:
        return False
    host = (parsed.hostname or "").lower()
    host = host[4:] if host.startswith("www.") else host
    if host.startswith("m.") and host[2:] in _YOUTUBE_HOSTS:
        host = host[2:]
    if host not in _YOUTUBE_HOSTS:
        return False
    if parsed.path.rstrip("/") != "/playlist":
        return False
    return bool(parse_qs(parsed.query).get("list"))


def is_youtube_url(url: str) -> bool:
    """True when *url* is a YouTube link this module can resolve.

    Covers watch links, ``youtu.be`` shorteners, ``/live/`` and ``/shorts/``
    paths, embeds, YouTube Music, and a channel's live page
    (``/@handle/live``, ``/channel/<id>/live``, ``/c/<name>/live``) -- the last
    of which is how a listener follows a station that broadcasts continuously.
    """
    candidate = (url or "").strip()
    if not candidate:
        return False
    if not candidate.lower().startswith(("http://", "https://")):
        return False
    try:
        parsed = urlparse(candidate)
    except ValueError:
        return False
    host = (parsed.hostname or "").lower()
    host = host[4:] if host.startswith("www.") else host
    if host.startswith("m.") and host[2:] in _YOUTUBE_HOSTS:
        host = host[2:]
    if host not in _YOUTUBE_HOSTS:
        return False
    if host == "youtu.be":
        return bool(parsed.path.strip("/"))
    path = parsed.path
    if path in ("/watch", "/watch/"):
        return bool(parse_qs(parsed.query).get("v"))
    if path.rstrip("/").endswith("/live"):
        return True
    return any(path.startswith(prefix) for prefix in _ID_PATH_PREFIXES)


def youtube_video_id(url: str) -> str:
    """The 11-character video id in *url*, or "" when it carries none.

    A channel-live link (``/@handle/live``) legitimately has no id -- yt-dlp
    resolves the currently-live broadcast at play time -- so "" is a normal
    answer, not a failure.
    """
    if not is_youtube_url(url):
        return ""
    parsed = urlparse(url.strip())
    host = (parsed.hostname or "").lower()
    if host.endswith("youtu.be"):
        candidate = parsed.path.strip("/").split("/")[0]
        return candidate if _VIDEO_ID_RE.match(candidate) else ""
    if parsed.path in ("/watch", "/watch/"):
        values = parse_qs(parsed.query).get("v") or [""]
        return values[0] if _VIDEO_ID_RE.match(values[0]) else ""
    for prefix in _ID_PATH_PREFIXES:
        if parsed.path.startswith(prefix):
            candidate = parsed.path[len(prefix) :].strip("/").split("/")[0]
            return candidate if _VIDEO_ID_RE.match(candidate) else ""
    return ""


def canonical_youtube_url(url: str) -> str:
    """The tidy link to *store* for this station.

    A video collapses to ``https://www.youtube.com/watch?v=<id>``, dropping
    playlist, timestamp, and tracking parameters that would otherwise ride along
    in a saved favorite. A channel-live link keeps its own shape (there is no id
    to canonicalize) with its query stripped. A non-YouTube URL is returned
    untouched, so this is safe to call on anything.
    """
    candidate = (url or "").strip()
    if not is_youtube_url(candidate):
        return candidate
    video_id = youtube_video_id(candidate)
    if video_id:
        return f"https://www.youtube.com/watch?v={video_id}"
    parsed = urlparse(candidate)
    host = (parsed.hostname or "").lower()
    host = host[2:] if host.startswith("m.") else host
    return f"https://{host}{parsed.path.rstrip('/')}"


def youtube_version() -> str:
    """The yt-dlp version currently in use, or ``""`` if it cannot be read.

    Reported after an update so "updated" is a checkable claim rather than a
    reassurance -- the whole point of the update path is that the bundled copy
    has gone stale, so which copy answers afterwards is the interesting part.
    """
    try:
        import yt_dlp

        return str(yt_dlp.version.__version__)
    except Exception:  # noqa: BLE001 -- a version read must never be fatal
        return ""


def youtube_available() -> bool:
    """True when yt-dlp is installed, so a YouTube link can resolve right now."""
    from quill.core.speech.engine_install import is_yt_dlp_available

    return is_yt_dlp_available()


#: A resolver: ``(page_url) -> YouTubeStream``. Injectable so every flow above
#: this module is testable without yt-dlp or the network.
Resolver = Callable[[str], YouTubeStream]

#: An installer: ``(progress) -> None``. Installs yt-dlp on demand. Injectable.
Installer = Callable[["ProgressCallback | None"], None]


def resolve_youtube_stream(url: str, *, resolver: Resolver | None = None) -> YouTubeStream:
    """Turn a YouTube page link into a playable audio stream.

    Raises :class:`YouTubeError` in Safe Mode, on a link that is not YouTube, if
    yt-dlp is not installed, or when the page yields no audio stream (a private,
    removed, region-blocked, or not-yet-live video). ``resolver`` is injectable
    for tests; the default uses yt-dlp in-process.
    """
    if os.environ.get("QUILL_SAFE_MODE") == "1":
        raise YouTubeError("Playing YouTube links is disabled in Safe Mode.")
    page_url = canonical_youtube_url(url)
    if not is_youtube_url(page_url):
        raise YouTubeError("That does not look like a YouTube link.")
    resolve = resolver or _default_resolver
    if resolver is None and not youtube_available():
        raise YouTubeError(
            "Playing YouTube links needs the yt-dlp component, which is not installed yet."
        )
    try:
        stream = resolve(page_url)
    except YouTubeError:
        raise
    except Exception as exc:  # noqa: BLE001 - surface a clean, coded message
        raise YouTubeError(f"Could not open that YouTube link: {exc}") from exc
    if not stream.stream_url:
        raise YouTubeError(
            "That YouTube link has no audio stream QUILL can play. It may be private, "
            "removed, blocked in your country, or not live yet."
        )
    return stream


def ensure_and_resolve(
    url: str,
    *,
    progress: ProgressCallback | None = None,
    installer: Installer | None = None,
    resolver: Resolver | None = None,
) -> YouTubeStream:
    """Install yt-dlp if missing, then resolve *url*'s audio stream.

    The one call a UI runs off-thread once the listener has consented: the
    on-demand install (first use only) and the resolve share one progress
    callback. Refused in Safe Mode. Both halves are injectable for tests.
    """
    if os.environ.get("QUILL_SAFE_MODE") == "1":
        raise YouTubeError("Playing YouTube links is disabled in Safe Mode.")
    if not is_youtube_url(url):
        raise YouTubeError("That does not look like a YouTube link.")
    if resolver is None and not youtube_available():
        install = installer or _default_installer
        if progress is not None:
            progress(0.05, "Installing the yt-dlp component...")
        try:
            install(progress)
        except YouTubeError:
            raise
        except Exception as exc:  # noqa: BLE001 - surface a clean, coded message
            raise YouTubeError(f"Could not install the yt-dlp component: {exc}") from exc
    if progress is not None:
        progress(0.6, "Finding the audio stream...")
    return resolve_youtube_stream(url, resolver=resolver)


def _default_installer(progress: ProgressCallback | None) -> None:
    from quill.core.speech.engine_install import install_yt_dlp

    install_yt_dlp(progress=progress)


def _default_resolver(page_url: str) -> YouTubeStream:
    """Ask yt-dlp for the best audio stream (the reviewed egress site).

    ``download=False``: nothing is written to disk here. The player streams the
    returned URL, and a recording re-resolves and captures it with ffmpeg, so
    QUILL never keeps a copy the listener did not ask for.
    """
    import yt_dlp  # imported lazily: installed on demand, absent until then

    options: dict[str, object] = {
        "format": "bestaudio/best",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(page_url, download=False)
    if not isinstance(info, dict):
        return YouTubeStream(stream_url="", page_url=page_url)
    # A channel-live link resolves to the live entry inside a playlist-shaped
    # result; take the first entry so "/@handle/live" behaves like a station.
    entries = info.get("entries")
    if isinstance(entries, list) and entries:
        first = entries[0]
        if isinstance(first, dict):
            info = first
    return stream_from_info(info, page_url)


def _duration_ms(info: dict[str, object]) -> int:
    """Duration in ms, or 0. A live broadcast has none, and saying so is right:
    0 is what tells the player this has no timeline to scrub."""
    value = info.get("duration")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0
    return int(round(float(value) * 1000)) if value > 0 else 0


def parse_chapters(info: dict[str, object]) -> tuple[YouTubeChapter, ...]:
    """YouTube's own chapter markers out of a yt-dlp info dict (pure).

    These are authored by the uploader, so they rank with the podcast cascade's
    "published" tier -- above anything inferred from the audio or a transcript.
    """
    raw = info.get("chapters")
    if not isinstance(raw, list):
        return ()
    chapters: list[YouTubeChapter] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        title = str(entry.get("title", "")).strip()
        start = entry.get("start_time")
        if not title or isinstance(start, bool) or not isinstance(start, (int, float)):
            continue
        if start < 0:
            continue
        chapters.append(YouTubeChapter(int(round(float(start) * 1000)), title))
    chapters.sort(key=lambda c: c.start_ms)
    return tuple(chapters)


def pick_caption_track(info: dict[str, object]) -> tuple[str, bool]:
    """The best timed caption track as ``(url, is_automatic)`` (pure).

    A human-written track is preferred over an automatic one, and English is
    preferred over other languages only as a tie-break -- a listener watching a
    French video wants the French captions. Returns ``("", False)`` when the
    video published none, which callers read as "no transcript available"
    rather than as an error.
    """
    for key, automatic in (("subtitles", False), ("automatic_captions", True)):
        tracks = info.get(key)
        if not isinstance(tracks, dict) or not tracks:
            continue
        languages = sorted(tracks, key=lambda code: (not str(code).startswith("en"), str(code)))
        for language in languages:
            formats = tracks.get(language)
            if not isinstance(formats, list):
                continue
            # Timed formats only: json3/srv*/vtt carry positions, and a plain
            # text dump would be useless for both seeking and segmentation.
            for wanted in ("vtt", "srt", "json3", "srv3", "srv1"):
                for entry in formats:
                    if not isinstance(entry, dict):
                        continue
                    if str(entry.get("ext", "")).lower() != wanted:
                        continue
                    url = str(entry.get("url", ""))
                    if url.startswith("https://"):
                        return url, automatic
    return "", False


def stream_from_info(info: dict[str, object], page_url: str) -> YouTubeStream:
    """Build a :class:`YouTubeStream` from a yt-dlp info dict (pure).

    Split out from the resolver so every field it captures is testable without
    touching the network.
    """
    caption_url, caption_is_automatic = pick_caption_track(info)
    return YouTubeStream(
        stream_url=_best_audio_url(info),
        page_url=str(info.get("webpage_url") or page_url),
        title=str(info.get("title") or ""),
        is_live=bool(info.get("is_live")),
        duration_ms=_duration_ms(info),
        uploader=str(info.get("uploader") or info.get("channel") or ""),
        description=str(info.get("description") or ""),
        chapters=parse_chapters(info),
        caption_url=caption_url,
        caption_is_automatic=caption_is_automatic,
    )


def resolve_youtube_playlist(
    url: str, *, resolver: Callable[[str], dict[str, object]] | None = None
) -> tuple[YouTubePlaylistEntry, ...]:
    """List a YouTube playlist's videos without resolving any of their audio.

    Deliberately a *flat* listing (``extract_flat``): a fifty-video playlist
    would otherwise mean fifty page fetches, which is both slow and far more
    traffic than the listener asked for by opening a list. Each entry's audio is
    resolved only when it is actually played, exactly as a saved station is.

    Raises :class:`YouTubeError` in Safe Mode or when yt-dlp is unavailable, and
    returns an empty tuple for a playlist that is private, empty, or removed.

    The entries half of :func:`resolve_youtube_playlist_details`, kept as its own
    name for callers that do not need the playlist's title.
    """
    return resolve_youtube_playlist_details(url, resolver=resolver)[1]


def resolve_youtube_playlist_details(
    url: str, *, resolver: Callable[[str], dict[str, object]] | None = None
) -> tuple[str, tuple[YouTubePlaylistEntry, ...]]:
    """The playlist's own name and its videos, from the same single request.

    The name rides along in the flat listing yt-dlp already returns, so keeping
    it costs nothing -- and without it the picker can only head itself with the
    raw ``playlist?list=PLxxxxxxxx`` address, which tells a listener nothing
    about what they are looking at. Empty string when the listing carries no
    title.
    """
    if os.environ.get("QUILL_SAFE_MODE") == "1":
        raise YouTubeError("Opening YouTube playlists is disabled in Safe Mode.")
    if not is_youtube_playlist_url(url):
        raise YouTubeError("That is not a YouTube playlist link.")
    fetch = resolver or _default_playlist_resolver
    if resolver is None and not youtube_available():
        raise YouTubeError(
            "Opening YouTube playlists needs the yt-dlp component, which is not installed yet."
        )
    try:
        info = fetch(url)
    except YouTubeError:
        raise
    except Exception as exc:  # noqa: BLE001 - one clean message for any failure
        raise YouTubeError(f"That YouTube playlist could not be opened: {exc}") from exc
    payload = info if isinstance(info, dict) else {}
    return playlist_title_from_info(payload), playlist_entries_from_info(payload)


def playlist_title_from_info(info: dict[str, object]) -> str:
    """The playlist's display name, or "" when the listing carries none (pure)."""
    for key in ("title", "playlist_title", "channel", "uploader"):
        value = str(info.get(key) or "").strip()
        if value:
            return value
    return ""


#: Cap on YouTube search results blended into Find Stations. One request
#: either way, so this is about not burying the radio directories under videos
#: rather than about network cost.
SEARCH_RESULT_CAP = 8


def search_youtube(
    query: str,
    *,
    limit: int = SEARCH_RESULT_CAP,
    resolver: Callable[[str], dict[str, object]] | None = None,
) -> tuple[YouTubePlaylistEntry, ...]:
    """Search YouTube, returning videos in YouTube's own relevance order.

    Uses yt-dlp's ``ytsearchN:`` prefix, which needs no API key and no account.
    That is the same extraction route FreeTube, NewPipe and Invidious all take;
    the sanctioned Data API would require every listener to create a Google
    Cloud project and paste a key, which is a wall in front of a search box.
    The trade-off is that this can break when YouTube changes -- which is
    exactly what **Station > Update YouTube Support...** is for, since a newer
    yt-dlp supersedes the bundled one without waiting for a Quill release.

    Flat, like a playlist listing: one request for the whole result set, and no
    video's audio is resolved until it is played.

    Raises :class:`YouTubeError` in Safe Mode or when yt-dlp is unavailable;
    returns an empty tuple for a search that matched nothing.
    """
    if os.environ.get("QUILL_SAFE_MODE") == "1":
        raise YouTubeError("Searching YouTube is disabled in Safe Mode.")
    text = query.strip()
    if not text:
        return ()
    fetch = resolver or _default_search_resolver
    if resolver is None and not youtube_available():
        raise YouTubeError("Searching YouTube needs the yt-dlp component, which is not available.")
    count = max(1, min(int(limit), 50))
    try:
        info = fetch(f"ytsearch{count}:{text}")
    except YouTubeError:
        raise
    except Exception as error:  # noqa: BLE001 - reported as a speakable failure
        raise YouTubeError("YouTube could not be searched right now.") from error
    return playlist_entries_from_info(info)[:count]


def _default_search_resolver(spec: str) -> dict[str, object]:
    """Run a ``ytsearchN:query`` through yt-dlp (a reviewed egress site).

    ``extract_flat="in_playlist"`` keeps it to one request: titles, durations
    and uploaders come back without visiting any video's page.
    """
    import yt_dlp  # imported lazily

    options: dict[str, object] = {
        "extract_flat": "in_playlist",
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(spec, download=False)
    return info if isinstance(info, dict) else {}


def _default_playlist_resolver(url: str) -> dict[str, object]:
    """Flat-list a playlist through yt-dlp (a reviewed egress site).

    ``extract_flat="in_playlist"`` returns each entry's id and title without
    visiting its page, so listing a playlist is one request rather than one per
    video.
    """
    import yt_dlp  # imported lazily: installed on demand, absent until then

    options: dict[str, object] = {
        "extract_flat": "in_playlist",
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=False)
    return info if isinstance(info, dict) else {}


def playlist_entries_from_info(info: dict[str, object]) -> tuple[YouTubePlaylistEntry, ...]:
    """Every playable video in a resolved playlist (pure, order preserved).

    A playlist's own order is the uploader's running order, so it is never
    re-sorted here. Entries with no usable page URL are dropped rather than
    offered as items that cannot play.
    """
    entries = info.get("entries")
    if not isinstance(entries, list):
        return ()
    items: list[YouTubePlaylistEntry] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        url = str(entry.get("webpage_url") or entry.get("url") or "")
        video_id = str(entry.get("id", ""))
        if not url and _VIDEO_ID_RE.match(video_id):
            url = f"https://www.youtube.com/watch?v={video_id}"
        if not url:
            continue
        items.append(
            YouTubePlaylistEntry(
                page_url=url,
                title=str(entry.get("title") or ""),
                duration_ms=_duration_ms(entry),
                uploader=str(entry.get("uploader") or entry.get("channel") or ""),
            )
        )
    return tuple(items)


def _best_audio_url(info: dict[str, object]) -> str:
    """The audio URL out of a yt-dlp info dict.

    yt-dlp usually resolves ``url`` directly under the requested format; when it
    hands back a format list instead, prefer an audio-only format (no video
    codec) and fall back to whatever carries a URL, so a live HLS manifest --
    which is audio+video in one -- still plays.
    """
    direct = info.get("url")
    if isinstance(direct, str) and direct:
        return direct
    formats = info.get("formats")
    if not isinstance(formats, list):
        return ""
    audio_only: list[dict[str, object]] = []
    any_url: list[dict[str, object]] = []
    for item in formats:
        if not isinstance(item, dict) or not isinstance(item.get("url"), str):
            continue
        any_url.append(item)
        if item.get("vcodec") in (None, "none") and item.get("acodec") not in (None, "none"):
            audio_only.append(item)
    pool = audio_only or any_url
    if not pool:
        return ""
    best = max(pool, key=lambda item: _as_float(item.get("abr")) or _as_float(item.get("tbr")))
    url = best.get("url")
    return url if isinstance(url, str) else ""


def _as_float(value: object) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0
