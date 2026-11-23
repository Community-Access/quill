"""Quill Inkwell types only into the place the text was meant for (FUX-07).

Two of Inkwell's insertions put a window of Inkwell's own between choosing the
text and typing it: **Quick Insert** (the picker, then perhaps a fill-in form)
and an abbreviation or snippet **with fields** (the fill-in form). While that
window is open the focus is Inkwell's, so the place to type has to be given
back before anything is typed -- and giving it back can fail: Windows refuses
to bring a window forward, the program was closed or restarted, another window
came up, or the focus landed on a different field.

So the place is captured **before** Inkwell's window opens -- the window, its
process and the focused control (:func:`probe_focused_target`) -- and checked
again at the moment of typing (:meth:`InkwellTextRuntime.replace_typed_text`
with ``expected_target``). Anywhere else, nothing is typed: the text is kept
and **Text Not Typed** (:mod:`quill.ui.held_text_dialog`) offers Insert (go
back there and try again) or Copy. It is never typed into whatever happens to
be in front, and its words are never read aloud.

Mixed into :class:`~quill.apps.inkwell.QuillInkwellFrame`; Quick Insert lives
here rather than in ``inkwell.py`` because typing it is this module's whole
concern.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

from quill.core.expansion.destination import HeldOffer, HeldText, held_offer

__all__ = ["FOCUS_SETTLE_MS", "InkwellDestinationMixin"]

#: How long to let the focus land after giving it back, before checking it.
FOCUS_SETTLE_MS = 150

_NOWHERE = "Nothing to insert into; copied to the clipboard instead."
_NO_CLIPBOARD = "Nothing to insert into, and the clipboard could not be opened."


class InkwellDestinationMixin:
    """Capture the place before Inkwell's own window opens; type only there."""

    frame: Any
    _library: Any
    _data_dir: Any
    _library_stamp: Any

    # Provided by the shell and the expansion mixin.
    def _announce(self, message: str, *, force: bool = False, sound: str = "") -> None:
        raise NotImplementedError

    def _show_modal_dialog(self, dialog: object, label: str) -> int:
        raise NotImplementedError

    def _copy_to_clipboard(self, text: str) -> bool:
        raise NotImplementedError

    def _clipboard_text(self) -> str:
        raise NotImplementedError

    def _injection_mode_now(self) -> str:
        raise NotImplementedError

    # -- seams (the tests replace these) ----------------------------------- #

    def _destination_now(self) -> Any:
        """The focused control now, or ``None`` when it is Inkwell's own or
        cannot be read. Never its text."""
        try:
            from quill.platform.windows.external_target import probe_focused_target

            target = probe_focused_target()
        except Exception:  # noqa: BLE001 - not Windows, or nothing readable
            return None
        if not target.target_id or not target.window_handle:
            return None
        if target.process_id == os.getpid():
            return None  # Inkwell never types into itself
        return target

    def _text_runtime(self) -> Any:
        from quill.platform.windows.text_runtime import InkwellTextRuntime

        return InkwellTextRuntime()

    def _bring_back(self, window: int) -> None:
        from quill.platform.windows.foreground import force_foreground_window

        force_foreground_window(window)

    def _after_focus_settles(self, action: Callable[[], None]) -> None:
        import wx

        wx.CallLater(FOCUS_SETTLE_MS, action)

    def _ask_held(self, offer: HeldOffer) -> str | None:
        from quill.ui.held_text_dialog import ask_held_text

        return ask_held_text(self.frame, offer, self._show_modal_dialog)

    # -- Quick Insert -------------------------------------------------------- #

    def open_quick_insert(self) -> None:
        """Pick an abbreviation and type its expansion where you were working.

        Inkwell's window is in front while the picker is open, so the place is
        remembered first and the expansion is typed after the focus is given
        back -- only if it is the same place.
        """
        import wx

        from quill.core.abbreviations import (
            record_use,
            resolve_expansion,
            save_abbreviation_library,
        )
        from quill.ui.fill_in_dialog import prompt_for_fields
        from quill.ui.quick_insert_dialog import QuickInsertDialog

        start = self._destination_now()
        dlg = QuickInsertDialog(self.frame, self._library)
        result = self._show_modal_dialog(dlg.dialog, "Quick Insert")
        chosen = dlg.chosen
        dlg.close()
        if result != wx.ID_OK or chosen is None:
            return
        filled = prompt_for_fields(
            self.frame, chosen.expansion, self._show_modal_dialog, title=chosen.abbreviation
        )
        if filled is None:
            return
        text, cursor_offset, has_cursor = resolve_expansion(filled, self._clipboard_text())
        record_use(self._library, chosen.id)
        save_abbreviation_library(self._library, self._data_dir)
        self._library_stamp = None
        caret_from_end = len(text) - cursor_offset if has_cursor else 0
        self._insert_held(HeldText(text, start, caret_from_end=caret_from_end))

    # -- typing it, or keeping it ------------------------------------------- #

    def _insert_held(self, held: HeldText, after: Callable[[], None] | None = None) -> None:
        """Give the focus back to *held*'s place, then type there or keep it.

        *after* runs once the text is typed (an expansion's undo and sound).
        """
        if held.target is None:
            self._announce(_NOWHERE if self._copy_to_clipboard(held.text) else _NO_CLIPBOARD)
            return
        try:
            self._bring_back(held.window)
        except Exception:  # noqa: BLE001 - the check before typing says if it did not
            pass
        self._after_focus_settles(lambda: self._type_held(held, after))

    def _type_held(self, held: HeldText, after: Callable[[], None] | None = None) -> None:
        """Type *held* if its place is in front; otherwise keep it and offer."""
        try:
            result = self._text_runtime().replace_typed_text(
                held.text,
                backspace_count=held.backspace_count,
                expected_window=held.window,
                expected_target=held.target,
                trailing_text=held.trailing_text,
                use_clipboard=self._injection_mode_now() == "paste",
                caret_from_end=held.caret_from_end,
            )
        except Exception:  # noqa: BLE001 - a failure keeps the text, never loses it
            from quill.core.external_text import (
                ExternalTextReason,
                OperationResult,
                OperationStatus,
            )

            result = OperationResult(
                OperationStatus.FAILED, ExternalTextReason.ADAPTER_UNAVAILABLE, ""
            )
        offer = held_offer(result)
        if offer is None:
            if after is not None:
                after()
            return
        self._offer_held(held, offer, after)

    def _offer_held(
        self, held: HeldText, offer: HeldOffer, after: Callable[[], None] | None = None
    ) -> None:
        """Text Not Typed: Insert tries the same place again; Copy copies."""
        from quill.ui.held_text_dialog import COPY, INSERT

        choice = self._ask_held(offer)
        if choice == INSERT:
            self._insert_held(held, after)
            return
        said = ""
        if choice == COPY:
            copied = self._copy_to_clipboard(held.text)
            said = "Copied." if copied else "The clipboard could not be opened."
        # Copy or Cancel: back to where you were, so a paste is one key away,
        # and the sentence after the focus lands, so the reader's announcement
        # of that program does not cut it off.
        if held.window:
            try:
                self._bring_back(held.window)
            except Exception:  # noqa: BLE001 - staying in Inkwell is harmless
                pass
        if said:
            self._after_focus_settles(lambda: self._announce(said))
