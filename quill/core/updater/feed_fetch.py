"""Fetching the signed v2 release list, and what this computer remembers of it.

The client half of :mod:`quill.core.updater.feed` (release-channels plan 3.4):

* :func:`fetch_feed` -- fetch ``<app>.json`` and its ``.sig``, verify the
  signature over the exact bytes, refuse a ``sequence`` lower than the highest
  one seen here (a replay), treat a list past ``expires_at`` as "couldn't
  check", and keep the last good list for offline answers.
* :func:`releases_for_check` -- what every app's update check chooses from: the
  signed list, or -- only when the server has *no* list for the app yet (HTTP
  404) -- the old GitHub path, today's behaviour rather than a weaker one. A
  list that exists but cannot be trusted is "couldn't check", never a fallback.
* :class:`FeedOffer` -- a listed build shaped like ``updates.GitHubRelease``, so
  it travels through the existing update dialog, download and installer helper
  unchanged, carrying the SHA-256 from the signed list.

wx-free and strict-typed. The only network call is :func:`http_get`, and every
caller can pass its own ``get`` (tests always do).
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from quill.core.error_codes import CodedError
from quill.core.updater.feed import FeedError, ReleaseFeed, parse_feed, verify_feed_bytes

__all__ = [
    "DEFAULT_FEED_BASE",
    "FeedCheckFailed",
    "FeedMissing",
    "FeedOffer",
    "FeedResult",
    "cached_feed",
    "feed_base",
    "fetch_feed",
    "http_get",
    "offers_from_feed",
    "releases_for_check",
]

DEFAULT_FEED_BASE = "https://community-access.github.io/quill/updates/v2/"
_BASE_ENV = "QUILL_UPDATE_FEED_BASE"
_USER_AGENT = "QuillVille-Updater/2"

Status = Literal["ok", "offline", "missing", "stale", "invalid", "unreachable"]


class FeedCheckFailed(CodedError):
    """An update check that could not get a trustworthy list; the text says why."""

    code = "QUILL-UPDATE-FEED-CHECK-FAILED"


class FeedMissing(CodedError):
    """The server has no v2 list for this app (HTTP 404)."""

    code = "QUILL-UPDATE-FEED-MISSING"


# -- where the lists live, and what this computer remembers ----------------------


def feed_base() -> str:
    """The folder URL the lists are read from; ``QUILL_UPDATE_FEED_BASE`` for rehearsals.

    The override only changes *where to look*: HTTPS, the trusted hosts and
    the signature all still apply.
    """
    override = os.environ.get(_BASE_ENV, "").strip()
    base = override or DEFAULT_FEED_BASE
    return base if base.endswith("/") else base + "/"


def _state_dir() -> Path:
    from quill.core.updater.channels import family_dir

    return family_dir() / "updates"


def _high_water(state_dir: Path, app_key: str) -> int:
    try:
        raw = json.loads((state_dir / "feed-state.json").read_text(encoding="utf-8"))
        return int(raw.get("apps", {}).get(app_key, {}).get("sequence", 0))
    except (OSError, ValueError, TypeError, AttributeError):
        return 0


def _remember(state_dir: Path, app_key: str, sequence: int, data: bytes, sig: str) -> None:
    from quill.core.storage import write_json_atomic

    try:
        path = state_dir / "feed-state.json"
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raw = {}
        except (OSError, ValueError):
            raw = {}
        found = raw.get("apps")
        apps: dict[str, object] = dict(found) if isinstance(found, dict) else {}
        apps[app_key] = {"sequence": max(sequence, _high_water(state_dir, app_key))}
        raw["version"] = 1
        raw["apps"] = apps
        state_dir.mkdir(parents=True, exist_ok=True)
        write_json_atomic(path, raw)
        cache = state_dir / "feed-cache"
        cache.mkdir(parents=True, exist_ok=True)
        (cache / f"{app_key}.json").write_bytes(data)
        (cache / f"{app_key}.json.sig").write_text(sig, encoding="utf-8", newline="\n")
    except OSError:
        return


def _cached(state_dir: Path, app_key: str) -> tuple[bytes, str] | None:
    cache = state_dir / "feed-cache"
    try:
        return (cache / f"{app_key}.json").read_bytes(), (cache / f"{app_key}.json.sig").read_text(
            encoding="utf-8"
        )
    except OSError:
        return None


# -- fetching --------------------------------------------------------------------


Getter = Callable[[str], bytes]


def http_get(url: str, timeout: int = 15) -> bytes:
    """One plain HTTPS GET: no query string, no cookies, a generic User-Agent.

    Raises :class:`FeedMissing` on 404 and ``OSError`` for anything else that
    stops it, so the caller can tell "not published" from "not reachable".
    """
    from urllib.error import HTTPError
    from urllib.request import Request, urlopen

    from quill.core.updates import _ssl_context, _validate_remote_url

    _validate_remote_url(url)
    request = Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urlopen(request, timeout=timeout, context=_ssl_context()) as response:
            return bytes(response.read(4 * 1024 * 1024))
    except HTTPError as error:
        if error.code == 404:
            raise FeedMissing(url) from error
        raise OSError(f"the update server answered {error.code}") from error


@dataclass(frozen=True)
class FeedResult:
    status: Status
    feed: ReleaseFeed | None = None
    #: One plain sentence when the status is not ``ok``.
    reason: str = ""

    @property
    def usable(self) -> bool:
        return self.feed is not None and self.status in ("ok", "offline")


def _check(
    data: bytes,
    sig: str,
    app_key: str,
    *,
    keys: Sequence[bytes] | None,
    floor: int,
) -> ReleaseFeed:
    if not verify_feed_bytes(data, sig, keys):
        raise FeedError("the list of versions was not signed by us, so it was not used")
    feed = parse_feed(data, app_key=app_key)
    if feed.sequence < floor:
        raise FeedError(
            "the list of versions is older than one this computer has already seen, "
            "so it was not used"
        )
    return feed


def fetch_feed(
    app_key: str,
    *,
    get: Getter | None = None,
    keys: Sequence[bytes] | None = None,
    state_dir: Path | None = None,
    now: datetime | None = None,
) -> FeedResult:
    """Fetch, verify and remember *app_key*'s list. Never raises."""
    getter = get or http_get
    folder = state_dir or _state_dir()
    moment = now or datetime.now(UTC)
    floor = _high_water(folder, app_key)
    url = f"{feed_base()}{app_key}.json"
    try:
        data = getter(url)
        sig = getter(url + ".sig").decode("utf-8", "replace")
    except FeedMissing:
        return FeedResult("missing", reason="no version 2 list has been published yet")
    except (OSError, ValueError) as error:
        cached = _cached(folder, app_key)
        if cached is not None:
            try:
                feed = _check(*cached, app_key, keys=keys, floor=0)
            except FeedError:
                feed = None
            if feed is not None and not feed.is_expired(moment):
                return FeedResult("offline", feed, "couldn't reach the update server just now")
        return FeedResult("unreachable", reason=f"couldn't reach the update server ({error})")
    try:
        feed = _check(data, sig, app_key, keys=keys, floor=floor)
    except FeedError as error:
        return FeedResult("invalid", reason=str(error))
    if feed.is_expired(moment):
        return FeedResult(
            "stale",
            feed,
            "the list of versions on the server is out of date, so nothing was offered",
        )
    _remember(folder, app_key, feed.sequence, data, sig)
    return FeedResult("ok", feed)


