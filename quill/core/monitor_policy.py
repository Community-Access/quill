"""One shared contract for every background watcher QUILL runs.

QUILL quietly watches several things on your behalf: a watched folder, the
weather, podcast feeds, a GitHub account. Each of those grew its own habits.
The watched folder had a poll interval; the weather had two; podcasts and
GitHub had none at all. None of them could tell you they were still alive, and
none of them let you say whether a *result* should cut across whatever your
screen reader was already saying.

The accessibility assessment made the pattern plain: an ambient monitor is only
trustworthy when the user controls three things, and controls them the same way
everywhere.

1. **How often it checks** -- the poll interval.
2. **Whether the check itself makes a sound** -- the audible tick. A short
   earcon on every check, so silence means "stopped", not "nothing new". Off by
   default, because a metronome nobody asked for is worse than silence.
3. **Whether a result interrupts speech** -- some people want a new-episode
   notice to wait its turn; some want a weather warning to cut in immediately.
   That is a preference, not a property of the message.

This module is the contract, not any particular monitor: a :class:`MonitorPolicy`
value, a per-monitor table of sane defaults and hard clamps, and a resolver that
reads a settings object by monitor name. A zero-second poll is not
representable -- every monitor declares its own floor and the clamp is applied
on the way in, on load, and again on resolve.

:meth:`MonitorPolicy.describe` renders the whole triple as one spoken English
sentence ("Checks every 15 minutes, ticks audibly, does not interrupt speech"),
which is QUILL's convention for any rule complex enough that a row of
checkboxes would make you assemble the meaning yourself.

wx-free, strict-typed.
"""

from __future__ import annotations

from dataclasses import dataclass

from quill.core.announce.message import Severity
from quill.core.sound_events import SoundEvent

#: Monitor names. These are the keys used by :func:`resolve_monitor_policy` and
#: the ids a UI passes when it wants "the policy for this watcher".
MONITOR_WATCH_FOLDER = "watch_folder"
MONITOR_WEATHER = "weather"
MONITOR_PODCASTS = "podcasts"
MONITOR_GITHUB = "github"

_SECONDS_PER_MINUTE = 60
_SECONDS_PER_HOUR = 3600


@dataclass(frozen=True, slots=True)
class MonitorSpec:
    """The per-monitor defaults and limits behind the shared triple.

    ``interval_setting`` names the :class:`~quill.core.settings.Settings` field
    holding the user's chosen cadence, and ``interval_unit`` says whether that
    field is stored in seconds or minutes -- a watched folder is tuned in
    seconds, a feed check in minutes, and forcing either into the other's unit
    would make one of the two spin boxes absurd.

    The weather monitor keeps its cadence in its own config file
    (``core/weather/monitor.py``) rather than in ``Settings``; its
    ``interval_setting`` is therefore empty and callers pass the value in via
    ``interval_seconds``.
    """

    name: str
    label: str
    default_seconds: int
    minimum_seconds: int
    maximum_seconds: int
    interval_setting: str = ""
    interval_unit: str = "seconds"
    tick_setting: str = ""
    interrupt_setting: str = ""

    def clamp(self, seconds: object) -> int:
        """``seconds`` forced into this monitor's legal range.

        Garbage, zero and negatives all land on the monitor's floor rather
        than raising: a settings file is user-editable, and a broken value must
        not stop a watcher from running. What it must never do is poll
        continuously, which is exactly what a 0 would mean.
        """
        try:
            value = int(seconds)  # type: ignore[call-overload]
        except (TypeError, ValueError):
            return self.default_seconds
        value = int(value)
        if value < self.minimum_seconds:
            return self.minimum_seconds
        if value > self.maximum_seconds:
            return self.maximum_seconds
        return value


