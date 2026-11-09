"""The suggestion list: Word Prediction on Ctrl+., shared by QUILL and QUILL Lite.

One implementation for both editors, so they cannot drift on what is offered,
what is said or what Escape does (the plan of record is
``docs/design/intellisense.md``). The suggestions themselves come from
:mod:`quill.core.intellisense`; this module is the floating list and the keys
that drive it. Each editor supplies the ``_suggest_*`` hooks at the bottom of
:class:`SuggestionListMixin` and nothing else.

What a listener gets:

* **Ctrl+.** opens the list. You hear the count and the first suggestion,
  "8 predictions. counter". In a code file the list holds the file's own
  names with their kinds instead (:mod:`quill.core.code_names`): "8
  suggestions. count, function". Focus stays in the text, so the screen
  reader goes on reading what you type.
* **Up** and **Down** move through the list and say each suggestion, and in
  code its kind. The list
  is not focused, so the app says it; the screen reader cannot.
* **Enter** or **Tab** inserts the selected suggestion in place of the part of
  the word you typed, and nothing else. **Escape** closes the list and never
  changes the text.
* Typing with the list open narrows it. With "as you type" on (QUILL only, off
  by default) the list also opens on its own after two letters.

If focus ever lands in the floating window (Tab, the mouse, a screen reader's
own navigation), Escape, Enter and Tab still work there, so it is never a trap.
"""

from __future__ import annotations

from typing import Any

from quill.core.code_names import code_language_for
from quill.core.intellisense import (
    IntellisenseContext,
    IntellisenseSuggestion,
    build_code_suggestions,
    build_intellisense_suggestions,
    collect_document_words,
    spoken_suggestion,
    suggestions_status,
)
from quill.ui.dpi import dip_size

__all__ = ["SuggestionListMixin", "SuggestionPopup", "suggestion_status"]

#: How many suggestions the list holds.
SUGGESTION_LIMIT = 8


def suggestion_status(suggestions: list[IntellisenseSuggestion]) -> str:
    """What is said when the list opens: the count, then the first suggestion.

    In code, the first suggestion's kind too: "8 suggestions. count, function".
    """
    return suggestions_status(suggestions)


