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
    (``s...``); a *category* is a browse link the caller can drill into with
    :func:`browse` using its ``guide_id`` (``c.../g...``).
    """

    guide_id: str
    title: str
    subtitle: str = ""
    image: str = ""
    is_station: bool = False


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


def browse(category: str = "", *, safe_mode: bool = False) -> list[TuneInResult]:
    """Browse the TuneIn category tree, or a category's contents (one GET).

    An empty *category* returns the top-level tree; a category guide id (a
    ``Browse.ashx`` row's ``guide_id``) drills into it.
    """
    refuse_in_safe_mode(safe_mode)
    params: dict[str, str] = {"render": "json"}
    if category.strip():
        params["c"] = category.strip()
    url = f"{_OPML_BASE}/Browse.ashx?{urllib.parse.urlencode(params)}"
    return parse_directory_results(_fetch(url))


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
