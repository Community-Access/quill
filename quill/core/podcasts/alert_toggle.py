"""Turning new-episode alerts on or off for one podcast, from its own row.

3.1.0 made the alert mode fully expressible -- on, quiet or off, set on the
podcast, on a folder, or as the shared default -- and reachable only by opening
settings. That is the right home for a three-way choice and the wrong cost for
the common one, which is somebody standing on a row thinking "tell me about
this one" or "stop telling me about this one".

### Why it is a toggle, and why "off" is not one of its two states

Off is a real answer and it stays in settings. It is not what somebody means
from a row, and it is the one mode that can lose news. The two states this
switches between are exactly the two that differ in whether you are
interrupted:

* **On** -- the desktop notification and the sound.
* **Quiet** -- still written to Notifications, still counted, never
  interrupting.

So pressing this can never cost anybody an episode in either direction, which
is what makes it safe to put one keystroke away. A show whose stored mode is
*off* reads as "not notifying you", and the toggle turns it on -- the direction
somebody who went looking for this verb is asking for.

wx-free and pure: it reads and writes the library it is handed, and the caller
owns loading and saving.
"""

from __future__ import annotations

from typing import Any

from quill.core.podcasts import episode_alerts

__all__ = ["alert_now", "menu_label", "outcome_sentence", "toggle"]


def alert_now(library: Any, show: Any) -> str:
    """The alert mode in force for *show*. Never raises.

    The *effective* mode, resolved through the whole chain rather than the
    show's own override: a menu reading only the override would offer to turn
    on something a folder already turned on, and then appear to do nothing.
    """
    try:
        return episode_alerts.alert_for_show(library.effective_settings(show))
    except Exception:  # noqa: BLE001 - an unreadable chain is the shipped default
        return episode_alerts.ALERT_DEFAULT


def menu_label(alerts_on: bool) -> str:
    """What the row's menu item says, given whether alerts are on right now.

    It names what pressing it *does*, not what is currently true: a menu item
    that reports state reads to a screen reader as a claim about the row, and
    the listener finds out it was a verb only by pressing it.

    A bool rather than the mode, because that is what both callers hold -- the
    menu builder gets it on :class:`FolderState`, having resolved the chain
    once while it was reading the library anyway.
    """
    if alerts_on:
        return "Stop &Notifying About This Podcast"
    return "&Notify Me About This Podcast"


def toggle(library: Any, show: Any) -> str:
    """Flip *show* between on and quiet. Returns the mode now in force.

    Writes a per-show override of that one field, so everything else about the
    podcast keeps following its folder and the shared default.
    """
    wanted = (
        episode_alerts.ALERT_QUIET
        if alert_now(library, show) == episode_alerts.ALERT_ON
        else episode_alerts.ALERT_ON
    )
    library.apply_show_override(show, new_episode_alert=wanted)
    return wanted


def outcome_sentence(title: str, alert: str) -> str:
    """What to say afterwards: the outcome, which nothing else reads out.

    It names what changed *and* what did not. Turning the interruption off
    leaves the notification list alone, and somebody who is not told that
    reasonably believes they have just stopped hearing about the show at all.
    """
    name = str(title or "").strip() or "This podcast"
    if alert == episode_alerts.ALERT_ON:
        return f"{name}: new episodes will notify you."
    return f"{name}: new episodes will be listed in Notifications only."
