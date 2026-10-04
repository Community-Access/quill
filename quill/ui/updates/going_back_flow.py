"""Coming back to Stable from a newer version, when the feed says how (plan 5.3).

Called by :mod:`quill.ui.updates.flow` when somebody on Beta or Dev chooses
Stable and Stable is older than what they have. It needs the signed release
list -- the copy the last update check kept, never a fresh network call from a
window -- and the data-format ledger, and from those it shows the one window
that fits (:mod:`quill.ui.updates.return_to_stable_dialog`):

* **Go back now**: Stable can read everything, so the channel flips to Stable
  and the Stable build is downloaded and offered for installing.
* **Use the copy**: a copy of how things are now is saved, the copy from when
  the app joined is put back (shared files a sibling on Beta or Dev wrote are
  left alone), the ledger is lowered to match, and Stable is installed.
* **Wait for Stable**: the Phase 1 path, unchanged.

Anything this cannot decide -- no list yet, no Stable build, Stable not older --
returns ``None`` and the caller falls back to waiting, which is always safe.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import wx

from quill.core.updater import history
from quill.core.updater.channels import (
    STABLE,
    ChannelState,
    channel_label,
    load_channels,
    save_channels,
)
from quill.core.updater.switch import SwitchOutcome, SwitchPlan

__all__ = ["go_back"]

ShowModal = Callable[[Any, str], int]


def _portable(app_key: str) -> bool:
    try:
        if app_key == "quill":
            from quill.core.updates import running_portable

            return bool(running_portable())
        from quill.core.install_edition import PORTABLE, detect

        return detect() == PORTABLE
    except Exception:  # noqa: BLE001 - unknown: an installed copy (the usual case)
        return False


def _tell(parent: Any, message: str, title: str, show_modal: ShowModal) -> None:
    box = wx.MessageDialog(parent, message, title, wx.OK | wx.ICON_INFORMATION)
    try:
        show_modal(box, title)
    finally:
        box.Destroy()


def go_back(
    parent: Any,
    plan: SwitchPlan,
    *,
    show_modal: ShowModal,
    announce: Callable[[str], None],
    install_release: Callable[[Any], None],
    wait: Callable[[], SwitchOutcome],
) -> SwitchOutcome | None:
    """Offer the ways back to Stable; ``None`` when only waiting is possible."""
    from quill.core.data_format_ledger import ledger_folder, read_ledger
    from quill.core.updater.feed_fetch import cached_feed, offers_from_feed
    from quill.core.updater.going_back import (
        UnsafeDowngradeError,
        assess_return,
        authorize_downgrade,
        shared_formats_kept,
    )
    from quill.core.updater.snapshots import SnapshotError, restore_snapshot
    from quill.core.updater.wording import chooser_title
    from quill.ui.updates.return_to_stable_dialog import ReturnToStableDialog

    app_key = plan.request.app_key
    name = plan.profile.display_name
    installed = plan.request.installed_version
    feed = cached_feed(app_key)
    if feed is None:
        return None
    channels = dict(load_channels().apps)
    state = channels.get(app_key, ChannelState())
    assessment = assess_return(
        app_key, installed, feed, state, [read_ledger(ledger_folder(app_key))], channels
    )
    if not assessment.is_downgrade or assessment.verdict is None or assessment.stable is None:
        return None
    label = channel_label(plan.current.channel)
    dialog = ReturnToStableDialog(parent, assessment, app_name=name, channel=plan.current.channel)
    try:
        show_modal(dialog, dialog.GetTitle())
        answer = dialog.answer()
    finally:
        dialog.Destroy()
    if answer == "close":
        return SwitchOutcome(False, f"{name} stayed on {label}.", cancelled=True)
    if answer == "wait":
        return wait()
    title = chooser_title(name)
    restored = False
    if answer == "restore" and assessment.snapshot is not None:
        try:
            outcome = restore_snapshot(
                app_key,
                assessment.snapshot,
                version_now=installed,
                keep_shared=shared_formats_kept(app_key, channels),
                fallback_formats=dict(assessment.stable.data_formats),
            )
        except SnapshotError as error:
            message = f"{name} couldn't put the saved copy back, so nothing changed. {error.reason}"
            _tell(parent, message, title, show_modal)
            return SwitchOutcome(False, message, cancelled=True)
        history.record(
            app_key,
            "snapshot_restored",
            from_version=installed,
            channel=STABLE,
            detail=(
                f"Put back {assessment.snapshot.name}; this moment saved as {outcome.before.name}."
            ),
        )
        restored = True
    try:
        target = authorize_downgrade(assessment, restored=restored, losses_confirmed=True)
    except UnsafeDowngradeError as error:
        _tell(parent, str(error), title, show_modal)
        return SwitchOutcome(False, str(error), cancelled=True)
    offer = next(
        (
            o
            for o in offers_from_feed(feed, portable=_portable(app_key))
            if o.version == target.version
        ),
        None,
    )
    if offer is None:
        message = (
            f"Stable {target.version} has no download for this copy of {name}, so nothing changed."
        )
        _tell(parent, message, title, show_modal)
        return SwitchOutcome(False, message, cancelled=True)
    new_state = ChannelState(channel=STABLE, set_by="you")
    save_channels(load_channels().with_state(app_key, new_state))
    history.record(
        app_key,
        "channel_changed",
        from_version=installed,
        to_version=target.version,
        channel=STABLE,
        detail=f"Went back to Stable {target.version}.",
    )
    install_release(offer)
    return SwitchOutcome(True, f"{name} is back on Stable.", {app_key: new_state})
