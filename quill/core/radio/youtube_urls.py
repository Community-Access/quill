"""What counts as a YouTube link, and the tidy form to keep.

Pure URL reading, split from :mod:`quill.core.radio.youtube` so the resolver
module stays within its size budget (GATE-11): everything here is answerable
from the string alone, with no yt-dlp and no network. The resolver re-exports
these names, so callers keep importing them from ``youtube``.

wx-free, strict-typed.
"""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

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
