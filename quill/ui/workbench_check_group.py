"""A check list a screen reader reads: one real check box per choice (GitHub PRD 15.2).

``wx.CheckListBox`` is banned (A11Y-SR-1): screen readers do not say a row's
checked state as you arrow through it. A Properties sheet's labels,
assignees, reviewers and reactions are therefore a group of ordinary
``wx.CheckBox`` controls, one per choice, each read in full ("bug, checked").

Over several objects the group is three-state (section 15.2): a choice on
some but not all of them is a third-state box whose label says how many,
"bug, on 3 of 5", and is left alone unless you change it. :meth:`delta` is
what you did, as additions and removals, so nothing you did not touch is sent.
"""

from __future__ import annotations

from typing import Any

from quill.core.workbench.properties import ListDelta
from quill.ui.spoken_name import set_spoken_name

__all__ = ["CheckGroup"]


class CheckGroup:
    """One check box per choice, in a panel; *counts* and *total* make it three-state."""

    def __init__(
        self,
        parent: Any,
        name: str,
        items: list[str],
        *,
        have: tuple[str, ...] = (),
        counts: dict[str, int] | None = None,
        total: int = 1,
        help_text: str = "",
    ) -> None:
        import wx

        self._wx = wx
        self.name = name
        self.total = total
        self._counts = dict(counts or {})
        self._help = help_text
        self.panel = wx.Panel(parent)
        self.panel.SetHelpText(help_text or name)
        set_spoken_name(self.panel, name)
        self._sizer = wx.BoxSizer(wx.VERTICAL)
        self.panel.SetSizer(self._sizer)
        self.boxes: dict[str, Any] = {}
        self._start: dict[str, str] = {}
        for item in items:
            self.add(item, on=self._initially_on(item, have))
        if not items:
            empty = wx.StaticText(self.panel, label="(None to choose from yet.)")
            self._sizer.Add(empty)

    def _initially_on(self, item: str, have: tuple[str, ...]) -> bool | None:
        if self.total <= 1:
            return item in have
        count = self._counts.get(item, 0)
        if count == self.total:
            return True
        return None if count else False

    def add(self, item: str, *, on: bool | None = False) -> None:
        """Add a choice (also New Label... and the like); *on* None is the third state."""
        wx = self._wx
        if item in self.boxes:
            self.set(item, bool(on))
            return
        count = self._counts.get(item, 0)
        label = item
        if self.total > 1 and 0 < count < self.total:
            label = f"{item}, on {count} of {self.total}"
        style = wx.CHK_3STATE | wx.CHK_ALLOW_3RD_STATE_FOR_USER if self.total > 1 else 0
        box = wx.CheckBox(self.panel, label=label, style=style)
        box.SetHelpText(self._help or self.name)
        if on is None:
            box.Set3StateValue(wx.CHK_UNDETERMINED)
        else:
            box.SetValue(bool(on))
        self.boxes[item] = box
        self._start[item] = self.state(item)
        self._sizer.Add(box, 0, wx.BOTTOM, 2)
        self.panel.Layout()

    def state(self, item: str) -> str:
        """ "on", "off" or "mixed" for one choice."""
        wx = self._wx
        box = self.boxes[item]
        if box.Is3State() and box.Get3StateValue() == wx.CHK_UNDETERMINED:
            return "mixed"
        return "on" if box.GetValue() else "off"

    def set(self, item: str, on: bool) -> None:
        box = self.boxes[item]
        if box.Is3State():
            box.Set3StateValue(self._wx.CHK_CHECKED if on else self._wx.CHK_UNCHECKED)
        else:
            box.SetValue(on)

    def checked(self) -> tuple[str, ...]:
        return tuple(item for item in self.boxes if self.state(item) == "on")

    def labels(self) -> list[str]:
        return [box.GetLabel() for box in self.boxes.values()]

    def reset(self, have: tuple[str, ...]) -> None:
        """After a save or reload: the boxes show *have*, and that is the new start."""
        for item in self.boxes:
            self.set(item, item in have)
            self._start[item] = self.state(item)

    def delta(self) -> ListDelta:
        """What the person changed: choices turned on, and off, from where they started."""
        added = tuple(i for i in self.boxes if self.state(i) == "on" and self._start[i] != "on")
        removed = tuple(i for i in self.boxes if self.state(i) == "off" and self._start[i] != "off")
        return ListDelta(added, removed)

    def SetFocus(self) -> None:  # noqa: N802 - the wx name the sheet calls
        first = next(iter(self.boxes.values()), None)
        (first or self.panel).SetFocus()

    def SetHelpText(self, text: str) -> None:  # noqa: N802
        self._help = text
        self.panel.SetHelpText(text)
        for box in self.boxes.values():
            box.SetHelpText(text)
