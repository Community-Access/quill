"""Moving an app between release channels, step by step (plan 7.5 and 7.6).

The Release Channel dialog asks; this module decides and does. Every side
effect -- the risk question, the saved copy, the file write, the history line --
is passed in, so the whole flow runs in a test with fakes and no wx.

**Joining Beta or Dev** (a riskier channel):

1. The shared-runtime rule must allow it (:mod:`.runtime_rule`).
2. The risk dialog is shown; anything but an explicit "Move" changes nothing.
3. A copy of each moving app's settings is saved (:mod:`.snapshots`). If any
   copy fails, nothing moves, and the message says which and why.
4. ``channels.json`` is written in one step for every app that moves, and the
   change goes in Update History.

**Coming back** (a less risky channel) never installs anything in Phase 1:

* If the installed build is one the chosen channel would list anyway (a final
  version, on the way to Stable), the channel simply flips -- the same version,
  so nothing about your data changes.
* Otherwise the app **waits for Stable**: it stops taking Beta updates and moves
  across by itself when Stable reaches the installed version. That is always
  safe, because nothing is ever installed backwards.

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from quill.core.updater import history
from quill.core.updater.channels import (
    BETA,
    DEV,
    STABLE,
    Channel,
    ChannelState,
    channel_label,
    is_riskier,
    load_channels,
    normalize_channel,
    save_channels,
)
from quill.core.updater.profiles import PROFILES, UpdaterProfile
from quill.core.updater.runtime_rule import RuntimeVerdict, runtime_verdict
from quill.core.updater.snapshots import SnapshotError
from quill.core.versioning import ReleaseVersion

__all__ = [
    "RiskContext",
    "SwitchOutcome",
    "SwitchPlan",
    "SwitchRequest",
    "perform_switch",
    "plan_switch",
]

Kind = Literal["already", "blocked", "join", "resume", "return_now", "return_wait"]


@dataclass(frozen=True)
class SwitchRequest:
    app_key: str
    target: Channel
    installed_version: str
    also_move: tuple[str, ...] = ()


@dataclass(frozen=True)
class SwitchPlan:
    request: SwitchRequest
    kind: Kind
    current: ChannelState
    verdict: RuntimeVerdict | None = None

    @property
    def profile(self) -> UpdaterProfile:
        return PROFILES[self.request.app_key]

    def summary(self) -> str:
        """What choosing Switch would do, for the dialog's "What this means" box."""
        name = self.profile.display_name
        target = channel_label(self.request.target)
        shown = ReleaseVersion.try_parse(self.request.installed_version)
        version = shown.display() if shown else self.request.installed_version
        if self.kind == "already":
            return f"{name} {version} is on {target} already. Nothing to change."
        if self.kind == "blocked" and self.verdict is not None:
            return self.verdict.explanation
        if self.kind == "join":
            return (
                f"{name} {version} will move to {target}. A copy of "
                f"{self.profile.snapshot_covers} is saved first, and the next check for "
                f"updates will offer {target} versions."
            )
        if self.kind == "resume":
            return f"{name} stops waiting for Stable and takes {target} updates again."
        if self.kind == "return_now":
            return (
                f"{name} {version} is already a version {target} lists, so it moves to "
                f"{target} straight away. Nothing is installed and nothing of yours changes."
            )
        return (
            f"{name} {version} is newer than Stable. Going straight back isn't offered "
            f"yet, so {name} will wait: it keeps {version}, stops taking "
            f"{channel_label(self.current.channel)} updates, and moves to Stable by itself "
            f"when Stable reaches {version}. That is always safe."
        )


@dataclass(frozen=True)
class RiskContext:
    """What the risk dialog needs to say (plan 7.3 and 7.4)."""

    app_key: str
    display_name: str
    target: Channel
    #: Display names of the other apps moving in the same step.
    also_moving: tuple[str, ...]
    snapshot_covers: str
    snapshot_leaves: str
    uses_shared_runtime: bool


@dataclass(frozen=True)
class SwitchOutcome:
    changed: bool
    #: One sentence for the person (spoken, or shown).
    message: str
    #: The states written, by app.
    states: Mapping[str, ChannelState] = field(default_factory=dict)
    snapshots: Mapping[str, Path] = field(default_factory=dict)
    cancelled: bool = False


def plan_switch(
    request: SwitchRequest,
    *,
    states: Mapping[str, ChannelState],
    runtime_apps: Sequence[str] = (),
    portable: bool = False,
    slots: bool = False,
) -> SwitchPlan:
    """Decide what moving *request.app_key* to *request.target* would mean."""
    current = states.get(request.app_key, ChannelState())
    target = normalize_channel(request.target)
    request = replace(request, target=target)
    if target == current.channel:
        kind: Kind = "resume" if current.pending_return else "already"
        return SwitchPlan(request, kind, current)
    if is_riskier(target, current.channel):
        verdict = runtime_verdict(
            request.app_key,
            target,
            runtime_apps=runtime_apps,
            states=states,
            moving_too=request.also_move,
            portable=portable,
            slots=slots,
        )
        return SwitchPlan(request, "join" if verdict.allowed else "blocked", current, verdict)
    return SwitchPlan(request, _return_kind(target, request.installed_version), current)


def _return_kind(target: Channel, installed: str) -> Kind:
    parsed = ReleaseVersion.try_parse(installed)
    stage = parsed.stage if parsed is not None else "dev"
    if target == STABLE:
        return "return_now" if stage == "final" else "return_wait"
    # Dev -> Beta: Beta lists everything but Dev builds.
    return "return_now" if stage != "dev" else "return_wait"


