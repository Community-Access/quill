"""Plain-language sentences about alert choices: what is being watched, and what
would happen to one alert. Split from ``alert_rules`` (GATE-11); wx-free."""

from __future__ import annotations

from quill.core.weather.alert_rules import (
    KIND_LABELS,
    KINDS,
    SEVERITIES,
    AlertChoices,
    Decision,
    Delivery,
    Selection,
    severity_of,
)
from quill.core.weather.models import WeatherAlert


def _join(items: list[str]) -> str:
    if len(items) <= 1:
        return "".join(items)
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def describe_selection(selection: Selection, *, extreme_always: bool = True) -> str:
    """'tornado, severe thunderstorm and flash flood warnings, and anything Extreme'."""
    if selection.preset == "essentials":
        return "tornado, severe thunderstorm and flash flood warnings, and anything Extreme"
    if selection.preset == "safety":
        return "all warnings, and Extreme or Severe watches" + (
            ", and anything Extreme" if extreme_always else ""
        )
    if selection.preset == "everything":
        return "every alert"
    c = selection.custom
    what = _join([x.lower() if x != "Other" else "other" for x in c.categories] + c.events)
    if not what:
        what = "every type of alert"
    kinds = _join([KIND_LABELS[k].lower() for k in KINDS if k in c.kinds]) if c.kinds else ""
    text = what + (f", {kinds} only" if kinds else "")
    if c.severities and set(c.severities) != set(SEVERITIES):
        text += f", severity {_join([s for s in SEVERITIES if s in c.severities])}"
    if c.skip_events:
        text += f", except {_join(c.skip_events)}"
    if extreme_always:
        text += ", and anything Extreme"
    return text


def describe_choices(choices: AlertChoices, watched: int | str) -> str:
    """The one sentence spoken after a save. ``watched`` is a count, or the places
    sentence already worded ("Watching 3 of 5 places. Cabin is snoozed until 6 PM.")."""
    if isinstance(watched, str):
        places = watched
    elif watched == 0:
        places = "Not watching any places."
    else:
        places = "Watching 1 place." if watched == 1 else f"Watching {watched} places."
    told = describe_selection(choices.general.selection, extreme_always=choices.extreme_always)
    sentence = f"{places} Telling you about {told}."
    if not choices.extreme_always:
        sentence += " Extreme alerts follow your choices like any other."
    if choices.quiet.enabled:
        tail = (
            "Extreme alerts still speak."
            if choices.quiet.extreme_breaks_through
            else "Nothing breaks through."
        )
        sentence += f" Quiet hours {choices.quiet.start} to {choices.quiet.end}. {tail}"
    return sentence


def describe_decision(decision: Decision, place_label: str) -> str:
    """One sentence: what would happen to this alert."""
    a = decision.alert
    sev = severity_of(a)
    name = f"A {a.event} ({sev})" if a.event else f"A {sev} alert"
    where = f" at {place_label}" if place_label else ""
    if decision.hidden:
        why = decision.reason or "your choices"
        return (
            f"{name}{where} would not be spoken or sounded because of {why}. "
            "It would still appear in the alert list."
        )
    how = {
        Delivery.INTERRUPT: "spoken, interrupting your screen reader, with the alert sound",
        Delivery.QUIET: "spoken quietly, waiting its turn, with the alert sound",
        Delivery.SOUND: "announced by the alert sound only",
    }[decision.delivery]
    extra = " It is told because Extreme alerts are always told." if decision.forced_extreme else ""
    return f"{name}{where} would be {how}.{extra}"


def sample_alert(event: str, severity: str) -> WeatherAlert:
    """A sample alert for the dialog's Preview."""
    urgency = "Immediate" if severity in ("Extreme", "Severe") else "Expected"
    return WeatherAlert(
        id="sample", event=event, severity=severity, urgency=urgency, headline=f"Sample {event}"
    )
