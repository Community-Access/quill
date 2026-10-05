"""The channel half of an update check, shared by every app (plan 6.3, Phase 1).

Each app still fetches its releases the way it always has (GitHub, page size
100). It then hands the list to :func:`evaluate`, which:

1. reads the app's channel from ``channels.json``;
2. applies the **birth-channel rule** (plan 2.1): an app with nothing stored
   that finds itself running a pre-release -- a tester installed a Beta by
   hand -- is set to that channel *once*, and says so. This replaces QUILL's
   old silent auto-enrol;
3. carries QUILL's old "Get beta updates" box across, once, the first time;
4. picks what may be offered (:func:`quill.core.updater.policy.choose_offer`);
5. moves a person who was waiting for Stable across once Stable has caught up,
   and says so.

The sentences it returns in :attr:`CheckResult.notices` are outcomes the
screen reader cannot know, said once each (GATE-13).

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from quill.core.updater import history
from quill.core.updater.channels import (
    BETA,
    DEV,
    STABLE,
    ChannelState,
    channel_label,
    load_channels,
    save_channels,
)
from quill.core.updater.policy import ReleaseLike, choose_offer
from quill.core.updater.profiles import PROFILES
from quill.core.versioning import ReleaseVersion

__all__ = ["CheckResult", "evaluate", "up_to_date_text"]


@dataclass(frozen=True)
class CheckResult[R: ReleaseLike]:
    target: R | None
    state: ChannelState
    notices: tuple[str, ...] = ()


def _birth_channel(installed: str) -> str:
    parsed = ReleaseVersion.try_parse(installed)
    if parsed is None or not parsed.is_prerelease:
        return STABLE
    return DEV if parsed.stage == "dev" else BETA


def evaluate[R: ReleaseLike](
    app_key: str,
    installed: str,
    releases: Sequence[R],
    *,
    legacy_beta: bool = False,
    path: Path | None = None,
    history_path: Path | None = None,
) -> CheckResult[R]:
    """Decide what this check may offer *app_key*, updating its channel if due."""
    profile = PROFILES.get(app_key)
    if profile is None:
        return CheckResult(choose_offer(installed, releases, ChannelState()).target, ChannelState())
    data = load_channels(path)
    state = data.state(app_key)
    notices: list[str] = []
    if not data.has(app_key):
        birth = _birth_channel(installed)
        if birth != STABLE:
            label = channel_label(birth)
            state = ChannelState(channel=birth, joined_from=installed, set_by="installed")  # type: ignore[arg-type]
            notices.append(
                f"You installed a {label} version, so {profile.display_name} will offer you "
                f"{label} updates. You can change this in Help, Release Channel."
            )
            history.record(
                app_key,
                "channel_changed",
                from_version=installed,
                channel=birth,
                detail=f"Started on {label} because a {label} version was installed.",
                path=history_path,
            )
            save_channels(data.with_state(app_key, state), path)
        elif legacy_beta:
            state = ChannelState(channel=BETA, set_by="legacy")
            save_channels(data.with_state(app_key, state), path)
    decision = choose_offer(installed, releases, state)
    if decision.stable_caught_up:
        state = ChannelState(channel=STABLE, set_by=state.set_by or "you")
        save_channels(load_channels(path).with_state(app_key, state), path)
        notices.append(
            f"Stable has caught up. {profile.display_name} is back on the Stable channel."
        )
        history.record(
            app_key, "stable_caught_up", from_version=installed, channel=STABLE, path=history_path
        )
    return CheckResult(decision.target, state, tuple(notices))


def up_to_date_text(installed: str, state: ChannelState, *, known_app: bool = True) -> str:
    """The manual check's "nothing newer" sentence, naming the channel."""
    parsed = ReleaseVersion.try_parse(installed)
    shown = parsed.display() if parsed is not None else installed
    text = f"You are up to date ({shown})."
    if not known_app:
        return text
    if state.pending_return:
        return text + " You are waiting for Stable to catch up with your version."
    return text + f" You are on the {channel_label(state.channel)} channel."


def mark_waiting_complete(state: ChannelState) -> ChannelState:
    """The state after Stable has caught up (exposed for tests and the dialog)."""
    return replace(state, channel=STABLE, pending_return=False, keep_beta_while_waiting=False)
