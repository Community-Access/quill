"""TuneIn directory client via the open RadioTime OPML API.

TuneIn's directory is reachable through RadioTime's OPML endpoints
(``opml.radiotime.com``) with no API key and no authentication:

* **Search** -- ``Search.ashx?query=<q>&render=json`` returns matching
  stations and shows, each with a ``guide_id`` (e.g. ``s24939``) and a title.
* **Browse** -- ``Browse.ashx?render=json`` (optionally ``&c=<category>``)
  returns the category tree / a category's contents.
* **Resolve** -- ``Tune.ashx?id=<guide_id>&partnerId=RadioTime&formats=...``
  returns the real playable stream URL(s), one per line. A bad or missing id
  answers with ``#STATUS: 4xx`` and no URLs, so a wrong id self-validates to
  "nothing found" rather than a guess.

``partnerId=RadioTime`` is a fixed, public string (the web player's own partner
id), not a secret. These endpoints return only what the user searched for, or
what a page already advertises -- the same shape as the Triton provisioning API
:mod:`quill.core.radio.triton` already depends on, and NOT a scrape of a
competitor's data files (per the ``feedback_no_competitor_data_features``
stance). This reverses the earlier "TuneIn deliberately left out" non-goal;
Jeff approved the reversal 2026-07-17 (see :mod:`quill.core.radio.radio_browser`
and PRD §5.84f).

Every request funnels through the single reviewed egress site
(:func:`_fetch` -- see ``quill/tools/network_egress_audit.py``), HTTPS-only over
a verified TLS context with a bounded timeout, reached only by an explicit
search/browse/resolve user action and disabled in Safe Mode via
:func:`refuse_in_safe_mode`. wx-free, strict-typed.
"""

from __future__ import annotations

import json
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from quill import __version__
from quill.core.error_codes import CodedError
from quill.core.radio.models import RadioStation

_USER_AGENT = f"QUILL/{__version__} (https://github.com/Community-Access/quill)"
_TIMEOUT_SECONDS = 12.0
_MAX_BYTES = 2_000_000

_OPML_BASE = "https://opml.radiotime.com"
#: The web player's own public partner id -- a fixed string, not a secret.
_PARTNER_ID = "RadioTime"
_FORMATS = "mp3,aac,ogg,hls"

#: A TuneIn/RadioTime station guide id, e.g. ``s24939`` (stations start ``s``);
#: browse categories/links use ``c``/``g``/``t`` prefixes we don't resolve.
_GUIDE_ID_RE = re.compile(r"\b(s\d{2,})\b", re.IGNORECASE)


class TuneInError(CodedError):
    """A TuneIn/RadioTime request failed (network, or Safe Mode refusal)."""

    code = "QUILL-RADIO-TUNEIN-REQUEST"


@dataclass(slots=True)
class TuneInResult:
    """One row from a TuneIn search or browse.

    A *station* (``is_station`` True) carries a resolvable ``guide_id``
    (``s...``). A *category* is a browse link the caller drills into with
    :func:`browse`; because RadioTime's levels use inconsistent ids (a top-level
    key like ``music``, a ``guide_id`` like ``c57940``, or an ``?id=r0`` URL),
    the category carries its own ``browse_url`` -- the exact next-level endpoint
    -- which :func:`browse` fetches directly.
    """

    guide_id: str
    title: str
    subtitle: str = ""
    image: str = ""
    is_station: bool = False
    browse_url: str = ""


def refuse_in_safe_mode(safe_mode: bool) -> None:
    """Raise :class:`TuneInError` when Safe Mode is active.

    Safe Mode (``QUILL_SAFE_MODE=1``) disables every network service; querying
    the TuneIn directory is one. Kept in core (flag passed in) so the refusal is
    unit-testable without wx, mirroring the sibling radio sources.
    """
    if safe_mode:
        raise TuneInError(
            "The TuneIn directory is disabled in Safe Mode. Restart QUILL normally to use it."
        )


def guide_id_from_page(url_or_text: str) -> str | None:
    """The TuneIn station guide id (``s\\d+``) in a URL/HTML, or ``None``.

    Pure. A TuneIn station page (``tunein.com/radio/<name>-s24939/``) and its
    embedded config both carry the ``s``-prefixed id; the Find Streams scanner
    uses this to turn a pasted TuneIn page into a resolvable station (#1087).
    """
    match = _GUIDE_ID_RE.search(url_or_text)
    return match.group(1).lower() if match else None


