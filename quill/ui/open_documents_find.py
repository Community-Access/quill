"""Find in Open Documents: the window, and F3 carrying on across documents.

One window for QUILL and QUILL Lite, over the shared model in
:mod:`quill.core.open_documents_search`. Each editor hands it an adapter --
:class:`OpenDocumentsHost` -- that knows what its open documents are, how to
bring one to the front and select a range, and how to write a document's new
text back. Everything else (what a query matches, which document comes next,
what Replace All will change, and what is said about it) is decided here once,
so the two editors cannot drift apart.

After the window closes, F3 and Shift+F3 keep searching across documents (see
:func:`find_again`) until the listener starts an ordinary Find, which is what
somebody who has just worked through forty files with Find Next expects the
next F3 to do.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from quill.core.find_model import FindPatternError, FindQuery
from quill.core.open_documents_search import (
    OpenDoc,
    find_across,
    find_all_across,
    line_text,
    plan_replace,
)

__all__ = [
    "MODES",
    "OpenDocumentsHost",
    "OpenDocumentsState",
    "find_again",
    "open_find_in_open_documents",
    "replace_text_in",
]

#: (value, label) for the Search mode choice: the same three modes as Find.
MODES: tuple[tuple[str, str], ...] = (
    ("normal", "Normal"),
    ("extended", "Extended (\\n, \\t, \\x41 ...)"),
    ("regex", "Regular expression"),
)


class OpenDocumentsHost(Protocol):  # pragma: no cover - a shape, not behaviour
    """What an editor tells the window about its open documents."""

    def documents(self) -> list[OpenDoc]:
        """Every open document, in tab or window order, with its live text."""

    def current(self) -> int:
        """Which of them is in front."""

    def selection(self) -> tuple[int, int]:
        """The selection in the document in front, ``(start, end)``."""

    def go_to(self, index: int, start: int, end: int) -> None:
        """Bring document *index* to the front and select ``[start, end)``."""

    def write(self, index: int, new_text: str, spans: list[tuple[int, int, str]]) -> None:
        """Give document *index* its replacements, and mark it changed.

        *spans* are ``(start, end, replacement)`` in the old text, last first;
        *new_text* is the whole result, for an editor that writes it at once.
        """

    def announce(self, text: str) -> None: ...

    def show_modal(self, dialog: Any, label: str) -> int: ...

    @property
    def parent(self) -> Any: ...

    @property
    def state(self) -> OpenDocumentsState: ...


class OpenDocumentsState:
    """What the window remembers between visits, and whether F3 is in it.

    One per editor app (QUILL's frame, QUILL Lite's app), not per window, so
    every Lite window's F3 carries on the same search.
    """

    def __init__(self) -> None:
        self.query = FindQuery("")
        self.replacement = ""
        #: True from the moment a search runs here until an ordinary Find.
        self.active = False

    def end(self) -> None:
        """An ordinary Find has started: F3 is that Find's again."""
        self.active = False


def replace_text_in(
    control: Any, new_text: str, spans: list[tuple[int, int, str]], *, rich: bool
) -> None:
    """Write one document's replacements into its text control.

    Plain text: the changed part as one undo step, so one Ctrl+Z undoes the
    whole document. Formatted text: one match at a time, last first, so the
    formatting between matches is never rewritten -- writing over a span makes
    it take the format at its start, which would flatten a heading into body
    text (main_frame._replace_document_text has the story).
    """
    from quill.core.selection import changed_span
    from quill.ui.atomic_edit import replace_as_one_undo

    if rich:
        for start, end, replacement in spans:
            replace_as_one_undo(control, start, end, replacement)
        return
    start, end, replacement = changed_span(control.GetValue(), new_text)
    if (start, end, replacement) != (0, 0, ""):
        replace_as_one_undo(control, start, end, replacement)


def _where(docs: list[OpenDoc], index: int, text: str, match: Any) -> str:
    return f"{docs[index].name}, line {match.line}: {line_text(text, match)}"


def find_again(host: OpenDocumentsHost, *, backwards: bool = False) -> bool:
    """F3 or Shift+F3 while a Find in Open Documents search is active.

    Returns False when it is not active, so the editor's ordinary F3 runs.
    """
    state = host.state
    if not state.active or not state.query.text:
        return False
    _step(host, state.query, backwards=backwards)
    return True


def _step(host: OpenDocumentsHost, query: FindQuery, *, backwards: bool) -> bool:
    docs = host.documents()
    start, end = host.selection()
    try:
        hit = find_across(
            docs,
            query,
            current=host.current(),
            position=start if backwards else end,
            backwards=backwards,
        )
    except FindPatternError as error:
        host.announce(str(error))
        return False
    if hit is None:
        host.announce(f'No matches for "{query.text}" in {len(docs)} open documents.')
        return False
    host.go_to(hit.doc, hit.match.start, hit.match.end)
    text = docs[hit.doc].text
    if hit.moved or hit.wrapped:
        prefix = "Back to the start. " if hit.wrapped and not backwards else ""
        prefix = "Back to the end. " if hit.wrapped and backwards else prefix
        host.announce(prefix + _where(docs, hit.doc, text, hit.match))
    else:
        host.announce(f"Line {hit.match.line}: {line_text(text, hit.match)}")
    return True


