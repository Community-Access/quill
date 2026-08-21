"""Your year in listening, as something to read rather than something to look at.

One read-only text box, a Copy, and a Save as Text. No charts and no tiles: the
text **is** the artefact. It is meant to be read straight through, and quite
possibly sent to somebody -- which a bar chart is not.

The year is chosen rather than assumed. In January the interesting year is
usually the one that just ended, so the picker offers both and opens on
whichever actually has listening in it.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from quill.ui.dialog_contract import apply_modal_ids

__all__ = ["YearInReviewDialog", "open_year_in_review"]

TITLE = "Year in Review"


class YearInReviewDialog:
    """A paragraph about one year, with a way to keep it."""

    def __init__(
        self,
        parent: object,
        *,
        sessions: list[Any],
        show_titles: dict[str, str] | None = None,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._sessions = sessions
        self._titles = show_titles or {}
        self._announce = announce_cb or (lambda _m: None)

        this_year = datetime.now().astimezone().year
        self._years = [this_year, this_year - 1]

        self.dialog = wx.Dialog(
            parent, title=TITLE, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize((560, 520))
        root = wx.BoxSizer(wx.VERTICAL)

        year_row = wx.BoxSizer(wx.HORIZONTAL)
        year_row.Add(
            wx.StaticText(self.dialog, label="&Year:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self._year_choice = wx.Choice(self.dialog, choices=[str(year) for year in self._years])
        self._year_choice.SetName("Which year to report on")
        self._year_choice.SetSelection(self._opening_year_index())
        year_row.Add(self._year_choice, 1, wx.EXPAND)
        root.Add(year_row, 0, wx.EXPAND | wx.ALL, 10)

        self._report = wx.TextCtrl(
            self.dialog, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2
        )
        self._report.SetName("Your year in listening; arrow through it line by line")
        root.Add(self._report, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        copy_btn = wx.Button(self.dialog, label="&Copy")
        save_btn = wx.Button(self.dialog, label="&Save as Text...")
        close_btn = wx.Button(self.dialog, wx.ID_CANCEL, "C&lose")
        buttons.Add(copy_btn, 0, wx.RIGHT, 6)
        buttons.Add(save_btn, 0)
        buttons.AddStretchSpacer()
        buttons.Add(close_btn, 0)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizer(root)
        self._year_choice.Bind(wx.EVT_CHOICE, lambda _e: self._refresh(speak=True))
        copy_btn.Bind(wx.EVT_BUTTON, lambda _e: self._copy())
        save_btn.Bind(wx.EVT_BUTTON, lambda _e: self._save())
        self._refresh()

    def _opening_year_index(self) -> int:
        """Open on a year that actually has something in it.

        In January the interesting year is almost always the one that just
        ended, and opening on an empty report reads as a broken feature.
        """
        from quill.core.podcasts.year_in_review import year_in_review

        for index, year in enumerate(self._years):
            if year_in_review(self._sessions, year, self._titles):
                return index
        return 0

    def _year(self) -> int:
        return self._years[max(0, self._year_choice.GetSelection())]

    def _text(self) -> str:
        from quill.core.podcasts.year_in_review import year_in_review

        return year_in_review(self._sessions, self._year(), self._titles) or (
            f"Nothing was recorded for {self._year()} yet. Your listening starts "
            "counting the first time you play an episode."
        )

    def _refresh(self, *, speak: bool = False) -> None:
        text = self._text()
        self._report.SetValue(text)
        self._report.SetInsertionPoint(0)
        if speak:
            self._announce(text.splitlines()[0] if text else "")

    def _copy(self) -> None:
        wx = self._wx
        text = self._report.GetValue()
        if text and wx.TheClipboard.Open():
            try:
                wx.TheClipboard.SetData(wx.TextDataObject(text))
            finally:
                wx.TheClipboard.Close()
            self._announce("Copied.")

    def _save(self) -> None:
        wx = self._wx
        with wx.FileDialog(
            self.dialog,
            "Save your year in review",
            defaultFile=f"quill-cast-{self._year()}.txt",
            wildcard="Text file (*.txt)|*.txt|All files (*.*)|*.*",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as file_dialog:
            if file_dialog.ShowModal() != wx.ID_OK:
                return
            destination = file_dialog.GetPath()
        from pathlib import Path

        try:
            Path(destination).write_text(self._report.GetValue(), encoding="utf-8")
        except OSError as error:
            self._announce(f"Could not save that file: {error}.")
            return
        self._announce(f"Saved to {Path(destination).name}.")

    def show(self) -> None:
        from quill.ui.dialog_contract import show_modal_dialog

        self.dialog.CentreOnParent()
        apply_modal_ids(
            self.dialog,
            affirmative_id=self._wx.ID_CANCEL,
            affirmative_label="Close",
            cancel_id=self._wx.ID_CANCEL,
            escape_id=self._wx.ID_CANCEL,
        )
        try:
            show_modal_dialog(self.dialog, TITLE, announce=self._announce)
        finally:
            self.dialog.Destroy()


def open_year_in_review(stats_dialog: Any) -> None:
    """Open the review over whatever the statistics window is already holding."""
    YearInReviewDialog(
        stats_dialog.dialog,
        sessions=list(stats_dialog._sessions),
        show_titles=dict(stats_dialog._show_titles),
        announce_cb=stats_dialog._announce,
    ).show()
