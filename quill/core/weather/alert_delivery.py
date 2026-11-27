"""Turn one poll's result into what to say, sound and show, under the user's
alert choices. Pure and wx-free; the UI and the headless check both use it so
they cannot disagree.

``plan_poll`` is the only place an alert can be held back from speech, and it
returns everything it held back (``hidden``), so a caller can count it, list it
and keep it in the alert list. Nothing is dropped.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import time

from quill.core.weather.alert_rules import AlertChoices, Decision, Delivery, decide
from quill.core.weather.models import WeatherAlert
from quill.core.weather.monitor import MonitorState, MonitorUpdate


@dataclass(slots=True)
class PollPlan:
    """What one poll of one place should do."""

    #: Alerts to speak, in order, with how.
    speak: list[Decision] = field(default_factory=list)
    #: Alerts that get the sound only.
    sound_only: list[Decision] = field(default_factory=list)
    #: Alerts the choices held back (rules, quiet hours or list-only delivery).
    hidden: list[Decision] = field(default_factory=list)
    #: Alerts that are told and active right now (for the start summary).
    active_told: int = 0
    #: Every alert the user chose to hear about has gone and none remain.
    cleared: bool = False

    @property
    def interrupt(self) -> bool:
        return any(d.delivery is Delivery.INTERRUPT for d in self.speak)

    @property
    def sounds(self) -> list[Decision]:
        return [*self.speak, *self.sound_only]

    def spoken_update(self, is_baseline: bool) -> MonitorUpdate:
        """The update ``monitor.update_announcement`` should speak."""
        return MonitorUpdate(
            new_alerts=[d.alert for d in self.speak],
            all_cleared=self.cleared,
            is_baseline=is_baseline,
        )


def hidden_ids(
    current: list[WeatherAlert],
    place_id: str,
    choices: AlertChoices,
    at: time | None,
    silenced: str = "",
) -> set[str]:
    """Ids of the active alerts the choices would hold back right now."""
    return {a.id for a in current if a.id and decide(a, place_id, choices, at, silenced).hidden}


def plan_poll(
    update: MonitorUpdate,
    current: list[WeatherAlert],
    state: MonitorState,
    place_id: str,
    choices: AlertChoices,
    at: time | None,
    silenced: str = "",
) -> PollPlan:
    """Decide each alert of a successful poll. Never called for a failed one."""
    plan = PollPlan()
    decisions = {a.id: decide(a, place_id, choices, at, silenced) for a in current if a.id}
    told_now = {i for i, d in decisions.items() if not d.hidden}
    plan.active_told = len(told_now)
    plan.hidden = [d for d in decisions.values() if d.hidden]
    if update.is_baseline:
        state.told_ids = told_now
        return plan
    for alert in update.new_alerts:
        d = decisions.get(alert.id)
        if d is None or d.hidden:
            continue
        (plan.speak if d.speaks else plan.sound_only).append(d)
    # "Cleared" means everything that was told is gone, and nothing is active.
    plan.cleared = update.all_cleared and bool(state.told_ids)
    state.told_ids = (state.told_ids | told_now) & {a.id for a in current}
    return plan
