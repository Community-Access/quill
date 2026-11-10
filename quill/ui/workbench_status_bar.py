"""The Workbench's status bar: cells you reach with F6, arrow across and act on.

GitHub PRD section 3.2.1, built once for every Workbench provider. It follows
the contract Quill Radio's bar (:mod:`quill.ui.radio.status_bar`) proved:

- reached with F6 and only F6: the cells take no Tab stops, so Tab never
  detours through them;
- Left and Right (and Up and Down, which would otherwise walk out of the
  panel) move cell to cell, Home and End jump to the ends;
- Enter or Space does the cell's obvious thing; the context menu (the
  Applications key, Shift+F10 or a right-click) does the rest, and every menu
  ends with Copy and Help for This Cell;
- Escape hands focus back to where it was.

Two differences from Radio's, both from GATE-13: arriving on a cell says
nothing (the cell is a button whose name is "Account, jeffbishop", which the
screen reader reads on focus), and refreshing the cells is never announced.
The same facts are mirrored into a native ``wx.StatusBar``, so a screen
reader's read-status-bar key says them too. A cell with nothing to say is
left out of the row rather than shown empty, and the order never changes.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

__all__ = ["StatusCell", "WorkbenchStatusBar"]


@dataclass(frozen=True)
class StatusCell:
    """One cell: *text* gives the live value ("" leaves the cell out)."""

    key: str
    name: str
    text: Callable[[], str]
    help: str
    activate: Callable[[], None] | None = None
    menu: Callable[[], Sequence[tuple[str, Callable[[], None]]]] = field(default=lambda: ())

    def spoken(self) -> str:
        value = self.text()
        return f"{self.name}, {value}" if value else self.name


class WorkbenchStatusBar:
    """A row of cell buttons along the bottom of a Workbench frame."""

    def __init__(
        self,
        frame: Any,
        parent: Any,
        cells: Sequence[StatusCell],
        *,
        copy_text: Callable[[str], None],
        show_help: Callable[[StatusCell], None],
    ) -> None:
        import wx

        self._wx = wx
        self._frame = frame
        self._cells = tuple(cells)
        self._copy_text = copy_text
        self._show_help = show_help
        self._inside = False
        self._return_focus: Any = None
        bar = self

        class _Panel(wx.Panel):
            def AcceptsFocusFromKeyboard(self) -> bool:  # noqa: N802 - wx override
                return bar._inside

        class _Cell(wx.Button):
            def AcceptsFocusFromKeyboard(self) -> bool:  # noqa: N802 - wx override
                return bar._inside

        self.panel = _Panel(parent, style=wx.TAB_TRAVERSAL)
        self.panel.SetName("Status bar")
        self.panel.SetHelpText("F6 reaches the status bar; arrows move across its cells.")
        self._sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._buttons: dict[str, Any] = {}
        for cell in self._cells:
            button = _Cell(self.panel, label=cell.name, style=wx.BU_EXACTFIT)
            button.SetHelpText(cell.help)
            button.Bind(wx.EVT_BUTTON, lambda _e, c=cell: self._activate(c))
            button.Bind(wx.EVT_KEY_DOWN, lambda e, c=cell: self._on_key(e, c))
            button.Bind(wx.EVT_CONTEXT_MENU, lambda _e, c=cell: self.show_menu(c))
            button.Bind(wx.EVT_KILL_FOCUS, self._on_blur)
            self._sizer.Add(button, 0, wx.ALL, 2)
            self._buttons[cell.key] = button
        self.panel.SetSizer(self._sizer)
        self._native = frame.CreateStatusBar(1)
        self.refresh()

    # -- state ------------------------------------------------------------------

    def visible_cells(self) -> list[StatusCell]:
        return [cell for cell in self._cells if self._buttons[cell.key].IsShown()]

    def refresh(self) -> None:
        """Repaint every cell from live state. Never announced (GATE-13)."""
        spoken: list[str] = []
        for cell in self._cells:
            button = self._buttons[cell.key]
            try:
                value = cell.text()
            except Exception:  # noqa: BLE001 - a status cell must never raise
                value = ""
            show = bool(value)
            button.Show(show)
            if show:
                words = f"{cell.name}, {value}"
                button.SetLabel(f"{cell.name}: {value}")
                button.SetName(words)
                spoken.append(words)
        self._native.SetStatusText(". ".join(spoken))
        self.panel.Layout()

    def has_focus(self) -> bool:
        focused = self._wx.Window.FindFocus()
        return any(button is focused for button in self._buttons.values())

    # -- moving -----------------------------------------------------------------

    def enter(self, return_focus: Any) -> bool:
        """F6 into the bar; False when no cell has anything to say."""
        cells = self.visible_cells()
        if not cells:
            return False
        self._return_focus = return_focus
        self._inside = True
        self._buttons[cells[0].key].SetFocus()
        return True

    def leave(self) -> None:
        self._inside = False
        target = self._return_focus
        if target is not None:
            try:
                target.SetFocus()
            except RuntimeError:
                pass

    def _on_blur(self, event: Any) -> None:
        gaining = event.GetWindow()
        if gaining is None or all(gaining is not b for b in self._buttons.values()):
            self._inside = False
        event.Skip()

    def _move(self, cell: StatusCell, step: int | None, *, end: bool = False) -> None:
        cells = self.visible_cells()
        if not cells:
            return
        if step is None:
            target = cells[-1] if end else cells[0]
        else:
            index = next(i for i, c in enumerate(cells) if c.key == cell.key)
            target = cells[max(0, min(len(cells) - 1, index + step))]
        self._buttons[target.key].SetFocus()

    def _on_key(self, event: Any, cell: StatusCell) -> None:
        wx = self._wx
        code = event.GetKeyCode()
        if code in (wx.WXK_LEFT, wx.WXK_UP):
            self._move(cell, -1)
        elif code in (wx.WXK_RIGHT, wx.WXK_DOWN):
            self._move(cell, 1)
        elif code == wx.WXK_HOME:
            self._move(cell, None)
        elif code == wx.WXK_END:
            self._move(cell, None, end=True)
        elif code == wx.WXK_ESCAPE:
            self.leave()
        elif code in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER, wx.WXK_SPACE):
            self._activate(cell)
        elif code == wx.WXK_TAB:
            self._inside = False
            event.Skip()
        else:
            event.Skip()

    # -- acting -----------------------------------------------------------------

    def _activate(self, cell: StatusCell) -> None:
        if cell.activate is not None:
            cell.activate()
        else:
            self.show_menu(cell)

    def menu_rows(self, cell: StatusCell) -> list[tuple[str, Callable[[], None]]]:
        """The cell's context menu: its own rows, then Copy and Help for This Cell."""
        rows = list(cell.menu())
        rows.append(("Copy", lambda: self._copy_text(cell.spoken())))
        rows.append(("Help for This Cell", lambda: self._show_help(cell)))
        return rows

    def show_menu(self, cell: StatusCell) -> None:
        wx = self._wx
        menu = wx.Menu()
        for label, action in self.menu_rows(cell):
            item_id = wx.NewIdRef()
            menu.Append(item_id, label)
            menu.Bind(wx.EVT_MENU, lambda _e, run=action: run(), id=item_id)
        try:
            self._buttons[cell.key].PopupMenu(menu)
        finally:
            menu.Destroy()
