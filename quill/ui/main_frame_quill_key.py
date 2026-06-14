"""QUILL-key / Quick-Nav prefix-and-browse behaviour for ``MainFrame`` (CQ-1).

Extracted verbatim from ``main_frame.py`` into a cohesive mixin so the UI
monolith shrinks without any behaviour change. ``MainFrame`` inherits
``QuillKeyMixin`` and every method resolves identically through the MRO; the
methods reference instance state and sibling methods (including
``BrowseModeMixin``) via ``self`` exactly as before.
"""

from __future__ import annotations

import time

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
from quill.ui.dialog_contract import apply_modal_ids


class QuillKeyMixin:
    def _handle_quill_key_mode_event(self, event: object) -> bool:
        wx = self._wx
        key_code = event.GetKeyCode()
        timeout = self._quill_key_timeout()
        if not self._quill_key_mode_active:
            if self._quill_key_prefix_pending:
                if timeout > 0 and (time.monotonic() - self._quill_key_prefix_started_at) > timeout:
                    self._quill_key_prefix_pending = False
                    self._quill_key_prefix_started_at = 0.0
                    self._set_status_quiet("QUILL key timed out")
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
                # §10.8.2: QUILL key, V = browser preview (Ctrl+Shift+Grave, V).
                if (
                    not event.ControlDown()
                    and not event.AltDown()
                    and not event.ShiftDown()
                    and key_code in (ord("V"), ord("v"))
                ):
                    self._quill_key_prefix_pending = False
                    self._quill_key_prefix_started_at = 0.0
                    self._refresh_statusbar()
                    self._run_command("view.browser_preview")
                    return True
                # §10.8.2: QUILL key, M = paste HTML as Markdown (magic paste).
                if (
                    not event.ControlDown()
                    and not event.AltDown()
                    and not event.ShiftDown()
                    and key_code in (ord("M"), ord("m"))
                ):
                    self._quill_key_prefix_pending = False
                    self._quill_key_prefix_started_at = 0.0
                    self._refresh_statusbar()
                    self.paste_html_as_markdown()
                    return True
                self._quill_key_prefix_pending = False
                self._quill_key_prefix_started_at = 0.0
                self._refresh_statusbar()
                return False
            if self._quill_key_prefix_matches(event):
                self._quill_key_prefix_pending = True
                self._quill_key_prefix_started_at = time.monotonic()
                message = (
                    "QUILL key prefix active. N for browse mode, press QUILL key again for "
                    "sticky mode, G for quick nav, M to paste HTML as Markdown, "
                    "V to preview in browser, ? for help"
                )
                if self._has_active_selection():
                    message = (
                        "QUILL key prefix active. N for browse mode, press QUILL key again for "
                        "sticky mode, G for quick nav, M to paste HTML as Markdown, "
                        "V to preview in browser, A for selection actions, ? for help"
                    )
                self._set_status_quiet(message)
                self._refresh_statusbar()
                return True
            return False

        if self._quill_key_mode_timed_out():
            self._exit_quill_key_mode("QUILL browse mode timed out")
            if self._event_has_modifiers(event):
                event.Skip()
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
        self._quill_key_prefix_pending = False
        self._quill_key_prefix_started_at = 0.0
        self._quill_key_mode_active = True
        self._quill_key_mode_sticky = sticky
        self._quill_key_mode_started_at = time.monotonic()
        if sticky:
            self._quill_feedback(
                "QUILL browse mode locked. It stays active until you press Escape.",
                status_message="QUILL browse mode locked",
                sound_kind="enter",
            )
            self._refresh_statusbar()
            return
        self._quill_feedback(
            "QUILL browse mode active. H headings, A links, L lists, I list items, "
            "T tables, Q block quotes, B bookmarks, P paragraphs, S sentences, "
            "1-6 heading levels, period repeats last action, ? for full help, Escape exits.",
            status_message="QUILL browse mode active",
            sound_kind="enter",
        )
        self._refresh_statusbar()

    def _exit_quill_key_mode(self, message: str) -> None:
        self._quill_key_mode_active = False
        self._quill_key_mode_sticky = False
        self._quill_key_mode_started_at = 0.0
        self._quill_feedback(message, status_message=message, sound_kind="exit")
        self._refresh_statusbar()

    def _quill_key_mode_timed_out(self) -> bool:
        if not self._quill_key_mode_active:
            return False
        if self._quill_key_mode_sticky:
            return False
        timeout = self._quill_key_timeout()
        if timeout <= 0:
            return False
        return (time.monotonic() - self._quill_key_mode_started_at) > timeout

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

    def _quill_key_prefix_matches(self, event: object) -> bool:
        binding = getattr(self.settings, "quill_key_binding", "Ctrl+Shift+Grave")
        parsed = self._parse_quill_key_binding(binding)
        if parsed is None:
            parsed = self._parse_quill_key_binding("Ctrl+Shift+Grave")
        if parsed is None:
            return False
        need_ctrl, need_shift, need_alt, key_code = parsed
        return (
            bool(event.ControlDown()) == need_ctrl
            and bool(event.ShiftDown()) == need_shift
            and bool(event.AltDown()) == need_alt
            and event.GetKeyCode() == key_code
        )

    def _event_has_modifiers(self, event: object) -> bool:
        return bool(event.ControlDown() or event.AltDown() or event.ShiftDown())

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
                f"No QUILL key action mapped to {action}",
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
        return bool(event.ShiftDown()) and key_code == ord("/")

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
            quill_key_label="QUILL key",
        )

    def _show_quill_key_cheat_sheet(self, mode: str) -> None:
        """Announce and present the live QUILL key cheat sheet (QK-2, QK-9)."""
        groups = self._build_quill_key_cheat_sheet(mode)
        self._announce(summarize_cheat_sheet(groups))
        self._present_quill_key_help(mode, format_cheat_sheet(groups))

    def _present_quill_key_help(self, mode: str, text: str) -> None:
        """Show the cheat sheet in an accessible, read-only dialog."""
        wx = self._wx
        title = "QUILL Key Help" if mode == MODE_BROWSE else "QUILL Key Prefix Help"
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
                        "Follow-on keys for the QUILL key, grouped by purpose. "
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
            self._announce(message)
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
