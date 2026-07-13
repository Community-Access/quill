"""iTunes Search API client: podcast discovery for Add Podcast.

Free, keyless, standard choice for podcast discovery (the same one FastPlay
uses). Every request funnels through the single reviewed egress site
(:func:`_http_json` -- see ``quill/tools/network_egress_audit.py``),
HTTPS-only with a verified TLS context, disabled in Safe Mode via
:func:`refuse_in_safe_mode`. wx-free, strict-typed.
"""

from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from quill import __version__
from quill.core.error_codes import CodedError

_USER_AGENT = f"QUILL/{__version__} (https://github.com/Community-Access/quill)"
_BASE_URL = "https://itunes.apple.com/search"
_TIMEOUT_SECONDS = 10.0
_DEFAULT_LIMIT = 25


class ITunesSearchError(CodedError):
    """An iTunes Search request failed (network, or Safe Mode refusal)."""

    code = "QUILL-PODCASTS-ITUNES-SEARCH"


def refuse_in_safe_mode(safe_mode: bool) -> None:
    """Raise :class:`ITunesSearchError` when Safe Mode is active.

    Safe Mode (``QUILL_SAFE_MODE=1``) disables every network service.
    Podcast discovery is a network service, so the UI calls this before
    constructing a request. Kept in core (with the flag passed in) so the
    refusal is unit-testable without wx.
    """
    if safe_mode:
        raise ITunesSearchError(
            "Podcast search is disabled in Safe Mode. "
            "Restart QUILL normally to search for podcasts."
        )


@dataclass(slots=True)
class PodcastSearchResult:
    """One show found via search -- enough to offer a subscribe action."""

    title: str
    feed_url: str
    artist: str = ""
    artwork_url: str = ""
    homepage: str = ""

    @property
    def display_name(self) -> str:
        if self.artist:
            return f"{self.title} — {self.artist}"
        return self.title


def _http_json(url: str) -> object:
    """One HTTPS GET returning decoded JSON -- the reviewed egress site."""
    if not url.startswith("https://"):
        raise ITunesSearchError("Refusing a non-HTTPS iTunes Search request.")
    request = urllib.request.Request(
        url, headers={"User-Agent": _USER_AGENT, "Accept": "application/json"}
    )
    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS, context=context) as resp:
            payload = resp.read().decode("utf-8")
    except (urllib.error.URLError, TimeoutError, ssl.SSLError, OSError) as error:
        raise ITunesSearchError(f"Could not reach the podcast directory: {error}") from error
    try:
        return json.loads(payload) if payload else {}
    except ValueError as error:
        raise ITunesSearchError("The podcast directory returned an unreadable reply.") from error


def _result_from_json(entry: dict[str, object]) -> PodcastSearchResult | None:
    title = str(entry.get("collectionName", "")).strip()
    feed_url = str(entry.get("feedUrl", "")).strip()
    if not title or not feed_url:
        return None
    return PodcastSearchResult(
        title=title,
        feed_url=feed_url,
        artist=str(entry.get("artistName", "")),
        artwork_url=str(entry.get("artworkUrl600") or entry.get("artworkUrl100") or ""),
        homepage=str(entry.get("collectionViewUrl", "")),
    )


def results_from_json(data: object) -> list[PodcastSearchResult]:
    """Parse an iTunes Search API payload (pure; tolerant of junk)."""
    results: list[PodcastSearchResult] = []
    entries = data.get("results") if isinstance(data, dict) else None
    for entry in entries if isinstance(entries, list) else []:
        if not isinstance(entry, dict):
            continue
        result = _result_from_json(entry)
        if result is not None:
            results.append(result)
    return results


def search_podcasts(
    query: str, *, limit: int = _DEFAULT_LIMIT, safe_mode: bool = False
) -> list[PodcastSearchResult]:
    """Shows matching *query* on iTunes' podcast directory."""
    refuse_in_safe_mode(safe_mode)
    if not query.strip():
        return []
    params = {"term": query, "media": "podcast", "limit": max(1, min(limit, 100))}
    url = f"{_BASE_URL}?{urllib.parse.urlencode(params)}"
    return results_from_json(_http_json(url))
