"""Workbench Options: the GitHub Workbench's own preferences (GitHub PRD section 4.1).

Tools > Workbench Options... (Ctrl+Shift+O) in the Workbench's menu bar. A
tabbed dialog parented to the Workbench, so it blocks only the Workbench and
never the editor, and the editors' main Options get no GitHub page at all
(decision 6). It reads and writes ``github_workbench.json`` through the
wx-free :mod:`quill.core.github.workbench_prefs`, which both editors share.

Every control has inline help (GATE-GITHUB-HELP), worded once in
:data:`quill.core.github.workbench_help.PREF_HELP`, and access keys are
unique across all five pages (GATE-14); OK and Cancel carry none. Nothing is
announced on opening: the reader says the title and the first control
(GATE-13). OK saves; Cancel changes nothing.
"""

from __future__ import annotations

from typing import Any

from quill.core.github.workbench_help import CHOICE_WORDS, PREF_HELP, PREF_PAGES
from quill.core.github.workbench_prefs import CHOICES, WorkbenchPrefs, load_prefs, save_prefs
from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog
from quill.ui.dpi import dip_size

__all__ = ["WorkbenchOptionsDialog", "show_workbench_options"]

_TITLE = "Workbench Options"


class WorkbenchOptionsDialog:
    """The five pages; :meth:`values` is what OK would save."""

    def __init__(self, parent: Any, prefs: WorkbenchPrefs) -> None:
        import wx

        self._wx = wx
        self.prefs = prefs
        self.controls: dict[str, Any] = {}
        self.dialog = wx.Dialog(parent, title=_TITLE, style=wx.DEFAULT_DIALOG_STYLE)
        self.dialog.SetSize(dip_size(self.dialog, 560, 460))
        root = wx.BoxSizer(wx.VERTICAL)
        self.notebook = wx.Notebook(self.dialog)
        self.notebook.SetHelpText("The option pages. Ctrl+Tab moves to the next page.")
        self.pages: dict[str, Any] = {}
        for title in PREF_PAGES:
            panel = wx.Panel(self.notebook)
            panel.SetSizer(wx.BoxSizer(wx.VERTICAL))
            self.pages[title] = panel
            self.notebook.AddPage(panel, title)
        for name, (page, label, help_text) in PREF_HELP.items():
            self._add(name, self.pages[page], label, help_text)
        self._add_repositories(self.pages["Repositories"])
        self._add_privacy_buttons(self.pages["Privacy"])
        root.Add(self.notebook, 1, wx.EXPAND | wx.ALL, 8)
        buttons = self.dialog.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
        ok = self.dialog.FindWindowById(wx.ID_OK)
        cancel = self.dialog.FindWindowById(wx.ID_CANCEL)
        ok.SetHelpText("Save these choices and close.")
        cancel.SetHelpText("Close without changing anything. Escape does the same.")
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        self.dialog.SetSizer(root)
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)

    # -- building ---------------------------------------------------------------

    def _add(self, name: str, panel: Any, label: str, help_text: str) -> None:
        wx = self._wx
        sizer = panel.GetSizer()
        value = getattr(self.prefs, name)
        if name in CHOICES:
            row = wx.BoxSizer(wx.HORIZONTAL)
            caption = wx.StaticText(panel, label=label)
            choice = wx.Choice(panel, choices=[CHOICE_WORDS[v] for v in CHOICES[name]])
            choice.SetSelection(CHOICES[name].index(value))
            choice.SetName(label.replace("&", "").rstrip(":"))
            choice.SetHelpText(help_text)
            row.Add(caption, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
            row.Add(choice, 1)
            sizer.Add(row, 0, wx.EXPAND | wx.ALL, 6)
            self.controls[name] = choice
        elif isinstance(value, bool):
            box = wx.CheckBox(panel, label=label)
            box.SetValue(value)
            box.SetHelpText(help_text)
            sizer.Add(box, 0, wx.ALL, 6)
            self.controls[name] = box
        else:
            row = wx.BoxSizer(wx.HORIZONTAL)
            caption = wx.StaticText(panel, label=label)
            spin = wx.SpinCtrl(panel, min=5, max=1440, initial=int(value))
            spin.SetName(label.replace("&", "").rstrip(":"))
            spin.SetHelpText(help_text)
            row.Add(caption, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
            row.Add(spin, 0)
            sizer.Add(row, 0, wx.EXPAND | wx.ALL, 6)
            self.controls[name] = spin

    def _add_repositories(self, panel: Any) -> None:
        """Pinned repositories and favorites, to manage in one place (GitHub Items' store)."""
        wx = self._wx
        sizer = panel.GetSizer()
        self._saved = self._load_saved()
        sizer.Add(wx.StaticText(panel, label="&Pinned repositories:"), 0, wx.LEFT | wx.TOP, 6)
        self.pinned = wx.ListBox(panel, choices=list(self._saved.pinned) if self._saved else [])
        self.pinned.SetHelpText("Repositories kept under Repositories, Pinned, in the tree.")
        sizer.Add(self.pinned, 1, wx.EXPAND | wx.ALL, 6)
        unpin = wx.Button(panel, label="&Unpin")
        unpin.SetHelpText("Take the selected repository out of Pinned when you press OK.")
        unpin.Bind(wx.EVT_BUTTON, lambda _e: self._drop(self.pinned))
        sizer.Add(unpin, 0, wx.LEFT, 6)
        sizer.Add(wx.StaticText(panel, label="Fa&vorites:"), 0, wx.LEFT | wx.TOP, 6)
        favorites = [f.title or f.url for f in self._saved.favorites] if self._saved else []
        self.favorites = wx.ListBox(panel, choices=favorites)
        self.favorites.SetHelpText("Items kept under Repositories, Favorites, in the tree.")
        sizer.Add(self.favorites, 1, wx.EXPAND | wx.ALL, 6)
        remove = wx.Button(panel, label="R&emove Favorite")
        remove.SetHelpText("Take the selected item out of Favorites when you press OK.")
        remove.Bind(wx.EVT_BUTTON, lambda _e: self._drop(self.favorites))
        sizer.Add(remove, 0, wx.LEFT | wx.BOTTOM, 6)

    def _add_privacy_buttons(self, panel: Any) -> None:
        wx = self._wx
        sizer = panel.GetSizer()
        self.forget_place = False
        forget = wx.Button(panel, label="Forget &Where I Was")
        forget.SetHelpText(
            "Forget the Workbench's last place, open nodes and recent repositories on "
            "this computer, when you press OK. Nothing on GitHub changes."
        )
        forget.Bind(wx.EVT_BUTTON, lambda _e: setattr(self, "forget_place", True))
        sizer.Add(forget, 0, wx.ALL, 6)
        clear = wx.Button(panel, label="Clear &Your Favorites")
        clear.SetHelpText("Empty Favorites on this computer when you press OK.")
        clear.Bind(wx.EVT_BUTTON, lambda _e: self.favorites.Clear())
        sizer.Add(clear, 0, wx.ALL, 6)

    @staticmethod
    def _load_saved() -> Any:
        try:
            from quill.core.github.navigation_state import account_key_for_token
            from quill.core.github.saved_items import GitHubSavedItems
            from quill.core.github.token_store import load_github_token

            return GitHubSavedItems.load(account_key=account_key_for_token(load_github_token()))
        except Exception:  # noqa: BLE001 - the page shows empty lists rather than failing
            return None

    def _drop(self, box: Any) -> None:
        index = box.GetSelection()
        if index != self._wx.NOT_FOUND:
            box.Delete(index)

    # -- reading ----------------------------------------------------------------

    def values(self) -> WorkbenchPrefs:
        changes: dict[str, Any] = {}
        for name, control in self.controls.items():
            if name in CHOICES:
                changes[name] = CHOICES[name][max(0, control.GetSelection())]
            else:
                changes[name] = control.GetValue()
        return self.prefs.with_changes(**changes)

    def save_lists(self) -> None:
        """Write back the pinned and favorite lists as the person left them."""
        saved = self._saved
        if saved is None:
            return
        kept_pins = set(self.pinned.GetStrings())
        kept_titles = list(self.favorites.GetStrings())
        saved.pinned = [repo for repo in saved.pinned if repo in kept_pins]
        saved.favorites = [f for f in saved.favorites if (f.title or f.url) in kept_titles]
        saved.save()

    def show(self) -> bool:
        wx = self._wx
        try:
            if show_modal_dialog(self.dialog, _TITLE) != wx.ID_OK:
                return False
            save_prefs(self.values())
            self.save_lists()
            if self.forget_place:
                _forget_places()
            return True
        finally:
            self.dialog.Destroy()


def _forget_places() -> None:
    from quill.core.github.navigation_state import (
        WorkbenchPlace,
        account_key_for_token,
        save_workbench_place,
    )
    from quill.core.github.token_store import load_github_token

    save_workbench_place(account_key_for_token(load_github_token()), WorkbenchPlace())


def show_workbench_options(parent: Any) -> bool:
    """Tools > Workbench Options...; True when the person pressed OK."""
    return WorkbenchOptionsDialog(parent, load_prefs()).show()
