"""The publisher's side of the signed release feed (release-channels plan 4).

Pure functions over :class:`~quill.core.updater.feed.ReleaseFeed` that
``scripts/publish_release.py``, ``scripts/promote_release.py`` and
``scripts/feed_tool.py`` share, so every rule is tested once without a network:

* :func:`list_release` -- a build's first listing, on Beta or Dev.
* :func:`promotion_checks` and :func:`promote` -- Dev to Beta, Beta to Stable,
  never touching the bytes. Stable takes **only final-numbered builds that were
  on Beta first**, after **at least 7 days** there; a shorter stay needs a
  written reason, which is recorded in the build's history.
* :func:`revoke` -- withdraw a build without deleting its files.
* :func:`refresh` -- every change bumps ``sequence`` and sets a fresh
  **90-day** ``expires_at``. The signing key stays on the owner's computer, so
  there is no scheduled re-signing: a feed is refreshed whenever a release is
  published or promoted, and :func:`expiry_warnings` speaks up 14 days ahead.
* :func:`page_budget_problems` -- installed Quill Radio 3.0.4 and QUILL Lite
  1.1.2 read only the first 30 GitHub releases, so the main repository may not
  hold more than 20 releases newer than any app's newest Stable one.
* :func:`sign_bytes` -- the minisign-shaped sidecar over the exact bytes.

wx-free and strict-typed.
"""

from __future__ import annotations

import base64
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta

from quill.core.updater.feed import (
    FEED_KEY_ID,
    FeedAsset,
    FeedRelease,
    ReleaseFeed,
    compute_rollback,
    with_rollback,
)
from quill.core.versioning import ReleaseVersion, sort_key

__all__ = [
    "BETA_SOAK_DAYS",
    "DEV_SOAK_DAYS",
    "EXPIRY_DAYS",
    "PAGE_BUDGET",
    "WARN_DAYS",
    "Check",
    "ListedRelease",
    "blocking",
    "expiry_warnings",
    "formats_for_build",
    "list_release",
    "load_seed",
    "new_feed",
    "page_budget_problems",
    "promote",
    "promotion_checks",
    "refresh",
    "revoke",
    "sign_bytes",
    "superseded_prereleases",
    "validate_feed",
]

EXPIRY_DAYS = 90
WARN_DAYS = 14
BETA_SOAK_DAYS = 7
DEV_SOAK_DAYS = 1
PAGE_BUDGET = 20


def _iso(moment: datetime) -> str:
    return moment.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def new_feed(app: str, app_name: str) -> ReleaseFeed:
    return ReleaseFeed(app=app, app_name=app_name, sequence=0, generated_at="", expires_at="")


def refresh(feed: ReleaseFeed, now: datetime) -> ReleaseFeed:
    """Bump the sequence, stamp the time, set a fresh expiry, recompute rollbacks."""
    return with_rollback(
        replace(
            feed,
            sequence=feed.sequence + 1,
            generated_at=_iso(now),
            expires_at=_iso(now + timedelta(days=EXPIRY_DAYS)),
        )
    )


def formats_for_build(app_key: str) -> tuple[dict[str, int], dict[str, int], dict[str, int]]:
    """``(data_formats, reads_formats, lossy_formats)`` from this source tree."""
    from quill.core.data_formats import formats_for

    writes: dict[str, int] = {}
    reads: dict[str, int] = {}
    lossy: dict[str, int] = {}
    for fmt in formats_for(app_key):
        writes[fmt.id] = fmt.current
        reads[fmt.id] = fmt.reads_up_to
        if fmt.readable_with_losses_from:
            lossy[fmt.id] = fmt.readable_with_losses_from
    return writes, reads, lossy


