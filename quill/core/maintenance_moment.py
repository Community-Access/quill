"""When maintenance may interrupt: never during the moment that matters (FUX-15).

An update offer, a one-time component prompt or a "downloaded, install now?"
window is maintenance. It is welcome at a quiet moment and unwelcome in four
places: while the person is recording, playing, dictating or broadcasting;
in the first minute after launch, when the screen reader is still reading the
window and the person is finding their place; in the seconds just after that
work stops or the app comes back to the front; while the person is typing;
and while this app is not the window in front.

:class:`MaintenanceMoment` is the one rule for all of them. An app asks it
whether an *automatic* offer may open now; when it may not, the offer is
held -- one per kind, the newest replacing an older one -- and the app is
told, once, a sentence saying what waits and how to reach it now. The app
polls :meth:`MaintenanceMoment.due` and runs what is due when the moment is
quiet. An explicit command (Help > Check for Updates) never waits: it takes the
held offer with :meth:`MaintenanceMoment.take` and runs it straight away.

Nothing here is a new notification centre: the sentence goes where each app
already records things (Notifications in QUILL, Update History in the apps
with release channels, the status bar everywhere).

A *probe* is a callable returning ``""`` when its work is idle, or the end of
the sentence "... waits until <phrase>" while it is busy -- "the recording
ends", "dictation ends". A probe that raises counts as idle: a broken probe
must never stop updates for good.

wx-free and strict-typed.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass

__all__ = [
    "FIRST_MINUTE",
    "INPUT_IDLE_SECONDS",
    "LAUNCH_SETTLE_SECONDS",
    "NOT_IN_FRONT",
    "QUIET_SETTLE_SECONDS",
    "SETTLING",
    "TYPING",
    "Decision",
    "MaintenanceMoment",
    "Probe",
]

Probe = Callable[[], str]

#: Nothing automatic opens in the first minute after launch.
LAUNCH_SETTLE_SECONDS = 60.0
#: After protected work stops, or the app comes back to the front, the moment
#: must stay quiet this long first, so an offer never lands on the keystroke
#: that stopped a recording or on somebody finding their place again.
QUIET_SETTLE_SECONDS = 20.0
#: No keyboard or mouse input for this long, so an offer never takes a
#: keystroke meant for the document (Enter would press its default button).
INPUT_IDLE_SECONDS = 10.0

FIRST_MINUTE = "the first minute after launch has passed"
SETTLING = "things have been quiet for a moment"
NOT_IN_FRONT = "you come back to this window"
TYPING = "you pause"
#: Reasons that are about timing rather than the person's work: the held line
#: does not name them, it says the offer waits for a quiet moment.
_TIMING = frozenset({FIRST_MINUTE, SETTLING, NOT_IN_FRONT, TYPING})


@dataclass(frozen=True)
class Decision:
    #: Run the offer now: the moment is quiet.
    run_now: bool
    #: The one sentence to record when the offer was held for the first time;
    #: empty when it runs now or was already said.
    line: str = ""


@dataclass
class _Held:
    label: str
    route: str
    run: Callable[[], object]


def _ask(probe: Probe) -> str:
    try:
        return str(probe() or "").strip()
    except Exception:  # noqa: BLE001 - a broken probe counts as idle
        return ""


class MaintenanceMoment:
    """Holds automatic maintenance until a quiet moment (see the module doc)."""

    def __init__(
        self,
        *,
        clock: Callable[[], float] = time.monotonic,
        launched: float | None = None,
    ) -> None:
        self._clock = clock
        self.launched = clock() if launched is None else launched
        self._last_busy: float | None = None
        self._held: dict[str, _Held] = {}
        self._said: set[tuple[str, str]] = set()

    # -- the rule ---------------------------------------------------------- #

    def hold_reason(
        self,
        probes: Iterable[Probe] = (),
        *,
        in_front: bool = True,
        input_idle: float | None = None,
    ) -> str:
        """Why an automatic offer must wait now, or ``""`` when it may open.

        *input_idle* is how many seconds since the last keyboard or mouse
        input on this computer, when the platform can tell (``None``: unknown).
        """
        now = self._clock()
        for probe in probes:
            reason = _ask(probe)
            if reason:
                self._last_busy = now
                return reason
        if not in_front:
            # Coming back to the window starts the settle again (FUX-15).
            self._last_busy = now
            return NOT_IN_FRONT
        if now - self.launched < LAUNCH_SETTLE_SECONDS:
            return FIRST_MINUTE
        if self._last_busy is not None and now - self._last_busy < QUIET_SETTLE_SECONDS:
            return SETTLING
        if input_idle is not None and input_idle < INPUT_IDLE_SECONDS:
            return TYPING
        return ""

    # -- offers -------------------------------------------------------------- #

    def offer(
        self,
        kind: str,
        label: str,
        run: Callable[[], object],
        *,
        route: str,
        probes: Iterable[Probe] = (),
        in_front: bool = True,
        input_idle: float | None = None,
    ) -> Decision:
        """Run *run* now (``run_now``), or hold it under *kind* until quiet.

        *label* names what waits ("Update 3.4.0"); *route* is the sentence that
        reaches it now ("Help, Check for Updates offers it now."). The held
        line is returned once per kind and label, never again on later polls.
        """
        probes = tuple(probes)
        reason = self.hold_reason(probes, in_front=in_front, input_idle=input_idle)
        if not reason:
            self._held.pop(kind, None)
            return Decision(run_now=True)
        self._held[kind] = _Held(label, route, run)
        key = (kind, label)
        if key in self._said:
            return Decision(run_now=False)
        self._said.add(key)
        if reason in _TIMING:
            line = f"{label} is ready and waits for a quiet moment."
        else:
            line = f"{label} waits until {reason}."
        if route:
            line = f"{line} {route}"
        return Decision(run_now=False, line=line)

    def due(
        self,
        probes: Iterable[Probe] = (),
        *,
        in_front: bool = True,
        input_idle: float | None = None,
    ) -> Callable[[], object] | None:
        """The oldest held offer, removed, when it may run now; else ``None``.

        One at a time: after one window closes, the moment is asked again, so
        a second offer never opens straight on top of the first.
        """
        if not self._held:
            return None
        if self.hold_reason(probes, in_front=in_front, input_idle=input_idle):
            return None
        kind = next(iter(self._held))
        return self._held.pop(kind).run

    def take(self, kind: str) -> Callable[[], object] | None:
        """Remove and return the held offer of *kind*, for an explicit command."""
        held = self._held.pop(kind, None)
        return held.run if held is not None else None

    def waiting(self) -> list[str]:
        """The labels of what is held, oldest first."""
        return [held.label for held in self._held.values()]

    @property
    def holding(self) -> bool:
        return bool(self._held)
