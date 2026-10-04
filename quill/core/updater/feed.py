"""The signed release feed, version 2: one list per app (release-channels plan 3).

Each app has one small file on the project site, ``updates/v2/<app>.json``,
beside a detached signature ``<app>.json.sig``. It lists every build the app
has published, which channels list it, the SHA-256 of every file, the data
formats each build writes and reads, and whether a build was withdrawn. The
binaries themselves stay on GitHub Releases; only this list says which channel
a build belongs to, so promoting a build never touches its bytes.

**What the client trusts, in order:**

1. The signature, over the exact bytes (never a re-encoding), against the
   bundled feed keys. There is no unsigned fallback: a missing or bad
   signature is "couldn't check", never "accept".
2. ``sequence`` only goes up. The highest number seen is stored on this
   computer, so an older signed list served again (a replay) is refused.
3. ``expires_at``: a list past its date is treated as "couldn't check", so a
   list frozen in time cannot keep somebody on an old build forever. Lists are
   re-signed at every release with a 90-day expiry
   (:data:`quill.core.updater.feed_publish.EXPIRY_DAYS`).

The last good list is cached beside its signature and re-verified on every
read; that is what an offline check answers from.

Fetching, caching and the sequence high-water mark live in
:mod:`quill.core.updater.feed_fetch`; this module is the data, the parsing,
the signatures and the rollback rule the publisher and the client share.

wx-free and strict-typed, and it never touches the network.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quill.core.error_codes import CodedError
from quill.core.versioning import ReleaseVersion, sort_key

__all__ = [
    "FEED_FORMAT",
    "FEED_KEY_ID",
    "FeedAsset",
    "FeedError",
    "FeedRelease",
    "ReleaseFeed",
    "compute_rollback",
    "with_rollback",
    "parse_feed",
    "trusted_feed_keys",
    "verify_feed_bytes",
]

FEED_FORMAT = "quillville-release-feed/2"
FEED_KEY_ID = "quill-feed-2026"
_KEYS_DIR = Path(__file__).resolve().parents[1]  # quill/core


class FeedError(CodedError):
    """A release list that cannot be used: unsigned, malformed, old or expired."""

    code = "QUILL-UPDATE-FEED-INVALID"


# -- the data ------------------------------------------------------------------


@dataclass(frozen=True)
class FeedAsset:
    kind: str  # "installer" | "portable" | "build-info"
    name: str
    url: str
    size: int
    sha256: str
    authenticode_subject: str = ""

    def to_json(self) -> dict[str, object]:
        data: dict[str, object] = {
            "kind": self.kind,
            "name": self.name,
            "url": self.url,
            "size": self.size,
            "sha256": self.sha256,
        }
        if self.authenticode_subject:
            data["authenticode_subject"] = self.authenticode_subject
        return data


@dataclass(frozen=True)
class FeedRelease:
    version: str
    tag: str
    channels: tuple[str, ...]
    assets: tuple[FeedAsset, ...] = ()
    history: tuple[Mapping[str, str], ...] = ()
    published_at: str = ""
    notes_url: str = ""
    notes_summary: str = ""
    runtime: Mapping[str, str] = field(default_factory=dict)
    carries: Mapping[str, str] = field(default_factory=dict)
    data_formats: Mapping[str, int] = field(default_factory=dict)
    reads_formats: Mapping[str, int] = field(default_factory=dict)
    #: Per format this build writes: the oldest version whose readers can read
    #: it losing only new fields (QUILL Lite's settings). Absent: no promise.
    lossy_formats: Mapping[str, int] = field(default_factory=dict)
    can_roll_back_to: tuple[str, ...] = ()
    min_safe_downgrade: str = ""
    min_upgrade_from: str = ""
    revoked: bool = False
    revoked_reason: str = ""
    replacement: str = ""
    advisories: tuple[Mapping[str, Any], ...] = ()

    @property
    def parsed(self) -> ReleaseVersion | None:
        return ReleaseVersion.try_parse(self.version)

    @property
    def is_final(self) -> bool:
        parsed = self.parsed
        return parsed is not None and parsed.stage == "final"

    def listed_on(self, channel: str) -> bool:
        return channel in self.channels

    def asset(self, kind: str) -> FeedAsset | None:
        return next((a for a in self.assets if a.kind == kind), None)

    def first_listed(self, channel: str) -> datetime | None:
        """When this build was first listed on *channel* (from its history)."""
        moments = [
            _parse_time(str(entry.get("at", "")))
            for entry in self.history
            if entry.get("channel") == channel
        ]
        found = [m for m in moments if m is not None]
        return min(found) if found else None

    def to_json(self) -> dict[str, object]:
        return {
            "version": self.version,
            "tag": self.tag,
            "channels": list(self.channels),
            "history": [dict(entry) for entry in self.history],
            "published_at": self.published_at,
            "notes_url": self.notes_url,
            "notes_summary": self.notes_summary,
            "assets": [asset.to_json() for asset in self.assets],
            "runtime": dict(self.runtime),
            "carries": dict(self.carries),
            "data_formats": dict(self.data_formats),
            "reads_formats": dict(self.reads_formats),
            "lossy_formats": dict(self.lossy_formats),
            "can_roll_back_to": list(self.can_roll_back_to),
            "min_safe_downgrade": self.min_safe_downgrade,
            "min_upgrade_from": self.min_upgrade_from,
            "revoked": self.revoked,
            "revoked_reason": self.revoked_reason,
            "replacement": self.replacement,
            "advisories": [dict(item) for item in self.advisories],
        }


@dataclass(frozen=True)
class ReleaseFeed:
    app: str
    app_name: str
    sequence: int
    generated_at: str
    expires_at: str
    releases: tuple[FeedRelease, ...] = ()
    security_floor: str = ""

    def release(self, version: str) -> FeedRelease | None:
        wanted = sort_key(version)
        return next((r for r in self.releases if sort_key(r.version) == wanted), None)

    def for_channel(self, channel: str) -> list[FeedRelease]:
        """Every build *channel* lists that has not been withdrawn, newest first."""
        listed = [r for r in self.releases if r.listed_on(channel) and not r.revoked]
        return sorted(listed, key=lambda r: sort_key(r.version), reverse=True)

    def current(self, channel: str) -> FeedRelease | None:
        listed = self.for_channel(channel)
        return listed[0] if listed else None

    def channels(self) -> dict[str, dict[str, str]]:
        """The ``channels`` block: each channel's newest build."""
        result: dict[str, dict[str, str]] = {}
        for channel in ("stable", "beta", "dev"):
            newest = self.current(channel)
            if newest is not None:
                result[channel] = {"current": newest.version}
        return result

    def expires(self) -> datetime | None:
        return _parse_time(self.expires_at)

    def is_expired(self, now: datetime | None = None) -> bool:
        moment = self.expires()
        return moment is None or (now or datetime.now(UTC)) >= moment

    def days_left(self, now: datetime | None = None) -> float:
        moment = self.expires()
        if moment is None:
            return 0.0
        return (moment - (now or datetime.now(UTC))).total_seconds() / 86400

    def to_json(self) -> dict[str, object]:
        ordered = sorted(self.releases, key=lambda r: sort_key(r.version), reverse=True)
        return {
            "format": FEED_FORMAT,
            "app": self.app,
            "app_name": self.app_name,
            "sequence": self.sequence,
            "generated_at": self.generated_at,
            "expires_at": self.expires_at,
            "security_floor": self.security_floor,
            "channels": self.channels(),
            "releases": [r.to_json() for r in ordered],
        }

    def to_bytes(self) -> bytes:
        """The exact bytes that are signed and published (LF, UTF-8, sorted)."""
        return (json.dumps(self.to_json(), indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _parse_time(text: str) -> datetime | None:
    if not text:
        return None
    try:
        moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=UTC)


def _str_map(raw: object) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    return {str(k): str(v) for k, v in raw.items()}


def _int_map(raw: object) -> dict[str, int]:
    if not isinstance(raw, dict):
        return {}
    result: dict[str, int] = {}
    for key, value in raw.items():
        try:
            result[str(key)] = int(value)
        except (TypeError, ValueError):
            raise FeedError(f"format {key!r} has a version that is not a number") from None
    return result


def _asset(raw: object) -> FeedAsset:
    if not isinstance(raw, dict):
        raise FeedError("an asset is not an object")
    sha = str(raw.get("sha256") or "").strip().lower()
    if len(sha) != 64 or any(ch not in "0123456789abcdef" for ch in sha):
        raise FeedError(f"asset {raw.get('name')!r} has no valid SHA-256")
    try:
        size = int(raw.get("size", 0))
    except (TypeError, ValueError):
        raise FeedError(f"asset {raw.get('name')!r} has no valid size") from None
    url = str(raw.get("url") or "")
    if not url.startswith("https://"):
        raise FeedError(f"asset {raw.get('name')!r} is not served over HTTPS")
    return FeedAsset(
        kind=str(raw.get("kind") or ""),
        name=str(raw.get("name") or ""),
        url=url,
        size=size,
        sha256=sha,
        authenticode_subject=str(raw.get("authenticode_subject") or ""),
    )


def _release(raw: object) -> FeedRelease:
    if not isinstance(raw, dict):
        raise FeedError("a release is not an object")
    version = str(raw.get("version") or "")
    if ReleaseVersion.try_parse(version) is None:
        raise FeedError(f"release version {version!r} cannot be read")
    channels = raw.get("channels", [])
    if not isinstance(channels, list):
        raise FeedError(f"release {version} has no channel list")
    history = raw.get("history", [])
    advisories = raw.get("advisories", [])
    return FeedRelease(
        version=version,
        tag=str(raw.get("tag") or ""),
        channels=tuple(str(c) for c in channels if c in ("stable", "beta", "dev")),
        assets=tuple(_asset(a) for a in raw.get("assets", []) or []),
        history=tuple(_str_map(h) for h in history if isinstance(h, dict))
        if isinstance(history, list)
        else (),
        published_at=str(raw.get("published_at") or ""),
        notes_url=str(raw.get("notes_url") or ""),
        notes_summary=str(raw.get("notes_summary") or ""),
        runtime=_str_map(raw.get("runtime")),
        carries=_str_map(raw.get("carries")),
        data_formats=_int_map(raw.get("data_formats")),
        reads_formats=_int_map(raw.get("reads_formats")),
        lossy_formats=_int_map(raw.get("lossy_formats")),
        can_roll_back_to=tuple(str(v) for v in raw.get("can_roll_back_to", []) or []),
        min_safe_downgrade=str(raw.get("min_safe_downgrade") or ""),
        min_upgrade_from=str(raw.get("min_upgrade_from") or ""),
        revoked=bool(raw.get("revoked", False)),
        revoked_reason=str(raw.get("revoked_reason") or ""),
        replacement=str(raw.get("replacement") or ""),
        advisories=tuple(a for a in advisories if isinstance(a, dict))
        if isinstance(advisories, list)
        else (),
    )


def parse_feed(data: bytes, *, app_key: str = "") -> ReleaseFeed:
    """Read a feed's JSON (already signature-checked). Raises :class:`FeedError`."""
    try:
        raw = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as error:
        raise FeedError(f"the release list is not readable JSON: {error}") from error
    if not isinstance(raw, dict) or raw.get("format") != FEED_FORMAT:
        raise FeedError("the release list is not a version 2 QuillVille feed")
    app = str(raw.get("app") or "")
    if app_key and app != app_key:
        raise FeedError(f"the release list is for {app!r}, not {app_key!r}")
    try:
        sequence = int(raw.get("sequence", -1))
    except (TypeError, ValueError):
        raise FeedError("the release list has no sequence number") from None
    if sequence < 0:
        raise FeedError("the release list has no sequence number")
    releases = raw.get("releases", [])
    if not isinstance(releases, list):
        raise FeedError("the release list has no releases")
    return ReleaseFeed(
        app=app,
        app_name=str(raw.get("app_name") or app),
        sequence=sequence,
        generated_at=str(raw.get("generated_at") or ""),
        expires_at=str(raw.get("expires_at") or ""),
        security_floor=str(raw.get("security_floor") or ""),
        releases=tuple(_release(r) for r in releases),
    )


# -- signatures ------------------------------------------------------------------


def trusted_feed_keys(folder: Path | None = None) -> list[bytes]:
    """Every feed key this build trusts.

    ``feed-pub.keys`` (one base64 key per line, ``#`` comments) when present,
    so a key rotation can be double-signed for one release; otherwise the
    single bundled ``feed-pub.key`` that v1 already uses.
    """
    base = folder or _KEYS_DIR
    keys: list[bytes] = []
    for name in ("feed-pub.keys", "feed-pub.key"):
        try:
            text = (base / name).read_text(encoding="utf-8")
        except OSError:
            continue
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                raw = base64.b64decode(line, validate=True)
            except ValueError:
                continue
            if len(raw) == 32 and raw not in keys:
                keys.append(raw)
        if keys:
            break
    return keys


def _signatures(sig_text: str) -> list[bytes]:
    """Every ``sig:`` line in a minisign-shaped sidecar (two during a rotation)."""
    found: list[bytes] = []
    for line in sig_text.splitlines():
        if line.startswith("sig:"):
            try:
                raw = base64.b64decode(line.split(":", 1)[1].strip(), validate=True)
            except ValueError:
                continue
            if len(raw) == 64:
                found.append(raw)
    return found


def verify_feed_bytes(data: bytes, sig_text: str, keys: Sequence[bytes] | None = None) -> bool:
    """True when any signature in *sig_text* verifies *data* under any trusted key.

    Fail-closed: no PyNaCl, no keys, or no signature is ``False``.
    """
    try:
        from nacl.exceptions import BadSignatureError
        from nacl.signing import VerifyKey
    except Exception:  # noqa: BLE001 - cannot verify means do not accept
        return False
    trusted = list(keys) if keys is not None else trusted_feed_keys()
    for signature in _signatures(sig_text):
        for key in trusted:
            try:
                VerifyKey(key).verify(data, signature)
            except (BadSignatureError, ValueError, TypeError):
                continue
            return True
    return False


# -- rollback targets (shared by the publisher and the client) ---------------------


def compute_rollback(feed: ReleaseFeed, release: FeedRelease) -> tuple[tuple[str, ...], str]:
    """``(can_roll_back_to, min_safe_downgrade)`` for *release* (plan 5.2).

    The older Stable builds that can read every format *release* writes, at
    or above the security floor, never a withdrawn one. Oldest is the minimum.
    """
    mine = sort_key(release.version)
    floor = sort_key(feed.security_floor) if feed.security_floor else None
    targets = []
    for other in feed.releases:
        if other.revoked or "stable" not in other.channels:
            continue
        key = sort_key(other.version)
        if key >= mine or (floor is not None and key < floor):
            continue
        if all(other.reads_formats.get(f, 0) >= v for f, v in release.data_formats.items()):
            targets.append(other)
    targets.sort(key=lambda r: sort_key(r.version), reverse=True)
    versions = tuple(r.version for r in targets)
    return versions, (versions[-1] if versions else "")


def with_rollback(feed: ReleaseFeed) -> ReleaseFeed:
    """*feed* with every release's rollback fields recomputed."""
    releases = tuple(
        replace(r, can_roll_back_to=can, min_safe_downgrade=low)
        for r in feed.releases
        for can, low in (compute_rollback(feed, r),)
    )
    return replace(feed, releases=releases)