def list_release(
    feed: ReleaseFeed,
    *,
    version: str,
    tag: str,
    channel: str,
    assets: Sequence[FeedAsset],
    now: datetime,
    notes_url: str = "",
    notes_summary: str = "",
    data_formats: Mapping[str, int] | None = None,
    reads_formats: Mapping[str, int] | None = None,
    lossy_formats: Mapping[str, int] | None = None,
    carries: Mapping[str, str] | None = None,
    runtime: Mapping[str, str] | None = None,
) -> ReleaseFeed:
    """*feed* with a new build listed on *channel* (``beta`` or ``dev``) only.

    Raises ``ValueError`` for a channel other than Beta or Dev (Stable is
    reached only by :func:`promote`), or a version already listed.
    """
    if channel not in ("beta", "dev"):
        raise ValueError("a new build is listed on Beta or Dev first, never straight on Stable")
    if ReleaseVersion.try_parse(version) is None:
        raise ValueError(f"{version!r} is not a version")
    if feed.release(version) is not None:
        raise ValueError(f"{version} is already in the {feed.app} list")
    stamp = _iso(now)
    entry = FeedRelease(
        version=version,
        tag=tag,
        channels=(channel,),
        assets=tuple(assets),
        history=({"channel": channel, "at": stamp, "by": "publish_release.py"},),
        published_at=stamp,
        notes_url=notes_url,
        notes_summary=notes_summary[:4000],
        runtime=dict(runtime or {}),
        carries=dict(carries or {}),
        data_formats=dict(data_formats or {}),
        reads_formats=dict(reads_formats or {}),
        lossy_formats=dict(lossy_formats or {}),
    )
    return refresh(replace(feed, releases=(*feed.releases, entry)), now)


def superseded_prereleases(feed: ReleaseFeed, channel: str) -> list[FeedRelease]:
    """Older builds listed only on *channel* (not Stable), now behind a newer one."""
    newest = feed.current(channel)
    if newest is None:
        return []
    return [
        r
        for r in feed.releases
        if r.channels == (channel,) and sort_key(r.version) < sort_key(newest.version)
    ]


# -- promotion ---------------------------------------------------------------------


@dataclass(frozen=True)
class Check:
    id: str
    title: str
    passed: bool
    detail: str = ""
    #: A warning is reported but does not stop the promotion.
    warning: bool = False

    def line(self) -> str:
        mark = "PASS" if self.passed else ("WARN" if self.warning else "FAIL")
        return f"{mark} {self.id} {self.title}" + (f": {self.detail}" if self.detail else "")


def promotion_checks(
    feed: ReleaseFeed,
    version: str,
    to: str,
    *,
    now: datetime,
    skip_soak_reason: str = "",
    sibling_feeds: Mapping[str, ReleaseFeed] | None = None,
) -> list[Check]:
    """The feed-level checks (P3, P4, P7, P10, P11 and the listing rules).

    The checks that need GitHub, the files or the docs (P1, P2, P5, P6, P8,
    P9, P12, P13) are run by ``scripts/promote_release.py`` around these.
    """
    checks: list[Check] = []
    release = feed.release(version)
    if release is None:
        # Promotion moves one build, never "whichever build of 3.2.0": name it.
        wanted = ReleaseVersion.try_parse(version)
        builds = [
            r.version
            for r in feed.releases
            if wanted is not None
            and (found := ReleaseVersion.try_parse(r.version)) is not None
            and found.same_number(wanted)
        ]
        detail = f"{version} is not listed"
        if builds:
            detail += "; name the build to promote: " + ", ".join(sorted(builds, key=sort_key))
        return [Check("P1", "the build is in the list", False, detail)]
    checks.append(Check("P1", "the build is listed and not withdrawn", not release.revoked))
    checks.append(Check("P3", "the list's sequence will increase", True, str(feed.sequence + 1)))
    if to not in ("beta", "stable"):
        checks.append(Check("P0", "promote to Beta or Stable", False, f"not {to!r}"))
        return checks
    already = release.listed_on(to)
    checks.append(Check("P0", f"not already on {to}", not already))
    if to == "stable":
        checks.append(
            Check(
                "P4",
                "Stable takes only a final-numbered build",
                release.is_final,
                "" if release.is_final else f"{version} is a pre-release number",
            )
        )
        checks.append(
            Check(
                "P4b",
                "the build was on Beta first",
                release.listed_on("beta"),
                "" if release.listed_on("beta") else "promote it to Beta and let it soak first",
            )
        )
    soak_channel = "beta" if to == "stable" else "dev"
    soak_days = BETA_SOAK_DAYS if to == "stable" else DEV_SOAK_DAYS
    since = release.first_listed(soak_channel)
    if since is None and to == "beta":
        checks.append(Check("P10", "time on Dev", True, "first listed straight on Beta"))
    else:
        days = (now - since).total_seconds() / 86400 if since is not None else 0.0
        enough = days >= soak_days
        reason = skip_soak_reason.strip()
        detail = f"{days:.1f} of {soak_days} days on {soak_channel.capitalize()}"
        if not enough and reason:
            detail += f"; shortened with the reason: {reason}"
        checks.append(Check("P10", "time on the earlier channel", enough or bool(reason), detail))
    checks.extend(_sibling_checks(release, to, sibling_feeds or {}))
    if to == "stable":
        checks.append(_format_warning(feed, release))
    return checks


