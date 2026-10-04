"""Going back to Stable, only when it is safe (release-channels plan 5).

**The rule.** Going back to Stable build T is safe if and only if, for every
data format recorded in every ledger the app touches, T can read the highest
version ever written on this computer -- and T is not withdrawn and not below
the feed's security floor. Formats a newer build declared "readable with
losses" by T's version make it *safe with losses* (QUILL Lite forgets a few
newer settings); anything else that T cannot read makes it *unsafe*.

What the person is offered (plan 5.3 and 7.6):

* **safe** -- "Go back to 3.2.0 now", or wait for Stable;
* **safe with losses** -- the same, naming what goes back to its usual value;
* **unsafe** -- wait for Stable (the default), or "Use the copy from 3 October":
  restore the copy saved when the app joined Beta, then install Stable. When
  there is no copy, waiting is the only choice, and the window says so.

The installer is never started for a lower version unless
:func:`authorize_downgrade` agrees -- a refusal is
:class:`UnsafeDowngradeError`, said in one sentence with what to do instead.

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

from quill.core.data_format_ledger import Ledger
from quill.core.data_formats import FORMATS, formats_for
from quill.core.error_codes import CodedError
from quill.core.updater.channels import STABLE, ChannelState
from quill.core.updater.feed import FeedRelease, ReleaseFeed
from quill.core.versioning import ReleaseVersion, sort_key

__all__ = [
    "ReturnAssessment",
    "UnsafeDowngradeError",
    "Verdict",
    "assess_return",
    "authorize_downgrade",
    "downgrade_verdict",
    "format_words",
]

VerdictKind = Literal["safe", "safe_with_losses", "unsafe"]

#: What each format is, in the words a person uses.
_WORDS: dict[str, str] = {
    "quill.settings": "settings",
    "quill.keymap": "keyboard shortcuts",
    "lite.settings": "settings",
    "lite.keymap": "keyboard shortcuts",
    "radio.favorites": "favorites",
    "radio.history": "history and settings",
    "cast.library": "subscriptions",
    "cast.history": "listening history and settings",
    "shared.media_bookmarks": "bookmarks",
    "shared.listens": "listening places",
}


class UnsafeDowngradeError(CodedError):
    """Going back would install a build that cannot read what is saved here."""

    code = "QUILL-UPDATE-CHANNEL-UNSAFE-DOWNGRADE"


@dataclass(frozen=True)
class Verdict:
    kind: VerdictKind
    #: Format ids the target cannot read (unsafe) ...
    blockers: tuple[str, ...] = ()
    #: ... or reads, forgetting newer fields (safe with losses).
    losses: tuple[str, ...] = ()
    #: Why, when the target itself is not allowed (withdrawn, below the floor).
    reason: str = ""

    @property
    def safe(self) -> bool:
        return self.kind != "unsafe"


def format_words(format_ids: Sequence[str]) -> str:
    """``favorites and bookmarks`` -- the formats, as one plain phrase."""
    words: list[str] = []
    for format_id in format_ids:
        word = _WORDS.get(format_id, format_id.split(".")[-1].replace("_", " "))
        if word not in words:
            words.append(word)
    if len(words) <= 1:
        return "".join(words)
    return ", ".join(words[:-1]) + " and " + words[-1]


def _relevant(app_key: str, target: FeedRelease) -> set[str]:
    return {f.id for f in formats_for(app_key)} | set(target.reads_formats)


def downgrade_verdict(
    target: FeedRelease,
    ledgers: Sequence[Ledger],
    *,
    app_key: str = "",
    lossy_ok: Mapping[str, int] | None = None,
    security_floor: str = "",
) -> Verdict:
    """Whether *target* can open everything this computer has saved.

    *lossy_ok* is the installed build's ``lossy_formats``: per format, the
    oldest reader version that loses only newer fields. A format the target
    has never heard of counts as version 0 -- unsafe if the ledger has it.
    """
    if target.revoked:
        return Verdict("unsafe", reason=f"{target.version} has been withdrawn")
    if security_floor and sort_key(target.version) < sort_key(security_floor):
        return Verdict("unsafe", reason=f"{target.version} has a known security problem")
    relevant = _relevant(app_key, target) if app_key else None
    allowance = dict(lossy_ok or {})
    blockers: list[str] = []
    losses: list[str] = []
    for ledger in ledgers:
        for format_id, entry in sorted(ledger.formats.items()):
            if relevant is not None and format_id not in relevant:
                continue
            readable = target.reads_formats.get(format_id, 0)
            if entry.high <= readable:
                continue
            floor = allowance.get(format_id, 0)
            if floor and readable >= floor:
                if format_id not in losses:
                    losses.append(format_id)
            elif format_id not in blockers:
                blockers.append(format_id)
    if blockers:
        return Verdict("unsafe", blockers=tuple(blockers), losses=tuple(losses))
    if losses:
        return Verdict("safe_with_losses", losses=tuple(losses))
    return Verdict("safe")


@dataclass(frozen=True)
class ReturnAssessment:
    """Everything the Go back to Stable? window needs, decided once."""

    app_key: str
    installed: str
    #: Stable's newest build, or ``None`` when the feed lists none.
    stable: FeedRelease | None
    verdict: Verdict | None
    #: The copy saved when this app joined Beta or Dev, if it still exists.
    snapshot: Path | None = None
    #: When that copy was made, as a person says it ("3 October").
    snapshot_date: str = ""
    #: Shared files a restore leaves alone, because a sibling on Beta or Dev
    #: wrote a newer version of them, as plain words.
    shared_kept: tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_downgrade(self) -> bool:
        return self.stable is not None and sort_key(self.stable.version) < sort_key(self.installed)


def _day(text: str) -> str:
    try:
        moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return ""
    return f"{moment.day} {moment:%B}"


def shared_formats_kept(app_key: str, channels: Mapping[str, ChannelState]) -> tuple[str, ...]:
    """Shared formats a restore must leave alone: another writer is on Beta or Dev."""
    kept = []
    for fmt in FORMATS:
        if fmt.owner != "shared" or app_key not in fmt.writers:
            continue
        others = [w for w in fmt.writers if w != app_key]
        if any(channels.get(w, ChannelState()).channel != STABLE for w in others):
            kept.append(fmt.id)
    return tuple(kept)


def assess_return(
    app_key: str,
    installed: str,
    feed: ReleaseFeed | None,
    state: ChannelState,
    ledgers: Sequence[Ledger],
    channels: Mapping[str, ChannelState],
) -> ReturnAssessment:
    """Decide what going back to Stable would mean for *app_key* right now."""
    stable = feed.current("stable") if feed is not None else None
    snapshot = Path(state.snapshot) if state.snapshot else None
    if snapshot is not None and not snapshot.is_file():
        snapshot = None
    verdict = None
    if stable is not None and feed is not None:
        mine = feed.release(installed)
        verdict = downgrade_verdict(
            stable,
            ledgers,
            app_key=app_key,
            lossy_ok=mine.lossy_formats if mine is not None else None,
            security_floor=feed.security_floor,
        )
    kept = shared_formats_kept(app_key, channels)
    return ReturnAssessment(
        app_key=app_key,
        installed=installed,
        stable=stable,
        verdict=verdict,
        snapshot=snapshot,
        snapshot_date=_day(state.joined_at),
        shared_kept=tuple(_WORDS.get(f, f) for f in kept),
    )


def authorize_downgrade(
    assessment: ReturnAssessment, *, restored: bool = False, losses_confirmed: bool = False
) -> FeedRelease:
    """The Stable build to install, or :class:`UnsafeDowngradeError` saying why not.

    Allowed when the verdict is safe; safe-with-losses once the person has
    confirmed it; and anything at all right after a saved copy was restored,
    because the files on disk are then the old ones.
    """
    stable = assessment.stable
    if stable is None or assessment.verdict is None:
        raise UnsafeDowngradeError("there is no Stable version to go back to yet")
    if stable.revoked:
        raise UnsafeDowngradeError(f"{stable.version} has been withdrawn")
    verdict = assessment.verdict
    if (
        restored
        or verdict.kind == "safe"
        or (verdict.kind == "safe_with_losses" and losses_confirmed)
    ):
        return stable
    shown = ReleaseVersion.try_parse(stable.version)
    target = shown.display() if shown else stable.version
    what = format_words(verdict.blockers) or "what is saved here"
    raise UnsafeDowngradeError(
        f"{target} cannot read the {what} saved by your current version, so it was not "
        "installed. Nothing of yours changed. You can wait for Stable to catch up, or go "
        "back using the copy saved when you joined."
    )