def _find_all(host: OpenDocumentsHost, query: FindQuery) -> bool:
    """Every match in a list; Enter goes there. True when the listener went."""
    docs = host.documents()
    try:
        hits, truncated = find_all_across(docs, query)
    except FindPatternError as error:
        host.announce(str(error))
        return False
    if not hits:
        host.announce(f'No matches for "{query.text}" in {len(docs)} open documents.')
        return False
    in_docs = len({index for index, _match in hits})
    rows = [
        (i, _where(docs, index, docs[index].text, match)) for i, (index, match) in enumerate(hits)
    ]
    title = f"{len(hits)} matches in {in_docs} of {len(docs)} open documents"
    if truncated:
        title += " (the first 5000)"
    chosen = _choose_match(host, title, rows)
    if chosen is None:
        return False
    index, match = hits[chosen]
    host.go_to(index, match.start, match.end)
    return True


def _choose_match(host: OpenDocumentsHost, title: str, rows: list[tuple[int, str]]) -> int | None:
    import wx

    dialog = wx.Dialog(host.parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
    root = wx.BoxSizer(wx.VERTICAL)
    label = wx.StaticText(dialog, label="&Matches:")
    listbox = wx.ListBox(dialog, choices=[text for _key, text in rows])
    listbox.SetHelpText(
        "Every match in every open document: the document, the line number and "
        "the line. Press Enter to go to the one you are on."
    )
    listbox.SetSelection(0)
    root.Add(label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
    root.Add(listbox, 1, wx.EXPAND | wx.ALL, 8)
    buttons = dialog.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
    root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
    dialog.SetSizer(root)
    dialog.SetSize((640, 420))
    from quill.ui.dialog_contract import apply_listbox_activation, apply_modal_ids

    apply_modal_ids(
        dialog, affirmative_id=wx.ID_OK, affirmative_label="&Go To", cancel_id=wx.ID_CANCEL
    )

    # Enter, Space or a double-click go there (GATE-13).
    apply_listbox_activation(listbox, lambda _e: dialog.EndModal(wx.ID_OK))
    listbox.SetFocus()
    try:
        if host.show_modal(dialog, title) != wx.ID_OK:
            return None
        picked = listbox.GetSelection()
        return rows[picked][0] if picked != wx.NOT_FOUND else None
    finally:
        dialog.Destroy()


def _replace_all(
    host: OpenDocumentsHost, query: FindQuery, replacement: str, confirm: Callable[[str], bool]
) -> bool:
    """Count first, ask, then write every editable document. Saves nothing."""
    docs = host.documents()
    try:
        plan = plan_replace(docs, query, replacement)
    except FindPatternError as error:
        host.announce(str(error))
        return False
    if not plan.changes:
        if plan.skipped:
            host.announce(
                f"{plan.skipped_matches} matches, all in documents that cannot be changed. "
                "Nothing was replaced."
            )
        else:
            host.announce(f'No matches for "{query.text}" in {len(docs)} open documents.')
        return False
    question = (
        f"{plan.total} matches in {plan.documents} of {len(docs)} open documents. "
        "Replace them all? Each document can be undone on its own, and nothing is saved."
    )
    if plan.skipped:
        question += f" {plan.skipped} read-only documents with matches will be left alone."
    if not confirm(question):
        return False
    from quill.core.find_model import all_matches, compile_query

    compiled = compile_query(query)
    for index, new_text, _count in plan.changes:
        matches, _ = all_matches(compiled, docs[index].text, max_matches=10**9)
        spans = [(m.start, m.end, replacement) for m in reversed(matches)]
        host.write(index, new_text, spans)
    said = f"Replaced {plan.total} in {plan.documents} documents. Nothing has been saved."
    if plan.skipped:
        said += f" Left {plan.skipped} read-only documents alone."
    host.announce(said)
    return True


def _stay(_result: bool) -> bool:
    """Find Next and Find Previous keep the window open, found or not."""
    return False


def open_find_in_open_documents(host: OpenDocumentsHost) -> None:
    """Edit > Find in Open Documents...: the window."""
    import wx

    state = host.state
    parent = host.parent
    dialog = wx.Dialog(parent, title="Find in Open Documents", style=wx.DEFAULT_DIALOG_STYLE)
    root = wx.BoxSizer(wx.VERTICAL)
    grid = wx.FlexGridSizer(cols=2, vgap=6, hgap=8)
    grid.AddGrowableCol(1)

    find_label = wx.StaticText(dialog, label="&Find what:")
    find_box = wx.TextCtrl(dialog, value=state.query.text, size=(320, -1))
    find_box.SetHelpText("The text to look for in every open document, saved or not.")
    replace_label = wx.StaticText(dialog, label="Replace w&ith:")
    replace_box = wx.TextCtrl(dialog, value=state.replacement)
    replace_box.SetHelpText(
        "What Replace All puts in place of every match. Leave it empty to delete the matches."
    )
    mode_label = wx.StaticText(dialog, label="Search &mode:")
    mode_choice = wx.Choice(dialog, choices=[label for _value, label in MODES])
    values = [value for value, _label in MODES]
    mode_choice.SetSelection(values.index(state.query.mode) if state.query.mode in values else 0)
    mode_choice.SetHelpText(
        "Normal finds the text as typed. Extended understands \\n for a new line, \\t "
        "for a tab and \\x41 for a character code. Regular expression is a pattern."
    )
    for widget in (find_label, find_box, replace_label, replace_box, mode_label, mode_choice):
        grid.Add(
            widget,
            0 if isinstance(widget, wx.StaticText) else 1,
            wx.ALIGN_CENTER_VERTICAL | (0 if isinstance(widget, wx.StaticText) else wx.EXPAND),
        )
    root.Add(grid, 0, wx.EXPAND | wx.ALL, 10)

    case_box = wx.CheckBox(dialog, label="Match &case")
    case_box.SetValue(state.query.case_sensitive)
    case_box.SetHelpText("Only find text with the same capital and small letters.")
    word_box = wx.CheckBox(dialog, label="&Whole word only")
    word_box.SetValue(state.query.whole_word)
    word_box.SetHelpText("Only find the text as a whole word, not inside a longer one.")
    wrap_box = wx.CheckBox(dialog, label="Wrap a&round")
    wrap_box.SetValue(state.query.wrap)
    wrap_box.SetHelpText(
        "After the last open document, carry on from the first, back to where you started."
    )
    for box in (case_box, word_box, wrap_box):
        root.Add(box, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

    row = wx.BoxSizer(wx.HORIZONTAL)
    next_button = wx.Button(dialog, label="Find &Next")
    next_button.SetHelpText(
        "Go to the next match, moving on to the next open document when this one has none."
    )
    previous_button = wx.Button(dialog, label="Find &Previous")
    previous_button.SetHelpText("Go to the previous match, moving back through the open documents.")
    all_button = wx.Button(dialog, label="Find A&ll")
    all_button.SetHelpText("List every match in every open document. Enter on one goes there.")
    replace_button = wx.Button(dialog, label="Replace &All")
    replace_button.SetHelpText(
        "Replace every match in every open document you can change. It tells you how many "
        "first and asks. Each document can be undone on its own; nothing is saved."
    )
    close_button = wx.Button(dialog, wx.ID_CANCEL, label="Close")
    close_button.SetHelpText("Close this window. F3 and Shift+F3 keep searching across documents.")
    for button in (next_button, previous_button, all_button, replace_button, close_button):
        row.Add(button, 0, wx.RIGHT, 6)
    root.Add(row, 0, wx.ALL, 10)
    dialog.SetSizerAndFit(root)
    next_button.SetDefault()

    def query() -> FindQuery:
        state.query = FindQuery(
            find_box.GetValue(),
            mode=values[max(0, mode_choice.GetSelection())],  # type: ignore[arg-type]
            case_sensitive=case_box.GetValue(),
            whole_word=word_box.GetValue(),
            wrap=wrap_box.GetValue(),
        )
        state.replacement = replace_box.GetValue()
        if state.query.text:
            state.active = True
        return state.query

    def run(action: Callable[[FindQuery], bool]) -> None:
        current = query()
        if not current.text:
            host.announce("Type something to find first.")
            find_box.SetFocus()
            return
        if action(current):
            dialog.EndModal(wx.ID_OK)

    def confirm(question: str) -> bool:
        from quill.ui.dialog_contract import show_message_box

        return (
            show_message_box(
                question, "Replace All in Open Documents", wx.YES_NO | wx.ICON_QUESTION, dialog
            )
            == wx.YES
        )

    next_button.Bind(
        wx.EVT_BUTTON, lambda _e: run(lambda q: _stay(_step(host, q, backwards=False)))
    )
    previous_button.Bind(
        wx.EVT_BUTTON, lambda _e: run(lambda q: _stay(_step(host, q, backwards=True)))
    )
    all_button.Bind(wx.EVT_BUTTON, lambda _e: run(lambda q: _find_all(host, q)))
    replace_button.Bind(
        wx.EVT_BUTTON,
        lambda _e: run(lambda q: _replace_all(host, q, replace_box.GetValue(), confirm)),
    )
    from quill.ui.dialog_contract import apply_modal_ids, bind_close_button

    # Escape is Close; Enter is Find Next, the default button.
    apply_modal_ids(dialog, cancel_id=wx.ID_CANCEL)
    bind_close_button(dialog, close_button, modeless=False)
    find_box.SetFocus()
    find_box.SelectAll()
    try:
        host.show_modal(dialog, "Find in Open Documents")
        query()
    finally:
        dialog.Destroy()