def _sibling_checks(
    release: FeedRelease, to: str, sibling_feeds: Mapping[str, ReleaseFeed]
) -> list[Check]:
    problems = []
    for app, carried in sorted(release.carries.items()):
        sibling = sibling_feeds.get(app)
        if sibling is None:
            continue
        newest = sibling.current("stable") if to == "stable" else _newest_beta_or_stable(sibling)
        if newest is None or sort_key(carried) > sort_key(newest.version):
            shown = newest.version if newest else "nothing"
            problems.append(f"carries {app} {carried}, ahead of its {to} {shown}")
    return [
        Check(
            "P7",
            "every app this build carries is not ahead of its own channel",
            not problems,
            "; ".join(problems),
        )
    ]


def _newest_beta_or_stable(feed: ReleaseFeed) -> FeedRelease | None:
    both = [*feed.for_channel("beta"), *feed.for_channel("stable")]
    return max(both, key=lambda r: sort_key(r.version), default=None)


def _format_warning(feed: ReleaseFeed, release: FeedRelease) -> Check:
    previous = feed.current("stable")
    if previous is None:
        return Check("P11", "data formats", True, "first Stable build")
    moved = [
        f"{f} {previous.reads_formats.get(f, 0)} -> {v}"
        for f, v in sorted(release.data_formats.items())
        if previous.reads_formats.get(f, 0) < v
    ]
    if not moved:
        return Check("P11", "data formats", True, f"{previous.version} can read everything")
    return Check(
        "P11",
        f"going back to {previous.version} will need a saved copy",
        False,
        ", ".join(moved),
        warning=True,
    )


def blocking(checks: Iterable[Check]) -> list[Check]:
    return [c for c in checks if not c.passed and not c.warning]


def promote(
    feed: ReleaseFeed,
    version: str,
    to: str,
    *,
    now: datetime,
    by: str = "promote_release.py",
    skip_soak_reason: str = "",
    notes_summary: str = "",
) -> ReleaseFeed:
    """*feed* with *version* also listed on *to*. Run :func:`promotion_checks` first."""
    release = feed.release(version)
    if release is None:
        raise ValueError(f"{version} is not in the list")
    entry: dict[str, str] = {"channel": to, "at": _iso(now), "by": by}
    if skip_soak_reason.strip():
        entry["reason"] = skip_soak_reason.strip()
    channels = tuple(c for c in ("stable", "beta", "dev") if c in (*release.channels, to))
    updated = replace(
        release,
        channels=channels,
        history=(*release.history, entry),
        notes_summary=notes_summary[:4000] if notes_summary else release.notes_summary,
    )
    releases = tuple(updated if r is release else r for r in feed.releases)
    return refresh(replace(feed, releases=releases), now)


