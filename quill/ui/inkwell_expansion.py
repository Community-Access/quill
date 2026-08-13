"""InkwellExpansionMixin -- the system-wide expansion service, as a mixin.

Extracted from :mod:`quill.apps.inkwell` so the app module stays a shell (menus,
window, commands) and the service that actually watches typing and types
expansions lives on its own, in the same mixin style QUILL's own frame uses.

The host must supply ``self.frame``, ``self._safe_mode``, ``self._data_dir``,
``self._settings``, ``self._library``, ``self._announce``,
``self._show_message_box``, ``self._reload_list``, and ``self._refresh_status``.
"""

from __future__ import annotations

from dataclasses import replace

import wx

from quill.core.abbreviations import (
    AbbreviationLibrary,
    load_abbreviation_library,
    record_use,
    save_abbreviation_library,
)
from quill.core.expansion.matcher import GlobalMatch

#: How often batched usage counts reach disk. Writing on every expansion would
#: put a disk write in the middle of someone's typing.
USAGE_SAVE_EVERY = 10


class InkwellExpansionMixin:
    """Installs the keyboard hook and performs expansions."""

    # -- expansion service -------------------------------------------------------

    def _start_expansion(self) -> None:
        """Install the keyboard hook. Announces, rather than fails silently, if
        Windows refuses -- a quiet failure here looks like a broken feature."""
        if self._hook is not None or self._safe_mode:
            return
        try:
            from quill.platform.windows.expansion_hook import ExpansionHook
        except Exception:  # noqa: BLE001 - non-Windows, or ctypes unavailable
            self._announce("System-wide expansion needs Windows.")
            return
        self._hook = ExpansionHook(
            self._on_global_match,
            self._current_library,
            get_clipboard_text=self._clipboard_text,
            excluded_processes=lambda: set(self._settings.excluded_processes),
            on_undo=self._on_global_undo,
            on_unreachable_window=self._on_unreachable_window,
        )
        self._hook.start()
        wx.CallLater(500, self._confirm_hook_installed)

    def _confirm_hook_installed(self) -> None:
        if self._hook is not None and not getattr(self._hook, "installed", False):
            self._show_message_box(
                "Quill Inkwell could not watch for abbreviations.\n\n"
                "Windows refused the keyboard hook. This usually means another "
                "program is already using it, or Inkwell needs to run at the same "
                "privilege level as the application you are typing into.",
                "Expansion unavailable",
                wx.ICON_WARNING | wx.OK,
            )
        self._refresh_status()

    def _stop_expansion(self) -> None:
        if self._hook is not None:
            self._hook.stop()
            self._hook = None
        if getattr(self, "_uses_pending", 0):
            self._uses_pending = 0
            try:
                save_abbreviation_library(self._library, self._data_dir)
            except Exception:  # noqa: BLE001 - shutdown must not fail on a counter
                pass

    def _current_library(self) -> AbbreviationLibrary:
        """The library as the hook should see it right now.

        Re-read from disk when the file changed, so an abbreviation added in
        QUILL is usable here without restarting either app -- the whole point of
        one shared library.
        """
        from quill.core.abbreviations import _ABBREVIATIONS_FILE  # noqa: PLC2701

        path = self._data_dir / _ABBREVIATIONS_FILE
        try:
            stamp = path.stat().st_mtime_ns
        except OSError:
            return self._library
        if stamp != getattr(self, "_library_stamp", None):
            self._library = load_abbreviation_library(self._data_dir)
            self._library_stamp = stamp
            wx.CallAfter(self._reload_list)
        return self._library

    def _clipboard_text(self) -> str:
        """The clipboard as plain text, for ``${clipboard}`` only.

        A snapshot taken at expansion time. Inkwell keeps no clipboard history
        of any kind.
        """
        try:
            import win32clipboard

            win32clipboard.OpenClipboard()
            try:
                if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
                    return str(win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT))
            finally:
                win32clipboard.CloseClipboard()
        except Exception:  # noqa: BLE001
            pass
        return ""

    def _on_global_undo(self, plan: object) -> None:
        """Put an abbreviation back, after Backspace right after it expanded.

        Runs on the hook's worker thread, like the expansion it reverses.
        """
        from quill.platform.windows import text_injector

        backspaces = int(getattr(plan, "backspaces", 0))
        text = str(getattr(plan, "text", ""))
        if backspaces <= 0 or not text:
            return
        # The Backspace the user pressed has already removed one character, so
        # only the rest of the expansion needs erasing.
        text_injector.inject_expansion(text, backspace_count=max(0, backspaces - 1))
        wx.CallAfter(self._announce, f"Undone. {text} is back.")

    def _on_unreachable_window(self) -> None:
        """Explain, once per window, why nothing expands in an elevated app."""
        wx.CallAfter(
            self._announce,
            "This application runs as administrator, so Quill Inkwell cannot see "
            "typing in it. Start Inkwell as administrator to expand there.",
        )

    def expand_now(self) -> None:
        """Expand the word just typed in whatever application has focus.

        The system-wide counterpart of QUILL's Expand Abbreviation command: it
        works mid-word, at the end of a line, and for entries set never to
        expand on their own.
        """
        hook = self._hook
        if hook is None:
            self._announce("System-wide expansion is not running.")
            return
        if not hook.expand_now():
            self._announce("No abbreviation to expand there.")

    def _on_global_match(self, match: GlobalMatch) -> None:
        """Perform one expansion. Runs on the hook's worker thread."""
        from quill.core.expansion.fields import has_fields

        if has_fields(match.abbreviation.expansion):
            # A form has to be filled on the UI thread, and it takes focus away
            # from wherever the user is typing -- so ask first, then give focus
            # back and type. Nothing has been erased yet, so cancelling leaves
            # their text exactly as they left it.
            wx.CallAfter(self._expand_with_fields, match)
            return
        self._inject(match)

    def _expand_with_fields(self, match: GlobalMatch) -> None:
        """Ask for the fields, restore focus, then expand. UI thread."""
        from quill.core.abbreviations import resolve_expansion
        from quill.ui.fill_in_dialog import prompt_for_fields

        target = self._foreground_before_dialog()
        filled = prompt_for_fields(
            self.frame,
            match.abbreviation.expansion,
            self._show_modal_dialog,
            title=match.abbreviation.abbreviation,
        )
        if filled is None:
            return
        text, cursor_offset, has_cursor = resolve_expansion(filled, self._clipboard_text())
        resolved = replace(match, text=text, cursor_offset=cursor_offset, has_cursor=has_cursor)
        if target:
            from quill.platform.windows.foreground import force_foreground_window

            force_foreground_window(target)
        # A moment for focus to actually land before typing into it.
        wx.CallLater(150, lambda: self._inject(resolved))

    def _inject(self, match: GlobalMatch) -> None:
        """Erase the abbreviation and type the expansion in the focused window."""
        from quill.platform.windows import text_injector

        caret_from_end = len(match.text) - match.cursor_offset if match.has_cursor else 0
        if self._injection_mode_now() == "paste":
            text_injector.send_backspaces(match.backspace_count)
            if not text_injector.paste_text(match.text):
                text_injector.send_text(match.text)
            # The hook swallowed the trigger character, so type it back here too.
            tail = match.trigger_char + (" " if match.trailing_space else "")
            if tail:
                text_injector.send_text(tail)
            text_injector.move_caret_left(caret_from_end + len(tail) if caret_from_end else 0)
        else:
            text_injector.inject_expansion(
                match.text,
                backspace_count=match.backspace_count,
                caret_from_end=caret_from_end,
                trailing_space=match.trailing_space,
                trigger_char=match.trigger_char,
            )
        # Arm the undo: a Backspace now puts the abbreviation back.
        hook = self._hook
        if hook is not None:
            # What is on screen now is the expansion, the trigger character, and
            # possibly a trailing space -- undo has to account for all of it and
            # put the user's own trigger character back with the abbreviation.
            hook.note_expansion(
                abbreviation=match.abbreviation.abbreviation + match.trigger_char,
                expanded_text=match.text + match.trigger_char,
                trailing_space=match.trailing_space,
            )
        wx.CallAfter(self._after_expansion, match)

    def _injection_mode_now(self) -> str:
        """How to deliver into the window that has focus right now.

        The per-application list wins over the global preference, so one
        stubborn program can use the clipboard route without every other one
        having its clipboard borrowed.
        """
        from quill.core.expansion.targets import injection_mode_for

        try:
            from quill.platform.windows.foreground import foreground_window_info

            process = foreground_window_info().process_name
        except Exception:  # noqa: BLE001
            process = ""
        return injection_mode_for(
            process,
            default_mode=self._settings.injection_mode,
            paste_processes=set(self._settings.paste_processes),
        )

    def _after_expansion(self, match: GlobalMatch) -> None:
        """UI-thread follow-up: usage counters, speech, and sound."""
        entry = match.abbreviation
        record_use(self._library, entry.id)
        # Batched, not per-expansion: a disk write belongs nowhere near typing.
        self._uses_pending = getattr(self, "_uses_pending", 0) + 1
        if self._uses_pending >= USAGE_SAVE_EVERY:
            self._uses_pending = 0
            save_abbreviation_library(self._library, self._data_dir)
            self._library_stamp = None  # our own write; force a re-read next time
        if entry.sound == "on" or (entry.sound == "inherit" and self._settings.announce_expansions):
            self._play_expansion_sound()
        if entry.speak_mode == "name":
            self._announce(entry.abbreviation)
        elif entry.speak_mode == "expansion":
            self._announce(match.text)
        elif self._settings.announce_expansions:
            preview = match.text[:40] + ("..." if len(match.text) > 40 else "")
            self._announce(f"Expanded to: {preview}")

    def _play_expansion_sound(self) -> None:
        """The shared sound-pack event, with the same winsound fallback the
        editor uses when no pack is configured."""
        try:
            from quill.core.sound_events import SoundEvent
            from quill.ui.sound_manager import is_active, post_sound

            if is_active():
                post_sound(SoundEvent.ABBREVIATION_EXPANDED)
                return
            import winsound

            winsound.MessageBeep(winsound.MB_OK)
        except Exception:  # noqa: BLE001 - a missing sound must never break expansion
            pass