class SuggestionPopup:
    """The floating window: a status line and the list, shown without focus."""

    def __init__(self, wx: Any, parent: Any) -> None:
        self._wx = wx
        self._accept_callback: Any = None
        self._dismiss_callback: Any = None
        self.frame = wx.Frame(
            parent,
            title="Word Prediction",
            style=wx.FRAME_NO_TASKBAR | wx.STAY_ON_TOP | wx.BORDER_SIMPLE,
        )
        self.frame.SetSize(dip_size(self.frame, 420, 220))
        root = wx.BoxSizer(wx.VERTICAL)
        self.status = wx.StaticText(self.frame, label="")
        root.Add(self.status, 0, wx.EXPAND | wx.ALL, 6)
        self.listbox = wx.ListBox(self.frame)
        # Accessible name so a screen reader announces the list's purpose if
        # focus ever lands here directly.
        self.listbox.SetName("Word prediction suggestions")
        self.listbox.SetHelpText(
            "Suggestions for the word you are typing. Up and Down choose one, "
            "Enter or Tab inserts it, and Escape closes the list without "
            "changing your text."
        )
        root.Add(self.listbox, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)
        self.frame.SetSizer(root)
        self.suggestions: list[IntellisenseSuggestion] = []
        self.frame.Bind(wx.EVT_CLOSE, self._on_close)
        self.listbox.Bind(wx.EVT_LISTBOX_DCLICK, self._on_accept)
        # The intended flow keeps focus in the editor and drives this list from
        # the editor's key handler. But focus can still land in the listbox (Tab,
        # mouse, or screen-reader navigation into this floating window), and a
        # bare wx.ListBox has no way out -- Escape/Tab/Enter would do nothing,
        # trapping the user. Handle those keys here too so the list is never a
        # dead end regardless of where focus is.
        self.listbox.Bind(wx.EVT_CHAR_HOOK, self._on_listbox_key)

    def set_accept_callback(self, callback: Any) -> None:
        self._accept_callback = callback

    def set_dismiss_callback(self, callback: Any) -> None:
        self._dismiss_callback = callback

    def _on_close(self, event: Any) -> None:
        self.frame.Hide()
        skip = getattr(event, "Skip", None)
        if callable(skip):
            skip()

    def _on_accept(self, _event: Any) -> None:
        if callable(self._accept_callback):
            self._accept_callback()

    def _dismiss(self) -> None:
        if callable(self._dismiss_callback):
            self._dismiss_callback()

    def _on_listbox_key(self, event: Any) -> None:
        """Keep the listbox from becoming a keyboard trap when it has focus.

        Escape cancels; Enter and Tab accept the highlighted suggestion. All
        three return focus to the editor (via the accept/dismiss callbacks),
        mirroring the editor-focused behaviour. Arrow keys fall through to the
        native listbox so the screen reader announces each selection."""
        wx = self._wx
        key_code = event.GetKeyCode()
        if key_code == wx.WXK_ESCAPE:
            self._dismiss()
            return
        if key_code in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER, wx.WXK_TAB):
            if callable(self._accept_callback):
                self._accept_callback()
            else:
                self._dismiss()
            return
        event.Skip()

    def update(self, suggestions: list[IntellisenseSuggestion], status: str) -> None:
        self.suggestions = list(suggestions)
        labels = [item.label for item in suggestions]
        self.listbox.Set(labels)
        if labels:
            self.listbox.SetSelection(0)
        self.status.SetLabel(status)

    def show(self, position: tuple[int, int]) -> None:
        self.frame.SetPosition(position)
        show_without_activating = getattr(self.frame, "ShowWithoutActivating", None)
        if callable(show_without_activating):
            show_without_activating()
        else:
            self.frame.Show(True)
        self.frame.Raise()

    def hide(self) -> None:
        self.frame.Hide()

    def is_visible(self) -> bool:
        # The popup's frame is a child of the editor's window; if that parent
        # was torn down and rebuilt (e.g. a crash-recovery restart) without this
        # popup object being recreated alongside it, self.frame is a deleted
        # C/C++ object and IsShown() raises RuntimeError (#917/#918).
        try:
            return bool(self.frame.IsShown())
        except RuntimeError:
            return False

    def selection_index(self) -> int:
        return int(self.listbox.GetSelection())

    def set_selection(self, index: int) -> None:
        if not self.suggestions:
            return
        index = max(0, min(index, len(self.suggestions) - 1))
        self.listbox.SetSelection(index)

    def selected_suggestion(self) -> IntellisenseSuggestion | None:
        index = self.listbox.GetSelection()
        if index < 0 or index >= len(self.suggestions):
            return None
        return self.suggestions[index]


