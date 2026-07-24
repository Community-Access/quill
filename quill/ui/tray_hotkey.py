"""Parse a keyboard chord into RegisterHotKey (flags, virtual-key) parts.

Shared by every QuillVille window that offers a system-wide "show/hide me to the
tray" hotkey (QUILL, Quill Radio, Quill Weather -- each a different, unique
chord). ``wx`` is passed in so the parser stays free of a hard wx import and can
be unit-tested with a tiny stand-in namespace.
"""

from __future__ import annotations

from typing import Any

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
}


def parse_hotkey(wx: Any, chord: str | None) -> tuple[int, int] | None:
    """``"Ctrl+Alt+Shift+R"`` -> ``(flags, key_code)`` for ``RegisterHotKey``,
    or ``None`` when the chord is empty or unparseable. Modifiers are Ctrl / Alt
    / Shift (Cmd maps to Ctrl); the final token is a letter, F1-F12, or a named
    key (Home/End/arrows/...)."""
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
        return flags, ord(token)
    if token.startswith("F") and token[1:].isdigit() and 1 <= int(token[1:]) <= 12:
        return flags, getattr(wx, f"WXK_F{int(token[1:])}")
    named = _NAMED_KEYS.get(token)
    if named is not None:
        return flags, getattr(wx, named)
    return None