def _joined(state: ChannelState, target: Channel, version: str, at: str, snap: str) -> ChannelState:
    return ChannelState(
        channel=target,
        joined_at=at,
        joined_from=version if state.channel == STABLE else state.joined_from or version,
        snapshot=snap,
        set_by="you",
    )


def perform_switch(
    plan: SwitchPlan,
    *,
    confirm_risk: Callable[[RiskContext], bool],
    confirm_wait: Callable[[SwitchPlan], bool],
    take_snapshot: Callable[[str, str, str], Path],
    version_of: Callable[[str], str],
    path: Path | None = None,
    history_path: Path | None = None,
    now: datetime | None = None,
) -> SwitchOutcome:
    """Carry out *plan*. Nothing changes unless every step before the write succeeds.

    ``take_snapshot(app_key, version, reason)`` returns the copy's path or
    raises :class:`SnapshotError`; ``version_of(app_key)`` names a sibling's
    installed version for its copy and its history line.
    """
    request = plan.request
    profile = plan.profile
    name = profile.display_name
    target = request.target
    label = channel_label(target)
    moment = now or datetime.now(UTC)
    at = moment.isoformat(timespec="seconds")
    if plan.kind == "already":
        return SwitchOutcome(False, f"Already on {label}.")
    if plan.kind == "blocked":
        return SwitchOutcome(False, plan.verdict.explanation if plan.verdict else "")
    data = load_channels(path)
    if plan.kind == "resume":
        state = replace(data.state(request.app_key), pending_return=False)
        save_channels(data.with_state(request.app_key, state), path)
        history.record(
            request.app_key,
            "channel_changed",
            from_version=request.installed_version,
            channel=target,
            detail="Stopped waiting for Stable.",
            path=history_path,
            now=moment,
        )
        return SwitchOutcome(True, f"{name} is on {label}.", {request.app_key: state})
    if plan.kind in ("return_now", "return_wait"):
        if plan.kind == "return_wait" and not confirm_wait(plan):
            return SwitchOutcome(
                False, f"{name} stayed on {channel_label(plan.current.channel)}.", cancelled=True
            )
        if plan.kind == "return_now":
            state = ChannelState(channel=target, set_by="you")
            message = f"{name} is back on {label}."
            detail = "Same version, so nothing was installed."
        else:
            state = replace(plan.current, pending_return=True, set_by="you")
            message = (
                f"{name} is waiting for Stable to catch up. You won't get Beta updates meanwhile."
            )
            detail = "Waiting for Stable to reach this version."
        save_channels(data.with_state(request.app_key, state), path)
        history.record(
            request.app_key,
            "channel_changed",
            from_version=request.installed_version,
            channel=state.channel if plan.kind == "return_now" else STABLE,
            detail=detail,
            path=history_path,
            now=moment,
        )
        return SwitchOutcome(True, message, {request.app_key: state})
    # Joining Beta or Dev.
    siblings = tuple(key for key in request.also_move if key in PROFILES and key != request.app_key)
    context = RiskContext(
        app_key=request.app_key,
        display_name=name,
        target=target,
        also_moving=tuple(PROFILES[key].display_name for key in siblings),
        snapshot_covers=profile.snapshot_covers,
        snapshot_leaves=profile.snapshot_leaves,
        uses_shared_runtime=profile.uses_shared_runtime,
    )
    if not confirm_risk(context):
        return SwitchOutcome(
            False, f"{name} stayed on {channel_label(plan.current.channel)}.", cancelled=True
        )
    reason = "joined-dev" if target == DEV else "joined-beta"
    snapshots: dict[str, Path] = {}
    versions = {request.app_key: request.installed_version}
    versions.update({key: version_of(key) for key in siblings})
    for key in (request.app_key, *siblings):
        try:
            snapshots[key] = take_snapshot(key, versions[key], reason)
        except SnapshotError as error:
            who = PROFILES[key].display_name
            current = channel_label(plan.current.channel)
            stayed = "nothing moved" if siblings else f"{name} stayed on {current}"
            return SwitchOutcome(
                False,
                f"{who} couldn't save a copy of {PROFILES[key].snapshot_covers}, so "
                f"{stayed}. {error.reason}".strip(),
            )
    written: dict[str, ChannelState] = {}
    for key in (request.app_key, *siblings):
        written[key] = _joined(data.state(key), target, versions[key], at, str(snapshots[key]))
        data = data.with_state(key, written[key])
    save_channels(data, path)
    for key in written:
        history.record(
            key,
            "snapshot_saved",
            from_version=versions[key],
            channel=target,
            detail=str(snapshots[key]),
            path=history_path,
            now=moment,
        )
        history.record(
            key,
            "channel_changed",
            from_version=versions[key],
            channel=target,
            detail=f"Joined {label}.",
            path=history_path,
            now=moment,
        )
    movers = [name, *context.also_moving]
    who = movers[0] if len(movers) == 1 else ", ".join(movers[:-1]) + " and " + movers[-1]
    verb = "is" if len(movers) == 1 else "are"
    return SwitchOutcome(
        True, f"Saved a copy of your settings. {who} {verb} on {label}.", written, snapshots
    )


#: Channels in the order the chooser lists them, re-exported for the dialog.
CHOICES: tuple[Channel, ...] = (STABLE, BETA, DEV)
