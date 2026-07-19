"""Xiph / Icecast public directory (dir.xiph.org): browse the long-running,
keyless Icecast "yellow pages" of free internet radio, by genre, on demand.

The directory has no JSON/OPML API -- only server-rendered HTML -- so this reads
its public pages: ``/genres`` lists every genre, and ``/genres/<name>`` lists
that genre's station cards, each of which advertises a **directly playable**
stream URL in its Play button (no separate resolve step, unlike TuneIn/iHeart).
The two small regex parsers below are deliberately tolerant: a directory HTML
tweak degrades to "fewer/zero rows", never a crash.

Fetched on demand and refreshable (never bundled). One HTTPS GET per action to
``dir.xiph.org`` -- a single reviewed egress site (:func:`_fetch`, see
``quill/tools/network_egress_audit.py``) -- HTTPS-only over a verified TLS
context with a bounded timeout/size, disabled in Safe Mode via
:func:`refuse_in_safe_mode`. wx-free, strict-typed.
"""

from __future__ import annotations

import html as _html
import re
import ssl
import urllib.error
import urllib.request

from quill.core.error_codes import CodedError
from quill.core.radio.models import RadioStation

_BASE = "https://dir.xiph.org"
_GENRES_URL = f"{_BASE}/genres"
_USER_AGENT: str | None = None
_TIMEOUT_SECONDS = 15.0
_MAX_BYTES = 4_000_000

CATEGORY_LABEL = "Xiph"
#: Spoken/shown attribution for this genre catalog.
CATALOG_CREDIT = "the Xiph/Icecast public directory"

#: A genre link on the /genres index: ``/genres/<name>``.
_GENRE_LINK_RE = re.compile(r'href="/genres/([^"/]+)"', re.IGNORECASE)
#: One station card: its title, then the first Play button's stream URL. The
#: non-greedy span stops at the card's own Play button.
_CARD_RE = re.compile(
    r'<h5[^>]*class="card-title"[^>]*>(?P<title>.*?)</h5>.*?'
    r'<a[^>]+href="(?P<url>https?://[^"]+)"[^>]*class="btn btn-sm btn-primary"',
    re.IGNORECASE | re.DOTALL,
)
#: The codec badge inside a card (best-effort; ``""`` if absent).
_CODEC_RE = re.compile(r'href="/codecs/([^"]+)"', re.IGNORECASE)


class XiphError(CodedError):
    """A Xiph/Icecast directory request failed (network, or Safe Mode refusal)."""

    code = "QUILL-RADIO-XIPH-REQUEST"


def refuse_in_safe_mode(safe_mode: bool) -> None:
    """Raise :class:`XiphError` when Safe Mode is active."""
    if safe_mode:
        raise XiphError(
            "The Xiph/Icecast directory is disabled in Safe Mode. "
            "Restart QUILL normally to browse it."
        )


# --- pure parsers -----------------------------------------------------------


def parse_genres(page_html: str) -> list[str]:
    """Every genre name from the ``/genres`` index (pure), de-duplicated
    case-insensitively (the directory lists e.g. both ``Pop`` and ``pop``),
    keeping the first spelling seen, sorted for a stable browse order."""
    seen: dict[str, str] = {}
    for raw in _GENRE_LINK_RE.findall(page_html):
        name = _html.unescape(raw).strip()
        key = name.casefold()
        if name and key not in seen:
            seen[key] = name
    return sorted(seen.values(), key=str.casefold)


def genre_display(name: str) -> str:
    """A human genre label (pure): ``80s`` stays ``80s``, ``jazz`` -> ``Jazz``."""
    return name if name.isupper() or any(c.isdigit() for c in name) else name.title()


def parse_stations(page_html: str) -> list[RadioStation]:
    """Playable stations from a genre page's cards (pure).

    Each card yields a title and the directly playable stream URL from its Play
    button; duplicate stream URLs are collapsed (first title wins). A card
    without a recognisable Play link is skipped."""
    stations: list[RadioStation] = []
    seen: set[str] = set()
    for match in _CARD_RE.finditer(page_html):
        url = match.group("url").strip()
        if not url or url in seen:
            continue
        title = _html.unescape(re.sub(r"<[^>]+>", "", match.group("title"))).strip()
        if not title:
            continue
        seen.add(url)
        codec = _CODEC_RE.search(page_html[match.start() : match.end()])
        stations.append(
            RadioStation(
                name=title,
                stream_url=url,
                station_uuid="",
                country="",
                tags=(CATEGORY_LABEL,),
                codec=codec.group(1).upper() if codec else "",
                source=CATEGORY_LABEL,
            )
        )
    return stations


# --- network ----------------------------------------------------------------


def _user_agent() -> str:
    global _USER_AGENT
    if _USER_AGENT is None:
        from quill import __version__

        _USER_AGENT = f"QUILL/{__version__} (https://github.com/Community-Access/quill)"
    return _USER_AGENT


def _fetch(url: str) -> str:
    """One HTTPS GET of a public dir.xiph.org page -- the reviewed egress site."""
    if not url.startswith("https://"):
        raise XiphError("Only https:// URLs can be fetched.")
    request = urllib.request.Request(url, headers={"User-Agent": _user_agent()})
    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS, context=context) as resp:
            payload: bytes = resp.read(_MAX_BYTES)
    except (urllib.error.URLError, TimeoutError, ssl.SSLError, OSError) as error:
        raise XiphError(f"Could not reach the Xiph directory: {error}") from error
    return payload.decode("utf-8", errors="replace")


def fetch_genres(*, safe_mode: bool = False) -> list[str]:
    """The directory's genre names, fetched live (Refresh re-calls this)."""
    refuse_in_safe_mode(safe_mode)
    try:
        return parse_genres(_fetch(_GENRES_URL))
    except XiphError:
        return []


def fetch_genre_stations(genre: str, *, safe_mode: bool = False) -> list[RadioStation]:
    """Every station in one genre, fetched fresh (Refresh re-calls this)."""
    refuse_in_safe_mode(safe_mode)
    if not genre.strip():
        return []
    return parse_stations(_fetch(f"{_GENRES_URL}/{urllib_quote(genre.strip())}"))


def urllib_quote(value: str) -> str:
    """URL-quote a genre segment (its own helper so the path build stays clear)."""
    import urllib.parse

    return urllib.parse.quote(value, safe="")
