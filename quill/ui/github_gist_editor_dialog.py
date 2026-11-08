"""Write a new gist, or change one: its description and its files.

Opened from Explore's gists view (New Gist, Edit Gist). Every change here is
local until the affirmative button: the window edits a
:class:`~quill.core.github.gists.GistDraft`, and the caller sends the draft to
GitHub off the UI thread. Deleting a file asks first. A file GitHub sent only
part of (over about a megabyte) is shown read-only, because saving it would cut
it short. QUILL and QUILL Lite share this window through Explore.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.github.gists import GistDraft
from quill.core.github.items_errors import GitHubItemsError
from quill.ui.dialog_contract import (
    apply_listbox_activation,
    apply_modal_ids,
    bind_close_button,
    show_modal_dialog,
)
from quill.ui.dpi import dip_size

__all__ = ["GitHubGistEditorDialog"]


def _words(exc: BaseException) -> str:
    return str(exc.args[0]) if exc.args else str(exc)


class GitHubGistEditorDialog:
    """Description, files and file text for one gist; returns the edited draft."""

    def __init__(
        self,
        parent: object,
        draft: GistDraft,
        *,
        creating: bool,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self.draft = draft
        self.public = False
        self._creating = creating
        self._announce = announce_cb or (lambda _message: None)
        self._current = ""
        self._title = "New Gist" if creating else "Edit Gist"
        self.dialog = wx.Dialog(
            parent, title=self._title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize(dip_size(self.dialog, 560, 480))
        self.dialog.SetSize(dip_size(self.dialog, 760, 600))
        panel = wx.Panel(self.dialog)
        root = wx.BoxSizer(wx.VERTICAL)

        root.Add(wx.StaticText(panel, label="&Description:"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        self._description = wx.TextCtrl(panel, value=draft.description)
        self._description.SetName("Gist description")
        self._description.SetHelpText(
            "A short line that says what the gist is. GitHub shows it in the gist list."
        )
        root.Add(self._description, 0, wx.EXPAND | wx.ALL, 8)
        self._public: Any = None
        if creating:
            self._public = wx.CheckBox(panel, label="Pu&blic gist")
            self._public.SetHelpText(
                "Checked, anyone can find the gist. Not checked, it is secret: unlisted, "
                "but anyone with its link can still read it. GitHub does not let you "
                "change this later."
            )
            root.Add(self._public, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        root.Add(wx.StaticText(panel, label="&Files:"), 0, wx.LEFT | wx.RIGHT, 8)
        self._files = wx.ListBox(panel, choices=[])
        self._files.SetName("Files in the gist")
        self._files.SetHelpText(
            "The gist's files. Choose one to read or change its text below; Enter moves there."
        )
        root.Add(self._files, 1, wx.EXPAND | wx.ALL, 8)
        root.Add(wx.StaticText(panel, label="File &text:"), 0, wx.LEFT | wx.RIGHT, 8)
        self._text = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_DONTWRAP)
        self._text.SetName("Text of the chosen gist file")
        self._text.SetHelpText(
            "The chosen file's text. A file too large for GitHub to send whole is read-only."
        )
        root.Add(self._text, 2, wx.EXPAND | wx.ALL, 8)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        add_btn = wx.Button(panel, label="&Add File...")
        add_btn.SetHelpText("Add a new file to the gist, with a name such as notes.md.")
        self._rename_btn = wx.Button(panel, label="Re&name File...")
        self._rename_btn.SetHelpText("Give the chosen file a new name.")
        self._delete_btn = wx.Button(panel, label="De&lete File...")
        self._delete_btn.SetHelpText(
            "Remove the chosen file from the gist when you save. QUILL asks first."
        )
        ok_btn = wx.Button(panel, wx.ID_OK, label="Create Gist" if creating else "Save Gist")
        ok_btn.SetHelpText(
            "Send the gist to GitHub. QUILL says it is saved only when GitHub confirms it."
        )
        cancel_btn = wx.Button(panel, wx.ID_CANCEL, label="Cancel")
        cancel_btn.SetHelpText("Close without sending anything to GitHub.")
        for button in (add_btn, self._rename_btn, self._delete_btn):
            buttons.Add(button, 0, wx.RIGHT, 6)
        buttons.AddStretchSpacer()
        buttons.Add(ok_btn, 0, wx.RIGHT, 6)
        buttons.Add(cancel_btn)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        panel.SetSizer(root)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.dialog.SetSizer(outer)

        self._files.Bind(wx.EVT_LISTBOX, self._on_file_chosen)
        apply_listbox_activation(self._files, lambda _event: self._text.SetFocus())
        add_btn.Bind(wx.EVT_BUTTON, self._add_file)
        self._rename_btn.Bind(wx.EVT_BUTTON, self._rename_file)
        self._delete_btn.Bind(wx.EVT_BUTTON, self._delete_file)
        ok_btn.Bind(wx.EVT_BUTTON, self._on_ok)
        bind_close_button(self.dialog, cancel_btn, modeless=False)
        self._refresh_files(next(iter(draft.files), ""))

    # -- Files -------------------------------------------------------------

    def _commit_text(self) -> bool:
        """Keep the text box's edits in the draft; False (and said) if refused."""
        if not self._current or self._current not in self.draft.files:
            return True
        try:
            self.draft.set_content(self._current, self._text.GetValue())
        except GitHubItemsError as exc:
            self._say(_words(exc))
            return False
        return True

    def _refresh_files(self, choose: str) -> None:
        names = self.draft.names()
        self._files.Set(names)
        self._current = choose if choose in names else (names[0] if names else "")
        if self._current:
            self._files.SetSelection(names.index(self._current))
        self._show_current()

    def _show_current(self) -> None:
        name = self._current
        self._text.ChangeValue(self.draft.files.get(name, ""))
        self._text.SetEditable(bool(name) and not self.draft.is_truncated(name))
        self._rename_btn.Enable(bool(name))
        self._delete_btn.Enable(len(self.draft.files) > 1)

    def _on_file_chosen(self, _event: object) -> None:
        if not self._commit_text():
            self._files.SetSelection(self.draft.names().index(self._current))
            return
        index = self._files.GetSelection()
        names = self.draft.names()
        if 0 <= index < len(names):
            self._current = names[index]
            self._show_current()

    def _prompt(self, message: str, title: str, value: str = "") -> str | None:
        wx = self._wx
        with wx.TextEntryDialog(self.dialog, message, title, value) as dialog:
            if show_modal_dialog(dialog, title, announce=self._announce) != wx.ID_OK:
                return None
            return dialog.GetValue().strip()

    def _add_file(self, _event: object) -> None:
        if not self._commit_text():
            return
        name = self._prompt("Name for the new file, such as notes.md:", "Add File")
        if not name:
            return
        try:
            added = self.draft.add_file(name)
        except GitHubItemsError as exc:
            self._say(_words(exc))
            return
        self._refresh_files(added)
        self._text.SetFocus()

    def _rename_file(self, _event: object) -> None:
        if not self._current or not self._commit_text():
            return
        name = self._prompt(f"New name for {self._current}:", "Rename File", self._current)
        if not name:
            return
        try:
            renamed = self.draft.rename_file(self._current, name)
        except GitHubItemsError as exc:
            self._say(_words(exc))
            return
        self._refresh_files(renamed)
        self._files.SetFocus()

    def _delete_file(self, _event: object) -> None:
        wx = self._wx
        name = self._current
        if not name:
            return
        title = "Delete File"
        with wx.MessageDialog(
            self.dialog,
            f"Delete {name} from this gist? It goes when you save, and GitHub keeps no "
            "copy you can bring back from QUILL.",
            title,
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
        ) as dialog:
            if show_modal_dialog(dialog, title, announce=self._announce) != wx.ID_YES:
                return
        try:
            self.draft.delete_file(name)
        except GitHubItemsError as exc:
            self._say(_words(exc))
            return
        self._refresh_files("")
        self._files.SetFocus()

    # -- Finishing ---------------------------------------------------------

    def _say(self, message: str) -> None:
        wx = self._wx
        with wx.MessageDialog(self.dialog, message, self._title, wx.OK | wx.ICON_INFORMATION) as d:
            show_modal_dialog(d, self._title, announce=self._announce)

    def _on_ok(self, _event: object) -> None:
        if not self._commit_text():
            return
        self.draft.description = self._description.GetValue().strip()
        self.public = bool(self._public is not None and self._public.GetValue())
        try:
            if self._creating:
                self.draft.create_payload(public=self.public)
            else:
                self.draft.changes()
        except GitHubItemsError as exc:
            self._say(_words(exc))
            return
        self.dialog.EndModal(self._wx.ID_OK)

    def show(self) -> bool:
        """True when the person chose Create or Save and the draft is valid."""
        wx = self._wx
        self.dialog.CentreOnParent()
        apply_modal_ids(
            self.dialog,
            affirmative_id=wx.ID_OK,
            affirmative_label="Create Gist" if self._creating else "Save Gist",
            cancel_id=wx.ID_CANCEL,
            cancel_label="Cancel",
            escape_id=wx.ID_CANCEL,
        )
        self._description.SetFocus()
        try:
            return show_modal_dialog(self.dialog, self._title, announce=self._announce) == wx.ID_OK
        finally:
            self.dialog.Destroy()
