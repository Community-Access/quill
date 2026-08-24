"""Winamp classic-skin playback keys, as one shared map (#1344).

Every JAWS user who came through Winamp has the main-window letter keys in
muscle memory -- ``Z X C V B`` along the bottom row for previous, play, pause,
stop and next, arrows for seeking. The recordings player had none of them, so
there was nothing for that muscle memory to land on.

This module is the map itself and nothing else: no wx, no dialog, no player.
Surfaces call :func:`resolve_winamp_action` with a normalized key token and the
modifier state and get back an action name, which they dispatch however they
like. Keeping it wx-free means it is testable without a display and adoptable
by the standalone Media Player and Cast without a second implementation.

**Deliberate deviations from Winamp classic**, both documented in
``CONTROL_REFERENCE.md``:

* ``Ctrl+T`` stays What's Playing (Quill Radio's own, more useful meaning);
  the elapsed/remaining toggle moves to plain ``T``, which is otherwise unused.
* Up/Down are list navigation, not volume. That is what Winamp itself does in
  the Playlist Editor, and the recordings list *is* a playlist editor; volume
  keeps Ctrl+Up/Ctrl+Down, which already worked.

Shuffle (``R``), repeat (``S``) and stop-after-current (``Ctrl+V``) were
deliberately absent at first, because all three describe a play queue and the
recordings player did not have one -- binding them to something that only
pretended to work would have been worse than leaving them unbound. The queue
now exists (:mod:`quill.core.radio.play_queue`), so they are bound.

A surface without a queue simply resolves those three to actions it has no
handler for, which does nothing and passes the key through; the map is shared,
but adopting an action has never been mandatory.
"""

from __future__ import annotations

from typing import Final

#: Transport.
ACTION_PLAY: Final = "play"
ACTION_PAUSE: Final = "pause"
ACTION_STOP: Final = "stop"
ACTION_STOP_FADE: Final = "stop_fade"
ACTION_NEXT: Final = "next"
ACTION_PREVIOUS: Final = "previous"

#: Seeking.
ACTION_BACK_5: Final = "back_5"
ACTION_FORWARD_5: Final = "forward_5"
ACTION_BACK_30: Final = "back_30"
ACTION_FORWARD_30: Final = "forward_30"

#: The play queue (item 12): what plays next, and whether to stop.
ACTION_SHUFFLE: Final = "shuffle"
ACTION_REPEAT: Final = "repeat"
ACTION_STOP_AFTER_CURRENT: Final = "stop_after_current"

#: Position, time, and finding your way around the list.
ACTION_TOGGLE_TIME: Final = "toggle_time"
ACTION_JUMP_TO_TIME: Final = "jump_to_time"
ACTION_JUMP_TO_FILE: Final = "jump_to_file"
ACTION_OPEN: Final = "open"

#: Volume (already wired before #1344; kept here so the map is the whole story).
ACTION_VOLUME_UP: Final = "volume_up"
ACTION_VOLUME_DOWN: Final = "volume_down"

#: ``(key, ctrl, shift, alt) -> action``. Keys are normalized tokens: a single
#: uppercase letter, or one of ``LEFT``/``RIGHT``/``UP``/``DOWN``.
_MAP: Final[dict[tuple[str, bool, bool, bool], str]] = {
    ("X", False, False, False): ACTION_PLAY,
    ("C", False, False, False): ACTION_PAUSE,
    ("V", False, False, False): ACTION_STOP,
    ("V", False, True, False): ACTION_STOP_FADE,
    ("B", False, False, False): ACTION_NEXT,
    ("Z", False, False, False): ACTION_PREVIOUS,
    ("LEFT", False, False, False): ACTION_BACK_5,
    ("RIGHT", False, False, False): ACTION_FORWARD_5,
    ("LEFT", False, True, False): ACTION_BACK_30,
    ("RIGHT", False, True, False): ACTION_FORWARD_30,
    ("R", False, False, False): ACTION_SHUFFLE,
    ("S", False, False, False): ACTION_REPEAT,
    ("V", True, False, False): ACTION_STOP_AFTER_CURRENT,
    ("T", False, False, False): ACTION_TOGGLE_TIME,
    ("J", False, False, False): ACTION_JUMP_TO_FILE,
    ("J", True, False, False): ACTION_JUMP_TO_TIME,
    ("L", False, False, False): ACTION_OPEN,
    ("UP", True, False, False): ACTION_VOLUME_UP,
    ("DOWN", True, False, False): ACTION_VOLUME_DOWN,
}