def revoke(
    feed: ReleaseFeed, version: str, *, reason: str, replacement: str = "", now: datetime
) -> ReleaseFeed:
    release = feed.release(version)
    if release is None:
        raise ValueError(f"{version} is not in the list")
    updated = replace(release, revoked=True, revoked_reason=reason, replacement=replacement)
    releases = tuple(updated if r is release else r for r in feed.releases)
    return refresh(replace(feed, releases=releases), now)


# -- gates -------------------------------------------------------------------------


def validate_feed(feed: ReleaseFeed) -> list[str]:
    """Everything wrong with a published feed (GATE-FEED); empty when sound."""
    problems: list[str] = []
    for release in feed.releases:
        if "stable" in release.channels and not release.is_final:
            problems.append(f"{release.version} is on Stable with a pre-release number")
        expected = compute_rollback(feed, release)
        if (release.can_roll_back_to, release.min_safe_downgrade) != expected:
            problems.append(f"{release.version}'s rollback fields are out of date")
        for asset in release.assets:
            if asset.size <= 0:
                problems.append(f"{release.version}: {asset.name} has no size")
    if feed.releases and not feed.expires_at:
        problems.append("the list has no expiry date")
    return problems


def expiry_warnings(
    feeds: Iterable[ReleaseFeed], *, now: datetime, days: int = WARN_DAYS
) -> list[str]:
    """One sentence per feed that expires within *days* (or already has)."""
    warnings = []
    for feed in feeds:
        left = feed.days_left(now)
        if left <= 0:
            warnings.append(
                f"The {feed.app_name} update list expired on {feed.expires_at}. Copies on "
                f"every channel now say they couldn't check. Publish or re-sign it now."
            )
        elif left <= days:
            warnings.append(
                f"The {feed.app_name} update list expires in {int(left)} days "
                f"({feed.expires_at}). Re-sign it with scripts/feed_tool.py refresh, or "
                f"publish a release, before then."
            )
    return warnings


@dataclass(frozen=True)
class ListedRelease:
    """One release on the main repository's default GitHub listing."""

    tag: str
    version: str
    app: str
    prerelease: bool
    created_at: str


def page_budget_problems(
    listing: Sequence[ListedRelease], *, adding: int = 1, budget: int = PAGE_BUDGET
) -> list[str]:
    """Refusals for publishing *adding* more releases to the main repository.

    Installed copies read GitHub's first page of 30, newest created first.
    For each app, every release created after that app's newest Stable one
    pushes it down the page; more than *budget* of them is refused.
    """
    ordered = sorted(listing, key=lambda r: r.created_at, reverse=True)
    problems = []
    for app in sorted({r.app for r in ordered if r.app}):
        stables = [i for i, r in enumerate(ordered) if r.app == app and not r.prerelease]
        if not stables:
            continue
        ahead = stables[0] + adding
        if ahead > budget:
            problems.append(
                f"{app}'s newest Stable release would be {ahead} releases down the list "
                f"(the budget is {budget}); installed copies read only the first 30. "
                f"Delete superseded Beta release objects (keep their tags) first."
            )
    return problems


# -- signing ------------------------------------------------------------------------


def load_seed(text: str) -> bytes:
    """A feed key file's seed: base64 of 32 bytes, or 64 (seed + public key).

    Comment lines (``untrusted comment:``, ``#``) are skipped. The key is read
    by the caller from the owner's own file; nothing here knows where it is.
    """
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.startswith(("#", "untrusted comment"))
    ]
    if not lines:
        raise ValueError("the key file is empty")
    raw = base64.b64decode(lines[-1])
    if len(raw) not in (32, 64):
        raise ValueError("the key file does not hold an Ed25519 key")
    return raw[:32]


def sign_bytes(data: bytes, seed: bytes, *, key_id: str = FEED_KEY_ID) -> str:
    """The minisign-shaped sidecar text for *data*."""
    from nacl.signing import SigningKey

    signature = SigningKey(seed).sign(data).signature
    return (
        "untrusted comment: quillville release feed signature\n"
        f"key id: {key_id}\n"
        f"sig: {base64.b64encode(signature).decode('ascii')}\n"
    )
