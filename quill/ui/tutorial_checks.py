"""Does the app agree that the step was done? The live half of the tutorials.

A tutorial step may name a ``check`` -- the id of a question about the app's
state right now. The lesson window takes a **baseline** when it shows the
step, then asks this module the same question every second or so until the
answer changes. When it does, the lesson says what it noticed and moves on.

Three rules, all of them about not being a nuisance:

* **It watches state, never keystrokes.** "Something is playing" is true
  whether you pressed the key, used the menu, clicked the status bar or asked
  the palette. A checker that watched for one route would be teaching the
  route rather than the thing.
* **It is a courtesy, not a gate.** Every step can be advanced by hand, and a
  check that never comes true costs one keypress. Nothing is graded and there
  is no way to fail a lesson.
* **It never guesses.** Anything it cannot read -- an attribute a future
  refactor renames, a controller that is not up yet -- answers "cannot tell",
  which the window treats exactly like a step with no check at all.

Two halves. **This module** answers the questions every app shares: is a peer
window open, and the handful of universal states. **Each app supplies a
probe** -- ``quill/ui/radio/tutorial_checks.py`` and its siblings -- answering
the questions only that app can, because "a recording is running" means
nothing in Quill Weather and "an alert is showing" means nothing in Radio.

An app registers its probe by passing it to the window; a check nothing can
answer is never satisfied, which the window treats exactly like a step with no
check at all. The content tests assert every check a lesson names against the
union of the shared ids and that app's own.
"""

from __future__ import annotations

from typing import Any, Protocol

#: The prefix that makes a check "is this peer window open?", followed by the
#: window's registered title. Only an app's real peer windows can be asked --
#: a modal dialog blocks the lesson window anyway, so watching for one would
#: be watching for something nobody could see happen.
WINDOW_PREFIX = "window:"

#: The peer windows a step may watch for, per app, by the title they register
#: under in :class:`quill.ui.window_menu.WindowManager`. Kept here as data
#: rather than read from the UI at import time so the content test can check a
#: lesson's ``window:`` check without building a window -- and so a surface
#: that stops being a peer breaks the test rather than the lesson.
PEER_WINDOWS: dict[str, frozenset[str]] = {
    "radio": frozenset({
        "Quill Radio",
        "Browse Stations",
        "Search Stations",
        "Manage Favorites",
        "Radio Recordings",
        "Schedule Recording",
        "Downloads",
        "Song History",
        "Now Playing",
        "Player",
    }),
    # Cast and QUILL keep their surfaces as modal dialogs rather than peer
    # windows, so there is nothing for a window: check to watch there. Their
    # lessons use their own probes' state checks instead.
    "cast": frozenset(),
    "weather": frozenset({"Quill Weather"}),
    "quill": frozenset(),
}


def peer_windows(app_id: str) -> frozenset[str]:
    """The peer-window titles *app_id* may watch for."""
    return PEER_WINDOWS.get(app_id, frozenset())


#: Checks every app shares. There is deliberately only one kind: an app's own
#: verbs ("something is playing", "an alert is showing") mean different things
#: in different apps, and a shared table of them would be a table of guesses.
#: ``window:<Title>`` is the exception because the window manager is shared.
_CHECKS: dict[str, str] = {}


class CheckProbe(Protocol):
    """What an app supplies so its own lessons can be watched.

    ``snapshot`` records whatever the app's checks compare against; ``answer``
    returns ``(satisfied, sentence)`` for one of that app's check ids, or
    ``None`` for an id it does not own -- which is how the shared checks and an
    app's own share one namespace without either having to know the other.
    """

    def snapshot(self, host: Any) -> dict[str, Any]: ...

    def answer(
        self, check: str, host: Any, baseline: dict[str, Any]
    ) -> tuple[bool, str] | None: ...

    def known(self) -> frozenset[str]: ...


def known_checks(probe: CheckProbe | None = None) -> frozenset[str]:
    """Every check id that can be answered: the shared ones, plus an app's own."""
    shared = frozenset(_CHECKS)
    return (shared | probe.known()) if probe is not None else shared


def open_titles(host: Any) -> frozenset[str]:
    """The titles of the peer windows open right now."""
    windows = getattr(host, "_windows", None)
    lister = getattr(windows, "open_titles", None)
    if lister is None:
        return frozenset()
    try:
        return frozenset(lister())
    except Exception:  # noqa: BLE001 - a window list is never worth an exception here
        return frozenset()


def snapshot(host: Any, probe: CheckProbe | None = None) -> dict[str, Any]:
    """What the app looked like when the step was shown.

    Deltas rather than absolutes wherever the question is "did you do it":
    somebody who already has 40 favorites has not failed the step about adding
    one, and an absolute test would either pass instantly or never.
    """
    taken: dict[str, Any] = {"windows": open_titles(host)}
    if probe is not None:
        taken.update(probe.snapshot(host))
    return taken


def evaluate(
    check: str,
    host: Any,
    baseline: dict[str, Any],
    probe: CheckProbe | None = None,
) -> tuple[bool, str]:
    """``(satisfied, sentence)`` for *check*. An unknown check is never satisfied.

    The sentence is what the lesson speaks when it moves you on, so it says
    what the app noticed rather than congratulating anybody.
    """
    if not check:
        return (False, "")
    if check.startswith(WINDOW_PREFIX):
        title = check[len(WINDOW_PREFIX) :]
        return ((title in open_titles(host)), f"{title} is open")
    if probe is not None:
        answered = probe.answer(check, host, baseline)
        if answered is not None:
            return answered
    return (False, "")
