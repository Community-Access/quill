"""Download Preferences: where things land, how they are filed, what closing means.

The model (:mod:`quill.core.radio.download_prefs`) shipped with the download
queue; this is the surface that makes it the listener's. Everything on it is a
standing rule rather than a per-download question -- which is the point: the
queue's promise is "say yes to four books and carry on listening", and a rule
you set once is how forty chapters get filed without forty prompts.

Plain native controls throughout: a text field for the folder with a Browse
button, and a checkbox per rule, each labelled with what it *does* rather than
what it is called internally. The current effect is restated in one live
sentence under the controls (``DownloadPrefs.describe``), so the dialog answers
"what will happen to the next thing I save?" before OK is ever pressed.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

from quill.core.radio import download_prefs
from quill.core.radio.download_prefs import DownloadPrefs
from quill.ui.dialog_contract import apply_modal_ids

TITLE = "Download Preferences"


class DownloadPrefsDialog:
    """Edit the standing rules for the download queue."""

    def __init__(
        self,
        parent: object,
        *,
        prefs: DownloadPrefs,
        show_modal_dialog: Callable,
        announce: Callable[[str], None],
    ) -> None:
        import wx

        self._wx = wx
        self._initial = prefs
        self._announce = announce
        self._show_modal = show_modal_dialog

        self.dialog = wx.Dialog(
            parent, title=TITLE, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self._build_ui(prefs)

    def _build_ui(self, prefs: DownloadPrefs) -> None:
        wx = self._wx
        panel = self.dialog
        root = wx.BoxSizer(wx.VERTICAL)

        folder_label = wx.StaticText(panel, label="Downloads &folder (blank uses the default):")
        root.Add(folder_label, 0, wx.LEFT | wx.TOP | wx.RIGHT, 10)
        folder_row = wx.BoxSizer(wx.HORIZONTAL)
        self._root_ctrl = wx.TextCtrl(panel, value=prefs.root)
        self._root_ctrl.SetName(
            f"Downloads folder; leave blank for the default, {download_prefs.default_root()}"
        )
        folder_row.Add(self._root_ctrl, 1, wx.EXPAND | wx.RIGHT, 6)
        browse_btn = wx.Button(panel, label="B&rowse...")
        browse_btn.SetName("Choose the downloads folder")
        folder_row.Add(browse_btn, 0)
        root.Add(folder_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self._per_show = wx.CheckBox(panel, label="A folder per podcast &show")
        self._per_book = wx.CheckBox(panel, label="A folder per &book")
        self._by_author = wx.CheckBox(
            panel, label="Group books by &author once an author has more than one"
        )
        self._keep_going = wx.CheckBox(
            panel, label="&Keep downloads going when the window closes to the tray"
        )
        self._always_ask = wx.CheckBox(
            panel, label="As&k where to save each download instead of filing it automatically"
        )
        self._per_show.SetValue(prefs.folder_per_show)
        self._per_book.SetValue(prefs.folder_per_book)
        self._by_author.SetValue(prefs.group_books_by_author)
        self._keep_going.SetValue(prefs.keep_going_in_background)
        self._always_ask.SetValue(prefs.always_ask)
        for box in (
            self._per_show,
            self._per_book,
            self._by_author,
            self._keep_going,
            self._always_ask,
        ):
            root.Add(box, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        #: The live one-sentence answer to "what will happen to the next thing
        #: I save?", updated as the controls change.
        self._effect = wx.StaticText(panel, label=self.value().describe())
        root.Add(self._effect, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        buttons = panel.CreateSeparatedButtonSizer(wx.OK | wx.CANCEL)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)
        apply_modal_ids(panel, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
        panel.SetSizer(root)
        root.Fit(panel)
        panel.SetMinSize(panel.GetSize())

        browse_btn.Bind(wx.EVT_BUTTON, lambda _e: self._browse())
        for control in (
            self._per_show,
            self._per_book,
            self._by_author,
            self._keep_going,
            self._always_ask,
        ):
            control.Bind(wx.EVT_CHECKBOX, lambda _e: self._refresh_effect())
        self._root_ctrl.Bind(wx.EVT_TEXT, lambda _e: self._refresh_effect())
        wx.CallAfter(self._root_ctrl.SetFocus)

    def _browse(self) -> None:
        wx = self._wx
        with wx.DirDialog(  # dialog_button_contract: exempt (platform picker)
            self.dialog,
            "Choose the downloads folder",
            defaultPath=self._root_ctrl.GetValue() or str(download_prefs.default_root()),
        ) as picker:
            if picker.ShowModal() == wx.ID_OK:
                self._root_ctrl.SetValue(picker.GetPath())

    def _refresh_effect(self) -> None:
        self._effect.SetLabel(self.value().describe())

    def value(self) -> DownloadPrefs:
        """The preferences as the controls currently read."""
        return replace(
            self._initial,
            root=self._root_ctrl.GetValue().strip(),
            folder_per_show=self._per_show.GetValue(),
            folder_per_book=self._per_book.GetValue(),
            group_books_by_author=self._by_author.GetValue(),
            keep_going_in_background=self._keep_going.GetValue(),
            always_ask=self._always_ask.GetValue(),
        )

    def show(self) -> DownloadPrefs | None:
        """The edited preferences, or ``None`` if the listener cancelled."""
        wx = self._wx
        chosen: DownloadPrefs | None = None
        try:
            result = self._show_modal(self.dialog, TITLE)
            # Read before Destroy: the controls the value comes from die with
            # the window.
            if result == wx.ID_OK:
                chosen = self.value()
        finally:
            self.dialog.Destroy()
        return chosen