class SuggestionListMixin:
    """Word Prediction's list and keys. Hooks: ``_suggest_*`` below."""

    _intellisense_popup: SuggestionPopup | None = None
    _intellisense_context: IntellisenseContext | None = None
    _intellisense_fragment_text: str = ""
    _intellisense_suggestions: list[IntellisenseSuggestion] = []  # noqa: RUF012 - replaced, never mutated
    _intellisense_guard: bool = False

    # -- opening and refreshing --------------------------------------------- #

    def _show_intellisense_popup(self, *, manual: bool) -> bool:
        popup = self._suggest_popup()
        if popup is None:
            return False
        if not manual and not self._suggest_as_you_type():
            if popup.is_visible():
                self._hide_intellisense_popup()
            return False
        text = self._suggest_text()
        cursor = self._suggest_caret()
        alias = code_language_for(self._suggest_path())
        if alias is not None:
            # A code file: its own names, with their kinds (layer 1).
            context, suggestions = build_code_suggestions(
                text, cursor, alias, limit=SUGGESTION_LIMIT
            )
        else:
            dictionary = self._suggest_dictionary() | collect_document_words(text)
            context, suggestions = build_intellisense_suggestions(
                text, cursor, dictionary, limit=SUGGESTION_LIMIT
            )
        if not suggestions:
            if popup.is_visible():
                self._hide_intellisense_popup()
            self._intellisense_context = context
            self._intellisense_fragment_text = context.fragment if context is not None else ""
            self._intellisense_suggestions = []
            return False
        if not manual and context is not None and len(context.fragment.strip()) < 2:
            if popup.is_visible():
                self._hide_intellisense_popup()
            return False
        self._intellisense_context = context
        self._intellisense_fragment_text = context.fragment if context is not None else ""
        self._intellisense_suggestions = suggestions
        status = suggestion_status(suggestions)
        was_visible = popup.is_visible()
        popup.update(suggestions, status)
        if not was_visible:
            popup.show(self._suggest_screen_position())
            self._suggest_announce(status)
        return True

    def _refresh_intellisense_popup(self) -> None:
        if self._intellisense_guard:
            return
        popup = self._suggest_popup(create=False)
        popup_visible = popup is not None and popup.is_visible()
        if not popup_visible and not self._suggest_as_you_type():
            return
        self._show_intellisense_popup(manual=popup_visible)

    def _hide_intellisense_popup(self) -> None:
        popup = self._suggest_popup(create=False)
        if popup is not None:
            popup.hide()
        self._intellisense_context = None
        self._intellisense_fragment_text = ""
        self._intellisense_suggestions = []

    def _dismiss_intellisense_popup(self) -> None:
        """Cancel the list and return focus to the editor.

        Used when the listbox itself has focus (Escape), so the user is never
        stranded in the floating window."""
        self._hide_intellisense_popup()
        self._suggest_focus_editor()
        self._suggest_say("Word prediction dismissed")

    def _apply_intellisense_selection(self) -> bool:
        popup = self._suggest_popup(create=False)
        context = self._intellisense_context
        if popup is None or context is None:
            return False
        suggestion = popup.selected_suggestion()
        if suggestion is None:
            return False
        self._intellisense_guard = True
        try:
            self._suggest_replace(
                context.replacement_start, context.replacement_end, suggestion.inserted_text
            )
            caret = context.replacement_start + suggestion.caret_offset
            caret = max(0, min(caret, len(self._suggest_text())))
            self._suggest_set_caret(caret)
        finally:
            self._intellisense_guard = False
        self._hide_intellisense_popup()
        # Return focus to the editor in case the listbox itself held focus
        # (e.g. the user Tabbed or clicked into the floating window).
        self._suggest_focus_editor()
        self._suggest_say(f'Inserted prediction "{suggestion.label}".')
        return True

    def _handle_intellisense_key_down(self, event: Any) -> bool:
        """The editor's key-down: True when the open list used the key.

        Ctrl+Space stays with the sentence commands (keymap section 4.22), so it
        is not intercepted here; the key that opens the list is a command.
        """
        wx = self._suggest_wx()
        popup = self._suggest_popup(create=False)
        if popup is None or not popup.is_visible():
            return False
        key_code = event.GetKeyCode()
        if key_code == wx.WXK_ESCAPE:
            self._hide_intellisense_popup()
            return True
        if key_code in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER, wx.WXK_TAB):
            return self._apply_intellisense_selection()
        if key_code in (wx.WXK_UP, wx.WXK_DOWN):
            step = -1 if key_code == wx.WXK_UP else 1
            popup.set_selection(popup.selection_index() + step)
            selection = popup.selected_suggestion()
            if selection is not None:
                self._suggest_announce(spoken_suggestion(selection))
            return True
        return False

    # -- hooks each editor supplies ------------------------------------------ #

    def _suggest_wx(self) -> Any:
        import wx

        return wx

    def _suggest_popup(self, *, create: bool = True) -> SuggestionPopup | None:
        """The floating list; the default builds it on first use."""
        popup = self._intellisense_popup
        if popup is None and create:
            popup = SuggestionPopup(self._suggest_wx(), self._suggest_parent())
            popup.set_accept_callback(self._apply_intellisense_selection)
            popup.set_dismiss_callback(self._dismiss_intellisense_popup)
            self._intellisense_popup = popup
        return popup

    def _suggest_parent(self) -> Any:
        raise NotImplementedError

    def _suggest_text(self) -> str:
        raise NotImplementedError

    def _suggest_caret(self) -> int:
        raise NotImplementedError

    def _suggest_replace(self, start: int, end: int, text: str) -> None:
        raise NotImplementedError

    def _suggest_set_caret(self, offset: int) -> None:
        raise NotImplementedError

    def _suggest_focus_editor(self) -> None:
        raise NotImplementedError

    def _suggest_screen_position(self) -> tuple[int, int]:
        raise NotImplementedError

    def _suggest_dictionary(self) -> set[str]:
        return set()

    def _suggest_path(self) -> Any:
        """The document's path; its extension says whether it is code."""
        return None

    def _suggest_as_you_type(self) -> bool:
        return False

    def _suggest_say(self, message: str) -> None:
        """An action's outcome: the status line, spoken."""
        raise NotImplementedError

    def _suggest_announce(self, message: str) -> None:
        """Said at once, because the list is not focused and the reader cannot."""
        raise NotImplementedError
