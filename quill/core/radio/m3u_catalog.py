"""Community M3U radio catalog: browse curated per-genre station playlists from
the public ``junguler/m3u-radio-music-playlists`` GitHub repo, fetched on demand
(never bundled -- the repo is ~1.7 GB) and refreshable by the user.

The repo publishes one ``.m3u`` per genre at its root (``jazz.m3u``,
``classical.m3u``, ``80s.m3u``, ...) plus a few ``---everything*`` aggregate
files. This module lists the genres from the GitHub tree API (so a newly added
genre appears when the user refreshes) and fetches a chosen genre's playlist,
parsing it into playable :class:`RadioStation` objects via
:func:`quill.core.radio.playlist_import.parse_m3u`.

Two HTTPS GETs to GitHub -- the tree listing (``api.github.com``) and a raw
``.m3u`` (``raw.githubusercontent.com``) -- both reviewed in
``quill/tools/network_egress_audit.py``, HTTPS-only over a verified TLS context
with bounded timeout/size, reached only by an explicit browse/refresh action and
disabled in Safe Mode via :func:`refuse_in_safe_mode`. The repo has no license,
so its lists are read on demand like RadioBrowser/TuneIn, never redistributed or
bundled. wx-free, strict-typed.
"""

from __future__ import annotations

import ssl
import urllib.error
import urllib.request

from quill.core.error_codes import CodedError
from quill.core.radio.models import RadioStation
from quill.core.radio.playlist_import import parse_m3u

_OWNER_REPO = "junguler/m3u-radio-music-playlists"
_BRANCH = "main"
_TREE_URL = f"https://api.github.com/repos/{_OWNER_REPO}/git/trees/{_BRANCH}"
_RAW_BASE = f"https://raw.githubusercontent.com/{_OWNER_REPO}/{_BRANCH}/"
_USER_AGENT: str | None = None
_TIMEOUT_SECONDS = 15.0
_MAX_BYTES = 8_000_000

#: Category/source label every station from this catalog carries, so the Browse
#: Stations Source facet can group and filter them.
CATEGORY_LABEL = "Community M3U"
#: Spoken/shown attribution for this genre catalog (junguler's repo).
CATALOG_CREDIT = "the community M3U catalog by junguler"

#: Shown if the live genre listing can't be fetched (offline / rate-limited), so
#: the feature still works with the repo's long-standing genre files.
_FALLBACK_GENRES: tuple[str, ...] = (
    "60s", "70s", "80s", "90s", "alternative", "ambient", "blues", "classical",
    "country", "dance", "electronic", "folk", "funk", "hip_hop", "house", "indie",
    "jazz", "latin", "lounge", "metal", "oldies", "pop", "punk", "reggae", "rock",
    "soul", "techno", "world",
)


class M3uCatalogError(CodedError):
    """A Community M3U catalog request failed (network, or Safe Mode refusal)."""

    code = "QUILL-RADIO-M3U-REQUEST"


def refuse_in_safe_mode(safe_mode: bool) -> None:
    """Raise :class:`M3uCatalogError` when Safe Mode is active."""
    if safe_mode:
        raise M3uCatalogError(
            "The Community M3U catalog is disabled in Safe Mode. "
            "Restart QUILL normally to browse it."
        )


# --- pure parsers -----------------------------------------------------------


def parse_genre_list(tree_json: str) -> list[str]:
    """Root-level genre slugs from a GitHub git-tree JSON reply (pure).

    Returns the ``.m3u`` blobs at the repo root, minus their extension, dropping
    the ``---everything*`` / ``---sorted`` / ``---randomized`` aggregate files
    (they start with ``-``) and anything inside a subdirectory (path has ``/``).
    Sorted for a stable, browsable order.
    """
    import json

    try:
        data = json.loads(tree_json)
    except (ValueError, TypeError):
        return []
    entries = data.get("tree") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        return []
    genres: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("type") != "blob":
            continue
        path = str(entry.get("path", ""))
        if "/" in path or not path.lower().endswith(".m3u"):
            continue
        slug = path[:-4]
        if not slug or slug.startswith("-"):
            continue
        genres.append(slug)
    return sorted(genres)


def genre_display(slug: str) -> str:
    """A human genre label from a repo slug (pure): ``acid_jazz`` -> ``Acid Jazz``."""
    words = [word for word in slug.replace("-", "_").split("_") if word]
    return " ".join(word.upper() if word.isupper() else word.capitalize() for word in words)


def genre_raw_url(slug: str) -> str:
    """The raw.githubusercontent.com URL for a genre's ``.m3u`` (pure)."""
    return f"{_RAW_BASE}{slug}.m3u"


def stations_from_m3u(text: str, genre_slug: str) -> list[RadioStation]:
    """Parse a genre ``.m3u`` into stations tagged with this source + genre (pure)."""
    label = genre_display(genre_slug)
    stations = parse_m3u(text)
    for station in stations:
        station.source = CATEGORY_LABEL
        station.tags = (label, CATEGORY_LABEL)
        if not station.country:
            station.country = ""
    return stations


# --- network ----------------------------------------------------------------


def _user_agent() -> str:
    global _USER_AGENT
    if _USER_AGENT is None:
        from quill import __version__

        _USER_AGENT = f"QUILL/{__version__} (https://github.com/Community-Access/quill)"
    return _USER_AGENT


def _fetch(url: str) -> str:
    """One HTTPS GET of a public GitHub URL -- the reviewed egress site.

    HTTPS-only over a verified TLS context, bounded timeout and response size.
    Serves both the genre tree listing and each raw genre ``.m3u``.
    """
    if not url.startswith("https://"):
        raise M3uCatalogError("Only https:// URLs can be fetched.")
    request = urllib.request.Request(url, headers={"User-Agent": _user_agent()})
    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS, context=context) as resp:
            payload: bytes = resp.read(_MAX_BYTES)
    except (urllib.error.URLError, TimeoutError, ssl.SSLError, OSError) as error:
        raise M3uCatalogError(f"Could not reach the Community M3U catalog: {error}") from error
    return payload.decode("utf-8", errors="replace")


def fetch_genres(*, safe_mode: bool = False) -> list[str]:
    """The available genre slugs, fetched live so a refresh picks up new ones.

    Falls back to :data:`_FALLBACK_GENRES` when the listing can't be fetched or
    is empty, so the feature still works offline / when GitHub rate-limits the
    unauthenticated tree API. Raises only on a Safe Mode refusal.
    """
    refuse_in_safe_mode(safe_mode)
    try:
        genres = parse_genre_list(_fetch(_TREE_URL))
    except M3uCatalogError:
        return list(_FALLBACK_GENRES)
    return genres or list(_FALLBACK_GENRES)


def fetch_genre_stations(genre_slug: str, *, safe_mode: bool = False) -> list[RadioStation]:
    """Every station in one genre's playlist, fetched fresh (Refresh re-calls this).

    One raw ``.m3u`` GET, parsed to playable stations. Raises
    :class:`M3uCatalogError` on a network failure or a Safe Mode refusal.
    """
    refuse_in_safe_mode(safe_mode)
    if not genre_slug.strip():
        return []
    return stations_from_m3u(_fetch(genre_raw_url(genre_slug)), genre_slug)
