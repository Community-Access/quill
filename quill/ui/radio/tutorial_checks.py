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

The check ids are content, so they live beside the lessons that use them and
:func:`known_checks` is what the test asserts against.
"""

from __future__ import annotations

from typing import Any

#: The prefix that makes a check "is this peer window open?", followed by the
#: window's registered title. Only Radio's real peer windows can be asked --
#: a modal dialog blocks the lesson window anyway, so watching for one would
#: be watching for something nobody could see happen.
WINDOW_PREFIX = "window:"

#: The peer windows a step may watch for, by the title they register under in
#: :class:`quill.ui.window_menu.WindowManager`. Kept here as a list rather than
#: read from the UI at import time so the content test can check a lesson's
#: ``window:`` check against it without building a window -- and so a surface
#: that stops being a peer breaks the test rather than the lesson.
PEER_WINDOW_TITLES: frozenset[str] = frozenset({
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
})

#: Every check id the content may use, with what a satisfied one says.
#: The sentence is spoken, so it is written as one: what changed, in words
#: somebody would use, and never "check passed".
_CHECKS: dict[str, str] = {
    "playing": "something is playing now",
    "paused": "it is paused",
    "muted": "the sound is muted",
    "volume-changed": "the volume moved",
    "favorite-added": "your favorites grew",
    "recording-started": "a recording is running",
    "recording-finished": "the recording finished",
}


def known_checks() -> frozenset[str]:
    """Every non-window check id this module can answer."""
    return frozenset(_CHECKS)


def _controller_state(host: Any) -> Any:
    controller = getattr(host, "_radio_controller", None)
    if controller is None:
        return None
    try:
        return controller.state
    except Exception:  # noqa: BLE001 - a half-built controller is not an error here
        return None


def _state_name(host: Any) -> str:
    state = _controller_state(host)
    inner = getattr(state, "state", None)
    name = getattr(inner, "name", "")
    return str(name)


def _volume(host: Any) -> int | None:
    state = _controller_state(host)
    value = getattr(state, "volume_percent", None)
    return int(value) if isinstance(value, int) else None


def _muted(host: Any) -> bool | None:
    state = _controller_state(host)
    value = getattr(state, "muted", None)
    return bool(value) if isinstance(value, bool) else None


def _favorite_count(host: Any) -> int | None:
    store = getattr(host, "_radio_favorites", None)
    entries = getattr(store, "favorites", None)
    try:
        return len(entries) if entries is not None else None
    except TypeError:
        return None


def _recording_count(host: Any) -> int | None:
    recorder = getattr(host, "_radio_recorder", None)
    if recorder is None:
        return None
    count = getattr(recorder, "active_count", None)
    if isinstance(count, int):
        return count
    flag = getattr(recorder, "is_recording", None)
    return int(bool(flag)) if isinstance(flag, bool) else None


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


def snapshot(host: Any) -> dict[str, Any]:
    """What the app looked like when the step was shown.

    Deltas rather than absolutes wherever the question is "did you do it":
    somebody who already has 40 favorites has not failed the step about adding
    one, and an absolute test would either pass instantly or never.
    """
    return {
        "state": _state_name(host),
        "volume": _volume(host),
        "muted": _muted(host),
        "favorites": _favorite_count(host),
        "recordings": _recording_count(host),
        "windows": open_titles(host),
    }


def evaluate(check: str, host: Any, baseline: dict[str, Any]) -> tuple[bool, str]:
    """``(satisfied, sentence)`` for *check*. An unknown check is never satisfied.

    The sentence is what the lesson speaks when it moves you on, so it says
    what the app noticed rather than congratulating anybody.
    """
    if not check:
        return (False, "")
    if check.startswith(WINDOW_PREFIX):
        title = check[len(WINDOW_PREFIX) :]
        return ((title in open_titles(host)), f"{title} is open")
    if check == "playing":
        return (_state_name(host) == "PLAYING", _CHECKS[check])
    if check == "paused":
        return (_state_name(host) == "PAUSED", _CHECKS[check])
    if check == "muted":
        muted = _muted(host)
        return (bool(muted), _CHECKS[check])
    if check == "volume-changed":
        before, now = baseline.get("volume"), _volume(host)
        return (before is not None and now is not None and now != before, _CHECKS[check])
    if check == "favorite-added":
        before, now = baseline.get("favorites"), _favorite_count(host)
        return (before is not None and now is not None and now > before, _CHECKS[check])
    if check == "recording-started":
        before, now = baseline.get("recordings"), _recording_count(host)
        return (before is not None and now is not None and now > before, _CHECKS[check])
    if check == "recording-finished":
        before, now = baseline.get("recordings"), _recording_count(host)
        return (
            before is not None and now is not None and before > 0 and now < before,
            _CHECKS[check],
        )
    return (False, "")