# -- what the apps' existing update flows consume ----------------------------------


@dataclass(frozen=True)
class FeedOffer:
    """A feed build shaped like ``updates.GitHubRelease``, plus its channels.

    The download, the update dialog and the installer helper read only
    ``version``, ``download_url``, ``notes``, ``published_at``, ``prerelease``
    and ``download_digest``, so a feed build travels through every app's
    existing flow unchanged -- with the hash from the *signed list*, not from
    GitHub.
    """

    version: str
    download_url: str
    published_at: str
    notes: str
    prerelease: bool
    channels: tuple[str, ...]
    download_digest: str
    size: int = 0
    tag: str = ""
    has_platform_asset: bool = True
    revoked: bool = False


def offers_from_feed(feed: ReleaseFeed, *, portable: bool) -> list[FeedOffer]:
    """Every listed, not-withdrawn build with a file this copy can install."""
    wanted = "portable" if portable else "installer"
    offers: list[FeedOffer] = []
    for release in feed.releases:
        if release.revoked or not release.channels:
            continue
        asset = release.asset(wanted)
        if asset is None:
            continue
        offers.append(
            FeedOffer(
                version=release.version,
                download_url=asset.url,
                published_at=release.published_at,
                notes=release.notes_summary,
                prerelease="stable" not in release.channels,
                channels=release.channels,
                download_digest=asset.sha256,
                size=asset.size,
                tag=release.tag,
            )
        )
    return offers


def releases_for_check(
    app_key: str,
    legacy: Callable[[], Iterable[Any]],
    *,
    portable: bool,
    get: Getter | None = None,
    state_dir: Path | None = None,
    keys: Sequence[bytes] | None = None,
) -> list[Any]:
    """The builds an update check chooses from: the signed list, else the old path.

    Raises :class:`FeedCheckFailed` when a list exists but cannot be trusted
    or reached -- never falls back to unsigned data in that case.
    """
    result = fetch_feed(app_key, get=get, state_dir=state_dir, keys=keys)
    if result.status == "missing":
        return list(legacy())
    if result.usable and result.feed is not None:
        return list(offers_from_feed(result.feed, portable=portable))
    raise FeedCheckFailed(result.reason or "the list of versions could not be checked")


def cached_feed(
    app_key: str,
    *,
    state_dir: Path | None = None,
    keys: Sequence[bytes] | None = None,
    now: datetime | None = None,
) -> ReleaseFeed | None:
    """The last good list, re-verified, with no network -- for windows that must
    not wait on one (the Release Channel window). ``None`` when there is none,
    it does not verify, or it has expired."""
    cached = _cached(state_dir or _state_dir(), app_key)
    if cached is None:
        return None
    try:
        feed = _check(*cached, app_key, keys=keys, floor=0)
    except FeedError:
        return None
    return None if feed.is_expired(now) else feed
