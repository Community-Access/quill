"""QUILL Transcribe's wake phrase, held key and status sentence (D-9, D-6).

Three small decisions, kept here so they are tested without a window:

* :class:`KeyHeldGate` -- **what is said while the start and stop key is held
  waits until it comes up.** A system-wide key needs Ctrl or Alt
  (``family_chords.show_hide_key_problem``), and nothing can be typed into
  another program while one of those is down: the letters would arrive as
  shortcuts, which is why the injector waits for them to be let go
  (``text_injector._wait_for_modifiers_released``) and gives up after two
  seconds. So holding the key to talk -- the editors' hold-to-talk, on QUILL
  Transcribe's own key -- keeps each finished phrase here and writes them, in
  order, the moment the key comes up. The gate sits between the recogniser and
  the controller, so a phrase that waits has not been parsed, composed or
  counted yet.
* :func:`standby_wanted` -- **when the wake phrase is listened for.** QUILL
  Transcribe types into whichever program is in front, so its microphone waits
  for the wake phrase only while another program is in front and that program
  is somewhere dictation would type: never while QUILL Transcribe's own window,
  a QUILL or QUILL Lite window (which has its own dictation), or a program on
  the never-type list is in front.
* :func:`status_sentence` -- **the Dictation Status key's one sentence**: the
  state, the program dictation writes into, the model, and how many phrases
  are held.

wx-free.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

__all__ = ["KeyHeldGate", "standby_wanted", "status_sentence"]


class KeyHeldGate:
    """The controller, as the recogniser sees it, with phrases held back while
    *held* answers ``True``. Everything else passes straight through."""

    def __init__(self, controller: Any, held: Callable[[], bool]) -> None:
        self._controller = controller
        self._held = held
        self._waiting: list[Any] = []

    @property
    def waiting(self) -> int:
        """How many phrases are waiting for the key to come up."""
        return len(self._waiting)

    def on_phrase(self, phrase: Any) -> None:
        if self._held():
            self._waiting.append(phrase)
            return
        self.release()  # anything still waiting goes first, in order
        self._controller.on_phrase(phrase)

    def on_finished(self) -> None:
        """The recogniser wrote its last phrase: the waiting ones go before the stop."""
        self.release()
        self._controller.on_finished()

    def release(self) -> None:
        """The key came up: write what was said while it was down."""
        waiting, self._waiting = self._waiting, []
        for phrase in waiting:
            self._controller.on_phrase(phrase)

    def drop(self) -> None:
        """The session is being thrown away (the app is closing)."""
        self._waiting.clear()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._controller, name)


def standby_wanted(
    *,
    wake_enabled: bool,
    refused: bool,
    front_allows: bool,
) -> bool:
    """Whether the microphone should wait for the wake phrase now.

    *refused*: dictation could not start at all (Safe Mode, Inkwell owns
    Dictate Anywhere, another program has the microphone, the model is
    missing). *front_allows*: another program is in front, it is not a QUILL
    window, and it is not on the never-type list.
    """
    return bool(wake_enabled and not refused and front_allows)


def _phrases(count: int) -> str:
    return f"{count} phrase{'s' if count != 1 else ''}"


def status_sentence(*, state: str, program: str, model: str, held: int) -> str:
    """One sentence: what dictation is doing, where, with which model, and
    what is held. *state* is the window's state line ("Listening", "Paused, 2
    phrases held", "Command mode"); *program* is "" when no field is locked."""
    words = state.split(".")[0].strip() or "Ready"
    lowered = words[0].lower() + words[1:]
    if lowered.startswith("paused"):
        lowered = "paused"  # the count is said once, at the end
    if lowered == "ready":
        doing = "Dictation is off"
    elif lowered.startswith(("listening", "paused", "waiting", "starting")):
        doing = f"Dictation is {lowered}"
    elif lowered == "hearing you":
        doing = "Dictation is hearing you"
    else:
        doing = f"Dictation is in {lowered}" if lowered.endswith("mode") else f"Dictation: {words}"
    no_field = lowered == "ready" or lowered.startswith(("listening for", "off", "waiting for you"))
    where = f" in {program}" if program and not no_field else ""
    keeping = f", with {_phrases(held)} held" if held else ""
    return f"{doing}{where}, using {model}{keeping}."
