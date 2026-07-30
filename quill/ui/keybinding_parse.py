"""Pure keybinding parsers shared by the keymap editor and global hotkeys.

These three helpers turn a textual binding (``"Ctrl+Shift+K"``, a chord's
second key ``"Shift+O"``, or a raw wx key code) into the shapes the dispatch
and recording layers need. They are pure -- they read only their arguments,
module-level constants, and ``self._wx`` (the wx module accessor every frame
carries) -- so one copy on :class:`KeybindingParseMixin` serves both
``MainFrame`` (via its ``QuillKeyMixin`` / ``KeymapEditorMixin`` callers) and
the standalone companion app frames (Quill Radio, Quill Cast), which now
compose ``GlobalHotkeysMixin`` / ``KeymapEditorMixin`` too. Keeping one source
of truth means the editor and the hotkey layer can never drift apart on what a
binding string means.
"""

from __future__ import annotations


class KeybindingParseMixin:
    """The three pure keybinding parsers, resolved via MRO on every host."""

    def _parse_keybinding(self, keybinding: str | None) -> tuple[int, int] | None:
        if not keybinding:
            return None
        wx = self._wx
        parts = [part.strip() for part in keybinding.split("+") if part.strip()]
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
                # "Cmd" is how DEFAULT_KEYMAP spells the macOS-only bindings
                # (navigate.back_location/forward_location, and
                # window.next_document/previous_document -- see keymap.py).
                # wx has no separate ACCEL_CMD flag: wx.ACCEL_CTRL is what
                # already maps to the Command key in a wx.AcceleratorTable on
                # macOS, so "Cmd" parses to the same flag as "Ctrl". Without
                # this, a "Cmd+..." binding fell through to the "else: return
                # None" branch below and silently never got an accelerator
                # table entry at all on any platform.
                flags |= wx.ACCEL_CTRL
            else:
                return None

        key_token = parts[-1].upper()
        if len(key_token) == 1:
            return flags, ord(key_token)

        function_keys: dict[str, int] = {
            f"F{index}": getattr(wx, f"WXK_F{index}") for index in range(1, 13)
        }
        named_keys: dict[str, int] = {
            "ENTER": wx.WXK_RETURN,
            "TAB": wx.WXK_TAB,
            "SPACE": wx.WXK_SPACE,
            "ESC": wx.WXK_ESCAPE,
            "ESCAPE": wx.WXK_ESCAPE,
            "DELETE": wx.WXK_DELETE,
            "BACKSPACE": wx.WXK_BACK,
            "HOME": wx.WXK_HOME,
            "END": wx.WXK_END,
            "LEFT": wx.WXK_LEFT,
            "RIGHT": wx.WXK_RIGHT,
        }
        if key_token in function_keys:
            return flags, function_keys[key_token]
        if key_token in named_keys:
            return flags, named_keys[key_token]
        return None

    def _is_bare_modifier_key(self, key_code: int) -> bool:
        """True when ``key_code`` is a modifier key pressed on its own.

        wx fires EVT_CHAR_HOOK for the modifier keydown itself (e.g. Shift
        going down just before the "/" that makes "?"), separately from the
        combo it's part of. Chord/browse-mode dispatch must ignore these or
        they get misread as an unrecognized second key.
        """
        wx = self._wx
        return key_code in {
            getattr(wx, "WXK_SHIFT", -11),
            getattr(wx, "WXK_CONTROL", -10),
            getattr(wx, "WXK_ALT", -12),
            getattr(wx, "WXK_RAW_CONTROL", -13),
            getattr(wx, "WXK_WINDOWS_LEFT", -14),
            getattr(wx, "WXK_WINDOWS_RIGHT", -15),
        }

    def _parse_chord_second_key(self, second_key: str) -> tuple[bool, bool, bool, int] | None:
        """Parse the second part of a chord binding into (ctrl, shift, alt, key_code).

        Handles bare keys (``V``, ``1``), modifier combos (``Shift+O``), and
        named keys (``Tab``, ``Enter``, ``F1``-``F12``).
        """
        wx = self._wx
        parts = [p.strip() for p in second_key.split("+") if p.strip()]
        if not parts:
            return None
        ctrl = shift = alt = False
        for modifier in parts[:-1]:
            lowered = modifier.lower()
            if lowered == "ctrl":
                ctrl = True
            elif lowered == "shift":
                shift = True
            elif lowered == "alt":
                alt = True
            else:
                return None
        token = parts[-1].upper()
        if len(token) == 1:
            return ctrl, shift, alt, ord(token)
        named: dict[str, int] = {
            "ENTER": getattr(wx, "WXK_RETURN", 13),
            "TAB": getattr(wx, "WXK_TAB", 9),
            "SPACE": getattr(wx, "WXK_SPACE", 32),
            "ESC": getattr(wx, "WXK_ESCAPE", 27),
            "ESCAPE": getattr(wx, "WXK_ESCAPE", 27),
            "DELETE": getattr(wx, "WXK_DELETE", 127),
            "BACKSPACE": getattr(wx, "WXK_BACK", 8),
            "HOME": getattr(wx, "WXK_HOME", 313),
            "END": getattr(wx, "WXK_END", 312),
            **{f"F{i}": getattr(wx, f"WXK_F{i}", 339 + i) for i in range(1, 13)},
        }
        if token in named:
            return ctrl, shift, alt, named[token]
        return None
