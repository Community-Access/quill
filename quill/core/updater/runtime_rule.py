"""The shared-runtime rule (release-channels plan 6.5): slots, or the interim rule.

**With runtime slots (Phase 3), any app may move on its own.** An installer
that knows about slots writes ``[runtime] slot=`` beside the app, and a Beta
app then runs from its own ``Runtime\3.13-beta`` folder, so nothing it installs
can reach a Stable sibling. :func:`runtime_verdict` is called with
``slots=True`` for such an install and simply allows the move. The rest of this
docstring is the rule for a copy installed before slots existed.

QUILL Lite, Quill Radio and QUILL Cast all run on one QuillVille Runtime, and
that runtime carries a copy of *every* app's code. Installing a Beta Quill Radio
puts a Beta runtime under a Stable QUILL Lite on the same computer, and going
back does not undo it, because a runtime is never replaced by an older one.
Channel runtime slots (Phase 3) fix that properly. Until they ship:

* an app that does not use the runtime (QUILL itself, or any portable copy,
  which carries its own) may move freely;
* a runtime app may join Beta or Dev only when it is the **only** app on the
  runtime, or when every other app on it moves too -- they then share one
  channel, so nothing runs code it did not choose;
* an app on the runtime that has no channel support yet (Quill Weather,
  Converter and the rest) cannot move with it, so while one is installed a
  runtime app stays on Stable.

Going back towards Stable is never blocked by this rule: it only ever reduces
what runs on the runtime.

wx-free, pure, and strict-typed.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from quill.core.updater.channels import CHANNELS, ChannelState, channel_label, normalize_channel
from quill.core.updater.profiles import PROFILES

__all__ = ["RuntimeVerdict", "runtime_verdict"]


@dataclass(frozen=True)
class RuntimeVerdict:
    #: The move may go ahead as asked.
    allowed: bool
    #: Runtime apps that must move too before it can (empty when allowed, or
    #: when moving them would not help).
    must_move: tuple[str, ...] = ()
    #: Runtime apps that cannot follow at all (no channel support yet).
    cannot_follow: tuple[str, ...] = ()
    #: One plain paragraph saying why, for the dialog. Empty when allowed
    #: without conditions.
    explanation: str = ""


def _name(app_key: str, display_names: Mapping[str, str]) -> str:
    profile = PROFILES.get(app_key)
    return profile.display_name if profile else display_names.get(app_key, app_key)


def _join(names: list[str]) -> str:
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + " and " + names[-1]


def runtime_verdict(
    app_key: str,
    target: str,
    *,
    runtime_apps: Iterable[str],
    states: Mapping[str, ChannelState],
    moving_too: Iterable[str] = (),
    portable: bool = False,
    display_names: Mapping[str, str] | None = None,
    slots: bool = False,
) -> RuntimeVerdict:
    """May *app_key* move to *target*, given who else is on its runtime?

    *runtime_apps* is every app registered on the shared runtime (profile keys
    or runtime ids; :func:`quill.core.runtime_apps.installed_apps`), *states*
    each app's current channel, and *moving_too* the siblings the person checked
    to move in the same step.
    """
    names = dict(display_names or {})
    profile = PROFILES.get(app_key)
    channel = normalize_channel(target)
    if portable or slots or profile is None or not profile.uses_shared_runtime:
        return RuntimeVerdict(allowed=True)
    current = states.get(app_key, ChannelState()).channel
    if CHANNELS.index(channel) <= CHANNELS.index(current):
        return RuntimeVerdict(allowed=True)
    moving = set(moving_too)
    runtime_keys = {_profile_key(app) for app in runtime_apps} - {app_key}
    cannot_follow = sorted(key for key in runtime_keys if key not in PROFILES)
    must_move = sorted(
        key
        for key in runtime_keys
        if key in PROFILES
        and key not in moving
        and states.get(key, ChannelState()).channel != channel
    )
    me = profile.display_name
    label = channel_label(channel)
    if cannot_follow:
        others = _join([_name(key, names) for key in cannot_follow])
        verb = "shares" if len(cannot_follow) == 1 else "share"
        return RuntimeVerdict(
            allowed=False,
            cannot_follow=tuple(cannot_follow),
            explanation=(
                f"{label} for {me} needs an update that is coming soon. {others} on this "
                f"computer {verb} {me}'s engine and can't follow it to {label} yet, so for "
                f"now {me} stays on Stable. Nothing has changed."
            ),
        )
    if must_move:
        others = _join([_name(key, names) for key in must_move])
        verb = "shares" if len(must_move) == 1 else "share"
        return RuntimeVerdict(
            allowed=False,
            must_move=tuple(must_move),
            explanation=(
                f"{label} for {me} needs an update that is coming soon, because {others} on "
                f"this computer {verb} {me}'s engine. You can move them together instead: "
                f'check them under "Also move my other QuillVille apps" and choose Switch.'
            ),
        )
    return RuntimeVerdict(allowed=True)


def _profile_key(app: str) -> str:
    """Runtime ids and profile keys agree today; this is where they would not."""
    for key, profile in PROFILES.items():
        if profile.runtime_ref and profile.runtime_ref == app:
            return key
    return app
