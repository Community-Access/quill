"""Which release an update check may offer, given the channel (plan 6.3, Phase 1).

Phase 1 reads the GitHub release list the apps already read; Phase 2 replaces
the list with the signed per-app feed and this table grows. The rules that
hold from today:

* **Stable never sees a pre-release** -- neither a build GitHub marks
  "prerelease" (a candidate still soaking on Beta) nor one whose version says
  so (``3.3.0-beta.2``).
* **Beta** sees Beta, release-candidate and Stable builds, but not Dev ones.
* **Dev** sees everything.
* Whatever the channel, the newest build *by version* wins, never by list order.
* **Waiting for Stable** (``pending_return``) offers only Stable builds -- unless
  the person asked to keep getting Beta fixes -- and reports when Stable has
  caught up with the version installed, so the app can say so and move across.

wx-free, pure and strict-typed.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from quill.core.updater.channels import BETA, DEV, STABLE, ChannelState, includes_prereleases
from quill.core.versioning import ReleaseVersion, sort_key

__all__ = ["OfferDecision", "ReleaseLike", "choose_offer", "visible_on"]


class ReleaseLike(Protocol):
    @property
    def version(self) -> str: ...

    @property
    def prerelease(self) -> bool: ...


@dataclass(frozen=True)
class OfferDecision[R: ReleaseLike]:
    #: The release to offer, or ``None`` when there is nothing newer.
    target: R | None
    #: Waiting for Stable, and a Stable build at or above the installed
    #: version now exists: the app may move the person back to Stable.
    stable_caught_up: bool = False


def _stage(release: ReleaseLike) -> str:
    parsed = ReleaseVersion.try_parse(release.version)
    return parsed.stage if parsed is not None else "dev"


def _is_stable_build(release: ReleaseLike) -> bool:
    return not release.prerelease and _stage(release) == "final"


def visible_on(release: ReleaseLike, state: ChannelState) -> bool:
    """Whether *release* may be offered to somebody in *state*.

    A build from the signed v2 list carries ``channels``: the list, not the
    version's spelling, then says where it belongs -- a Dev build promoted to
    Beta keeps its Dev version and is still a Beta listing (plan 4.1).
    """
    listed = getattr(release, "channels", None)
    if listed is not None:
        return _visible_by_listing(tuple(listed), state)
    if _is_stable_build(release):
        return True
    if not includes_prereleases(state):
        return False
    if state.channel == BETA or (state.channel != STABLE and state.pending_return):
        return _stage(release) != "dev"
    return True


def _visible_by_listing(listed: tuple[str, ...], state: ChannelState) -> bool:
    if "stable" in listed:
        return True
    if not includes_prereleases(state):
        return False
    if state.channel == DEV and not state.pending_return:
        return bool(listed)
    return "beta" in listed


def choose_offer[R: ReleaseLike](
    installed: str, releases: Sequence[R], state: ChannelState
) -> OfferDecision[R]:
    """The newest release *state* may see that is newer than *installed*."""
    usable = [r for r in releases if getattr(r, "has_platform_asset", True)]
    visible = [r for r in usable if visible_on(r, state)]
    best = max(visible, key=lambda r: sort_key(r.version), default=None)
    installed_key = sort_key(installed)
    target = best if best is not None and sort_key(best.version) > installed_key else None
    caught_up = state.pending_return and any(
        _is_stable_build(r) and sort_key(r.version) >= installed_key for r in usable
    )
    return OfferDecision(target=target, stable_caught_up=caught_up)
