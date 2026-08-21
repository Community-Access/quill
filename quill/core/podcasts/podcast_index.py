"""Podcast Index: a second directory, and the one that knows Podcasting 2.0.

Add Podcast has searched iTunes and only iTunes. iTunes is a good default --
free, keyless, and it indexes nearly everything -- but it knows nothing about
the Podcasting 2.0 tags Cast has built a great deal on: chapters documents,
transcripts, soundbites, funding, people. Podcast Index does, because it is the
index those tags were defined for.

**Two directories, not a replacement.** iTunes stays the default and stays
keyless. Podcast Index needs credentials, which most people will never get, and
a feature that only works after somebody registers for an API key is a feature
most people do not have. So the source is a choice, it defaults to the one that
needs nothing, and the other simply does not appear until it can work.

**Credentials never touch a settings file.** They go through the platform
credential store (DPAPI on Windows) exactly like every other secret in QUILL,
and the *absence* of credentials is a missing option with a one-line
explanation -- never an error, and never a dialog somebody has to dismiss.

**The result type is iTunes'.** :class:`~quill.core.podcasts.itunes_search.PodcastSearchResult`
is imported rather than redefined, so the dialog, the merge and every consumer
downstream cannot tell which directory answered. A second result class would be
two things to keep in step for no gain.

Every request funnels through one reviewed egress site, HTTPS-only with a
verified TLS context, and refuses in Safe Mode. wx-free, strict-typed.
"""

from __future__ import annotations

import hashlib
import json
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

from quill import __version__
from quill.core.error_codes import CodedError
from quill.core.net_retry import retry_transient
from quill.core.podcasts.itunes_search import PodcastSearchResult

__all__ = [
    "CREDENTIAL_KEY",
    "CREDENTIAL_KEY_SECRET",
    "PodcastIndexError",
    "auth_headers",
    "merge_results",
    "refuse_in_safe_mode",
    "results_from_json",
    "search_podcasts",
]

_USER_AGENT = f"QUILL/{__version__} (https://github.com/Community-Access/quill)"
_BASE_URL = "https://api.podcastindex.org/api/1.0/search/byterm"
_TIMEOUT_SECONDS = 10.0
_DEFAULT_LIMIT = 25

#: Where the two halves of the credential live in the platform store. Two
#: entries rather than one joined string, so neither can be logged by accident
#: while the other is redacted.
CREDENTIAL_KEY = "quill:podcasts:podcastindex:key"
CREDENTIAL_KEY_SECRET = "quill:podcasts:podcastindex:secret"


class PodcastIndexError(CodedError):
    """A Podcast Index request failed, or was refused."""

    code = "QUILL-PODCASTS-PODCASTINDEX"


def refuse_in_safe_mode(safe_mode: bool) -> None:
    """Raise :class:`PodcastIndexError` when Safe Mode is active."""
    if safe_mode:
        raise PodcastIndexError(
            "Podcast search is disabled in Safe Mode. "
            "Restart QUILL normally to search for podcasts."
        )


def auth_headers(key: str, secret: str, *, now: int | None = None) -> dict[str, str]:
    """The three headers Podcast Index authenticates with.

    ``Authorization`` is the SHA-1 of key + secret + unix-seconds, which is the
    scheme the service publishes. SHA-1 is not a security choice made here: it
    is what the server checks, and the value is a per-request token over a TLS
    connection rather than a stored digest.

    Pure, and *now* is injectable, so the signature can be checked against a
    known vector without a clock.
    """
    stamp = str(int(now if now is not None else time.time()))
    digest = hashlib.sha1(f"{key}{secret}{stamp}".encode()).hexdigest()  # noqa: S324
    return {
        "X-Auth-Key": key,
        "X-Auth-Date": stamp,
        "Authorization": digest,
        "User-Agent": _USER_AGENT,
        "Accept": "application/json",
    }


