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
* Moving the caret any other way (Left, Right, Home, End, Page Up, Page Down,
  a click), switching to another window or moving focus out of the text
  closes it, and Enter always inserts for the word at the caret *now*, never
  for the one the list was last refreshed for.

If focus ever lands in the floating window (Tab, the mouse, a screen reader's
own navigation), Escape, Enter and Tab still work there, so it is never a trap.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core.code_names import code_language_for
from quill.core.intellisense import (
    IntellisenseContext,
    IntellisenseSuggestion,
    build_code_suggestions,
    build_intellisense_suggestions,
    collect_document_words,
    extract_code_context,
    extract_intellisense_context,
    spoken_suggestion,
    suggestions_status,
)
from quill.core.project_names import (
    ProjectNameIndex,
    build_project_index,
    imported_modules,
    marked_project_root,
)
from quill.core.text_units import native_length, native_offset, text_index
from quill.ui.dpi import dip_size
from quill.ui.suggestion_watch import SuggestionWatchMixin

__all__ = ["SuggestionListMixin", "SuggestionPopup", "suggestion_status"]

#: How many suggestions the list holds.
SUGGESTION_LIMIT = 8

#: Keys that move the caret without typing: with the list open they close it
#: and then move the caret as usual (review 2026-11-09, QUILL 7).
_CARET_KEYS = ("WXK_LEFT", "WXK_RIGHT", "WXK_HOME", "WXK_END", "WXK_PAGEUP", "WXK_PAGEDOWN")

#: How old a project index may be before the next Ctrl+. rebuilds it in the
#: background (the old one answers meanwhile).
PROJECT_INDEX_MAX_AGE = 300.0

#: One index per project folder, shared by every window in the process, with
#: the time it was built. Read and written on the UI thread only: the walk
#: runs in the background and hands its result back through the task manager.
_PROJECT_INDEXES: dict[Path, tuple[ProjectNameIndex, float]] = {}
_PROJECT_BUILDS: set[Path] = set()


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

    def contains(self, window: Any) -> bool:
        """True when *window* is this floating window or inside it."""
        while window is not None:
            if window is self.frame:
                return True
            get_parent = getattr(window, "GetParent", None)
            window = get_parent() if callable(get_parent) else None
        return False

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


