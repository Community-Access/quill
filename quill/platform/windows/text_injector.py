"""Type text into whatever window has focus (Windows SendInput).

Used by system-wide abbreviation expansion: erase the abbreviation the user
typed, then type its expansion into the application they are actually working
in. Two routes:

- **SendInput (default).** Synthesised keystrokes. Touches nothing but the
  input queue -- in particular it never disturbs the clipboard, which is the
  user's, not ours. A character the keyboard layout has is sent as *its key*
  (with Shift when it needs it), exactly as a keyboard would; only one the
  layout lacks goes as a Unicode keystroke (:func:`_layout_key`).
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
from collections.abc import Callable
from ctypes import wintypes
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# A private instance, so the signatures below are ours and no other module's
# (``ctypes.windll.user32`` is one object shared by the whole process). Without
# them a 64-bit HWND or HKL goes through ctypes' default 32-bit ``int``.
_user32 = ctypes.WinDLL("user32")
_user32.GetForegroundWindow.restype = wintypes.HWND
_user32.GetForegroundWindow.argtypes = []
_user32.GetWindowThreadProcessId.restype = wintypes.DWORD
_user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
_user32.GetKeyboardLayout.restype = wintypes.HKL
_user32.GetKeyboardLayout.argtypes = [wintypes.DWORD]
_user32.VkKeyScanExW.restype = ctypes.c_short
_user32.VkKeyScanExW.argtypes = [ctypes.c_ushort, wintypes.HKL]  # a WCHAR, by code
_user32.MapVirtualKeyExW.restype = wintypes.UINT
_user32.MapVirtualKeyExW.argtypes = [wintypes.UINT, wintypes.UINT, wintypes.HKL]

_INPUT_KEYBOARD = 1
_KEYEVENTF_UNICODE = 0x0004
_KEYEVENTF_KEYUP = 0x0002
_VK_BACK = 0x08
_VK_LEFT = 0x25
_VK_CONTROL = 0x11
_VK_V = 0x56
_VK_SHIFT = 0x10
_VK_CAPITAL = 0x14
_MAPVK_VK_TO_VSC = 0
_MAPVK_VK_TO_CHAR = 2

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


class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_void_p),
    ]


class _HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class _INPUT_UNION(ctypes.Union):
    # All three members, though only ``ki`` is used: MOUSEINPUT is the largest,
    # and it is what makes sizeof(INPUT) 40 on 64-bit Windows. With ``ki`` alone
    # it was 32, SendInput rejected every call with ERROR_INVALID_PARAMETER
    # (87), and nothing dictated or expanded ever reached another program --
    # QUILL Transcribe into Outlook, 2026-10-12: "delivered 0 of 42 events".
    _fields_ = [("ki", _KEYBDINPUT), ("mi", _MOUSEINPUT), ("hi", _HARDWAREINPUT)]


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


@dataclass(frozen=True, slots=True)
class InjectionResult:
    """How much of one injection Windows actually accepted.

    ``SendInput`` returns the number of events it queued, and that number can
    be **smaller than what was asked for**: another process holding a low-level
    hook, an elevated window refusing input from a non-elevated sender, or the
    target's input queue simply full. The old ``_send`` logged the shortfall and
    returned ``None``, so every caller carried on as if the whole expansion had
    landed -- and the one place that matters is the middle of a replacement,
    where the abbreviation has been erased and its expansion has not arrived.
    Half of an expansion is a damaged document that nothing reported.
    """

    requested_events: int
    sent_events: int

    @property
    def complete(self) -> bool:
        """True when every event asked for was accepted."""
        return self.sent_events >= self.requested_events


#: Keys that turn a typed letter into a command while they are held. Shift is
#: not one: it changes nothing about a KEYEVENTF_UNICODE character.
_COMMAND_MODIFIERS = (0x12, 0x11, 0x5B, 0x5C)  # Alt, Ctrl, left and right Windows
#: How long to wait for them to be let go before typing anyway is refused.
_MODIFIER_WAIT_S = 2.0


def _command_modifier_held() -> bool:
    state = _user32.GetAsyncKeyState
    return any(int(state(vk)) & 0x8000 for vk in _COMMAND_MODIFIERS)


def _wait_for_modifiers_released(
    held: Callable[[], bool] | None = None,
    timeout_s: float | None = None,
) -> bool:
    """Wait until Alt, Ctrl and Windows are up. False when one is still held.

    Typing while one is down sends commands instead of letters. Pressing
    Alt+Shift+\\ to stop QUILL Transcribe writes the last phrase at once --
    while the fingers are still on Alt -- and Outlook took its letters as Alt
    shortcuts: an "s" anywhere in the phrase was Alt+S, Send (2026-10-12).
    """
    held = held or _command_modifier_held
    deadline = time.monotonic() + (_MODIFIER_WAIT_S if timeout_s is None else timeout_s)
    while held():
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.02)
    return True


def _send(inputs: list[_INPUT]) -> InjectionResult:
    if not inputs:
        return InjectionResult(0, 0)
    if not _wait_for_modifiers_released():
        logger.warning("Not typing %d events: Alt, Ctrl or Windows is still held", len(inputs))
        return InjectionResult(len(inputs), 0)
    array = (_INPUT * len(inputs))(*inputs)
    sent = int(_user32.SendInput(len(inputs), array, ctypes.sizeof(_INPUT)))
    if sent != len(inputs):
        logger.warning("SendInput delivered %d of %d events", sent, len(inputs))
    return InjectionResult(len(inputs), sent)


def _target_layout() -> int:
    """The keyboard layout of the window the text is going to."""
    thread = _user32.GetWindowThreadProcessId(_user32.GetForegroundWindow(), None)
    return int(_user32.GetKeyboardLayout(thread) or 0)


def _layout_key(char: str, layout: int, caps_lock: bool) -> list[_INPUT] | None:
    """*char* as the key that types it on *layout*, or None when it has none.

    Why not always Unicode: JAWS announces a Unicode keystroke (VK_PACKET) as a
    key of its own -- heard as "c" every time QUILL Transcribe wrote a phrase,
    in Outlook and the Run box alike, and absent from JAWS's speech history
    (2026-10-12). A real key is ordinary typing, and the reader treats it so.

    Only a key with no modifier or Shift alone: Ctrl and Alt (AltGr) would be
    shortcuts in the target, and a dead key would join the next letter.
    """
    if len(char) != 1 or not char.isprintable():
        return None  # line breaks and tabs keep the Unicode route
    if ord(char) > 0xFFFF:
        # Emoji and every other astral character: no layout has a key for one,
        # and asking would lie. VkKeyScanExW takes a 16-bit WCHAR, so ctypes
        # silently cuts U+20041 (a CJK Extension B ideograph) to U+0041 and the
        # layout answers with the A key -- the character typed as a letter.
        return None
    scanned = int(_user32.VkKeyScanExW(ord(char), layout))
    if scanned == -1 or scanned & 0xFFFF == 0xFFFF:
        return None
    vk, shift_state = scanned & 0xFF, (scanned >> 8) & 0xFF
    if shift_state & ~0x01:
        return None  # needs Ctrl or Alt
    if int(_user32.MapVirtualKeyExW(vk, _MAPVK_VK_TO_CHAR, layout)) & 0x80000000:
        return None  # a dead key
    shifted = bool(shift_state & 0x01)
    if caps_lock and char.isalpha():
        shifted = not shifted  # Caps Lock flips the letter keys
    scan = int(_user32.MapVirtualKeyExW(vk, _MAPVK_VK_TO_VSC, layout)) & 0xFF
    keys = [_key(vk=vk, scan=scan), _key(vk=vk, scan=scan, flags=_KEYEVENTF_KEYUP)]
    if shifted:
        keys = [_key(vk=_VK_SHIFT), *keys, _key(vk=_VK_SHIFT, flags=_KEYEVENTF_KEYUP)]
    return keys


def unicode_key_sequence(text: str) -> list[tuple[int, bool]]:
    """*text* as ``(utf16_unit, key_up)`` pairs, in the order they are sent.

    One down and one up per BMP character. An astral character -- every emoji
    -- is two UTF-16 units, and its two key-downs go **together**, before
    either key-up: high down, low down, low up, high up. Sending each half as
    its own down-up tap put a key-up between the halves, and an emoji
    dictated by QUILL Transcribe into a plain Edit control arrived without its
    first half (todo P3, 2026-10). A key-up between the halves is the one
    thing that separates the two ``WM_CHAR`` messages; with the downs
    adjacent, ``TranslateMessage`` posts them back to back, which is the
    order a control that pairs surrogates expects. (Not reproduced against a
    live window: the overnight rules forbid driving the desktop, so the
    sequence is pinned by a unit test and the field check is Jeff's.) Pure,
    so it is testable off Windows.
    """
    sequence: list[tuple[int, bool]] = []
    for char in text:
        units = utf16_code_units(char)
        sequence.extend((unit, False) for unit in units)
        sequence.extend((unit, True) for unit in reversed(units))
    return sequence


def _unicode_inputs(text: str) -> list[_INPUT]:
    return [
        _key(scan=unit, flags=_KEYEVENTF_UNICODE | (_KEYEVENTF_KEYUP if up else 0))
        for unit, up in unicode_key_sequence(text)
    ]


def _text_inputs(text: str) -> list[_INPUT]:
    try:
        layout = _target_layout()
        caps_lock = bool(int(_user32.GetKeyState(_VK_CAPITAL)) & 0x01)
        inputs: list[_INPUT] = []
        for char in text:
            keys = _layout_key(char, layout, caps_lock)
            inputs.extend(keys if keys is not None else _unicode_inputs(char))
        return inputs
    except Exception:  # noqa: BLE001 - no layout to ask: Unicode always types
        return _unicode_inputs(text)


def _backspace_inputs(count: int) -> list[_INPUT]:
    inputs: list[_INPUT] = []
    for _ in range(max(0, count)):
        inputs.append(_key(vk=_VK_BACK))
        inputs.append(_key(vk=_VK_BACK, flags=_KEYEVENTF_KEYUP))
    return inputs


def _ctrl_tap() -> list[_INPUT]:
    return [_key(vk=_VK_CONTROL), _key(vk=_VK_CONTROL, flags=_KEYEVENTF_KEYUP)]


def send_text_checked(text: str, *, hush_reader: bool = False) -> InjectionResult:
    """Type *text*, and say how much of it Windows accepted.

    ``hush_reader`` presses Ctrl on its own straight after the text, in the
    same batch: the key every screen reader takes as "stop talking". The
    reader echoes typed keys, and because they come faster than it can speak
    only the last is heard -- "period" after every dictated phrase
    (2026-10-12). A timed stop through the reader's API arrived before the
    echo had begun; a key in the same queue cannot. Ctrl alone does nothing
    in the program typed into. It is never left down: when Windows takes the
    press and not the release, the release is sent again by itself.
    """
    inputs = _text_inputs(text)
    if not hush_reader or not inputs:
        return _send(inputs)
    result = _send([*inputs, *_ctrl_tap()])
    if result.sent_events == len(inputs) + 1:  # Ctrl went down and did not come up
        _release_ctrl()
    return InjectionResult(len(inputs), min(result.sent_events, len(inputs)))


def _release_ctrl() -> None:
    array = (_INPUT * 1)(_key(vk=_VK_CONTROL, flags=_KEYEVENTF_KEYUP))
    if int(_user32.SendInput(1, array, ctypes.sizeof(_INPUT))) != 1:
        logger.warning("Could not release the Ctrl key QUILL pressed after typing")


def send_backspaces_checked(count: int) -> InjectionResult:
    """Press Backspace *count* times, and say how many landed."""
    return _send(_backspace_inputs(count))


def inject_expansion_checked(text: str, *, backspace_count: int) -> InjectionResult:
    """Erase, then type -- and **stop** if the erase was not fully delivered.

    The order matters and so does the stopping. Typing an expansion on top of
    an abbreviation that is still half there produces text nobody wrote, in a
    document QUILL does not own and cannot undo for you. When the backspaces
    come up short the expansion is not sent at all: the result says so, the
    abbreviation is still (partly) on screen, and the person can see -- or be
    told -- that nothing was replaced.
    """
    erased = send_backspaces_checked(backspace_count)
    if not erased.complete:
        return erased
    typed = send_text_checked(text)
    return InjectionResult(
        erased.requested_events + typed.requested_events,
        erased.sent_events + typed.sent_events,
    )


def send_text(text: str) -> None:
    """Type *text* as Unicode keystrokes.

    Characters outside the Basic Multilingual Plane (emoji, some CJK extensions)
    are sent as their two surrogate code units, both key-downs before either
    key-up (:func:`unicode_key_sequence`), which is what Windows expects.

    Returns nothing: :func:`send_text_checked` is the one that reports what
    landed, and is what a replacement should use.
    """
    _send(_text_inputs(text))


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
    _send(_backspace_inputs(count))


def _caret_left_inputs(steps: int) -> list[_INPUT]:
    inputs: list[_INPUT] = []
    for _ in range(max(0, steps)):
        inputs.append(_key(vk=_VK_LEFT))
        inputs.append(_key(vk=_VK_LEFT, flags=_KEYEVENTF_KEYUP))
    return inputs


def _paste_inputs() -> list[_INPUT]:
    return [
        _key(vk=_VK_CONTROL),
        _key(vk=_VK_V),
        _key(vk=_VK_V, flags=_KEYEVENTF_KEYUP),
        _key(vk=_VK_CONTROL, flags=_KEYEVENTF_KEYUP),
    ]


def move_caret_left(steps: int) -> None:
    """Press Left Arrow *steps* times, to land the caret inside an expansion."""
    if steps <= 0:
        return
    _send(_caret_left_inputs(steps))


def move_caret_left_checked(steps: int) -> InjectionResult:
    """As :func:`move_caret_left`, reporting how many presses landed.

    A caret that only travelled half way is not a cosmetic failure: the next
    thing typed goes into the middle of the expansion rather than where the
    snippet asked for it.
    """
    return _send(_caret_left_inputs(steps))


def send_paste_checked() -> InjectionResult:
    """Press Ctrl+V, reporting whether all four key events were accepted.

    A partial Ctrl+V is the worst shape of failure here -- a Control key that
    went down and never came up leaves the target believing Control is still
    held, so the person's next keystroke is a shortcut they did not ask for.
    """
    return _send(_paste_inputs())


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

    _send(_paste_inputs())

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
