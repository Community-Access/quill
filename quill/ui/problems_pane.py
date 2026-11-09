"""The Problems pane: a list of problems docked below the editor.

Shared by QUILL and QUILL Lite. It stays open while you work, the way the
modal Problems list cannot: you go to a problem, fix it, and the list is still
there. What it shows and says is :mod:`quill.core.problems.pane`; the checking
is :mod:`quill.core.problems`; the commands are
:class:`quill.ui.problems_commands.ProblemsCommandsMixin`. This module is only
the widgets.

The layout, top to bottom:

* the **filter row**, Show and Source, so Tab and Shift+Tab reach it from the
  list;
* the **list**, one row per problem, severity first. F6 lands here.

The keys:

* **Enter** on a row (or a double click) goes to that place in the text and
  puts focus there.
* **Escape** anywhere in the pane goes back to the editor and leaves the pane
  open.
* The **context menu** (the Applications key or Shift+F10) has Go To and Copy
  Message.

No control here has an access key. The pane sits under the window's menu bar,
which owns Alt plus most letters, so a mnemonic here would either collide with
a menu (GATE-14) or steal it; Tab and Shift+Tab reach both choosers.

Nothing is spoken when focus arrives -- the screen reader says the row
(GATE-13). The host speaks the one count sentence when the count changes.

*host* supplies four callables: ``go_to(index)`` with the problem's index in
the report, ``back_to_editor()``, ``copy_text(text)`` and ``say(sentence)``.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.problems.model import CheckReport, summarize
from quill.core.problems.pane import (
    ALL_SOURCES,
    SHOW_CHOICES,
    PaneFilter,
    count_sentence,
    filter_problems,
    pane_row,
    source_choices,
)

__all__ = ["NOT_CHECKED_ROW", "ProblemsPane"]

#: The one row an empty, never-checked pane shows, so the list is never a bare
#: "list, empty" that leaves somebody wondering whether it worked.
NOT_CHECKED_ROW = "Not checked yet. Check This File fills this list."

_PANE_HELP = (
    "The Problems pane lists every problem Check This File found, one row each, "
    "severity first. Enter goes to the problem in the text; Escape goes back to "
    "the editor and leaves the pane open. F6 moves between the editor, this pane "
    "and the status bar."
)


class ProblemsPane:
    """The panel, its filter row and its list."""

    def __init__(
        self,
        wx: Any,
        parent: Any,
        *,
        go_to: Callable[[int], None],
        back_to_editor: Callable[[], None],
        copy_text: Callable[[str], None],
        say: Callable[[str], None],
    ) -> None:
        self._wx = wx
        self._go_to = go_to
        self._back_to_editor = back_to_editor
        self._copy_text = copy_text
        self._say = say
        self._report: CheckReport | None = None
        self._filter = PaneFilter()
        #: For each list row, the problem's index in the report, or ``None``
        #: for the placeholder row.
        self._row_indices: list[int | None] = []

        self.panel = wx.Panel(parent)
        self.panel.SetName("Problems")
        self.panel.SetHelpText(_PANE_HELP)
        sizer = wx.BoxSizer(wx.VERTICAL)

        row = wx.BoxSizer(wx.HORIZONTAL)
        show_label = wx.StaticText(self.panel, label="Show:")
        self._show = wx.Choice(self.panel, choices=[label for _key, label in SHOW_CHOICES])
        self._show.SetSelection(0)
        self._show.SetHelpText(
            "Which problems the list shows: all of them, errors and warnings, or "
            "errors only. The count says how many are hidden."
        )
        source_label = wx.StaticText(self.panel, label="Source:")
        self._source = wx.Choice(self.panel, choices=[ALL_SOURCES])
        self._source.SetSelection(0)
        self._source.SetHelpText(
            "Which checker's problems the list shows: every checker, or only the "
            "one chosen, such as the built-in JSON checker or ruff."
        )
        row.Add(show_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT | wx.RIGHT, 4)
        row.Add(self._show, 0, wx.RIGHT, 8)
        row.Add(source_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
        row.Add(self._source, 0)
        sizer.Add(row, 0, wx.TOP | wx.BOTTOM, 2)

        list_label = wx.StaticText(self.panel, label="Problems")
        sizer.Add(list_label, 0, wx.LEFT, 4)
        self._list = wx.ListBox(self.panel, style=wx.LB_SINGLE | wx.LB_NEEDED_SB)
        self._list.SetHelpText(_PANE_HELP)
        sizer.Add(self._list, 1, wx.EXPAND | wx.ALL, 2)
        self.panel.SetSizer(sizer)

        self._show.Bind(wx.EVT_CHOICE, self._on_filter)
        self._source.Bind(wx.EVT_CHOICE, self._on_filter)
        self._list.Bind(wx.EVT_LISTBOX_DCLICK, lambda _event: self.go_to_selected())
        self._list.Bind(wx.EVT_CONTEXT_MENU, self._on_context_menu)
        self.panel.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)
        self._fill()

    # -- what the host calls ------------------------------------------------- #

    @property
    def report(self) -> CheckReport | None:
        return self._report

    def is_shown(self) -> bool:
        return bool(self.panel.IsShown())

    def show_report(self, report: CheckReport) -> None:
        """Fill the list from *report*, keeping the filter and the selected row."""
        self._report = report
        self._refresh_sources()
        self._fill()

    def shown_count(self) -> int:
        problems = self._report.problems if self._report is not None else ()
        return len(filter_problems(problems, self._filter))

    def count_sentence(self) -> str:
        total = len(self._report.problems) if self._report is not None else 0
        return count_sentence(total, self.shown_count())

    def focus(self) -> None:
        """Put focus on the list, on its selected row."""
        if self._list.GetCount() and self._list.GetSelection() == self._wx.NOT_FOUND:
            self._list.SetSelection(0)
        self._list.SetFocus()

    def has_focus(self) -> bool:
        try:
            win = self._wx.Window.FindFocus()
        except Exception:  # noqa: BLE001 - no focus is not a failure
            return False
        while win is not None:
            if win is self.panel:
                return True
            get_parent = getattr(win, "GetParent", None)
            win = get_parent() if callable(get_parent) else None
        return False

    def go_to_selected(self) -> None:
        index = self._selected_problem_index()
        if index is not None:
            self._go_to(index)

    # -- filling ------------------------------------------------------------- #

    def _refresh_sources(self) -> None:
        current = self._filter.source
        choices = source_choices(self._report)
        self._source.Set(list(choices))
        if current not in choices:
            current = ALL_SOURCES
            self._filter = PaneFilter(show=self._filter.show, source=current)
        self._source.SetSelection(choices.index(current))

    def _fill(self) -> None:
        previous = self._selected_problem_index()
        if self._report is None:
            self._row_indices = [None]
            self._list.Set([NOT_CHECKED_ROW])
            self._list.SetSelection(0)
            return
        shown = filter_problems(self._report.problems, self._filter)
        if not self._report.checked:
            # "No checker for Go", not "No problems": nothing looked.
            self._row_indices = [None]
            self._list.Set([summarize(self._report)])
            self._list.SetSelection(0)
            return
        if not shown:
            self._row_indices = [None]
            self._list.Set([self.count_sentence() + "."])
            self._list.SetSelection(0)
            return
        self._row_indices = [index for index, _problem in shown]
        self._list.Set([pane_row(problem) for _index, problem in shown])
        row = self._row_indices.index(previous) if previous in self._row_indices else 0
        self._list.SetSelection(row)

    def _selected_problem_index(self) -> int | None:
        row = self._list.GetSelection() if self._row_indices else -1
        if 0 <= row < len(self._row_indices):
            return self._row_indices[row]
        return None

    # -- events -------------------------------------------------------------- #

    def _on_filter(self, _event: Any) -> None:
        show_row = max(0, self._show.GetSelection())
        source_row = max(0, self._source.GetSelection())
        sources = source_choices(self._report)
        self._filter = PaneFilter(
            show=SHOW_CHOICES[min(show_row, len(SHOW_CHOICES) - 1)][0],
            source=sources[min(source_row, len(sources) - 1)],
        )
        self._fill()
        # The list changed while focus is on the chooser, which the screen
        # reader cannot know: one sentence, the new count.
        self._say(self.count_sentence())

    def _on_char_hook(self, event: Any) -> None:
        wx = self._wx
        key = event.GetKeyCode()
        if key == wx.WXK_ESCAPE:
            self._back_to_editor()
            return
        if key in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER) and self._list.HasFocus():
            self.go_to_selected()
            return
        event.Skip()

    def _on_context_menu(self, _event: Any) -> None:
        wx = self._wx
        menu = wx.Menu()
        go_id = wx.NewIdRef()
        copy_id = wx.NewIdRef()
        menu.Append(go_id, "&Go To\tEnter")
        menu.Append(copy_id, "&Copy Message")
        has_problem = self._selected_problem_index() is not None
        menu.Enable(go_id, has_problem)
        menu.Enable(copy_id, has_problem)
        menu.Bind(wx.EVT_MENU, lambda _e: self.go_to_selected(), id=go_id)
        menu.Bind(wx.EVT_MENU, lambda _e: self._copy_selected(), id=copy_id)
        self._list.PopupMenu(menu)
        menu.Destroy()

    def _copy_selected(self) -> None:
        index = self._selected_problem_index()
        if index is None or self._report is None:
            return
        problem = self._report.problems[index]
        self._copy_text(problem.message)
        self._say("Message copied")
