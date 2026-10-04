"""The one call each app makes: Help > Release Channel... and Update History.

Every app -- QUILL, QUILL Lite, Quill Radio and QUILL Cast -- opens the same
windows through :func:`open_release_channel` and :func:`open_update_history`,
passing its own modal runner and announcer, so the keyboard contract, F1 and
the dialog-transition cues are each app's own while the words and the rules
are the family's.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from typing import Any

import wx

from quill.core.updater import history, snapshots
from quill.core.updater.channels import (
    BETA,
    STABLE,
    ChannelState,
    channel_label,
    is_riskier,
    load_channels,
    normalize_channel,
)
from quill.core.updater.profiles import PROFILES
from quill.core.updater.switch import (
    RiskContext,
    SwitchOutcome,
    SwitchPlan,
    SwitchRequest,
    perform_switch,
    plan_switch,
)
from quill.core.updater.wording import WAIT_TITLE, wait_text
from quill.core.versioning import ReleaseVersion

__all__ = ["open_release_channel", "open_update_history", "runtime_context"]

ShowModal = Callable[[Any, str], int]


def runtime_context(app_key: str) -> tuple[list[str], bool]:
    """(apps registered on the shared runtime, whether this copy is portable)."""
    profile = PROFILES.get(app_key)
    if profile is None or not profile.uses_shared_runtime:
        return [], False
    try:
        from quill.core.install_edition import PORTABLE, detect

        portable = detect() == PORTABLE
    except Exception:  # noqa: BLE001 - unknown edition: assume installed (the cautious answer)
        portable = False
    try:
        from quill.core.paths import app_data_dir
        from quill.core.runtime_apps import installed_apps

        apps = [app.ref_id for app in installed_apps(app_data_dir())]
    except Exception:  # noqa: BLE001 - no answer is "alone", which the rule then allows
        apps = []
    return apps, portable


def slots_available(app_key: str) -> bool:
    """Whether this install runs from a release-channel runtime slot (Phase 3).

    The installer that writes ``[runtime] slot=`` is the one whose launcher
    honours it, so a slot in the marker means a Beta install of this app gets
    its own runtime folder and the interim "alone on the runtime" rule is moot.
    """
    profile = PROFILES.get(app_key)
    if profile is None or not profile.uses_shared_runtime:
        return False
    try:
        from quill.core.app_version import runtime_slot

        return bool(runtime_slot())
    except Exception:  # noqa: BLE001 - unknown: the cautious interim rule applies
        return False


def _siblings(app_key: str, runtime_apps: list[str]) -> list[tuple[str, str, ChannelState]]:
    data = load_channels()
    rows = []
    for key, profile in PROFILES.items():
        if key == app_key:
            continue
        if profile.runtime_ref in runtime_apps or data.has(key):
            rows.append((key, profile.display_name, data.state(key)))
    return rows


def _shown(version: str) -> str:
    parsed = ReleaseVersion.try_parse(version)
    return parsed.display() if parsed is not None else version


def open_update_history(parent: Any, *, app_key: str, show_modal: ShowModal) -> None:
    from quill.ui.updates.update_history_dialog import UpdateHistoryDialog

    name = PROFILES[app_key].display_name
    dialog = UpdateHistoryDialog(parent, app_name=name, events=history.read_events(app_key))
    try:
        show_modal(dialog, dialog.GetTitle())
    finally:
        dialog.Destroy()


def open_release_channel(
    parent: Any,
    *,
    app_key: str,
    installed_version: str,
    show_modal: ShowModal,
    announce: Callable[[str], None],
    on_changed: Callable[[ChannelState], None] | None = None,
    check_now: Callable[[], None] | None = None,
    install_release: Callable[[Any], None] | None = None,
) -> SwitchOutcome | None:
    """Show the chooser and carry out what the person chose. Returns the outcome."""
    from quill.ui.updates.release_channel_dialog import ReleaseChannelDialog

    profile = PROFILES[app_key]
    runtime_apps, portable = runtime_context(app_key)
    states = dict(load_channels().apps)
    state = states.get(app_key, ChannelState())

    def _plan(target: str, also: tuple[str, ...]) -> SwitchPlan:
        request = SwitchRequest(app_key, normalize_channel(target), installed_version, also)
        return plan_switch(
            request,
            states=states,
            runtime_apps=runtime_apps,
            portable=portable,
            slots=slots_available(app_key),
        )

    dialog = ReleaseChannelDialog(
        parent,
        app_name=profile.display_name,
        state=state,
        siblings=_siblings(app_key, runtime_apps),
        describe=_plan,
        show_history=lambda: open_update_history(dialog, app_key=app_key, show_modal=show_modal),
    )
    try:
        if show_modal(dialog, dialog.GetTitle()) != wx.ID_OK:
            return None
        plan = _plan(dialog.chosen(), dialog.also_move())
    finally:
        dialog.Destroy()
    outcome = _carry_out(
        parent, plan, show_modal=show_modal, announce=announce, install_release=install_release
    )
    if outcome.changed:
        written = outcome.states.get(app_key)
        if written is not None and on_changed is not None:
            on_changed(written)
        if written is not None and is_riskier(written.channel, state.channel) and check_now:
            check_now()
    return outcome


def _carry_out(
    parent: Any,
    plan: SwitchPlan,
    *,
    show_modal: ShowModal,
    announce: Callable[[str], None],
    install_release: Callable[[Any], None] | None = None,
) -> SwitchOutcome:
    from quill.ui.updates.channel_risk_dialog import RiskDialog

    retarget: list[str] = []

    def _confirm_risk(context: RiskContext) -> bool:
        risk = RiskDialog(parent, context, announce=announce)
        try:
            show_modal(risk, risk.GetTitle())
            answer = risk.answer()
        finally:
            risk.Destroy()
        if answer == "beta_instead":
            retarget.append(BETA)
        return answer == "move"

    def _confirm_wait(wait_plan: SwitchPlan) -> bool:
        name = wait_plan.profile.display_name
        message = wx.MessageDialog(
            parent,
            wait_text(name, _shown(wait_plan.request.installed_version), wait_plan.current.channel),
            WAIT_TITLE,
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_INFORMATION,
        )
        stay = f"Stay on {channel_label(wait_plan.current.channel)}"
        message.SetYesNoLabels("Wait for Stable", stay)
        try:
            return bool(show_modal(message, WAIT_TITLE) == wx.ID_YES)
        finally:
            message.Destroy()

    def _run_waiting(current: SwitchPlan) -> SwitchOutcome:
        # The person already chose "Wait for Stable" in the going-back window.
        return perform_switch(
            current,
            confirm_risk=_confirm_risk,
            confirm_wait=lambda _plan: True,
            take_snapshot=lambda key, version, reason: snapshots.take_snapshot(
                key, version or "unknown", reason
            ),
            version_of=lambda _key: "",
        )

    def _run(current: SwitchPlan) -> SwitchOutcome:
        return perform_switch(
            current,
            confirm_risk=_confirm_risk,
            confirm_wait=_confirm_wait,
            take_snapshot=lambda key, version, reason: snapshots.take_snapshot(
                key, version or "unknown", reason
            ),
            version_of=lambda _key: "",
        )

    outcome: SwitchOutcome | None = None
    if plan.kind == "return_wait" and plan.request.target == STABLE and install_release:
        # Phase 4: when the signed list says how, offer going back now (or the
        # saved copy) as well as waiting; otherwise waiting, as before.
        from quill.ui.updates.going_back_flow import go_back

        outcome = go_back(
            parent,
            plan,
            show_modal=show_modal,
            announce=announce,
            install_release=install_release,
            wait=lambda: _run_waiting(plan),
        )
    if outcome is None:
        outcome = _run(plan)
    if retarget:
        request = replace(plan.request, target=BETA)
        states = dict(load_channels().apps)
        runtime_apps, portable = runtime_context(plan.request.app_key)
        outcome = _run(
            plan_switch(
                request,
                states=states,
                runtime_apps=runtime_apps,
                portable=portable,
                slots=slots_available(plan.request.app_key),
            )
        )
    if outcome.cancelled:
        return outcome
    if not outcome.changed and plan.kind != "already":
        # Something stopped the move: say why in a window, not only aloud.
        box = wx.MessageDialog(
            parent, outcome.message, parent_title(plan), wx.OK | wx.ICON_INFORMATION
        )
        try:
            show_modal(box, parent_title(plan))
        finally:
            box.Destroy()
        return outcome
    announce(outcome.message)
    return outcome


def parent_title(plan: SwitchPlan) -> str:
    from quill.core.updater.wording import chooser_title

    return chooser_title(plan.profile.display_name)
