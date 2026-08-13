"""Type text into whatever window has focus (Windows SendInput).

Used by system-wide abbreviation expansion: erase the abbreviation the user
typed, then type its expansion into the application they are actually working
in. Two routes:

- **SendInput (default).** Synthesised Unicode keystrokes. Touches nothing but
  the input queue -- in particular it never disturbs the clipboard, which is
  the user's, not ours.
- **Clipboard paste (opt-in).** Some rich editors and terminals drop or reorder
  fast synthetic keystrokes. For those, the expansion is put on the clipboard,
  pasted with Ctrl+V, and the previous clipboard contents are restored. This is
  a fallback precisely *because* borrowing the clipboard is rude; it is never
  the default and it always restores.

Windows-only, wx-free.
"""

from __future__ import annotations

import ctypes
import logging
import time
from ctypes import wintypes

logger = logging.getLogger(__name__)

_user32 = ctypes.windll.user32

_INPUT_KEYBOARD = 1
_KEYEVENTF_UNICODE = 0x0004
_KEYEVENTF_KEYUP = 0x0002
_VK_BACK = 0x08
_VK_LEFT = 0x25
_VK_CONTROL = 0x11
_VK_V = 0x56

#: A pause between batches of synthetic keys. Zero is tempting and wrong: some
#: targets (Electron apps especially) silently drop keys delivered faster than
#: their input loop drains them.
_BATCH_PAUSE_S = 0.005


#: Stamped into ``dwExtraInfo`` on every key this module synthesises, so the
#: expansion hook can recognise its own output and ignore it. Without this an
#: expansion would be re-read as typing and could trigger itself. Deliberately
#: *not* done by ignoring all injected keys: dictation software and on-screen
#: keyboards inject too, and their users must still get expansion.
INJECTION_SIGNATURE = 0x51494E4B  # "QINK"


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_void_p),
    ]


class _INPUT_UNION(ctypes.Union):
    _fields_ = [("ki", _KEYBDINPUT)]


class _INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUT_UNION)]


def _key(vk: int = 0, scan: int = 0, flags: int = 0) -> _INPUT:
    return _INPUT(
        type=_INPUT_KEYBOARD,
        u=_INPUT_UNION(
            ki=_KEYBDINPUT(
                wVk=vk,
                wScan=scan,
                dwFlags=flags,
                time=0,
                dwExtraInfo=ctypes.c_void_p(INJECTION_SIGNATURE),
            )
        ),
    )


def _send(inputs: list[_INPUT]) -> None:
    if not inputs:
        return
    array = (_INPUT * len(inputs))(*inputs)
    sent = _user32.SendInput(len(inputs), array, ctypes.sizeof(_INPUT))
    if sent != len(inputs):
        logger.warning("SendInput delivered %d of %d events", sent, len(inputs))


def send_text(text: str) -> None:
    """Type *text* as Unicode keystrokes.

    Characters outside the Basic Multilingual Plane (emoji, some CJK extensions)
    are sent as their two surrogate code units, which is what Windows expects.
    """
    inputs: list[_INPUT] = []
    for unit in utf16_code_units(text):
        inputs.append(_key(scan=unit, flags=_KEYEVENTF_UNICODE))
        inputs.append(_key(scan=unit, flags=_KEYEVENTF_UNICODE | _KEYEVENTF_KEYUP))
    _send(inputs)


def utf16_code_units(text: str) -> list[int]:
    """*text* as 16-bit units -- what SendInput's ``wScan`` field carries.

    Astral characters become their surrogate pair automatically, because that
    is what UTF-16 encoding produces. Pure, so it is testable off Windows.
    """
    encoded = text.encode("utf-16-le")
    return [int.from_bytes(encoded[i : i + 2], "little") for i in range(0, len(encoded), 2)]


def send_backspaces(count: int) -> None:
    """Press Backspace *count* times."""
    if count <= 0:
        return
    inputs: list[_INPUT] = []
    for _ in range(count):
        inputs.append(_key(vk=_VK_BACK))
        inputs.append(_key(vk=_VK_BACK, flags=_KEYEVENTF_KEYUP))
    _send(inputs)


def move_caret_left(steps: int) -> None:
    """Press Left Arrow *steps* times, to land the caret inside an expansion."""
    if steps <= 0:
        return
    inputs: list[_INPUT] = []
    for _ in range(steps):
        inputs.append(_key(vk=_VK_LEFT))
        inputs.append(_key(vk=_VK_LEFT, flags=_KEYEVENTF_KEYUP))
    _send(inputs)


def inject_expansion(
    text: str,
    *,
    backspace_count: int,
    caret_from_end: int = 0,
    trailing_space: bool = False,
    trigger_char: str = "",
) -> None:
    """Replace the just-typed abbreviation with *text* in the focused window.

    *trigger_char* is the character that fired the expansion. The hook swallows
    it -- letting it through would race these backspaces -- so it is typed back
    here, after the expansion, exactly where the user pressed it.

    *caret_from_end* is how far back the caret should end up *within the
    expansion*; everything typed after it is accounted for automatically, so a
    ``${cursor}`` marker lands where the entry asked for it.
    """
    send_backspaces(backspace_count)
    time.sleep(_BATCH_PAUSE_S)
    tail = text + trigger_char + (" " if trailing_space else "")
    send_text(tail)
    if caret_from_end > 0:
        time.sleep(_BATCH_PAUSE_S)
        move_caret_left(caret_from_end + len(trigger_char) + (1 if trailing_space else 0))


def paste_text(text: str, *, restore_delay_s: float = 0.2) -> bool:
    """Put *text* on the clipboard, press Ctrl+V, then restore the clipboard.

    Returns False when the clipboard could not be reached, so the caller can
    fall back to :func:`send_text` rather than silently doing nothing.
    """
    try:
        import win32clipboard  # noqa: PLC0415  (optional, Windows-only)
    except ImportError:
        return False

    previous: str | None = None
    try:
        win32clipboard.OpenClipboard()
        try:
            if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
                previous = str(win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT))
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32clipboard.CF_UNICODETEXT, text)
        finally:
            win32clipboard.CloseClipboard()
    except Exception:  # noqa: BLE001
        return False

    _send([
        _key(vk=_VK_CONTROL),
        _key(vk=_VK_V),
        _key(vk=_VK_V, flags=_KEYEVENTF_KEYUP),
        _key(vk=_VK_CONTROL, flags=_KEYEVENTF_KEYUP),
    ])

    # The target needs a moment to read the clipboard before we put it back.
    time.sleep(restore_delay_s)
    if previous is not None:
        try:
            win32clipboard.OpenClipboard()
            try:
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32clipboard.CF_UNICODETEXT, previous)
            finally:
                win32clipboard.CloseClipboard()
        except Exception:  # noqa: BLE001
            logger.warning("Could not restore the previous clipboard contents")
    return True
