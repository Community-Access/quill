"""Global Player station pages: the streams the page offers to everyone (pure).

Global (Capital, Heart, LBC, Classic FM, Smooth, Radio X and the rest) plays
its stations at ``www.globalplayer.com/live/<brand>/<region>/``. The page is a
Next.js app, but it is not computed at runtime: the server writes the whole
page state into ``<script id="__NEXT_DATA__">``, and under
``props.pageProps.playable.playback`` it lists every way the station can be
played. Each entry has a ``canUse`` rule. Most rules need a signed-in or paid
listener (``user.logged_in``, ``cap.license``, a premium bundle); the plain
Icecast stream everyone may play says exactly ``"true"``. Only those entries
are offered, so QUILL never lists a stream Global keeps for subscribers.

The idea of reading Global Player's page state is from Andre Louis's
StreamSift (https://github.com/OnjLouis/StreamSift); this is QUILL's own
implementation, not a port.

No network: the caller fetches the page. wx-free, strict-typed.
"""

from __future__ import annotations

import json
import re
import urllib.parse

__all__ = ["is_station_page", "station_title", "stream_urls_from_page"]

_HOSTS = ("globalplayer.com", "www.globalplayer.com")
_NEXT_DATA_RE = re.compile(
    r"<script[^>]*\bid=[\"']__NEXT_DATA__[\"'][^>]*>(.*?)</script>", re.IGNORECASE | re.DOTALL
)
_MAX_ENTRIES = 12


def is_station_page(url: str) -> bool:
    """True for a Global Player live station page (``/live/<brand>/...``)."""
    parts = urllib.parse.urlsplit(url.strip())
    if (parts.hostname or "").lower() not in _HOSTS or parts.port not in (None, 443):
        return False
    segments = [s for s in parts.path.split("/") if s]
    return len(segments) >= 2 and segments[0].lower() == "live"


def _playable(html: str) -> dict[str, object]:
    match = _NEXT_DATA_RE.search(html)
    if not match:
        return {}
    try:
        state = json.loads(match.group(1))
    except ValueError:
        return {}
    node: object = state
    for key in ("props", "pageProps", "playable"):
        node = node.get(key) if isinstance(node, dict) else None
    return node if isinstance(node, dict) else {}


def station_title(html: str) -> str:
    """The station's name as the page states it ("Capital UK"), or ""."""
    title = _playable(html).get("title")
    return " ".join(title.split())[:80] if isinstance(title, str) else ""


def stream_urls_from_page(html: str) -> list[str]:
    """Every stream the page lets anyone play, in the page's order."""
    playback = _playable(html).get("playback")
    found: list[str] = []
    for entry in playback[:_MAX_ENTRIES] if isinstance(playback, list) else []:
        if not isinstance(entry, dict) or entry.get("canUse") != "true":
            continue
        url = entry.get("url")
        if isinstance(url, str) and url.startswith(("https://", "http://")) and url not in found:
            found.append(url)
    return found