class SuggestionListMixin(SuggestionWatchMixin):
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
        # Code points from here on; the control counts UTF-16 units (QUILL 5).
        cursor = text_index(text, self._suggest_caret())
        alias = code_language_for(self._suggest_path())
        if alias is not None:
            # A code file: its own names, with their kinds (layer 1), then
            # the rest of the project's (layer 2) while there is room.
            context, suggestions = build_code_suggestions(
                text, cursor, alias, limit=SUGGESTION_LIMIT
            )
            if context is not None and len(suggestions) < SUGGESTION_LIMIT:
                suggestions = suggestions + self._project_suggestions(
                    text, context.fragment, {item.label for item in suggestions}
                )
        else:
            dictionary = self._suggest_dictionary() | collect_document_words(text)
            context, suggestions = build_intellisense_suggestions(
                text, cursor, dictionary, limit=SUGGESTION_LIMIT
            )
        if manual and alias is not None and context is not None:
            if self._ask_language_server(text, cursor, context, suggestions):
                return True
        return self._present_suggestions(context, suggestions, manual=manual)

    def _ask_language_server(
        self,
        text: str,
        cursor: int,
        context: IntellisenseContext,
        local: list[IntellisenseSuggestion],
    ) -> bool:
        """Layer 4: when a server is running for this file, its list comes first.

        True when the request went out; the list appears when it answers (or
        with layers 1 and 2 alone if it has nothing). The text and caret must
        still be where they were, or the answer is dropped: a list for a word
        you have since changed would insert the wrong thing.
        """
        path = self._suggest_path()
        ready = getattr(self, "_ls_completions_ready", None)
        if not callable(ready) or not ready(path):
            return False

        def done(items: list[Any] | None) -> None:
            if not self._suggest_window_alive():
                # The window closed while the server answered (QUILL Lite 3).
                return
            now = self._suggest_text()
            if now != text or text_index(now, self._suggest_caret()) != cursor:
                return
            rows = [
                IntellisenseSuggestion(
                    label=item.label,
                    inserted_text=item.insert,
                    caret_offset=len(item.insert),
                    kind=item.kind,
                )
                for item in items or []
            ]
            labels = {row.label for row in rows}
            merged = rows + [row for row in local if row.label not in labels]
            if not self._present_suggestions(context, merged[:SUGGESTION_LIMIT], manual=True):
                self._suggest_say("No predictions available")

        request = getattr(self, "_ls_request_completions", None)
        return callable(request) and bool(request(path, text, cursor, context.fragment, done))

    def _present_suggestions(
        self,
        context: IntellisenseContext | None,
        suggestions: list[IntellisenseSuggestion],
        *,
        manual: bool,
    ) -> bool:
        popup = self._suggest_popup()
        if popup is None:
            return False
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
            self._watch_for_caret_and_focus(popup)
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
        refreshed = self._intellisense_context
        if popup is None or refreshed is None:
            return False
        suggestion = popup.selected_suggestion()
        if suggestion is None:
            return False
        # The word at the caret now, not at the last refresh: a letter typed
        # and Enter pressed before the list caught up gave "countern", and a
        # caret moved by a menu key put the word somewhere else entirely
        # (review 2026-11-09, QUILL 7 and QUILL Lite 8).
        text = self._suggest_text()
        cursor = text_index(text, self._suggest_caret())
        if refreshed.mode == "code":
            context = extract_code_context(text, cursor)
        else:
            context = extract_intellisense_context(text, cursor)
        if context is None:
            context = IntellisenseContext(
                replacement_start=cursor, replacement_end=cursor, fragment="", mode=refreshed.mode
            )
        start = native_offset(text, context.replacement_start)
        self._intellisense_guard = True
        try:
            self._suggest_replace(
                start, native_offset(text, context.replacement_end), suggestion.inserted_text
            )
            offset = max(0, min(suggestion.caret_offset, len(suggestion.inserted_text)))
            self._suggest_set_caret(start + native_length(suggestion.inserted_text[:offset]))
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
        if key_code in {getattr(wx, name, None) for name in _CARET_KEYS} - {None}:
            # The caret is about to move without typing: the list is for a word
            # it is leaving. Close it and let the key do what it does.
            self._hide_intellisense_popup()
            return False
        if key_code in (wx.WXK_UP, wx.WXK_DOWN):
            step = -1 if key_code == wx.WXK_UP else 1
            popup.set_selection(popup.selection_index() + step)
            selection = popup.selected_suggestion()
            if selection is not None:
                self._suggest_announce(spoken_suggestion(selection))
            return True
        return False

    # -- layer 2: the rest of the project ------------------------------------ #

    def _project_suggestions(
        self, text: str, fragment: str, already: set[str]
    ) -> list[IntellisenseSuggestion]:
        path = self._suggest_path()
        # Only a marked project: a loose file on the Desktop would otherwise
        # index the whole Desktop, or the home folder (review QUILL Lite 12).
        root = marked_project_root(path)
        if root is None:
            return []
        entry = _PROJECT_INDEXES.get(root)
        if entry is None or time.monotonic() - entry[1] > PROJECT_INDEX_MAX_AGE:
            self._start_project_index(root)
        if entry is None:
            # The first press in a project starts the walk; the next has it.
            return []
        names = entry[0].complete(
            fragment,
            exclude=already,
            imports=imported_modules(text),
            own_stem=Path(path).stem if path else "",
            limit=SUGGESTION_LIMIT - len(already),
        )
        return [
            IntellisenseSuggestion(
                label=item.name,
                inserted_text=item.name,
                caret_offset=len(item.name),
                kind=item.kind,
            )
            for item in names
        ]

    def _start_project_index(self, root: Path) -> None:
        if root in _PROJECT_BUILDS:
            return
        _PROJECT_BUILDS.add(root)

        def done(index: ProjectNameIndex | None) -> None:
            _PROJECT_BUILDS.discard(root)
            if index is not None:
                _PROJECT_INDEXES[root] = (index, time.monotonic())

        if not self._suggest_in_background(lambda: build_project_index(root), done):
            _PROJECT_BUILDS.discard(root)

    # -- hooks each editor supplies ------------------------------------------ #

    def _suggest_in_background(self, work: Callable[[], Any], done: Callable[[Any], None]) -> bool:
        """Run *work* off the UI thread and hand its result to *done* on it.

        False when this editor has no background runner, and then the project
        layer is simply absent: it never walks a disk on the UI thread.
        """
        return False

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

    def _suggest_control(self) -> Any:
        """The text control the list serves; ``None`` leaves clicks unwatched."""
        return None

    def _suggest_window_alive(self) -> bool:
        """False once this window has closed: a late answer is dropped."""
        return True

    def _suggest_char_before_caret(self) -> str:
        """The one character before the caret ("" at the start).

        The default reads the whole text; each editor reads just that
        character from its control.
        """
        text = self._suggest_text()
        caret = text_index(text, self._suggest_caret())
        return text[caret - 1] if 0 < caret <= len(text) else ""

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