#: Hosts/markers whose presence on a scanned page identifies it as a TuneIn
#: (RadioTime) station page, so the Find Streams scanner only resolves a guide
#: id against TuneIn's API for pages that actually are TuneIn -- a bare ``s\d+``
#: elsewhere is not treated as a TuneIn station.
_TUNEIN_MARKERS = ("tunein.com", "radiotime.com", "opml.radiotime")


def page_is_tunein(url: str, html: str) -> bool:
    """True when the scanned page itself is a TuneIn (RadioTime) page.

    Pure and cheap: matches on the *URL host* only, not the HTML, so a page
    that merely *links* to a TuneIn station (a directory listing) is not treated
    as a TuneIn page -- it is followed one level like any portal link, and the
    resolution happens on the followed TuneIn page. ``html`` is accepted for a
    signature symmetric with :func:`page_is_triton_player` but is unused.
    """
    lowered_url = url.lower()
    return any(marker in lowered_url for marker in _TUNEIN_MARKERS)


# --- pure parsers -----------------------------------------------------------


def _iter_outline(node: object) -> list[dict]:
    """Flatten RadioTime OPML-JSON ``body``/``children`` outline items."""
    items: list[dict] = []
    if isinstance(node, dict):
        body = node.get("body")
        if isinstance(body, list):
            for child in body:
                items.extend(_iter_outline(child))
            return items
        # An outline item; recurse into nested children too.
        items.append(node)
        children = node.get("children")
        if isinstance(children, list):
            for child in children:
                items.extend(_iter_outline(child))
    elif isinstance(node, list):
        for child in node:
            items.extend(_iter_outline(child))
    return items


def parse_directory_results(json_text: str) -> list[TuneInResult]:
    """Parse a RadioTime ``Search.ashx``/``Browse.ashx`` JSON body (pure).

    Returns one :class:`TuneInResult` per outline item that carries a title and
    a guide id. An ``item``/``type`` of ``audio`` (a station) is marked
    ``is_station``; ``link``/category items are returned as browseable rows.
    Tolerant: a malformed document or an item missing a title/id is skipped,
    never fatal.
    """
    try:
        data = json.loads(json_text)
    except (ValueError, TypeError):
        return []
    results: list[TuneInResult] = []
    for item in _iter_outline(data):
        if not isinstance(item, dict):
            continue
        guide_id = str(item.get("guide_id") or item.get("guideId") or "").strip()
        title = str(item.get("text") or item.get("title") or "").strip()
        if not guide_id or not title:
            continue
        kind = str(item.get("type") or item.get("item") or "").strip().lower()
        is_station = kind == "audio" or guide_id[:1].lower() == "s"
        results.append(
            TuneInResult(
                guide_id=guide_id,
                title=title,
                subtitle=str(item.get("subtext") or item.get("subtitle") or "").strip(),
                image=str(item.get("image") or "").strip(),
                is_station=is_station,
            )
        )
    return results


def _browse_result(item: object) -> TuneInResult | None:
    """One browse row from a RadioTime outline item (pure), or None to skip.

    A category carries its own next-level ``URL`` (``browse_url``); a station
    carries a resolvable ``guide_id`` (``s...``). ``type`` decides which -- the
    id prefix is not reliable (a category key like ``sports`` starts with s)."""
    if not isinstance(item, dict):
        return None
    title = str(item.get("text") or item.get("title") or "").strip()
    if not title:
        return None
    guide_id = str(item.get("guide_id") or item.get("guideId") or "").strip()
    browse_url = str(item.get("URL") or item.get("url") or "").strip()
    kind = str(item.get("type") or item.get("item") or "").strip().lower()
    is_station = kind in ("audio", "station")
    if is_station:
        if not guide_id:
            return None  # a station with no id can't be resolved
    elif not browse_url and not guide_id:
        return None  # a category with nowhere to drill
    return TuneInResult(
        guide_id=guide_id,
        title=title,
        subtitle=str(item.get("subtext") or item.get("subtitle") or "").strip(),
        image=str(item.get("image") or "").strip(),
        is_station=is_station,
        browse_url=browse_url,
    )