#: Every monitor QUILL runs in the background, with its own cadence limits.
#: Watched folders are tuned in seconds because a dropped file should be picked
#: up while you are still looking at the folder; feed and account checks are
#: tuned in minutes because a server does not thank you for a faster loop.
MONITOR_SPECS: dict[str, MonitorSpec] = {
    MONITOR_WATCH_FOLDER: MonitorSpec(
        name=MONITOR_WATCH_FOLDER,
        label="Watched folders",
        default_seconds=5,
        minimum_seconds=2,
        maximum_seconds=300,
        interval_setting="watch_folder_poll_interval_seconds",
        interval_unit="seconds",
        tick_setting="watch_folder_audible_tick",
        interrupt_setting="watch_folder_interrupt_speech",
    ),
    MONITOR_WEATHER: MonitorSpec(
        name=MONITOR_WEATHER,
        label="Weather monitoring",
        default_seconds=10 * _SECONDS_PER_MINUTE,
        minimum_seconds=5 * _SECONDS_PER_MINUTE,
        maximum_seconds=120 * _SECONDS_PER_MINUTE,
        interval_setting="",
        interval_unit="minutes",
        tick_setting="weather_monitor_audible_tick",
        interrupt_setting="weather_monitor_interrupt_speech",
    ),
    MONITOR_PODCASTS: MonitorSpec(
        name=MONITOR_PODCASTS,
        label="Podcast new-episode check",
        default_seconds=60 * _SECONDS_PER_MINUTE,
        minimum_seconds=5 * _SECONDS_PER_MINUTE,
        maximum_seconds=24 * _SECONDS_PER_HOUR,
        interval_setting="podcast_check_interval_minutes",
        interval_unit="minutes",
        tick_setting="podcast_check_audible_tick",
        interrupt_setting="podcast_check_interrupt_speech",
    ),
    MONITOR_GITHUB: MonitorSpec(
        name=MONITOR_GITHUB,
        label="GitHub check",
        default_seconds=15 * _SECONDS_PER_MINUTE,
        minimum_seconds=5 * _SECONDS_PER_MINUTE,
        maximum_seconds=24 * _SECONDS_PER_HOUR,
        interval_setting="github_poll_interval_minutes",
        interval_unit="minutes",
        tick_setting="github_poll_audible_tick",
        interrupt_setting="github_poll_interrupt_speech",
    ),
}


def monitor_spec(monitor: str) -> MonitorSpec:
    """The spec for *monitor*, or a conservative unknown-monitor fallback.

    An unknown name is not an error: a Quillin or a companion app may ask about
    a watcher this build has never heard of, and answering "five minutes,
    silent, polite" is more useful than raising.
    """
    spec = MONITOR_SPECS.get(monitor)
    if spec is not None:
        return spec
    return MonitorSpec(
        name=monitor,
        label=monitor.replace("_", " ").strip() or "Monitor",
        default_seconds=5 * _SECONDS_PER_MINUTE,
        minimum_seconds=5,
        maximum_seconds=24 * _SECONDS_PER_HOUR,
    )


@dataclass(frozen=True, slots=True)
class MonitorPolicy:
    """How one background watcher behaves, as the user asked it to.

    The three fields are the whole contract. Everything else on this class is a
    rendering of them: the sound id to post for a tick, the severity a result
    should be announced at, and the spoken sentence that describes the lot.
    """

    monitor: str = ""
    poll_interval_seconds: int = 300
    audible_tick: bool = False
    interrupt_speech: bool = False

    @property
    def poll_interval_ms(self) -> int:
        """The interval in milliseconds, for a timer that wants it that way."""
        return self.poll_interval_seconds * 1000

    @property
    def poll_interval_minutes(self) -> int:
        """The interval rounded to whole minutes (at least one)."""
        return max(1, round(self.poll_interval_seconds / _SECONDS_PER_MINUTE))

    @property
    def tick_sound_event(self) -> str:
        """The earcon id for one check, or ``""`` when ticks are off.

        The progress tick is deliberately reused rather than given a new cue:
        it already means "still working" everywhere else in QUILL, and a
        monitor's heartbeat is the same idea on a longer timescale.
        """
        return str(SoundEvent.PROGRESS_TICK) if self.audible_tick else ""

    @property
    def severity(self) -> Severity:
        """The severity a *result* from this monitor should be announced at.

        ``WARNING`` interrupts under the announcement policy; ``ROUTINE`` waits
        its turn. Errors are not routed through here -- a monitor that breaks
        still raises its own ``ERROR``, which no setting can suppress.
        """
        return Severity.WARNING if self.interrupt_speech else Severity.ROUTINE

    @property
    def force_speech(self) -> bool:
        """The legacy ``_announce(..., force=)`` form of :attr:`severity`."""
        return self.interrupt_speech

    def is_due(self, last_check: float, now: float) -> bool:
        """Whether a check started at *last_check* is old enough to repeat.

        A ``last_check`` of 0 (never checked) is always due, and a clock that
        has jumped backwards is treated as due rather than blocking the monitor
        until the clock catches up.
        """
        if last_check <= 0:
            return True
        elapsed = now - last_check
        if elapsed < 0:
            return True
        return elapsed >= self.poll_interval_seconds

    def describe(self) -> str:
        """The whole triple as one spoken English sentence.

        "Checks every 15 minutes, ticks audibly, does not interrupt speech."
        """
        tick = "ticks audibly" if self.audible_tick else "checks silently"
        interrupt = "interrupts speech" if self.interrupt_speech else "does not interrupt speech"
        return f"Checks {interval_phrase(self.poll_interval_seconds)}, {tick}, {interrupt}."


