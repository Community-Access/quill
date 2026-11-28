"""Which alerts Weather Guardian tells you about, and how (Quill Weather 2.3.0).

The model is deliberately small enough to explain in a sentence:

* A **selection** says which alerts count. It is one or more *clauses*; an alert
  is selected when any clause matches. A clause narrows by alert type (a
  category such as "Tornado", or one named event), by kind (Warning, Watch,
  Advisory, Statement) and by the National Weather Service severity (Extreme,
  Severe, Moderate, Minor).
* A **delivery** says what happens to a selected alert: speak and interrupt,
  speak quietly, sound only, or show in the list only.
* **Presets** are ready-made selections (Essentials, Safety, Everything); Custom
  is your own.
* A place can use the general choices or its own. Quiet hours hold back
  everything below Extreme.

Two promises are enforced here and nowhere else, so they cannot drift:

1. **Nothing is lost.** An alert your choices hide from speech is still in the
   alert list and in Alert Feed Status; ``decide`` reports it as hidden, it never
   drops it.
2. **Extreme is never hidden by accident.** While ``extreme_always`` is on (the
   default) an Extreme alert is told whatever the selection says. Turning it off
   is a deliberate act the dialog warns about in plain words.

The default (``AlertChoices()``) is "Everything, delivered as before", so a user
who never opens the dialog sees no change from earlier versions.

Pure and wx-free; the clock is passed in.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import time
from enum import StrEnum

from quill.core.weather.models import ALERT_TIERS, WeatherAlert

logger = logging.getLogger(__name__)


SEVERITIES = ("Extreme", "Severe", "Moderate", "Minor")
KINDS = ("Warning", "Watch", "Advisory", "Statement")
KIND_LABELS = {
    "Warning": "Warnings",
    "Watch": "Watches",
    "Advisory": "Advisories",
    "Statement": "Statements and other notices",
}

CATEGORIES = (
    "Tornado",
    "Severe thunderstorm",
    "Flash flood and flood",
    "Winter weather",
    "Heat and cold",
    "Wind",
    "Fire weather",
    "Hurricane and tropical",
    "Coastal and marine",
    "Air quality",
    "Other",
)

#: The events the National Weather Service issues most, by category, for the
#: expandable lists. Any event not named here is still sorted into a category by
#: ``category_of`` (and "Other" when nothing fits), so a new product is never
#: silently outside every choice.
EVENTS_BY_CATEGORY: dict[str, tuple[str, ...]] = {
    "Tornado": ("Tornado Warning", "Tornado Watch"),
    "Severe thunderstorm": ("Severe Thunderstorm Warning", "Severe Thunderstorm Watch"),
    "Flash flood and flood": (
        "Flash Flood Warning",
        "Flash Flood Watch",
        "Flash Flood Statement",
        "Flood Warning",
        "Flood Watch",
        "Flood Advisory",
        "Flood Statement",
    ),
    "Winter weather": (
        "Winter Storm Warning",
        "Winter Storm Watch",
        "Blizzard Warning",
        "Ice Storm Warning",
        "Winter Weather Advisory",
        "Freezing Rain Advisory",
        "Lake Effect Snow Warning",
        "Lake Effect Snow Advisory",
        "Snow Squall Warning",
    ),
    "Heat and cold": (
        "Excessive Heat Warning",
        "Excessive Heat Watch",
        "Heat Advisory",
        "Extreme Cold Warning",
        "Extreme Cold Watch",
        "Cold Weather Advisory",
        "Wind Chill Warning",
        "Wind Chill Watch",
        "Wind Chill Advisory",
        "Freeze Warning",
        "Freeze Watch",
        "Frost Advisory",
    ),
    "Wind": (
        "High Wind Warning",
        "High Wind Watch",
        "Wind Advisory",
        "Extreme Wind Warning",
        "Dust Storm Warning",
        "Blowing Dust Advisory",
    ),
    "Fire weather": ("Red Flag Warning", "Fire Weather Watch", "Fire Warning"),
    "Hurricane and tropical": (
        "Hurricane Warning",
        "Hurricane Watch",
        "Tropical Storm Warning",
        "Tropical Storm Watch",
        "Storm Surge Warning",
        "Storm Surge Watch",
        "Hurricane Local Statement",
    ),
    "Coastal and marine": (
        "Coastal Flood Warning",
        "Coastal Flood Watch",
        "Coastal Flood Advisory",
        "Small Craft Advisory",
        "Gale Warning",
        "Special Marine Warning",
        "High Surf Advisory",
        "Rip Current Statement",
        "Beach Hazards Statement",
        "Tsunami Warning",
        "Tsunami Watch",
        "Tsunami Advisory",
    ),
    "Air quality": (
        "Air Quality Alert",
        "Air Stagnation Advisory",
        "Dense Smoke Advisory",
        "Ashfall Warning",
        "Ashfall Advisory",
    ),
    "Other": (
        "Special Weather Statement",
        "Dense Fog Advisory",
        "Civil Emergency Message",
        "Earthquake Warning",
        "Avalanche Warning",
        "Hazardous Materials Warning",
        "Shelter In Place Warning",
        "Evacuation Immediate",
        "Law Enforcement Warning",
    ),
}

_EVENT_TO_CATEGORY = {e.lower(): c for c, events in EVENTS_BY_CATEGORY.items() for e in events}

#: Keyword fallbacks for events not in the table, most specific first.
_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("tornado", "Tornado"),
    ("coastal flood", "Coastal and marine"),
    ("lakeshore flood", "Coastal and marine"),
    ("thunderstorm", "Severe thunderstorm"),
    ("flood", "Flash flood and flood"),
    ("blizzard", "Winter weather"),
    ("winter", "Winter weather"),
    ("snow", "Winter weather"),
    ("ice", "Winter weather"),
    ("freezing", "Winter weather"),
    ("heat", "Heat and cold"),
    ("cold", "Heat and cold"),
    ("chill", "Heat and cold"),
    ("freeze", "Heat and cold"),
    ("frost", "Heat and cold"),
    ("red flag", "Fire weather"),
    ("fire", "Fire weather"),
    ("hurricane", "Hurricane and tropical"),
    ("tropical", "Hurricane and tropical"),
    ("typhoon", "Hurricane and tropical"),
    ("storm surge", "Hurricane and tropical"),
    ("wind", "Wind"),
    ("dust", "Wind"),
    ("marine", "Coastal and marine"),
    ("craft", "Coastal and marine"),
    ("gale", "Coastal and marine"),
    ("surf", "Coastal and marine"),
    ("rip current", "Coastal and marine"),
    ("beach", "Coastal and marine"),
    ("tsunami", "Coastal and marine"),
    ("seas", "Coastal and marine"),
    ("air quality", "Air quality"),
    ("smoke", "Air quality"),
    ("ash", "Air quality"),
    ("stagnation", "Air quality"),
)


def category_of(event: str) -> str:
    """The category an event belongs to ("Other" when nothing fits)."""
    name = event.strip().lower()
    if name in _EVENT_TO_CATEGORY:
        return _EVENT_TO_CATEGORY[name]
    for word, category in _KEYWORDS:
        if word in name:
            return category
    return "Other"


def kind_of(event: str) -> str:
    """Warning, Watch, Advisory or Statement (the last for everything else)."""
    name = event.strip().lower()
    if name.endswith("warning") or name.endswith("emergency") or name == "evacuation immediate":
        return "Warning"
    if name.endswith("watch"):
        return "Watch"
    if name.endswith("advisory") or name.endswith("alert"):
        return "Advisory"
    return "Statement"


def severity_of(alert: WeatherAlert) -> str:
    """The NWS severity, with anything unrecognised treated as Minor (never as
    something that would be hidden by a "this severity and above" choice only
    because the service did not say)."""
    value = alert.severity.strip().capitalize()
    return value if value in SEVERITIES else "Minor"


class Delivery(StrEnum):
    AUTO = "auto"  # as before: interrupt for urgent alerts, speak the rest
    INTERRUPT = "interrupt"  # speak and interrupt
    QUIET = "quiet"  # speak quietly: waits its turn
    SOUND = "sound"  # sound only
    LIST = "list"  # show in the list only


DELIVERY_LABELS = {
    Delivery.AUTO: "As before: interrupt for urgent alerts, speak the rest",
    Delivery.INTERRUPT: "Speak and interrupt",
    Delivery.QUIET: "Speak quietly",
    Delivery.SOUND: "Sound only",
    Delivery.LIST: "Show in the list only",
}


@dataclass(slots=True)
class Clause:
    """One AND of narrowing choices. An empty list means "any"."""

    categories: list[str] = field(default_factory=list)
    #: Specific events (named exactly) that count even outside ``categories``.
    events: list[str] = field(default_factory=list)
    #: Specific events switched off even inside ``categories``.
    skip_events: list[str] = field(default_factory=list)
    kinds: list[str] = field(default_factory=list)
    severities: list[str] = field(default_factory=list)

    def matches(self, alert: WeatherAlert) -> bool:
        event = alert.event.strip()
        low = event.lower()
        if any(low == s.lower() for s in self.skip_events):
            return False
        if self.kinds and kind_of(event) not in self.kinds:
            return False
        if self.severities and severity_of(alert) not in self.severities:
            return False
        if not self.categories and not self.events:
            return True
        if any(low == e.lower() for e in self.events):
            return True
        return bool(self.categories) and category_of(event) in self.categories


PRESETS = ("everything", "essentials", "safety", "custom")
PRESET_LABELS = {
    "everything": "Everything",
    "essentials": "Essentials",
    "safety": "Safety",
    "custom": "Custom",
}
PRESET_HELP = {
    "everything": "Every alert the National Weather Service issues for your places.",
    "essentials": ("Tornado, severe thunderstorm and flash flood warnings, and anything Extreme."),
    "safety": "All warnings, and watches that are Extreme or Severe.",
    "custom": "Your own choice of alert types, kinds and severities.",
}


@dataclass(slots=True)
class Selection:
    preset: str = "everything"
    #: Used when ``preset`` is "custom".
    custom: Clause = field(default_factory=Clause)

    def clauses(self) -> list[Clause]:
        if self.preset == "essentials":
            return [
                Clause(
                    events=["Tornado Warning", "Severe Thunderstorm Warning", "Flash Flood Warning"]
                ),
                Clause(severities=["Extreme"]),
            ]
        if self.preset == "safety":
            return [
                Clause(kinds=["Warning"]),
                Clause(kinds=["Watch"], severities=["Extreme", "Severe"]),
            ]
        if self.preset == "custom":
            return [self.custom]
        return [Clause()]

    def matches(self, alert: WeatherAlert) -> bool:
        return any(c.matches(alert) for c in self.clauses())


@dataclass(slots=True)
class RuleSet:
    selection: Selection = field(default_factory=Selection)
    delivery: Delivery = Delivery.AUTO


@dataclass(slots=True)
class QuietHours:
    enabled: bool = False
    start: str = "22:00"
    end: str = "07:00"
    #: Extreme alerts still speak during quiet hours.
    extreme_breaks_through: bool = True

    def active_at(self, moment: time) -> bool:
        if not self.enabled:
            return False
        start, end = _parse_clock(self.start), _parse_clock(self.end)
        if start == end:
            return False
        if start < end:
            return start <= moment < end
        return moment >= start or moment < end  # spans midnight


def _parse_clock(text: str) -> time:
    hours, _, minutes = text.partition(":")
    return time(max(0, min(23, int(hours))), max(0, min(59, int(minutes or 0))))


def valid_clock(text: str) -> bool:
    try:
        hours, sep, minutes = text.strip().partition(":")
        return bool(sep) and 0 <= int(hours) <= 23 and 0 <= int(minutes) <= 59
    except ValueError:
        return False


@dataclass(slots=True)
class AlertChoices:
    general: RuleSet = field(default_factory=RuleSet)
    #: Place id -> that place's own choices (absent: the place uses the general ones).
    places: dict[str, RuleSet] = field(default_factory=dict)
    quiet: QuietHours = field(default_factory=QuietHours)
    #: Tell me about every Extreme alert whatever else I chose.
    extreme_always: bool = True
    #: Severity -> sound file ("" or absent: the standard alert sound).
    sounds: dict[str, str] = field(default_factory=dict)

    def rules_for(self, place_id: str) -> RuleSet:
        return self.places.get(place_id) or self.general

    def is_default(self) -> bool:
        return AlertChoices() == self


@dataclass(slots=True)
class Decision:
    """What to do with one alert at one place."""

    alert: WeatherAlert
    delivery: Delivery  # never AUTO: resolved
    #: True when the alert will not be spoken or sounded (the list still has it).
    hidden: bool
    #: Why, in a clause: "your choices", "quiet hours", "list only", "" when told.
    reason: str = ""
    forced_extreme: bool = False

    @property
    def speaks(self) -> bool:
        return self.delivery in (Delivery.INTERRUPT, Delivery.QUIET)

    @property
    def sounds(self) -> bool:
        return self.delivery in (Delivery.INTERRUPT, Delivery.QUIET, Delivery.SOUND)


_URGENT_RANK = ALERT_TIERS.index("Urgent")


def decide(
    alert: WeatherAlert,
    place_id: str,
    choices: AlertChoices,
    at: time | None = None,
    silenced: str = "",
) -> Decision:
    """Apply the user's choices to one alert for one place.

    ``silenced`` names why the whole place is quiet right now ("a snooze", "its
    schedule"); it is held back exactly like quiet hours, and an Extreme alert
    breaks through under the same rule."""
    rules = choices.rules_for(place_id)
    extreme = severity_of(alert) == "Extreme"
    selected = rules.selection.matches(alert)
    forced = False
    if not selected and extreme and choices.extreme_always:
        selected, forced = True, True
    if not selected:
        return Decision(alert, Delivery.LIST, hidden=True, reason="your alert choices")
    delivery = rules.delivery
    if delivery is Delivery.AUTO:
        delivery = Delivery.INTERRUPT if alert.tier_rank <= _URGENT_RANK else Delivery.QUIET
    if forced and delivery is Delivery.LIST:
        delivery = Delivery.INTERRUPT  # an Extreme alert is never list-only by accident
    hold = silenced or ("quiet hours" if at is not None and choices.quiet.active_at(at) else "")
    if hold and not (extreme and choices.quiet.extreme_breaks_through):
        return Decision(alert, Delivery.LIST, hidden=True, reason=hold)
    if delivery is Delivery.LIST:
        return Decision(alert, Delivery.LIST, hidden=True, reason="the list-only delivery")
    return Decision(alert, delivery, hidden=False, forced_extreme=forced)
