"""Edit Release: name, notes, draft and prerelease (QUILL and QUILL Lite).

Opened from the GitHub Items viewer's Releases view (Actions button or the
row's context menu). It shows what GitHub holds now -- the release is read
again by tag before this opens -- and returns what the person chose; the
caller sends it and reports what GitHub confirmed. Clearing Draft publishes
a draft, which the caller confirms first because watchers are notified.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog
from quill.ui.dpi import dip_size

if TYPE_CHECKING:
    from collections.abc import Callable

    from quill.core.github.release_admin import ReleaseRecord

__all__ = ["EditReleaseDialog", "EditReleaseValues"]


@dataclass(frozen=True, slots=True)
class EditReleaseValues:
    name: str
    body: str
    draft: bool
    prerelease: bool


class EditReleaseDialog:
    """Four fields and Save or Cancel; nothing is sent from here."""

    def __init__(
        self,
        parent: object,
        release: ReleaseRecord,
        *,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._announce = announce_cb
        self.dialog = wx.Dialog(
            parent,
            title=f"Edit Release {release.tag}",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize(dip_size(self.dialog, 520, 420))
        panel = wx.Panel(self.dialog)
        root = wx.BoxSizer(wx.VERTICAL)

        root.Add(wx.StaticText(panel, label="Release &name:"), 0, wx.LEFT | wx.TOP, 8)
        self._name = wx.TextCtrl(panel, value=release.name)
        self._name.SetName("Release name")
        self._name.SetHelpText(
            "The release's title on GitHub. Leave it blank and GitHub shows the tag instead."
        )
        root.Add(self._name, 0, wx.EXPAND | wx.ALL, 8)

        root.Add(wx.StaticText(panel, label="Release n&otes:"), 0, wx.LEFT, 8)
        self._body = wx.TextCtrl(panel, value=release.body, style=wx.TE_MULTILINE | wx.TE_RICH2)
        self._body.SetName("Release notes, in Markdown")
        self._body.SetHelpText(
            "The release notes, in Markdown. Arrow through them like a document; "
            "Tab leaves the box."
        )
        root.Add(self._body, 1, wx.EXPAND | wx.ALL, 8)

        self._draft = wx.CheckBox(panel, label="&Draft (not published yet)")
        self._draft.SetValue(release.draft)
        self._draft.SetHelpText(
            "Checked, the release stays a draft that only people with push access see. "
            "Clear it to publish the release; QUILL asks first, because watchers are notified."
        )
        root.Add(self._draft, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        self._prerelease = wx.CheckBox(panel, label="&Pre-release")
        self._prerelease.SetValue(release.prerelease)
        self._prerelease.SetHelpText(
            "Checked, GitHub marks the release as not ready for production and does not "
            "show it as the latest release."
        )
        root.Add(self._prerelease, 0, wx.ALL, 8)

        buttons = wx.StdDialogButtonSizer()
        save = wx.Button(panel, wx.ID_OK, "Save")
        save.SetHelpText("Sends these four fields to GitHub.")
        save.SetDefault()
        cancel = wx.Button(panel, wx.ID_CANCEL, "Cancel")
        cancel.SetHelpText("Closes without changing the release.")
        buttons.AddButton(save)
        buttons.AddButton(cancel)
        buttons.Realize()
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        panel.SetSizer(root)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.dialog.SetSizer(outer)
        self.dialog.SetSize(dip_size(self.dialog, 620, 520))
        self._name.SetFocus()

    def values(self) -> EditReleaseValues:
        return EditReleaseValues(
            self._name.GetValue().strip(),
            self._body.GetValue(),
            bool(self._draft.GetValue()),
            bool(self._prerelease.GetValue()),
        )

    def show(self) -> EditReleaseValues | None:
        wx = self._wx
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        try:
            answer = show_modal_dialog(self.dialog, self.dialog.GetTitle(), announce=self._announce)
            return self.values() if answer == wx.ID_OK else None
        finally:
            self.dialog.Destroy()
