"""QUILL-key / Quick-Nav prefix-and-browse behaviour for ``MainFrame`` (CQ-1).

Extracted verbatim from ``main_frame.py`` into a cohesive mixin so the UI
monolith shrinks without any behaviour change. ``MainFrame`` inherits
``QuillKeyMixin`` and every method resolves identically through the MRO; the
methods reference instance state and sibling methods (including
``BrowseModeMixin``) via ``self`` exactly as before.
"""

from __future__ import annotations

import time

from quill.branding import QUILL_KEY_LABEL

try:
    import winsound as _winsound  # type: ignore[import]
except ImportError:  # pragma: no cover - non-Windows fallback
    _winsound = None  # type: ignore[assignment]

from quill.core.quill_key_help import (
    MODE_BROWSE,
    MODE_PREFIX,
    build_cheat_sheet,
    format_cheat_sheet,
    summarize_cheat_sheet,
)
from quill.ui.dialog_contract import apply_modal_ids, set_accessible_name

#: Named presets for the browse-mode follow-on timeout (seconds).
#: Tokens match the values in ``settings_specs.SETTING_SPECS`` for
#: ``browse_mode_followon_timeout``. ``"instant"``,
#: ``"unlimited"`` and ``"custom"`` are resolved separately in
#: :meth:`QuillKeyMixin._browse_mode_timeout`.
_BROWSE_TIMEOUT_PRESETS: dict[str, float] = {
    "fast": 1.5,
    "normal": 4.0,
    "slow": 8.0,
}