def interval_phrase(seconds: int) -> str:
    """A cadence as spoken English: "every 30 seconds", "every 2 hours".

    Whole hours and whole minutes are named as such; anything else stays in the
    largest unit that divides it evenly, falling back to seconds. Nobody wants
    to hear "every 5400 seconds".
    """
    value = max(0, int(seconds))
    if value < _SECONDS_PER_MINUTE:
        return "every second" if value == 1 else f"every {value} seconds"
    if value % _SECONDS_PER_HOUR == 0:
        hours = value // _SECONDS_PER_HOUR
        return "every hour" if hours == 1 else f"every {hours} hours"
    if value % _SECONDS_PER_MINUTE == 0:
        minutes = value // _SECONDS_PER_MINUTE
        return "every minute" if minutes == 1 else f"every {minutes} minutes"
    minutes, remainder = divmod(value, _SECONDS_PER_MINUTE)
    minute_word = "minute" if minutes == 1 else "minutes"
    second_word = "second" if remainder == 1 else "seconds"
    return f"every {minutes} {minute_word} and {remainder} {second_word}"


def clamp_interval_seconds(monitor: str, seconds: object) -> int:
    """*seconds* clamped into *monitor*'s legal range (never zero)."""
    return monitor_spec(monitor).clamp(seconds)


def clamp_interval_minutes(monitor: str, minutes: object) -> int:
    """*minutes* clamped into *monitor*'s legal range, returned in minutes.

    The settings loader uses this so a hand-edited settings file can never
    persist a cadence the monitor would have to override at run time.
    """
    spec = monitor_spec(monitor)
    try:
        value = int(minutes)  # type: ignore[call-overload]
    except (TypeError, ValueError):
        return max(1, spec.default_seconds // _SECONDS_PER_MINUTE)
    clamped = spec.clamp(value * _SECONDS_PER_MINUTE)
    return max(1, clamped // _SECONDS_PER_MINUTE)


def resolve_monitor_policy(
    settings: object | None,
    monitor: str,
    *,
    interval_seconds: int | None = None,
) -> MonitorPolicy:
    """The live policy for *monitor*, read off *settings*.

    ``settings`` is duck-typed on purpose: ``Settings``, a companion app's own
    config object, or ``None`` all work, and anything missing falls back to the
    monitor's default. ``interval_seconds`` overrides the settings lookup for a
    monitor that stores its cadence elsewhere (the weather watch keeps its
    interval in its own config file).
    """
    spec = monitor_spec(monitor)
    if interval_seconds is not None:
        resolved_seconds = spec.clamp(interval_seconds)
    elif spec.interval_setting:
        raw = getattr(settings, spec.interval_setting, None)
        if raw is None:
            resolved_seconds = spec.default_seconds
        elif spec.interval_unit == "minutes":
            resolved_seconds = spec.clamp(clamp_interval_minutes(monitor, raw) * 60)
        else:
            resolved_seconds = spec.clamp(raw)
    else:
        resolved_seconds = spec.default_seconds
    return MonitorPolicy(
        monitor=spec.name,
        poll_interval_seconds=resolved_seconds,
        audible_tick=_flag(settings, spec.tick_setting),
        interrupt_speech=_flag(settings, spec.interrupt_setting),
    )


def _flag(settings: object | None, attribute: str) -> bool:
    """A boolean setting, defaulting to off when absent or unreadable.

    Off is the only safe default for both flags in the triple: an unexpected
    tick is noise, and an unexpected interruption talks over a screen reader
    mid-sentence.
    """
    if not attribute:
        return False
    return bool(getattr(settings, attribute, False))


__all__ = [
    "MONITOR_GITHUB",
    "MONITOR_PODCASTS",
    "MONITOR_SPECS",
    "MONITOR_WATCH_FOLDER",
    "MONITOR_WEATHER",
    "MonitorPolicy",
    "MonitorSpec",
    "clamp_interval_minutes",
    "clamp_interval_seconds",
    "interval_phrase",
    "monitor_spec",
    "resolve_monitor_policy",
]
