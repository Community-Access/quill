"""Choose Repositories as a real checklist (PRD 22.11, GX16; GH-E).

One check box per repository, named ``owner/name`` -- a real ``wx.CheckBox``
in a scrolled panel, not a ``wx.CheckListBox`` (A11Y-SR-1), so a screen reader
reads its checked state with the name. Space checks or unchecks the box in
place and Enter saves. The candidates are the Repository Set's own
repositories first, then those the account can reach (read before the
dialog opens). Add takes ``owner/name`` or a link: a repository already in
the list is checked once and scrolled into view, never listed twice.

The dialog goes through the caller's ``show_modal`` (the dialog contract),
carries its help inline, and leaves OK and Cancel without access keys
(GATE-14).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

import wx

from quill.core.github.repository_sets import normalize_repository
from quill.ui.dialog_contract import apply_modal_ids
from quill.ui.dpi import dip_size
from quill.ui.spoken_name import set_spoken_name
from quill.ui.workbench_check_group import CheckGroup

__all__ = ["RepositoryChecklistDialog", "choose_repositories"]

ShowModal = Callable[[Any, str], int]


class RepositoryChecklistDialog(wx.Dialog):
    def __init__(
        self,
        parent: wx.Window,
        *,
        title: str,
        repositories: Sequence[str],
        checked: Sequence[str],
        note: str = "",
    ) -> None:
        super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.SetHelpText(
            "Choose the repositories in this Repository Set. Space checks or unchecks the "
            "repository you are on; Enter saves; Escape keeps the set as it was."
        )
        sizer = wx.BoxSizer(wx.VERTICAL)
        if note:
            said = wx.StaticText(self, label=note)
            said.SetHelpText("Why the list may not hold every repository you can reach.")
            sizer.Add(said, 0, wx.ALL, 8)
        label = wx.StaticText(self, label="&Repositories:")
        #: One real check box per repository (A11Y-SR-1: a CheckListBox row's
        #: checked state is not read), scrolled when the list is long.
        self.scroller = wx.ScrolledWindow(self, style=wx.VSCROLL | wx.TAB_TRAVERSAL)
        self.scroller.SetHelpText(
            "Each repository by owner and name, checked when it is in the set. Space "
            "checks or unchecks it; Enter saves."
        )
        self.scroller.SetScrollRate(0, 20)
        self.scroller.SetMinSize(dip_size(self, 460, 260))
        set_spoken_name(self.scroller, "Repositories")
        self.group = CheckGroup(
            self.scroller,
            "Repositories",
            [],
            help_text=(
                "Each repository by owner and name, checked when it is in the set. Space "
                "checks or unchecks it; Enter saves."
            ),
        )
        wanted = {r.lower() for r in checked}
        for repo in repositories:
            if self._find(repo) is None:
                self.group.add(repo, on=repo.lower() in wanted)
        inner = wx.BoxSizer(wx.VERTICAL)
        inner.Add(self.group.panel, 1, wx.EXPAND | wx.ALL, 4)
        self.scroller.SetSizer(inner)
        self.scroller.FitInside()
        sizer.Add(label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        sizer.Add(self.scroller, 1, wx.EXPAND | wx.ALL, 8)
        row = wx.BoxSizer(wx.HORIZONTAL)
        add_label = wx.StaticText(self, label="A&dd owner/name:")
        self.add_box = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
        self.add_box.SetHelpText(
            "Type owner/name or a GitHub link and press Enter or Add: it joins the list "
            "checked. One already listed is checked, not added twice."
        )
        set_spoken_name(self.add_box, "Add owner/name")
        self.add_button = wx.Button(self, label="&Add")
        self.add_button.SetHelpText("Add the repository typed in the box, checked.")
        row.Add(add_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        row.Add(self.add_box, 1, wx.EXPAND | wx.RIGHT, 6)
        row.Add(self.add_button, 0)
        sizer.Add(row, 0, wx.EXPAND | wx.ALL, 8)
        buttons = wx.StdDialogButtonSizer()
        ok = wx.Button(self, wx.ID_OK, "OK")
        ok.SetHelpText("Save the checked repositories as the set. Enter does the same.")
        ok.SetDefault()
        cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")
        cancel.SetHelpText("Close without changing the set. Escape does the same.")
        buttons.AddButton(ok)
        buttons.AddButton(cancel)
        buttons.Realize()
        sizer.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(sizer)
        apply_modal_ids(self)
        self.add_box.Bind(wx.EVT_TEXT_ENTER, lambda _e: self.add())
        self.add_button.Bind(wx.EVT_BUTTON, lambda _e: self.add())

    def _find(self, repo: str) -> str | None:
        """The listed row for *repo*, matched without regard to case."""
        wanted = repo.lower()
        return next((item for item in self.group.boxes if item.lower() == wanted), None)

    def add(self) -> str:
        """Add the typed repository (or check the listed one); "" when it is not one."""
        repo = normalize_repository(self.add_box.GetValue())
        if not repo:
            self.add_box.SelectAll()
            return ""
        listed = self._find(repo)
        if listed is None:
            self.group.add(repo, on=True)
            listed = repo
        else:
            self.group.set(listed, True)
        self.scroller.FitInside()
        self.scroller.Layout()
        self._scroll_to(listed)
        self.add_box.ChangeValue("")
        return repo

    def _scroll_to(self, item: str) -> None:
        """Bring *item*'s box into view (wx.ScrolledWindow has no ScrollChildIntoView)."""
        box = self.group.boxes[item]
        top = self.scroller.CalcUnscrolledPosition(self.group.panel.GetPosition()).y
        _rate_x, rate_y = self.scroller.GetScrollPixelsPerUnit()
        if rate_y > 0:
            self.scroller.Scroll(-1, (top + box.GetPosition().y) // rate_y)

    def rows(self) -> list[str]:
        """Every listed repository, in order."""
        return list(self.group.boxes)

    def chosen(self) -> list[str]:
        return list(self.group.checked())


def choose_repositories(
    parent: wx.Window,
    show_modal: ShowModal,
    *,
    title: str,
    repositories: Sequence[str],
    checked: Sequence[str],
    note: str = "",
) -> list[str] | None:
    """The checked repositories, or None when the person cancels."""
    dialog = RepositoryChecklistDialog(
        parent, title=title, repositories=repositories, checked=checked, note=note
    )
    try:
        if show_modal(dialog, title) != wx.ID_OK:
            return None
        return dialog.chosen()
    finally:
        dialog.Destroy()