def parse_browse_level(json_text: str) -> list[TuneInResult]:
    """Parse one Browse.ashx level into its direct rows (pure), for the tree.

    Unlike :func:`parse_directory_results` (which flattens the whole document for
    a flat search list), this keeps the level's own rows: a plain group header
    (an outline with ``children`` but no ``URL``/``guide_id`` of its own -- e.g.
    the ``FM``/``AM`` groups under Local Radio) is transparent, so its child
    stations appear at this level rather than as an un-openable folder.
    """
    try:
        data = json.loads(json_text)
    except (ValueError, TypeError):
        return []
    body = data.get("body") if isinstance(data, dict) else None
    if not isinstance(body, list):
        return []
    results: list[TuneInResult] = []
    for node in body:
        if not isinstance(node, dict):
            continue
        children = node.get("children")
        if isinstance(children, list) and not (node.get("URL") or node.get("guide_id")):
            for child in children:
                row = _browse_result(child)
                if row is not None:
                    results.append(row)
            continue
        row = _browse_result(node)
        if row is not None:
            results.append(row)
    return results


def parse_tune_response(text: str) -> list[str]:
    """Playable stream URLs from a ``Tune.ashx`` body (pure).

    The resolver returns one URL per line. An error answer begins with
    ``#STATUS:`` (e.g. a bad id) and carries no URLs, so such a body yields an
    empty list. Query strings (jwt/session tokens the CDN itself requires) are
    preserved verbatim -- they are part of the playable URL, not QUILL data.
    """
    urls: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith(("http://", "https://")):
            urls.append(line)
    return urls


# --- network ----------------------------------------------------------------


def _fetch(url: str) -> str:
    """One HTTPS GET of a RadioTime endpoint -- the reviewed egress site.

    HTTPS-only over a verified TLS context, bounded timeout and response size.
    """
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS, context=context) as resp:
            payload: bytes = resp.read(_MAX_BYTES)
    except (urllib.error.URLError, TimeoutError, ssl.SSLError, OSError) as error:
        raise TuneInError(f"Could not reach the TuneIn directory: {error}") from error
    return payload.decode("utf-8", errors="replace")


def search(query: str, *, safe_mode: bool = False) -> list[TuneInResult]:
    """Search the TuneIn directory for *query* (one GET + parse)."""
    refuse_in_safe_mode(safe_mode)
    cleaned = query.strip()
    if not cleaned:
        return []
    params = urllib.parse.urlencode({"query": cleaned, "render": "json", "formats": _FORMATS})
    return parse_directory_results(_fetch(f"{_OPML_BASE}/Search.ashx?{params}"))


def _browse_json_url(target: str) -> str:
    """The JSON Browse.ashx URL for a drill *target* (pure).

    Empty target -> the top-level tree. A full RadioTime URL (a category row's
    own ``browse_url``, e.g. ``.../Browse.ashx?c=music`` or ``?id=r0``) is used
    directly, upgraded to HTTPS with ``render=json`` ensured. Anything else is
    treated as a bare ``c=`` category id.
    """
    value = target.strip()
    if not value:
        return f"{_OPML_BASE}/Browse.ashx?render=json"
    if value.lower().startswith(("http://", "https://")):
        if value.lower().startswith("http://"):
            value = "https://" + value[len("http://") :]
        if "render=json" not in value:
            value += ("&" if "?" in value else "?") + "render=json"
        return value
    return f"{_OPML_BASE}/Browse.ashx?{urllib.parse.urlencode({'c': value, 'render': 'json'})}"


def browse(target: str = "", *, safe_mode: bool = False) -> list[TuneInResult]:
    """Browse one level of the TuneIn tree (one GET).

    An empty *target* returns the top-level tree; otherwise *target* is a
    category row's ``browse_url`` (or a bare ``c=`` id) to drill into. Returns
    that level's direct rows (folders + stations).
    """
    refuse_in_safe_mode(safe_mode)
    return parse_browse_level(_fetch(_browse_json_url(target)))


def resolve_station_streams(guide_id: str, *, safe_mode: bool = False) -> list[str]:
    """Resolve a station *guide_id* to its playable stream URL(s) (one GET).

    Returns an empty list -- never raises for a "no such station" answer --
    when the resolver reports ``#STATUS: 4xx`` or no URLs, so a wrong id
    degrades to "nothing found". Raises :class:`TuneInError` only for a genuine
    network failure or a Safe Mode refusal.
    """
    refuse_in_safe_mode(safe_mode)
    normalized = guide_id.strip()
    if not normalized:
        return []
    params = urllib.parse.urlencode({
        "id": normalized,
        "partnerId": _PARTNER_ID,
        "formats": _FORMATS,
    })
    return parse_tune_response(_fetch(f"{_OPML_BASE}/Tune.ashx?{params}"))


