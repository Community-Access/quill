"""QUILL's own Find and Replace dialog (unified search F1, #1327).

The accessible replacement for the native Windows Find/Replace common dialog,
shipped behind ``settings.find_use_quill_dialog`` (default off) until the
JAWS/NVDA validation pass. What the native dialog could never give us:

- **Extended mode**: search for characters you cannot type — ``\\n``, ``\\t``,
  ``\\xNN``, ``\\N{EM DASH}`` — plus a named special-character picker, so the
  invisible characters that wreck formatting become findable, nameable things.
- **A spoken incremental count** ("17 matches") as the query is typed, polite
  and debounced, with the nearest match spoken as a sentence on demand.
- **Peek navigation**: Ctrl+Down / Ctrl+Up step through matches while focus
  STAYS in the query field — browse the matches, keep typing, press Enter.
- **A Direction radio group whose name is actually announced** — the report
  that started #1327.

The dialog is modeless (focus hops between it and the editor, F3/Shift+F3 keep
working globally) and talks to its host exclusively through small callbacks, so
every behavior is unit-testable with a stub host. All match logic lives in the
wx-free :mod:`quill.core.find_model`; this module is presentation only.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from quill.core.find_model import (
    NAMED_CHARACTERS,
    FindMatch,
    FindQuery,
    all_matches,
    compile_query,
    context_sentence,
    count_matches,
    find_next,
    translate_extended,
)
from quill.ui.dialog_contract import apply_modal_ids, set_accessible_name

_MODES = ("Normal", "Extended (special characters)")
_INCREMENTAL_DELAY_MS = 350


@dataclass
class FindHost:
    """Everything the dialog needs from its owner, as plain callables.

    Kept tiny on purpose: the dialog must be drivable by a stub in unit tests
    and must never reach into MainFrame internals.
    """

    get_text: Callable[[], str]
    get_insertion_point: Callable[[], int]
    select_range: Callable[[int, int], None]
    replace_range: Callable[[int, int, str], None]
    announce: Callable[[str], None]
    is_read_only: Callable[[], bool]
    # Optional: lets the host remember the query so global F3/Shift+F3 repeat
    # THIS search after the dialog closes. Args: literal query text,
    # case_sensitive, whole_word.
    remember_query: Callable[[str, bool, bool], None] | None = None


class QuillFindDialog:
    """The modeless unified Find/Replace dialog (document scope, F1)."""

    def __init__(
        self,
        parent: object,
        host: FindHost,
        *,
        wx: object,
        replace: bool = False,
        initial_query: str = "",
    ) -> None:
        self._wx = wx
        self._host = host
        self._replace_action = replace
        self._last_match: FindMatch | None = None
        self._peek_match: FindMatch | None = None
        self._pending_count = None  # wx.CallLater handle
        self._last_incremental: str | None = None  # dedup the spoken count

        title = "Replace" if replace else "Find"
        self.dialog = wx.Dialog(
            parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        root = wx.BoxSizer(wx.VERTICAL)

        root.Add(wx.StaticText(self.dialog, label="Search &for:"), 0, wx.LEFT | wx.TOP, 10)
        self.query = wx.TextCtrl(self.dialog, style=wx.TE_PROCESS_ENTER)
        set_accessible_name(self.query, "Search for")
        self.query.SetValue(initial_query)
        root.Add(self.query, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        self._replace_label = wx.StaticText(self.dialog, label="Replace &with:")
        root.Add(self._replace_label, 0, wx.LEFT | wx.TOP, 10)
        self.replace_with = wx.TextCtrl(self.dialog, style=wx.TE_PROCESS_ENTER)
        set_accessible_name(self.replace_with, "Replace with")
        root.Add(self.replace_with, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        options_row = wx.BoxSizer(wx.HORIZONTAL)
        options_row.Add(
            wx.StaticText(self.dialog, label="&Mode:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6
        )
        self.mode = wx.Choice(self.dialog, choices=list(_MODES))
        set_accessible_name(self.mode, "Search mode")
        self.mode.SetSelection(0)
        options_row.Add(self.mode, 0, wx.RIGHT, 10)
        self.case = wx.CheckBox(self.dialog, label="Match &case")
        options_row.Add(self.case, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        self.whole_word = wx.CheckBox(self.dialog, label="Whole wor&d")
        options_row.Add(self.whole_word, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        self.wrap = wx.CheckBox(self.dialog, label="Wra&p around")
        self.wrap.SetValue(True)
        options_row.Add(self.wrap, 0, wx.ALIGN_CENTER_VERTICAL)
        root.Add(options_row, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)

        # The group name every screen reader announces — the original report.
        # "Down" carries no mnemonic: &w collided with "Replace &with" and &n
        # with "Find &Next"; the RadioBox is arrow-navigable, so no key is lost.
        self.direction = wx.RadioBox(
            self.dialog, label="Direction", choices=["&Up", "Down"], majorDimension=2
        )
        self.direction.SetSelection(1)
        root.Add(self.direction, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)

        button_row = wx.BoxSizer(wx.HORIZONTAL)
        self.find_next_btn = wx.Button(self.dialog, label="Find &Next")
        self.find_prev_btn = wx.Button(self.dialog, label="Find Pre&vious")
        self.count_btn = wx.Button(self.dialog, label="Coun&t")
        self.special_btn = wx.Button(self.dialog, label="&Insert Special Character...")
        button_row.Add(self.find_next_btn, 0, wx.RIGHT, 6)
        button_row.Add(self.find_prev_btn, 0, wx.RIGHT, 6)
        button_row.Add(self.count_btn, 0, wx.RIGHT, 6)
        button_row.Add(self.special_btn, 0, wx.RIGHT, 6)
        root.Add(button_row, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)

        replace_row = wx.BoxSizer(wx.HORIZONTAL)
        self.replace_btn = wx.Button(self.dialog, label="&Replace")
        self.replace_all_btn = wx.Button(self.dialog, label="Replace &All")
        replace_row.Add(self.replace_btn, 0, wx.RIGHT, 6)
        replace_row.Add(self.replace_all_btn, 0, wx.RIGHT, 6)
        replace_row.AddStretchSpacer()
        close_btn = wx.Button(self.dialog, id=wx.ID_CLOSE, label="Close")
        replace_row.Add(close_btn, 0)
        self._replace_row = replace_row
        root.Add(replace_row, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizerAndFit(root)
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_CLOSE, escape_id=wx.ID_CLOSE)
        self.find_next_btn.SetDefault()
        self._apply_action_visibility()

        # Notepad semantics: Find Next follows the Direction radio; Find
        # Previous is its reverse. The radio is not decoration (#1327).
        self.find_next_btn.Bind(
            wx.EVT_BUTTON, lambda _e: self.find(backwards=self._direction_backwards())
        )
        self.find_prev_btn.Bind(
            wx.EVT_BUTTON, lambda _e: self.find(backwards=not self._direction_backwards())
        )
        self.count_btn.Bind(wx.EVT_BUTTON, lambda _e: self.announce_count())
        self.special_btn.Bind(wx.EVT_BUTTON, lambda _e: self.insert_special_character())
        self.replace_btn.Bind(wx.EVT_BUTTON, lambda _e: self.replace_current())
        self.replace_all_btn.Bind(wx.EVT_BUTTON, lambda _e: self.replace_everywhere())
        close_btn.Bind(wx.EVT_BUTTON, lambda _e: self.close())
        self.query.Bind(wx.EVT_TEXT_ENTER, self._on_query_enter)
        self.replace_with.Bind(wx.EVT_TEXT_ENTER, lambda _e: self.replace_current())
        self.query.Bind(wx.EVT_TEXT, self._on_query_changed)
        self.query.Bind(wx.EVT_KEY_DOWN, self._on_query_key)
        self.dialog.Bind(wx.EVT_CHAR_HOOK, self._on_dialog_key)
        self.dialog.Bind(wx.EVT_CLOSE, lambda _e: self.close())

    # -- state ------------------------------------------------------------------

    def _build_query(self) -> FindQuery:
        mode = "extended" if self.mode.GetSelection() == 1 else "normal"
        return FindQuery(
            text=self.query.GetValue(),
            mode=mode,
            case_sensitive=self.case.GetValue(),
            whole_word=self.whole_word.GetValue(),
            wrap=self.wrap.GetValue(),
        )

    def _apply_action_visibility(self) -> None:
        """Replace controls exist always; they hide in the plain Find action."""
        show = self._replace_action
        for ctrl in (
            self._replace_label,
            self.replace_with,
            self.replace_btn,
            self.replace_all_btn,
        ):
            ctrl.Show(show)
        self.dialog.SetTitle("Replace" if show else "Find")
        self.dialog.Layout()

    def set_action(self, *, replace: bool) -> None:
        """Ctrl+H while open switches the action in place (and vice versa)."""
        if replace != self._replace_action:
            self._replace_action = replace
            self._apply_action_visibility()
        (self.replace_with if replace else self.query).SetFocus()

    def focus_query(self) -> None:
        """Ctrl+F while open — and Ctrl+L from anywhere in the dialog."""
        self.query.SetFocus()
        self.query.SelectAll()

    # -- find -------------------------------------------------------------------

    def _translated_replacement(self) -> str | None:
        """The replace-with text, escape-translated in Extended mode.

        Returns None (after announcing) when the translation fails, so a bad
        ``\\N{...}`` name never silently replaces with the wrong text.
        """
        raw = self.replace_with.GetValue()
        if self.mode.GetSelection() != 1:
            return raw
        try:
            return translate_extended(raw)
        except Exception as error:  # noqa: BLE001 - plain-language relay
            self._host.announce(str(error))
            return None

    def _direction_backwards(self) -> bool:
        return self.direction.GetSelection() == 0

    def _remember_for_global_repeat(self, query: FindQuery) -> None:
        """Sync the host's F3/Shift+F3 state so global repeat continues THIS
        search after the dialog closes (the docstring's modeless promise)."""
        if self._host.remember_query is None:
            return
        literal = query.text
        if query.mode == "extended":
            try:
                literal = translate_extended(query.text)
            except Exception:  # noqa: BLE001 - unlikely: the query already compiled
                return
        self._host.remember_query(literal, query.case_sensitive, query.whole_word)

    def find(self, *, backwards: bool) -> None:
        query = self._build_query()
        if not query.text:
            self._host.announce("Type something to search for")
            return
        try:
            compiled = compile_query(query)
        except Exception as error:  # noqa: BLE001 - plain-language relay
            self._host.announce(str(error))
            return
        text = self._host.get_text()
        from_pos = self.query_anchor(backwards=backwards)
        match, wrapped = find_next(compiled, text, from_pos=from_pos, backwards=backwards)
        if match is None:
            self._host.announce(f'No matches for "{query.text}"')
            return
        self._last_match = match
        self._peek_match = None
        self._remember_for_global_repeat(query)
        self._host.select_range(match.start, match.end)
        prefix = (
            "Wrapped past the end. "
            if wrapped and not backwards
            else ("Wrapped past the start. " if wrapped else "")
        )
        self._host.announce(f"{prefix}{context_sentence(text, match)}")

    def query_anchor(self, *, backwards: bool = False) -> int:
        """Where the next search starts.

        Direction-aware: repeating backwards must anchor at the last match's
        START (anchoring at its end re-finds the same match forever); forwards
        anchors at its end. Falls back to the caret.
        """
        anchor_match = self._peek_match or self._last_match
        if anchor_match is not None:
            return anchor_match.start if backwards else anchor_match.end
        return self._host.get_insertion_point()

    def peek(self, *, backwards: bool) -> None:
        """Ctrl+Up/Down: step matches while focus stays in the query field."""
        query = self._build_query()
        if not query.text:
            return
        try:
            compiled = compile_query(query)
        except Exception:  # noqa: BLE001 - incremental peeks stay silent on bad input
            return
        text = self._host.get_text()
        if self._peek_match is not None:
            start = self._peek_match.start if backwards else self._peek_match.end
        else:
            start = self._host.get_insertion_point()
        match, wrapped = find_next(compiled, text, from_pos=start, backwards=backwards)
        if match is None:
            self._host.announce("No matches")
            return
        self._peek_match = match
        self._host.select_range(match.start, match.end)
        prefix = "Wrapped. " if wrapped else ""
        self._host.announce(f"{prefix}{context_sentence(text, match)}")

    def announce_count(self) -> None:
        query = self._build_query()
        if not query.text:
            self._host.announce("Type something to search for")
            return
        try:
            compiled = compile_query(query)
        except Exception as error:  # noqa: BLE001
            self._host.announce(str(error))
            return
        count, truncated = count_matches(compiled, self._host.get_text())
        suffix = " or more" if truncated else ""
        noun = "match" if count == 1 else "matches"
        self._host.announce(f"{count}{suffix} {noun}")

    # -- replace ----------------------------------------------------------------

    def replace_current(self) -> None:
        if self._host.is_read_only():
            self._host.announce("Document is read-only")
            return
        query = self._build_query()
        if not query.text:
            self._host.announce("Type something to search for")
            return
        replacement = self._translated_replacement()
        if replacement is None:
            return
        try:
            compiled = compile_query(query)
        except Exception as error:  # noqa: BLE001
            self._host.announce(str(error))
            return
        text = self._host.get_text()
        backwards = self._direction_backwards()
        anchor = self._last_match.start if self._last_match else self._host.get_insertion_point()
        match, _wrapped = find_next(compiled, text, from_pos=anchor, backwards=backwards)
        if match is None:
            self._host.announce(f'No matches for "{query.text}"')
            return
        # Range replacement (not whole-document SetValue) keeps the editor's
        # undo history and caret machinery intact.
        self._host.replace_range(match.start, match.end, replacement)
        self._host.select_range(match.start, match.start + len(replacement))
        self._last_match = None
        self._peek_match = None
        self._remember_for_global_repeat(query)
        shown = replacement if replacement else "nothing"
        self._host.announce(f"Replaced '{match.text}' with '{shown}' at line {match.line}")

    def replace_everywhere(self) -> None:
        if self._host.is_read_only():
            self._host.announce("Document is read-only")
            return
        query = self._build_query()
        if not query.text:
            self._host.announce("Type something to search for")
            return
        replacement = self._translated_replacement()
        if replacement is None:
            return
        try:
            compiled = compile_query(query)
        except Exception as error:  # noqa: BLE001
            self._host.announce(str(error))
            return
        text = self._host.get_text()
        matches, truncated = all_matches(compiled, text)
        if not matches:
            self._host.announce(f'No matches for "{query.text}"')
            return
        if len(matches) <= 100:
            # Back to front so earlier offsets stay valid, via range
            # replacement so every change stays on the editor's undo stack
            # (one undo step per occurrence).
            for match in reversed(matches):
                self._host.replace_range(match.start, match.end, replacement)
        else:
            # Thousands of individual RichEdit edits stall the UI thread and
            # bury undo in per-occurrence steps; above the threshold, rebuild
            # once and replace the whole document in a single edit (one undo
            # step), matching the native Replace All path.
            pieces: list[str] = []
            cursor = 0
            for match in matches:
                pieces.append(text[cursor : match.start])
                pieces.append(replacement)
                cursor = match.end
            pieces.append(text[cursor:])
            self._host.replace_range(0, len(text), "".join(pieces))
        self._last_match = None
        self._peek_match = None
        self._remember_for_global_repeat(query)
        count = len(matches)
        noun = "occurrence" if count == 1 else "occurrences"
        extra = (
            " Reached the result limit; run Replace All again for the rest." if truncated else ""
        )
        self._host.announce(f"Replaced {count} {noun}.{extra}")

    # -- special characters ------------------------------------------------------

    def insert_special_character(self) -> None:
        """Pick a named character; Extended mode inserts its escape, Normal the
        character itself — either way the query stays honest about its mode."""
        wx = self._wx
        names = list(NAMED_CHARACTERS)
        with wx.SingleChoiceDialog(
            self.dialog, "Character to search for:", "Insert Special Character", names
        ) as picker:
            if picker.ShowModal() != wx.ID_OK:
                return
            name = names[picker.GetSelection()]
        if self.mode.GetSelection() == 1:
            import unicodedata

            unicode_name = unicodedata.name(NAMED_CHARACTERS[name], "")
            snippet = f"\\N{{{unicode_name}}}" if unicode_name else NAMED_CHARACTERS[name]
        else:
            snippet = NAMED_CHARACTERS[name]
        self.query.WriteText(snippet)
        self._host.announce(f"{name} inserted")
        self.query.SetFocus()

    # -- incremental count -------------------------------------------------------

    def _on_query_changed(self, event: object) -> None:
        event.Skip()
        self._last_match = None
        self._peek_match = None
        wx = self._wx
        if self._pending_count is not None:
            self._pending_count.Stop()
        self._pending_count = wx.CallLater(_INCREMENTAL_DELAY_MS, self._announce_incremental)

    def _announce_incremental(self) -> None:
        self._pending_count = None
        query = self._build_query()
        if not query.text:
            # Clearing the field resets the dedup, so retyping the same query
            # speaks its count again instead of staying silent.
            self._last_incremental = None
            return
        try:
            compiled = compile_query(query)
        except Exception:  # noqa: BLE001 - half-typed escapes stay silent
            return
        count, truncated = count_matches(compiled, self._host.get_text())
        suffix = " or more" if truncated else ""
        noun = "match" if count == 1 else "matches"
        message = f"{count}{suffix} {noun}"
        # Dedup on (query, message): the same count for a DIFFERENT query is
        # new information and must be spoken.
        stamp = f"{query.text}\x00{message}"
        if stamp == self._last_incremental:
            return
        self._last_incremental = stamp
        self._host.announce(message)

    # -- keys --------------------------------------------------------------------

    def _on_query_enter(self, event: object) -> None:
        # Enter follows the Direction radio; Shift+Enter reverses it.
        shift = bool(self._wx.GetKeyState(self._wx.WXK_SHIFT))
        self.find(backwards=shift != self._direction_backwards())

    def _on_query_key(self, event: object) -> None:
        wx = self._wx
        code = event.GetKeyCode()
        if event.ControlDown() and code == wx.WXK_DOWN:
            self.peek(backwards=False)
            return
        if event.ControlDown() and code == wx.WXK_UP:
            self.peek(backwards=True)
            return
        event.Skip()

    def _on_dialog_key(self, event: object) -> None:
        # A modeless dialog is its own top-level window and never receives the
        # MainFrame's Ctrl+F/Ctrl+H accelerators, so the documented "while open"
        # chords must be handled here (Ctrl+L refocuses the query too).
        if event.ControlDown() and not event.AltDown() and not event.ShiftDown():
            code = event.GetKeyCode()
            if code in (ord("L"), ord("F")):
                self.focus_query()
                return
            if code == ord("H"):
                self.set_action(replace=True)
                return
        event.Skip()

    # -- lifecycle ---------------------------------------------------------------

    def show(self) -> None:
        self.dialog.Show(True)
        self.dialog.Raise()
        self.focus_query()

    def close(self) -> None:
        if self._pending_count is not None:
            self._pending_count.Stop()
            self._pending_count = None
        self.dialog.Hide()
        self.dialog.Destroy()


def open_for_main_frame(controller: object, *, replace: bool) -> None:
    """Open (or refocus) the singleton QuillFindDialog for a MainFrame host.

    Lives here rather than on the search mixin so the whole surface — dialog
    plus its editor wiring — stays in one module. Ctrl+F while it is open
    refocuses the query field; Ctrl+H switches the action to Replace in place;
    never a second dialog.
    """
    existing = getattr(controller, "_quill_find_dialog", None)
    if existing is not None:
        try:
            existing.set_action(replace=replace)
            existing.dialog.Raise()
            return
        except RuntimeError:  # the wx dialog was destroyed under us
            controller._quill_find_dialog = None

    editor = controller.editor

    def _select(start: int, end: int) -> None:
        editor.SetSelection(start, end)
        editor.ShowPosition(start)

    def _remember(query_text: str, case_sensitive: bool, whole_word: bool) -> None:
        # Keep the global F3/Shift+F3 repeat and search history on THIS query.
        from quill.core.search import SearchOptions

        controller._last_find_query = query_text
        controller._last_search_options = SearchOptions(
            case_sensitive=case_sensitive, whole_word=whole_word
        )

    host = FindHost(
        get_text=lambda: str(editor.GetValue()),
        get_insertion_point=lambda: int(editor.GetInsertionPoint()),
        select_range=_select,
        replace_range=lambda start, end, value: editor.Replace(start, end, value),
        announce=lambda message: controller._announce(message),
        is_read_only=lambda: bool(getattr(controller, "_document_is_read_only", lambda: False)()),
        remember_query=_remember,
    )
    seed = str(editor.GetStringSelection()) or getattr(controller, "_last_find_query", "")
    if "\n" in seed:  # a multi-line selection is context, not a query
        seed = ""
    dialog = QuillFindDialog(
        controller.frame, host, wx=controller._wx, replace=replace, initial_query=seed
    )
    controller._quill_find_dialog = dialog
    original_close = dialog.close

    def _close_and_forget() -> None:
        controller._quill_find_dialog = None
        original_close()
        editor.SetFocus()

    dialog.close = _close_and_forget  # type: ignore[method-assign]
    dialog.show()