class QuillKeyMixin:
    def _handle_quill_key_mode_event(self, event: object) -> bool:
        wx = self._wx
        key_code = event.GetKeyCode()
        timeout = self._quill_key_timeout()
        if not self._quill_key_mode_active:
            if self._quill_key_prefix_pending:
                # A bare modifier keydown (e.g. pressing Shift before the "/"
                # in Shift+/ to type "?") fires its own EVT_CHAR_HOOK ahead of
                # the actual character. Without this guard it was treated as
                # the chord's second key, fell through to "Unrecognized QUILL
                # key chord", and cleared the pending prefix before the real
                # follow-on key ever arrived.
                if self._is_bare_modifier_key(key_code):
                    return True
                if timeout > 0 and (time.monotonic() - self._quill_key_prefix_started_at) > timeout:
                    self._quill_key_prefix_pending = False
                    self._quill_key_prefix_started_at = 0.0
                    self._set_status_quiet(f"{QUILL_KEY_LABEL} timed out")
                    self._refresh_statusbar()
                    return False
                if key_code in {getattr(wx, "WXK_ESCAPE", 27), 27}:
                    self._quill_key_prefix_pending = False
                    self._quill_key_prefix_started_at = 0.0
                    self._refresh_statusbar()
                    return True
                # QK-9: question mark after the prefix shows the prefix cheat sheet.
                if self._event_is_help_key(event):
                    self._quill_key_prefix_pending = False
                    self._quill_key_prefix_started_at = 0.0
                    self._refresh_statusbar()
                    self._show_quill_key_cheat_sheet(MODE_PREFIX)
                    return True
                # QK-5: a second press of the QUILL key locks a sticky browse
                # mode that ignores the timeout until Escape.
                if self._quill_key_prefix_matches(event):
                    self._quill_key_prefix_pending = False
                    self._quill_key_prefix_started_at = 0.0
                    self._enter_quill_key_mode(sticky=True)
                    return True
                if (
                    not event.ControlDown()
                    and not event.AltDown()
                    and not event.ShiftDown()
                    and key_code in (ord("N"), ord("n"))
                ):
                    self._quill_key_prefix_pending = False
                    self._quill_key_prefix_started_at = 0.0
                    # SET-4: when sticky browse is the configured default,
                    # entering browse mode with N stays locked until Escape
                    # instead of expiring on the QUILL key timeout.
                    sticky_default = bool(getattr(self.settings, "browse_mode_sticky", False))
                    self._enter_quill_key_mode(sticky=sticky_default)
                    return True
                # SEL-3: with text selected, the QUILL key offers scope-aware
                # actions. Pressing A after the prefix opens the actions surface.
                if (
                    not event.ControlDown()
                    and not event.AltDown()
                    and not event.ShiftDown()
                    and key_code in (ord("A"), ord("a"))
                    and self._has_active_selection()
                ):
                    self._quill_key_prefix_pending = False
                    self._quill_key_prefix_started_at = 0.0
                    self._refresh_statusbar()
                    self.quill_key_selection_actions()
                    return True
                # NAV-4: the QUILL key then G opens Quick Nav / Go to Anything.
                if (
                    not event.ControlDown()
                    and not event.AltDown()
                    and not event.ShiftDown()
                    and key_code in (ord("G"), ord("g"))
                ):
                    self._quill_key_prefix_pending = False
                    self._quill_key_prefix_started_at = 0.0
                    self._refresh_statusbar()
                    self.open_quick_nav()
                    return True
                # Data-driven chord dispatch: scan the keymap for any command
                # whose binding matches "<prefix>, <second-key>". Mode gates
                # (N, G, A+selection, QUILL+QUILL, Escape, ?) are handled
                # above and are never reached here.
                chord_command = self._chord_command_for_event(event)
                if chord_command is not None:
                    self._quill_key_prefix_pending = False
                    self._quill_key_prefix_started_at = 0.0
                    self._refresh_statusbar()
                    self._run_command(chord_command)
                    return True
                # Unrecognized second key — consume the event so the character
                # is never typed into the editor. Announce so the user knows
                # why nothing happened.
                self._quill_key_prefix_pending = False
                self._quill_key_prefix_started_at = 0.0
                self._refresh_statusbar()
                self._set_status_quiet(f"Unrecognized {QUILL_KEY_LABEL} chord. Press ? for help.")
                self._announce(f"Unrecognized {QUILL_KEY_LABEL} chord", force=True)
                return True
            if self._quill_key_prefix_matches(event):
                self._quill_key_prefix_pending = True
                self._quill_key_prefix_started_at = time.monotonic()
                message = (
                    f"{QUILL_KEY_LABEL} prefix active. N for browse mode, press "
                    f"{QUILL_KEY_LABEL} again for sticky mode, G for quick nav, "
                    "then any configured chord key, ? for help"
                )
                if self._has_active_selection():
                    message = (
                        f"{QUILL_KEY_LABEL} prefix active. N for browse mode, press "
                        f"{QUILL_KEY_LABEL} again for sticky mode, G for quick nav, "
                        "A for selection actions, then any configured chord key, ? for help"
                    )
                self._set_status_quiet(message)
                self._refresh_statusbar()
                # Speak the prefix so screen-reader users hear "QUILL" before
                # the chord sound. Gated by announce_mode_changes so users in
                # quiet / no-speech profiles keep the prefix silent.
                if bool(getattr(self.settings, "announce_mode_changes", True)):
                    self._announce(QUILL_KEY_LABEL, force=True)
                from quill.core.sound_events import SoundEvent
                from quill.ui.sound_manager import post_sound

                post_sound(SoundEvent.QUILL_KEY_PRESSED)
                return True
            return False

        if self._browse_mode_timed_out():
            self._exit_quill_key_mode("QUILL browse mode timed out")
            if self._event_has_modifiers(event):
                event.Skip()
            return True

        # Same bare-modifier issue as the prefix-pending branch above: a lone
        # Shift keydown ahead of e.g. Shift+Tab or Shift+1 would otherwise
        # read as "a modified key with no matching action" and exit browse
        # mode before the real combo ever arrived.
        if self._is_bare_modifier_key(key_code):
            return True

        if key_code in {getattr(wx, "WXK_ESCAPE", 27), 27}:
            if event.ShiftDown():
                self._refresh_browse_navigation_cache_now()
                return True
            self._exit_quill_key_mode("Exited QUILL browse mode")
            return True

        if self._quill_key_prefix_matches(event):
            self._exit_quill_key_mode("Exited QUILL browse mode")
            return True

        # QK-9: question mark inside browse mode shows the browse cheat sheet
        # for the active keymap without leaving browse mode.
        if self._event_is_help_key(event):
            self._show_quill_key_cheat_sheet(MODE_BROWSE)
            return True

        action = self._quill_key_action_for_event(event)
        if action is None:
            if self._event_has_modifiers(event):
                self._exit_quill_key_mode("QUILL browse mode closed for normal shortcut use")
                event.Skip()
                return True
            self._exit_quill_key_mode("No QUILL key action matched")
            return True

        if action == "exit":
            self._exit_quill_key_mode("Exited QUILL browse mode")
            return True

        self._run_quill_key_action(action)
        return True

    def _enter_quill_key_mode(self, *, sticky: bool = False) -> None:
        from quill.core.sound_events import SoundEvent
        from quill.ui.sound_manager import post_sound

        self._quill_key_prefix_pending = False
        self._quill_key_prefix_started_at = 0.0
        self._quill_key_mode_active = True
        self._quill_key_mode_sticky = sticky
        self._quill_key_mode_started_at = time.monotonic()
        post_sound(SoundEvent.BROWSE_MODE_ON)
        if sticky:
            self._quill_feedback(
                "QUILL browse mode locked. It stays active until you press Escape.",
                status_message="QUILL browse mode locked",
                sound_kind="enter",
            )
            self._refresh_statusbar()
            return
        self._quill_feedback(
            "QUILL browse mode active. Press ? for help, Escape to exit.",
            status_message="QUILL browse mode active",
            sound_kind="enter",
        )
        self._refresh_statusbar()

    def _exit_quill_key_mode(self, message: str) -> None:
        from quill.core.sound_events import SoundEvent
        from quill.ui.sound_manager import post_sound

        self._quill_key_mode_active = False
        self._quill_key_mode_sticky = False
        self._quill_key_mode_started_at = 0.0
        post_sound(SoundEvent.BROWSE_MODE_OFF)
        self._quill_feedback(message, status_message=message, sound_kind="exit")
        self._refresh_statusbar()

    def _browse_mode_timed_out(self) -> bool:
        if not self._quill_key_mode_active:
            return False
        if self._quill_key_mode_sticky:
            return False
        timeout = self._browse_mode_timeout()
        if timeout <= 0:
            return False
        return (time.monotonic() - self._quill_key_mode_started_at) > timeout

    # Backwards-compatible alias — the prefix-timeout path uses the same name
    # in callers and was renamed internally to make the role explicit.
    def _quill_key_mode_timed_out(self) -> bool:
        return self._browse_mode_timed_out()

    def _quill_key_timeout(self) -> float:
        """Return the configured QUILL key timeout in seconds (0 = no timeout)."""
        raw = getattr(
            self.settings, "quill_key_timeout_seconds", self._quill_key_mode_timeout_seconds
        )
        try:
            value = float(raw)
        except (TypeError, ValueError):
            value = self._quill_key_mode_timeout_seconds
        return max(value, 0.0)

    def _browse_mode_timeout(self) -> float:
        """Return the browse-mode follow-on timeout in seconds (0 = no timeout).

        The follow-on timeout governs how long browse mode stays active
        between follow-on keypresses after entering with N. It is separate
        from :meth:`_quill_key_timeout` so the prefix-decision window
        stays snappy while browse mode gives users a generous window to
        find the next key.

        Resolution rules (see the
        ``browse_mode_followon_timeout`` setting spec):

        - ``instant`` -> a tiny positive timeout (``0.001`` s) so
          :meth:`_browse_mode_timed_out` fires on the very next check;
          ``0`` is reserved for "no timeout"
        - ``fast`` / ``normal`` / ``slow`` -> preset seconds
        - ``custom`` -> ``browse_mode_followon_custom_ms / 1000``,
          clamped to ``>= 0`` (``0`` means no timeout)
        - ``unlimited`` and any unknown token -> ``0`` (no timeout)
        """
        token = (
            str(getattr(self.settings, "browse_mode_followon_timeout", "unlimited")).strip().lower()
        )
        if token == "instant":
            return 0.001
        if token in _BROWSE_TIMEOUT_PRESETS:
            return _BROWSE_TIMEOUT_PRESETS[token]
        if token == "custom":
            try:
                ms = float(getattr(self.settings, "browse_mode_followon_custom_ms", 4000))
            except (TypeError, ValueError):
                ms = 4000.0
            return max(ms / 1000.0, 0.0)
        return 0.0

    def _parse_quill_key_binding(self, binding: str | None) -> tuple[bool, bool, bool, int] | None:
        """Parse the configurable QUILL key binding into (ctrl, shift, alt, key_code).

        Understands the Grave/backtick key that ``_parse_keybinding`` does not.
        """
        if not binding:
            return None
        parts = [part.strip() for part in str(binding).split("+") if part.strip()]
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
        if token in {"GRAVE", "BACKTICK", "`"}:
            key_code = getattr(self._wx, "WXK_BACKTICK", ord("`"))
            return ctrl, shift, alt, key_code
        parsed = self._parse_keybinding("+".join(parts))
        if parsed is None:
            return None
        _flags, key_code = parsed
        return ctrl, shift, alt, key_code

    def _event_ctrl_equivalent_down(self, event: object) -> bool:
        """True if the binding's "Ctrl" modifier is satisfied on this platform.

        On macOS, wx's ``ControlDown()`` reflects the Cmd key, not the
        physical Control key — the physical key is exposed separately via
        ``RawControlDown()`` (a Mac-only method; identical to
        ``ControlDown()`` on Windows/Linux). Checking only ``ControlDown()``
        means a literal Ctrl+Shift+` press is invisible to the QUILL key on
        macOS, and Cmd+Shift+` is macOS's own reserved "cycle windows"
        shortcut, so it never reaches the app either — leaving the default
        binding unusable on macOS both ways.
        """
        if event.ControlDown():
            return True
        raw_ctrl_fn = getattr(event, "RawControlDown", None)
        return bool(raw_ctrl_fn()) if callable(raw_ctrl_fn) else False

    def _quill_key_prefix_matches(self, event: object) -> bool:
        binding = getattr(self.settings, "quill_key_binding", "Ctrl+Shift+Grave")
        parsed = self._parse_quill_key_binding(binding)
        if parsed is None:
            parsed = self._parse_quill_key_binding("Ctrl+Shift+Grave")
        if parsed is None:
            return False
        need_ctrl, need_shift, need_alt, key_code = parsed
        if (
            self._event_ctrl_equivalent_down(event) != need_ctrl
            or bool(event.ShiftDown()) != need_shift
            or bool(event.AltDown()) != need_alt
        ):
            return False
        # For grave/backtick, wxPython on Windows often reports VK_OEM_3
        # (0xC0 = 192) instead of ord("`") = 96.  Use multi-strategy detection
        # so the key is found regardless of what the driver reports.
        if key_code in (ord("`"), 0xC0):
            return self._event_matches_grave_key(event)
        return event.GetKeyCode() == key_code

    def _event_has_modifiers(self, event: object) -> bool:
        return bool(event.ControlDown() or event.AltDown() or event.ShiftDown())

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

    def _quill_key_action_for_event(self, event: object) -> str | None:
        wx = self._wx
        key_code = event.GetKeyCode()
        shift = event.ShiftDown()
        key_binding_map = {
            "quill.quick_nav.heading": "heading",
            "quill.quick_nav.link": "link",
            "quill.quick_nav.list": "list",
            "quill.quick_nav.list_item": "list_item",
            "quill.quick_nav.table": "table",
            "quill.quick_nav.block_quote": "block_quote",
            "quill.quick_nav.bookmark": "bookmark",
            "quill.quick_nav.code_block": "code_block",
            "quill.quick_nav.table_of_contents": "table_of_contents",
            "quill.quick_nav.paragraph": "paragraph",
            "quill.quick_nav.sentence": "sentence",
            "quill.quick_nav.block": "block",
            "quill.quick_nav.skip_forward": "skip_forward",
            "quill.quick_nav.skip_backward": "skip_backward",
        }
        for binding_key, action in key_binding_map.items():
            configured = str(self._binding_for(binding_key) or "").strip().upper()
            if not configured or "," in configured:
                continue
            if configured in {"TAB", "SHIFT+TAB"}:
                continue
            parsed = self._parse_keybinding(configured)
            if parsed is None:
                continue
            _flags, configured_key_code = parsed
            if key_code == configured_key_code:
                return f"browse.{action}.previous" if shift else f"browse.{action}.next"
        if ord("1") <= key_code <= ord("6"):
            level = key_code - ord("0")
            return (
                f"browse.heading_level.{level}.previous"
                if shift
                else f"browse.heading_level.{level}.next"
            )
        if key_code in {getattr(wx, "WXK_TAB", 9)}:
            return "browse.block.previous" if shift else "browse.block.next"
        if key_code == ord(".") and not event.ControlDown() and not event.AltDown() and not shift:
            return "browse.repeat_last"
        return None

    def _run_quill_key_action(self, action: str) -> None:
        if action == "browse.repeat_last":
            last = getattr(self, "_last_quill_action", None)
            if last is None:
                self._quill_feedback(
                    "No previous QUILL action to repeat",
                    status_message="No previous QUILL action",
                    sound_kind="error",
                )
                return
            self._run_quill_key_action(last)
            return
        self._last_quill_action = action
        if action.startswith("browse.heading_level."):
            parts = action.split(".")
            level = int(parts[2])
            reverse = parts[3] == "previous"
            self._browse_heading_level(level, reverse=reverse)
            return
        mapping = {
            "browse.heading.next": lambda: self.navigate_next_heading(),
            "browse.heading.previous": lambda: self.navigate_previous_heading(),
            "browse.link.next": lambda: self._browse_link(reverse=False),
            "browse.link.previous": lambda: self._browse_link(reverse=True),
            "browse.list.next": lambda: self._browse_list(reverse=False),
            "browse.list.previous": lambda: self._browse_list(reverse=True),
            "browse.list_item.next": lambda: self._browse_list_item(reverse=False),
            "browse.list_item.previous": lambda: self._browse_list_item(reverse=True),
            "browse.table.next": lambda: self._browse_table(reverse=False),
            "browse.table.previous": lambda: self._browse_table(reverse=True),
            "browse.block_quote.next": lambda: self._browse_block_quote(reverse=False),
            "browse.block_quote.previous": lambda: self._browse_block_quote(reverse=True),
            "browse.bookmark.next": lambda: self._browse_bookmark(reverse=False),
            "browse.bookmark.previous": lambda: self._browse_bookmark(reverse=True),
            "browse.code_block.next": lambda: self._browse_code_block(reverse=False),
            "browse.code_block.previous": lambda: self._browse_code_block(reverse=True),
            "browse.table_of_contents.next": lambda: self.open_outline_navigator(),
            "browse.table_of_contents.previous": lambda: self.open_outline_navigator(),
            "browse.paragraph.next": lambda: self._browse_paragraph(reverse=False),
            "browse.paragraph.previous": lambda: self._browse_paragraph(reverse=True),
            "browse.sentence.next": lambda: self._browse_sentence(reverse=False),
            "browse.sentence.previous": lambda: self._browse_sentence(reverse=True),
            "browse.block.next": lambda: self.navigate_next_block(),
            "browse.block.previous": lambda: self.navigate_previous_block(),
            "browse.skip_forward.next": lambda: self._browse_skip_container(reverse=False),
            "browse.skip_forward.previous": lambda: self._browse_skip_container(reverse=False),
            "browse.skip_backward.next": lambda: self._browse_skip_container(reverse=True),
            "browse.skip_backward.previous": lambda: self._browse_skip_container(reverse=True),
        }
        runner = mapping.get(action)
        if runner is None:
            self._quill_feedback(
                f"No {QUILL_KEY_LABEL} action mapped to {action}",
                status_message="No browse action mapped",
                sound_kind="error",
            )
            return
        runner()

    def _event_is_help_key(self, event: object) -> bool:
        """Return True when the event is a question mark (cheat-sheet request)."""
        key_code = event.GetKeyCode()
        if key_code == ord("?"):
            return True
        # '?' is Shift+'/' on most layouts; wx reports the '/' virtual key.
        if bool(event.ShiftDown()) and key_code == ord("/"):
            return True
        # Some layouts report neither the shifted key nor the modifier state
        # cleanly. The Unicode key is the most reliable fallback — wx returns
        # ord("?") (63) when Shift+Slash produces a question mark regardless
        # of what GetKeyCode / ShiftDown report.
        unicode_fn = getattr(event, "GetUnicodeKey", None)
        if callable(unicode_fn) and int(unicode_fn()) == ord("?"):
            return True
        return False

    def _event_matches_grave_key(self, event: object) -> bool:
        """Multi-strategy detection for the physical grave/backtick key.

        wxPython on Windows commonly reports VK_OEM_3 (0xC0 = 192) rather than
        ord("`") = 96 for Ctrl+Shift+`.  Three independent strategies are tried
        so the key is recognised on any driver or keyboard layout:
        1. wxPython key code or Unicode key == ord("`") or ord("~")
        2. Windows virtual-key VK_OEM_3 via GetRawKeyCode()
        3. Physical scan code 0x29 (the key below Esc / above Tab on PC
           keyboards) via bits 16-23 of GetRawKeyFlags() — reliable on
           international layouts that do not call this key a backtick.
        """
        kc = event.GetKeyCode()
        if kc in (ord("`"), ord("~")):
            return True
        unicode_key_fn = getattr(event, "GetUnicodeKey", None)
        if callable(unicode_key_fn) and int(unicode_key_fn()) in (ord("`"), ord("~")):
            return True
        VK_OEM_3 = 0xC0
        raw_kc_fn = getattr(event, "GetRawKeyCode", None)
        raw_kc = int(raw_kc_fn()) if callable(raw_kc_fn) else 0
        if raw_kc == VK_OEM_3 or kc == VK_OEM_3:
            return True
        raw_flags_fn = getattr(event, "GetRawKeyFlags", None)
        raw_flags = int(raw_flags_fn()) if callable(raw_flags_fn) else 0
        if raw_flags and ((raw_flags >> 16) & 0xFF) == 0x29:
            return True
        return False

    def _chord_command_for_event(self, event: object) -> str | None:
        """Return the command_id for a chord that matches the current event.

        Scans the live keymap for bindings of the form ``<prefix>, <second-key>``
        and returns the first command_id whose second key matches the event.
        Mode-gate keys (N, G, A+selection, QUILL+QUILL, Escape, ?) are consumed
        before this is called and will never be returned here.
        """
        prefix = str(getattr(self.settings, "quill_key_binding", "Ctrl+Shift+Grave")).strip()
        chord_prefix = prefix + ", "
        for command_id, binding in (getattr(self, "keymap", None) or {}).items():
            if not binding or not binding.startswith(chord_prefix):
                continue
            second_key = binding[len(chord_prefix) :].strip()
            parsed = self._parse_chord_second_key(second_key)
            if parsed is None:
                continue
            if self._second_key_matches_event(parsed, event):
                return command_id
        return None

    def _parse_chord_second_key(self, second_key: str) -> tuple[bool, bool, bool, int] | None:
        """Parse the second part of a chord binding into (ctrl, shift, alt, key_code).

        Handles bare keys (``V``, ``1``), modifier combos (``Shift+O``), and
        named keys (``Tab``, ``Enter``, ``F1``–``F12``).
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

    def _second_key_matches_event(
        self, parsed: tuple[bool, bool, bool, int], event: object
    ) -> bool:
        need_ctrl, need_shift, need_alt, key_code = parsed
        return (
            bool(event.ControlDown()) == need_ctrl
            and bool(event.ShiftDown()) == need_shift
            and bool(event.AltDown()) == need_alt
            and event.GetKeyCode() == key_code
        )

    def _quill_key_help_counts(self) -> dict[str, int]:
        """Build live element counts for the QUILL key cheat sheet."""
        try:
            context = self._browse_navigation_context()
        except Exception:
            return {}
        headings_by_level = context.get("headings_by_level") or {}
        counts: dict[str, int] = {}
        total_headings = 0
        for level in range(1, 7):
            positions = headings_by_level.get(level) or []
            counts[f"heading_level_{level}"] = len(positions)
            total_headings += len(positions)
        counts["headings"] = total_headings
        counts["links"] = len(context.get("links") or [])
        counts["lists"] = len(context.get("lists") or [])
        counts["list_items"] = len(context.get("list_items") or [])
        counts["tables"] = len(context.get("tables") or [])
        counts["block_quotes"] = len(context.get("block_quotes") or [])
        counts["bookmarks"] = len(context.get("bookmarks") or [])
        counts["code_blocks"] = len(context.get("code_blocks") or [])
        counts["paragraphs"] = len(context.get("paragraph_spans") or [])
        counts["sentences"] = len(context.get("sentence_spans") or [])
        return counts

    def _build_quill_key_cheat_sheet(self, mode: str) -> tuple[object, ...]:
        counts = self._quill_key_help_counts() if mode == MODE_BROWSE else {}
        return build_cheat_sheet(
            mode=mode,
            binding_lookup=self._binding_for,
            counts=counts,
            selection_active=self._has_active_selection(),
            quill_key_label=QUILL_KEY_LABEL,
            chord_map=self.keymap,
            prefix=str(getattr(self.settings, "quill_key_binding", "Ctrl+Shift+Grave")),
        )

    def _show_quill_key_cheat_sheet(self, mode: str) -> None:
        """Announce and present the live QUILL key cheat sheet (QK-2, QK-9)."""
        groups = self._build_quill_key_cheat_sheet(mode)
        self._announce(summarize_cheat_sheet(groups), force=True)
        self._present_quill_key_help(mode, format_cheat_sheet(groups))

    def _present_quill_key_help(self, mode: str, text: str) -> None:
        """Show the cheat sheet in an accessible, read-only dialog."""
        wx = self._wx
        title = (
            f"{QUILL_KEY_LABEL} Help" if mode == MODE_BROWSE else f"{QUILL_KEY_LABEL} Prefix Help"
        )
        dialog = wx.Dialog(
            self.frame,
            title=title,
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            size=(560, 560),
        )
        try:
            inner = wx.BoxSizer(wx.VERTICAL)
            inner.Add(
                wx.StaticText(
                    dialog,
                    label=(
                        f"Follow-on keys for the {QUILL_KEY_LABEL}, grouped by purpose. "
                        "Counts show how many of each element are in this document."
                    ),
                ),
                0,
                wx.ALL | wx.EXPAND,
                8,
            )
            review = wx.TextCtrl(
                dialog,
                value=text,
                style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_DONTWRAP,
            )
            set_accessible_name(review, title)
            inner.Add(review, 1, wx.ALL | wx.EXPAND, 8)
            close_button = wx.Button(dialog, id=wx.ID_OK, label="Close")
            buttons = wx.StdDialogButtonSizer()
            buttons.AddButton(close_button)
            buttons.Realize()
            inner.Add(buttons, 0, wx.ALL | wx.EXPAND, 8)
            dialog.SetSizer(inner)
            close_button.SetDefault()
            apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_OK)
            call_after = getattr(wx, "CallAfter", None)
            if callable(call_after):
                call_after(review.SetFocus)
            else:
                review.SetFocus()
            self._show_modal_dialog(dialog, title)
        finally:
            dialog.Destroy()
            self.editor.SetFocus()

    def _quill_feedback(
        self, message: str, *, status_message: str | None = None, sound_kind: str | None = None
    ) -> None:
        mode = str(getattr(self.settings, "browse_mode_feedback", "speech")).strip().lower()
        status = status_message or message
        announce_modes = bool(getattr(self.settings, "announce_mode_changes", True))
        if mode in {"speech", "both"} and announce_modes:
            self._announce(message, force=True)
        else:
            self._set_status_quiet(status)
        if sound_kind and mode in {"sound", "both"}:
            self._play_quill_sound(sound_kind)

    def _play_quill_sound(self, kind: str) -> None:
        custom_path = str(getattr(self.settings, f"quill_key_sound_{kind}", "") or "").strip()
        if custom_path and _winsound is not None:
            try:
                _winsound.PlaySound(
                    custom_path,
                    _winsound.SND_FILENAME | _winsound.SND_ASYNC | _winsound.SND_NODEFAULT,
                )
                return
            except Exception:
                pass
        # When QSP is active, route to the Ink pack instead of winsound.Beep.
        # "enter"/"exit" are already fired unconditionally by _enter/exit_quill_key_mode.
        from quill.ui.sound_manager import is_active, post_sound

        if is_active():
            from quill.core.sound_events import SoundEvent

            _QSP_MAP = {"move": SoundEvent.HEADING_JUMPED, "error": SoundEvent.ERROR}
            event = _QSP_MAP.get(kind)
            if event:
                post_sound(event)
            return
        # Legacy winsound.Beep fallback when QSP is not available.
        pattern = {
            "enter": [(880, 45), (1175, 45)],
            "exit": [(660, 70)],
            "move": [(784, 30)],
            "error": [(392, 70), (311, 90)],
        }.get(kind, [(784, 30)])
        if _winsound is not None:
            try:
                for frequency, duration in pattern:
                    _winsound.Beep(frequency, duration)
                return
            except Exception:
                pass
        bell = getattr(self._wx, "Bell", None)
        if callable(bell):
            bell()