#: TuneIn's own player endpoint, which several engines cannot follow. The host
#: is regionalised (``stream.platform.prod.us-west-2.tunein.com``) but the path
#: is stable, so match on the path rather than the host.
_TUNEIN_REDIRECT_PATH = "tunein.com/listen.stream"


def _stream_rank(url: str) -> tuple[int, int]:
    """Sort key for one Tune.ashx URL (pure). Lower is better.

    Two preferences, most significant first:

    1. **Not TuneIn's own redirect.** ``stream.platform...tunein.com/listen.stream``
       is a player endpoint several engines cannot follow, so a directly-playable
       CDN URL always wins -- even an insecure one, because an http stream that
       plays beats an https URL that does not.
    2. **https over http.** Measured across 40 stations on 2026-08-13, one
       returned an http URL ahead of an https alternative for the same station,
       so first-wins silently chose plaintext where TLS was on offer.

    Everything else keeps TuneIn's own order, which is its stated preference --
    :func:`sorted` is stable, so equal-ranked URLs are never reshuffled.
    """
    lowered = url.lower()
    return (
        1 if _TUNEIN_REDIRECT_PATH in lowered else 0,
        1 if lowered.startswith("http://") else 0,
    )


def _is_hls(lowered_url: str) -> bool:
    """Whether this URL is an HLS manifest rather than a progressive stream.

    Path-only on purpose: a query string can carry ``.m3u8`` as a parameter
    value (TuneIn's own URLs are full of tracking parameters), and matching that
    would demote a perfectly ordinary stream.
    """
    path = lowered_url.split("?", 1)[0]
    return path.endswith((".m3u8", ".m3u")) or "/manifest/" in path


def best_stream(streams: list[str]) -> str:
    """Pick the most broadly-playable URL from a Tune.ashx result (pure).

    Ranked by :func:`_stream_rank` rather than "first that is not the redirect",
    so the choice is a stated preference instead of an accident of ordering.
    When every URL is TuneIn's un-followable redirect the best of those is still
    returned -- a URL we are unsure about beats no URL, and the player's own
    repair ladder (``core/radio/recovery.py``) gets its turn.

    Then one more preference, and the reason it is **host-scoped** is the whole
    point of it (2026-08-14). HLS delivers a short segment window that must be
    topped up every few seconds, so a single failed refresh drains the buffer and
    the stream dies twenty to thirty seconds later -- the fault reported against
    96.5 The Fan, and the same one already fixed for iHeart by preferring its
    progressive stream. The obvious fix is "prefer progressive everywhere", and
    it is wrong: for that very station TuneIn returns an HLS manifest on one CDN
    and an MP3 on a **completely different** one, whose own query string names a
    different station id and a music genre where the station is sports. Choosing
    it might well play somebody a different broadcaster, which is a far worse
    failure than a dropout.

    So progressive wins over HLS **only when both come from the same host**,
    which is a strong signal that they are two forms of one stream rather than
    two streams -- and is exactly the shape of the iHeart case. Where the hosts
    differ, the HLS form is kept and the engine's reconnect options plus
    ``ui/radio/live_reconnect`` do the work instead.
    """
    if not streams:
        return ""
    ranked = sorted(streams, key=_stream_rank)
    best = ranked[0]
    if not _is_hls(best.lower()):
        return best
    host = _host_of(best)
    for candidate in ranked[1:]:
        if _host_of(candidate) == host and not _is_hls(candidate.lower()):
            return candidate
    return best


def _host_of(url: str) -> str:
    """The lowercased host of *url*, or "" when it has none."""
    from urllib.parse import urlsplit

    try:
        return (urlsplit(url).hostname or "").lower()
    except ValueError:
        return ""


def to_radio_station(result: TuneInResult, stream_url: str) -> RadioStation:
    """Build a :class:`RadioStation` from a resolved TuneIn station."""
    return RadioStation(
        name=result.title,
        stream_url=stream_url,
        station_uuid=result.guide_id,
        favicon=result.image,
        tags=(result.subtitle,) if result.subtitle else (),
        source="TuneIn",
    )