def _http_json(url: str, headers: dict[str, str]) -> object:
    """One HTTPS GET returning decoded JSON -- the reviewed egress site."""
    if not url.startswith("https://"):
        raise PodcastIndexError("Refusing a non-HTTPS Podcast Index request.")
    request = urllib.request.Request(url, headers=headers)
    context = ssl.create_default_context()

    def _fetch_once() -> str:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS, context=context) as resp:
            decoded: str = resp.read().decode("utf-8")
            return decoded

    try:
        payload = retry_transient(_fetch_once)
    except urllib.error.HTTPError as error:
        if error.code in (401, 403):
            raise PodcastIndexError(
                "Podcast Index did not accept those credentials. Check the key "
                "and secret in Podcast Settings."
            ) from error
        raise PodcastIndexError(f"Could not reach Podcast Index: {error}") from error
    except (urllib.error.URLError, TimeoutError, ssl.SSLError, OSError) as error:
        raise PodcastIndexError(f"Could not reach Podcast Index: {error}") from error
    try:
        return json.loads(payload) if payload else {}
    except ValueError as error:
        raise PodcastIndexError("Podcast Index returned an unreadable reply.") from error


def _result_from_json(entry: dict[str, object]) -> PodcastSearchResult | None:
    title = str(entry.get("title", "")).strip()
    feed_url = str(entry.get("url", "")).strip()
    if not title or not feed_url:
        return None
    return PodcastSearchResult(
        title=title,
        feed_url=feed_url,
        artist=str(entry.get("author") or entry.get("ownerName") or ""),
        artwork_url=str(entry.get("artwork") or entry.get("image") or ""),
        homepage=str(entry.get("link", "")),
        # Podcast Index has its own numeric id, which is not an iTunes
        # collection id and must not be handed to a surface expecting one.
        collection_id="",
    )


def results_from_json(data: object) -> list[PodcastSearchResult]:
    """Parse a Podcast Index payload (pure; tolerant of junk)."""
    results: list[PodcastSearchResult] = []
    entries = data.get("feeds") if isinstance(data, dict) else None
    for entry in entries if isinstance(entries, list) else []:
        if not isinstance(entry, dict):
            continue
        result = _result_from_json(entry)
        if result is not None:
            results.append(result)
    return results


def search_podcasts(
    query: str,
    *,
    key: str,
    secret: str,
    limit: int = _DEFAULT_LIMIT,
    safe_mode: bool = False,
) -> list[PodcastSearchResult]:
    """Shows matching *query* on Podcast Index.

    Raises :class:`PodcastIndexError` with a sentence somebody can act on when
    the credentials are missing, rather than sending an unauthenticated request
    and reporting whatever the server says about it.
    """
    refuse_in_safe_mode(safe_mode)
    if not key or not secret:
        raise PodcastIndexError(
            "Podcast Index needs a key and secret. Add them in Podcast Settings, "
            "or search iTunes instead."
        )
    if not query.strip():
        return []
    params = {"q": query, "max": max(1, min(limit, 100))}
    url = f"{_BASE_URL}?{urllib.parse.urlencode(params)}"
    return results_from_json(_http_json(url, auth_headers(key, secret)))


def merge_results(
    first: list[PodcastSearchResult], second: list[PodcastSearchResult]
) -> list[PodcastSearchResult]:
    """Both directories' answers as one list, de-duplicated by feed address.

    First-seen wins, so the order the caller asked in is the order that decides
    a tie. Feed URLs are compared case-insensitively with a trailing slash
    ignored, because the same feed genuinely appears both ways -- and *not*
    normalised any harder than that: two addresses that differ by more than
    punctuation may really be two feeds, and merging them would hide one.
    """
    merged: list[PodcastSearchResult] = []
    seen: set[str] = set()
    for result in [*first, *second]:
        fingerprint = result.feed_url.strip().rstrip("/").casefold()
        if not fingerprint or fingerprint in seen:
            continue
        seen.add(fingerprint)
        merged.append(result)
    return merged
