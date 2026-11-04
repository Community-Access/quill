"""The WordPress keys: Ctrl+Alt+Shift+Grave, then one letter (wordpress.md 19).

One prefix beside the QUILL key, the same in QUILL and QUILL Lite, because no
plain chord was free in both editors for more than two commands. The letters
are :data:`quill.core.wordpress.menu.LAYER_KEYS`; each editor's keymap carries
them as ``"Ctrl+Alt+Shift+Grave, O"`` bindings, so its menus, its key lists and
its Keyboard Manager show them like any other key.

This module is the layer itself and has no ``wx``: each editor turns a key
event into the spelling :meth:`WordPressKeyLayer.press` takes and runs whatever
command comes back (``quill/ui/main_frame_wordpress.py``,
``quill/apps/lite_window_wordpress.py``). One implementation, so the two
editors cannot come to disagree about what Escape or an unknown letter says.

What is spoken (GATE-13: only what the screen reader cannot know): "WordPress
keys" when the layer starts, because the prefix changes nothing on screen;
"Left WordPress keys" on Escape; "No WordPress command on X." for a letter with
no command. A command that runs speaks for itself.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from quill.core.wordpress.menu import LAYER_KEYS, LAYER_PREFIX, layer_chord

__all__ = [
    "ESCAPE",
    "LAYER_PREFIX",
    "LEFT_MESSAGE",
    "STARTED_MESSAGE",
    "TIMEOUT_SECONDS",
    "Outcome",
    "WordPressKeyLayer",
    "default_bindings",
    "event_key",
    "is_sequence",
    "layer_from_bindings",
    "second_key",
    "unknown_message",
]

#: How long the layer waits for its letter, as the QUILL key's prefix does.
TIMEOUT_SECONDS = 4.0

#: What :meth:`WordPressKeyLayer.press` is given for the Escape key.
ESCAPE = "Escape"

STARTED_MESSAGE = "WordPress keys"
LEFT_MESSAGE = "Left WordPress keys"


def unknown_message(key: str) -> str:
    """What an unknown key says: ``"No WordPress command on Q."``."""
    return f"No WordPress command on {key}."


def default_bindings() -> dict[str, str]:
    """Command id -> its shipped layer chord, for QUILL's ``DEFAULT_KEYMAP``."""
    return {command_id: layer_chord(command_id) for command_id in LAYER_KEYS.values()}


def is_sequence(binding: str) -> bool:
    """Whether *binding* is two presses (``"X, Y"``) rather than one chord.

    A sequence cannot sit after the tab in a wx menu label -- wx would try to
    parse it as an accelerator and drop it -- so the menus show it in brackets.
    """
    return ", " in str(binding or "")


def second_key(binding: str) -> str:
    """The key after the prefix in a layer binding, or "" for anything else."""
    head, sep, tail = str(binding or "").partition(", ")
    if not sep or head.strip().lower() != LAYER_PREFIX.lower():
        return ""
    return tail.strip()


def layer_from_bindings(bindings: Mapping[str, str]) -> dict[str, str]:
    """``{"O": "wordpress.open", ...}`` out of a live keymap (id or handler -> binding).

    Read from the keymap rather than from :data:`LAYER_KEYS`, so a key the user
    moved in the Keyboard Manager moves the layer letter too. The second key is
    upper-cased and its modifiers kept (``"Shift+S"``), the spelling
    :meth:`WordPressKeyLayer.press` compares against.
    """
    layer: dict[str, str] = {}
    for owner, binding in bindings.items():
        key = second_key(binding)
        if key:
            layer.setdefault(_canonical(key), owner)
    return layer


def _canonical(key: str) -> str:
    parts = [part.strip() for part in key.split("+") if part.strip()]
    if not parts:
        return ""
    held = {part.lower() for part in parts[:-1]}
    mods = [mod for mod in ("Ctrl", "Alt", "Shift") if mod.lower() in held]
    return "+".join([*mods, parts[-1].upper()])


@dataclass(frozen=True)
class Outcome:
    """What one key press in the layer came to.

    *consumed* False means the key was not the layer's and goes on to the
    editor as usual (the layer had timed out). *command* is what to run, and
    *message* what to say; at most one of them is set.
    """

    consumed: bool = True
    command: str = ""
    message: str = ""


class WordPressKeyLayer:
    """The prefix-then-letter state, one per editor window."""

    def __init__(
        self,
        timeout: float = TIMEOUT_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._timeout = timeout
        self._clock = clock
        self._started_at: float | None = None

    @property
    def active(self) -> bool:
        """Whether the prefix has been pressed and its letter not yet."""
        if self._started_at is None:
            return False
        if self._timeout > 0 and self._clock() - self._started_at > self._timeout:
            self._started_at = None
            return False
        return True

    def start(self) -> str:
        """The prefix was pressed. Returns what to say."""
        self._started_at = self._clock()
        return STARTED_MESSAGE

    def cancel(self) -> None:
        """Leave silently (focus left the document, a menu opened)."""
        self._started_at = None

    def press(self, key: str, layer: Mapping[str, str]) -> Outcome:
        """The key after the prefix, spelled ``"O"``, ``"Shift+S"`` or :data:`ESCAPE`.

        *layer* is :func:`layer_from_bindings` over the editor's live keymap.
        A key pressed after the layer timed out is not the layer's.
        """
        if not self.active:
            return Outcome(consumed=False)
        self._started_at = None
        if key == ESCAPE:
            return Outcome(message=LEFT_MESSAGE)
        spelled = _canonical(key)
        command = layer.get(spelled, "")
        if command:
            return Outcome(command=command)
        return Outcome(message=unknown_message(spelled or key))


def event_key(key_code: int, *, ctrl: bool, alt: bool, shift: bool, escape_code: int = 27) -> str:
    """A key event in :meth:`WordPressKeyLayer.press`'s spelling, or "" for none.

    A printable key, with any modifiers held (a held Ctrl or Alt makes it a
    key no layer letter is on, which then says so). "" for anything without a
    character -- an arrow, Tab, Enter -- which the caller lets through after
    leaving the layer. A bare modifier going down on the way to Shift+S is the
    caller's to ignore first, since only it knows wx's codes for them.
    """
    if key_code == escape_code:
        return ESCAPE
    if not (ord("0") <= key_code <= ord("9") or ord("A") <= key_code <= ord("Z")):
        if ord("a") <= key_code <= ord("z"):
            key_code -= 32
        elif 0 < key_code < 256 and chr(key_code).isprintable() and not chr(key_code).isspace():
            pass
        else:
            return ""
    mods = [name for name, down in (("Ctrl", ctrl), ("Alt", alt), ("Shift", shift)) if down]
    return "+".join([*mods, chr(key_code).upper()])
