"""Parse a keyboard chord into RegisterHotKey (flags, virtual-key) parts.

Shared by every QuillVille window that offers a system-wide "show/hide me to the
tray" hotkey (QUILL, Quill Radio, Quill Weather -- each a different, unique
chord). ``wx`` is passed in so the parser stays free of a hard wx import and can
be unit-tested with a tiny stand-in namespace.
"""

from __future__ import annotations

import sys
from typing import Any

#: Windows virtual-key codes for the punctuation keys on a US layout, used when
#: the live layout cannot be asked (:func:`_punctuation_vk`). A punctuation
#: character's own code point is NOT its virtual key: ``ord("\\")`` is 0x5C,
#: VK_RWIN, so Alt+Shift+\ registered as Alt+Shift+Right Windows -- Windows
#: accepted it, nothing warned, and the real key dinged in Outlook (QUILL
#: Transcribe, 2026-10-12). The same held for every key here (``,`` was Print
#: Screen, ``.`` Delete, ``-`` Insert).
_US_PUNCTUATION_VK = {
    ";": 0xBA,
    "=": 0xBB,
    ",": 0xBC,
    "-": 0xBD,
    ".": 0xBE,
    "/": 0xBF,
    "`": 0xC0,
    "[": 0xDB,
    "\\": 0xDC,
    "]": 0xDD,
    "'": 0xDE,
}

_NAMED_KEYS = {
    "ENTER": "WXK_RETURN",
    "TAB": "WXK_TAB",
    "SPACE": "WXK_SPACE",
    "ESC": "WXK_ESCAPE",
    "ESCAPE": "WXK_ESCAPE",
    "DELETE": "WXK_DELETE",
    "HOME": "WXK_HOME",
    "END": "WXK_END",
    "LEFT": "WXK_LEFT",
    "RIGHT": "WXK_RIGHT",
    "UP": "WXK_UP",
    "DOWN": "WXK_DOWN",
    "PAGEUP": "WXK_PAGEUP",
    "PAGEDOWN": "WXK_PAGEDOWN",
    "INSERT": "WXK_INSERT",
}


def _punctuation_vk(char: str) -> int | None:
    """The virtual key that types *char* on this keyboard layout.

    ``VkKeyScanW`` answers for the live layout (on a UK keyboard ``\\`` is not
    where a US one has it); the US table covers other platforms and a layout
    with no such key. ``None`` when neither knows it.
    """
    if sys.platform == "win32":
        try:
            import ctypes

            scan = int(ctypes.windll.user32.VkKeyScanW(ord(char)))
            if scan != -1 and (scan & 0xFF) != 0xFF:
                return scan & 0xFF
        except Exception:  # noqa: BLE001 - fall back to the US layout
            pass
    return _US_PUNCTUATION_VK.get(char)


def parse_hotkey(wx: Any, chord: str | None) -> tuple[int, int] | None:
    """``"Ctrl+Alt+Shift+R"`` -> ``(flags, key_code)`` for ``RegisterHotKey``,
    or ``None`` when the chord is empty or unparseable. Modifiers are Ctrl / Alt
    / Shift (Cmd maps to Ctrl); the final token is a letter, a digit, a
    punctuation key (``\\``, ``;``, ``,`` ...), F1-F12, or a named key
    (Home/End/arrows/...)."""
    if not chord:
        return None
    parts = [part.strip() for part in chord.split("+") if part.strip()]
    if not parts:
        return None
    flags = 0
    for modifier in parts[:-1]:
        lowered = modifier.lower()
        if lowered == "ctrl":
            flags |= wx.ACCEL_CTRL
        elif lowered == "shift":
            flags |= wx.ACCEL_SHIFT
        elif lowered == "alt":
            flags |= wx.ACCEL_ALT
        elif lowered in ("cmd", "command"):
            flags |= wx.ACCEL_CTRL
        else:
            return None
    token = parts[-1].upper()
    if len(token) == 1:
        if token.isascii() and token.isalnum():
            return flags, ord(token)  # A-Z and 0-9 are their own virtual keys
        vk = _punctuation_vk(parts[-1])
        return None if vk is None else (flags, vk)
    if token.startswith("F") and token[1:].isdigit() and 1 <= int(token[1:]) <= 12:
        return flags, getattr(wx, f"WXK_F{int(token[1:])}")
    named = _NAMED_KEYS.get(token)
    if named is not None:
        return flags, getattr(wx, named)
    return None


#: Windows virtual-key codes for the named keys :func:`parse_hotkey` accepts.
#: ``parse_hotkey`` answers in wx key codes, which ``RegisterHotKey`` converts;
#: ``GetAsyncKeyState`` wants the Windows code itself.
_NAMED_VIRTUAL_KEYS = {
    "ENTER": 0x0D,
    "TAB": 0x09,
    "SPACE": 0x20,
    "ESC": 0x1B,
    "ESCAPE": 0x1B,
    "DELETE": 0x2E,
    "HOME": 0x24,
    "END": 0x23,
    "LEFT": 0x25,
    "RIGHT": 0x27,
    "UP": 0x26,
    "DOWN": 0x28,
    "PAGEUP": 0x21,
    "PAGEDOWN": 0x22,
    "INSERT": 0x2D,
}


def virtual_key(chord: str | None) -> int | None:
    """The Windows virtual-key code of *chord*'s main key ("Alt+Shift+\\" ->
    0xDC on a US layout), or ``None`` when the chord is empty or unparseable.
    For asking whether the key is still held (QUILL Transcribe's hold-to-talk)."""
    parts = [part.strip() for part in str(chord or "").split("+") if part.strip()]
    if not parts:
        return None
    token = parts[-1].upper()
    if len(token) == 1:
        if token.isascii() and token.isalnum():
            return ord(token)
        return _punctuation_vk(parts[-1])
    if token.startswith("F") and token[1:].isdigit() and 1 <= int(token[1:]) <= 12:
        return 0x70 + int(token[1:]) - 1  # VK_F1 is 0x70
    return _NAMED_VIRTUAL_KEYS.get(token)