#: What each action is called when it is announced or written down. Surfaces
#: use this so the spoken word and the documented word are the same word.
ACTION_LABELS: Final[dict[str, str]] = {
    ACTION_PLAY: "Play",
    ACTION_PAUSE: "Pause",
    ACTION_STOP: "Stop",
    ACTION_STOP_FADE: "Stop with fade out",
    ACTION_NEXT: "Next recording",
    ACTION_PREVIOUS: "Previous recording",
    ACTION_BACK_5: "Back 5 seconds",
    ACTION_FORWARD_5: "Forward 5 seconds",
    ACTION_BACK_30: "Back 30 seconds",
    ACTION_FORWARD_30: "Forward 30 seconds",
    ACTION_SHUFFLE: "Shuffle",
    ACTION_REPEAT: "Repeat",
    ACTION_STOP_AFTER_CURRENT: "Stop after the current recording",
    ACTION_TOGGLE_TIME: "Elapsed or remaining time",
    ACTION_JUMP_TO_TIME: "Jump to time",
    ACTION_JUMP_TO_FILE: "Jump to file",
    ACTION_OPEN: "Open",
    ACTION_VOLUME_UP: "Volume up",
    ACTION_VOLUME_DOWN: "Volume down",
}


def resolve_winamp_action(
    key: str, *, ctrl: bool = False, shift: bool = False, alt: bool = False
) -> str | None:
    """The action *key* means with those modifiers, or None when it means nothing.

    *key* is a normalized token: one uppercase letter, or ``LEFT``, ``RIGHT``,
    ``UP``, ``DOWN``. Anything unmapped returns None so the caller passes the
    keystroke straight through -- a letter typed into a text field must never be
    swallowed (the trap #1263 hit).
    """
    return _MAP.get((key.upper(), bool(ctrl), bool(shift), bool(alt)))


def normalize_key_code(code: int, wx: object) -> str:
    """Turn a wx key code into the token :func:`resolve_winamp_action` expects.

    Returns ``""`` for anything that is not a letter or one of the four arrows,
    which resolves to no action.
    """
    arrows = {
        getattr(wx, "WXK_LEFT", -1): "LEFT",
        getattr(wx, "WXK_RIGHT", -2): "RIGHT",
        getattr(wx, "WXK_UP", -3): "UP",
        getattr(wx, "WXK_DOWN", -4): "DOWN",
    }
    if code in arrows:
        return arrows[code]
    if 65 <= code <= 90:  # A-Z as wx reports them from a char hook
        return chr(code)
    if 97 <= code <= 122:  # a-z, defensively
        return chr(code).upper()
    return ""


def parse_time_to_ms(text: str) -> int | None:
    """Parse a Jump To Time entry into milliseconds, or None if it is not a time.

    Accepts what a listener actually types: ``90`` (seconds), ``1:30``,
    ``62:03`` (minutes past the hour mark) and ``1:02:03``. Blank or nonsense
    returns None so the caller can say so rather than silently seeking to zero.

    One parser, not two (11.8): this used to have its own arithmetic, which
    differed from :func:`quill.core.media.timecode.parse_timecode` in what it
    accepted -- so the same string could work in one player and not the other.
    It now delegates, and the None-instead-of-raise contract is the only
    difference that remains.
    """
    from quill.core.media.errors import InvalidTimecodeError
    from quill.core.media.timecode import parse_timecode

    try:
        return parse_timecode(str(text or ""))
    except InvalidTimecodeError:
        return None


def keymap_rows() -> list[tuple[str, str]]:
    """``(keystroke, action label)`` pairs in documentation order.

    One source for the help dialog, the user guide table, and the tests that
    keep the three in agreement.
    """
    return [
        ("X", ACTION_LABELS[ACTION_PLAY]),
        ("C", ACTION_LABELS[ACTION_PAUSE]),
        ("V", ACTION_LABELS[ACTION_STOP]),
        ("Shift+V", ACTION_LABELS[ACTION_STOP_FADE]),
        ("B", ACTION_LABELS[ACTION_NEXT]),
        ("Z", ACTION_LABELS[ACTION_PREVIOUS]),
        ("Left", ACTION_LABELS[ACTION_BACK_5]),
        ("Right", ACTION_LABELS[ACTION_FORWARD_5]),
        ("Shift+Left", ACTION_LABELS[ACTION_BACK_30]),
        ("Shift+Right", ACTION_LABELS[ACTION_FORWARD_30]),
        ("R", ACTION_LABELS[ACTION_SHUFFLE]),
        ("S", ACTION_LABELS[ACTION_REPEAT]),
        ("Ctrl+V", ACTION_LABELS[ACTION_STOP_AFTER_CURRENT]),
        ("T", ACTION_LABELS[ACTION_TOGGLE_TIME]),
        ("J", ACTION_LABELS[ACTION_JUMP_TO_FILE]),
        ("Ctrl+J", ACTION_LABELS[ACTION_JUMP_TO_TIME]),
        ("L", ACTION_LABELS[ACTION_OPEN]),
        ("Ctrl+Up", ACTION_LABELS[ACTION_VOLUME_UP]),
        ("Ctrl+Down", ACTION_LABELS[ACTION_VOLUME_DOWN]),
    ]
