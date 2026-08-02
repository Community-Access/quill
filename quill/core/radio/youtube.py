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
* **yt-dlp is never bundled.** It reaches arbitrary media hosts and updates
  constantly, so it installs on demand -- the same posture the converter's URL
  import takes (:mod:`quill.core.audio.url_import`) -- and only after the
  listener has accepted the one-time consent + rights notice at the UI call
  site (``RadioHistory.youtube_consented``).

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
class YouTubeStream:
    """One resolved YouTube audio stream.

    ``stream_url`` is the short-lived media URL the player/recorder loads;
    ``page_url`` is the durable link a favorite stores. ``title`` seeds the
    station name so a saved YouTube station reads as its video/broadcast name
    rather than a URL, and ``is_live`` lets a caller say "live" out loud.
    """

    stream_url: str
    page_url: str
    title: str = ""
    is_live: bool = False


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
    return YouTubeStream(
        stream_url=_best_audio_url(info),
        page_url=str(info.get("webpage_url") or page_url),
        title=str(info.get("title") or ""),
        is_live=bool(info.get("is_live")),
    )


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
