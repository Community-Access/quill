"""Remappable keyboard model (PRD 10.1, "All shortcuts must be remappable").

A wx-free mapping between stable command ids and key chords written as plain
strings ("Ctrl+N", "Ctrl+Shift+R", "F6"). The UI translates a live key event
into a chord string with :func:`chord_from_event` (the only wx-touching helper,
imported lazily) and asks the keymap which command that chord runs.

Keeping the model as strings means bindings persist as readable JSON, can be
edited by hand, and are trivial to unit-test. Conflicts are detected on rebind
so two commands never silently share a chord.
"""

from __future__ import annotations

import json
from pathlib import Path

BINDINGS_NAME = "keymap.json"

# Canonical modifier order so chord strings compare equal regardless of how the
# user typed them.
_MOD_ORDER = ("Ctrl", "Alt", "Shift")

# Default bindings straight from PRD 10.1. Command ids are stable identifiers
# the command registry also uses.
DEFAULT_BINDINGS: dict[str, str] = {
    "compose": "Ctrl+N",
    "reply": "Ctrl+R",
    "repost": "Ctrl+Shift+R",
    "quote": "Ctrl+Q",
    "favourite": "Ctrl+F",
    "bookmark": "Alt+B",
    "open_conversation": "Ctrl+G",
    "open_links": "Ctrl+O",
    "play_media": "Ctrl+Enter",
    "command_center": "Ctrl+Shift+C",
    "where_am_i": "Ctrl+Shift+I",
    "next_pane": "F6",
    "prev_pane": "Shift+F6",
    "refresh": "F5",
    "mark_read": "Ctrl+K",
    "search": "Ctrl+L",
    "help": "F1",
    "goto_1": "Ctrl+1",
    "goto_2": "Ctrl+2",
    "goto_3": "Ctrl+3",
    "goto_4": "Ctrl+4",
    "goto_5": "Ctrl+5",
    "goto_6": "Ctrl+6",
    "goto_7": "Ctrl+7",
    "goto_8": "Ctrl+8",
    "goto_9": "Ctrl+9",
}


def normalize_chord(chord: str) -> str:
    """Canonicalize a chord string: title-cased mods in a fixed order + key.

    ``"shift+ctrl+r"`` and ``"Ctrl+Shift+R"`` both normalize to ``"Ctrl+Shift+R"``.
    """
    if not chord:
        return ""
    parts = [p.strip() for p in chord.split("+") if p.strip()]
    mods_present = []
    key = ""
    for p in parts:
        low = p.lower()
        if low in ("ctrl", "control"):
            mods_present.append("Ctrl")
        elif low == "alt":
            mods_present.append("Alt")
        elif low == "shift":
            mods_present.append("Shift")
        else:
            key = p if len(p) > 1 else p.upper()
    ordered = [m for m in _MOD_ORDER if m in mods_present]
    return "+".join([*ordered, key]) if key else "+".join(ordered)


class Keymap:
    """Bidirectional command <-> chord map with conflict-safe rebinding."""

    def __init__(self, bindings: dict[str, str] | None = None) -> None:
        src = bindings if bindings is not None else dict(DEFAULT_BINDINGS)
        self._by_command: dict[str, str] = {
            cmd: normalize_chord(ch) for cmd, ch in src.items()
        }

    def chord_for(self, command_id: str) -> str:
        return self._by_command.get(command_id, "")

    def command_for(self, chord: str) -> str | None:
        target = normalize_chord(chord)
        for cmd, ch in self._by_command.items():
            if ch == target:
                return cmd
        return None

    def conflict(self, chord: str) -> str | None:
        """Return the command currently bound to ``chord``, if any."""
        return self.command_for(chord)

    def rebind(self, command_id: str, chord: str, *, force: bool = False) -> None:
        """Assign ``chord`` to ``command_id``.

        Raises ``ValueError`` if another command already owns the chord unless
        ``force`` is set, in which case the previous owner is unbound.
        """
        target = normalize_chord(chord)
        if not target:
            self._by_command.pop(command_id, None)
            return
        owner = self.command_for(target)
        if owner and owner != command_id:
            if not force:
                raise ValueError(f"{chord} is already bound to {owner!r}")
            del self._by_command[owner]
        self._by_command[command_id] = target

    def as_dict(self) -> dict[str, str]:
        return dict(self._by_command)


def load(data_dir: str | Path) -> Keymap:
    p = Path(data_dir) / BINDINGS_NAME
    if not p.exists():
        return Keymap()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        merged = dict(DEFAULT_BINDINGS)
        merged.update({k: v for k, v in data.items() if isinstance(v, str)})
        return Keymap(merged)
    except Exception:
        return Keymap()


def save(data_dir: str | Path, keymap: Keymap) -> None:
    (Path(data_dir) / BINDINGS_NAME).write_text(
        json.dumps(keymap.as_dict(), indent=2), encoding="utf-8")


def chord_from_event(event) -> str:
    """Translate a live ``wx.KeyEvent`` into a normalized chord string.

    The only wx-touching helper in this module; wx is imported lazily so the
    model stays testable headlessly.
    """

    mods = []
    if event.ControlDown():
        mods.append("Ctrl")
    if event.AltDown():
        mods.append("Alt")
    if event.ShiftDown():
        mods.append("Shift")
    code = event.GetKeyCode()
    key = _KEYCODE_NAMES.get(code)
    if key is None:
        if 32 < code < 127:
            key = chr(code).upper()
        else:
            key = ""
    return normalize_chord("+".join([*mods, key])) if key else ""


# Named keys we care about for chords (function keys, Enter, etc.). Resolved
# lazily so importing keymap never imports wx.
def _build_keycode_names() -> dict[int, str]:
    import wx

    names = {
        wx.WXK_F1: "F1",
        wx.WXK_F2: "F2",
        wx.WXK_F3: "F3",
        wx.WXK_F4: "F4",
        wx.WXK_F5: "F5",
        wx.WXK_F6: "F6",
        wx.WXK_F7: "F7",
        wx.WXK_F8: "F8",
        wx.WXK_F9: "F9",
        wx.WXK_F10: "F10",
        wx.WXK_F11: "F11",
        wx.WXK_F12: "F12",
        wx.WXK_RETURN: "Enter",
        wx.WXK_NUMPAD_ENTER: "Enter",
        wx.WXK_SPACE: "Space",
        wx.WXK_DELETE: "Delete",
        wx.WXK_BACK: "Backspace",
        wx.WXK_ESCAPE: "Escape",
        wx.WXK_TAB: "Tab",
    }
    return names


class _LazyKeycodeNames:
    """Dict-like that builds the wx keycode map on first access."""

    def __init__(self) -> None:
        self._map: dict[int, str] | None = None

    def get(self, code: int, default=None):
        if self._map is None:
            try:
                self._map = _build_keycode_names()
            except Exception:
                self._map = {}
        return self._map.get(code, default)


_KEYCODE_NAMES = _LazyKeycodeNames()
