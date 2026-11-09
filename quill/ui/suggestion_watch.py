"""Closing the Word Prediction list when the caret or focus moves away.

Part of :mod:`quill.ui.suggestion_list`, split out on 2026-11-09 to keep that
module under the size budget (GATE-11). A stay-on-top list left floating over
another program, or over text whose caret has moved, is one Enter away from a
wrong edit (review 2026-11-09, QUILL 7 and QUILL Lite 9), so the list closes on
a click in the text, on focus leaving it, and on the window going to the
background. Caret keys are handled with the list's other keys.
"""

from __future__ import annotations

from typing import Any

__all__ = ["SuggestionWatchMixin"]


class SuggestionWatchMixin:
    """The watch; the hooks it calls are :class:`SuggestionListMixin`'s."""

    # Supplied by SuggestionListMixin and the editor: type-only annotations.
    _suggest_wx: Any
    _suggest_control: Any
    _suggest_parent: Any
    _suggest_popup: Any
    _hide_intellisense_popup: Any

    def _watch_for_caret_and_focus(self, popup: Any) -> None:
        """Close the list on a click in the text, on focus leaving it, and on
        the window going to the background (review 2026-11-09, QUILL 7, QUILL
        Lite 9): a stay-on-top list left floating over another program, or
        over text whose caret has moved, is one Enter away from a wrong edit.

        Bound once per control and once per window; every handler skips.
        """
        wx = self._suggest_wx()
        control = self._suggest_control()
        click = getattr(wx, "EVT_LEFT_DOWN", None)
        focus = getattr(wx, "EVT_KILL_FOCUS", None)
        if (
            control is not None
            and click is not None
            and focus is not None
            and not getattr(control, "_quill_suggest_watch", False)
        ):
            try:
                control.Bind(click, self._on_suggest_click)
                control.Bind(focus, self._on_suggest_focus_change)
                popup.listbox.Bind(focus, self._on_suggest_focus_change)
                control._quill_suggest_watch = True
            except (AttributeError, RuntimeError, TypeError):
                pass
        activate = getattr(wx, "EVT_ACTIVATE", None)
        if activate is not None and not getattr(self, "_intellisense_activate_bound", False):
            try:
                self._suggest_parent().Bind(activate, self._on_suggest_activate)
                self._intellisense_activate_bound = True
            except (AttributeError, RuntimeError, TypeError, NotImplementedError):
                pass

    def _on_suggest_click(self, event: Any) -> None:
        self._hide_intellisense_popup()
        event.Skip()

    def _on_suggest_focus_change(self, event: Any) -> None:
        event.Skip()
        # Focus has not landed yet; look once it has.
        call_after = getattr(self._suggest_wx(), "CallAfter", None)
        if callable(call_after):
            call_after(self._hide_unless_focus_is_ours)

    def _on_suggest_activate(self, event: Any) -> None:
        event.Skip()
        if not event.GetActive():
            call_after = getattr(self._suggest_wx(), "CallAfter", None)
            if callable(call_after):
                call_after(self._hide_unless_focus_is_ours)

    def _hide_unless_focus_is_ours(self) -> None:
        """Close the list unless focus is in the text or in the list itself."""
        popup = self._suggest_popup(create=False)
        if popup is None or not popup.is_visible():
            return
        try:
            focus = self._suggest_wx().Window.FindFocus()
        except Exception:  # noqa: BLE001 - no focus at all: another program has it
            focus = None
        if focus is not None and (focus is self._suggest_control() or popup.contains(focus)):
            return
        self._hide_intellisense_popup()
