"""Set three things for every podcast in a folder, once.

Deliberately three, and deliberately not "folder settings" in the sense of a
value the folder keeps. **The chosen values are written into each member show's
own override and the folder then forgets them.** One inheritance chain, not two:
what a show's setting *is* stays what ``PodcastLibrary.effective_settings`` has
always said it is, and nothing in the app has to ask a folder for an opinion.

The cost of that choice is honest and is stated in the window: a show moved into
the folder later does not inherit anything, because there is nothing to inherit
from. The alternative -- a folder value resolved at read time -- means every
consumer of every setting has to walk the folder tree, and two shows in the same
folder can disagree about what their setting is depending on which code path
asked. That is the bug this design refuses to have.

Three settings because they are the three that are genuinely folder-shaped: how
long queued episodes live, whether new episodes go to the Inbox, and the speed a
folder of shows should play at. The rest are per-show for good reasons.

**Each control starts at "leave alone".** A dialog that opened showing defaults
would apply those defaults to forty shows the moment somebody pressed OK.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.ui.dialog_contract import apply_modal_ids

__all__ = ["FolderSettingsDialog"]

TITLE = "Folder Settings"

#: The Inbox choice, and its "do not touch" first entry.
_INBOX_LABELS = ("Leave each podcast as it is", "Route new episodes to the Inbox", "Do not")
_INBOX_VALUES: tuple[bool | None, ...] = (None, True, False)


class FolderSettingsDialog:
    """Returns a dict of settings to apply, or ``{}`` when nothing was chosen."""

    def __init__(
        self,
        parent: object,
        *,
        folder_name: str,
        show_count: int,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._announce = announce_cb or (lambda _m: None)
        self._result: dict[str, Any] = {}
        self._count = show_count

        self.dialog = wx.Dialog(
            parent, title=f"{TITLE} -- {folder_name}", style=wx.DEFAULT_DIALOG_STYLE
        )
        root = wx.BoxSizer(wx.VERTICAL)

        intro = wx.StaticText(
            self.dialog,
            label=(
                f"Whatever you set here is applied to all {show_count} "
                f"podcast{'' if show_count == 1 else 's'} in {folder_name} and its "
                "sub-folders, as if you had set it on each one. A podcast you move "
                "in later keeps its own settings."
            ),
        )
        intro.Wrap(520)
        root.Add(intro, 0, wx.ALL | wx.EXPAND, 10)

        grid = wx.FlexGridSizer(cols=2, gap=(6, 8))
        grid.AddGrowableCol(1, 1)

        grid.Add(
            wx.StaticText(self.dialog, label="Queued episodes e&xpire after:"),
            0,
            wx.ALIGN_CENTER_VERTICAL,
        )
        self._age = wx.SpinCtrl(self.dialog, min=-1, max=365, initial=-1)
        self._age.SetName(
            "Days a queued episode stays in the Play Queue before moving to "
            "Recently Expired. Zero turns it off. Leave this at minus one to "
            "change nothing."
        )
        grid.Add(self._age, 0)

        grid.Add(wx.StaticText(self.dialog, label="&New episodes:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._inbox = wx.Choice(self.dialog, choices=list(_INBOX_LABELS))
        self._inbox.SetName("Whether new episodes from these podcasts land in the Inbox")
        self._inbox.SetSelection(0)
        grid.Add(self._inbox, 1, wx.EXPAND)

        grid.Add(wx.StaticText(self.dialog, label="Playback &speed:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._speed = wx.SpinCtrlDouble(self.dialog, min=0.0, max=5.0, initial=0.0, inc=0.1)
        self._speed.SetDigits(1)
        self._speed.SetName(
            "The speed these podcasts play at. Leave this at zero to change nothing."
        )
        grid.Add(self._speed, 0)
        root.Add(grid, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        note = wx.StaticText(
            self.dialog,
            label="Anything left at its 'change nothing' value is not applied.",
        )
        root.Add(note, 0, wx.ALL, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        buttons.AddStretchSpacer()
        buttons.Add(wx.Button(self.dialog, wx.ID_OK, "&Apply"), 0, wx.RIGHT, 6)
        buttons.Add(wx.Button(self.dialog, wx.ID_CANCEL, "Cancel"), 0)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizer(root)
        self.dialog.Fit()
        self.dialog.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)

    def _on_ok(self, event: Any) -> None:
        chosen: dict[str, Any] = {}
        age = int(self._age.GetValue())
        if age >= 0:
            chosen["queue_age_limit_days"] = age
        inbox = _INBOX_VALUES[max(0, self._inbox.GetSelection())]
        if inbox is not None:
            chosen["route_to_inbox"] = inbox
        speed = float(self._speed.GetValue())
        if speed > 0:
            chosen["speed"] = speed
        if not chosen:
            # Nothing chosen is not an error, but silently applying nothing to
            # forty shows would leave somebody wondering whether it worked.
            self._announce("Nothing was set, so nothing was changed.")
        self._result = chosen
        event.Skip()

    def show(self) -> dict[str, Any]:
        from quill.ui.dialog_contract import show_modal_dialog

        self.dialog.CentreOnParent()
        apply_modal_ids(
            self.dialog,
            affirmative_id=self._wx.ID_OK,
            affirmative_label="Apply",
            cancel_id=self._wx.ID_CANCEL,
            escape_id=self._wx.ID_CANCEL,
        )
        try:
            answer = show_modal_dialog(self.dialog, TITLE, announce=self._announce)
            return self._result if answer == self._wx.ID_OK else {}
        finally:
            self.dialog.Destroy()
