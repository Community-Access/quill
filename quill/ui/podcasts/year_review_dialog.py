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

__all__ = ["YearInReviewWindow", "open_year_in_review"]

TITLE = "Year in Review"


class YearInReviewWindow:
    """A paragraph about one year, with a way to keep it -- a peer window.

    Made once and raised again (qc.md Phase 4): asked for a second time from
    Listening Statistics it re-reads the statistics window's sessions, keeps
    the year you chose, and Escape returns you to the button that opened it.
    """

    TITLE = TITLE
    MENU_TITLE = "Year in Re&view"

    def __init__(
        self,
        parent: object,
        *,
        sessions: list[Any],
        show_titles: dict[str, str] | None = None,
        announce_cb: Callable[[str], None] | None = None,
        reload: Callable[[], tuple[list[Any], dict[str, str]]] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._reload = reload
        self._sessions = sessions
        self._titles = show_titles or {}
        self._announce = announce_cb or (lambda _m: None)

        this_year = datetime.now().astimezone().year
        self._years = [this_year, this_year - 1]

        self.frame = wx.Frame(parent, title=TITLE, size=(600, 560))
        self.frame.SetMinSize((560, 520))
        panel = wx.Panel(self.frame, style=wx.TAB_TRAVERSAL)
        root = wx.BoxSizer(wx.VERTICAL)

        year_row = wx.BoxSizer(wx.HORIZONTAL)
        year_row.Add(
            wx.StaticText(panel, label="&Year:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self._year_choice = wx.Choice(panel, choices=[str(year) for year in self._years])
        self._year_choice.SetName("Which year to report on")
        self._year_choice.SetHelpText(
            "This year or last year. The report below changes as soon as you choose."
        )
        self._year_choice.SetSelection(self._opening_year_index())
        year_row.Add(self._year_choice, 1, wx.EXPAND)
        root.Add(year_row, 0, wx.EXPAND | wx.ALL, 10)

        # Created immediately before the field: the association is by creation
        # order, so the "Year:" label belongs to the combo after it and this
        # field, carrying only a SetName, announced as a bare read-only "edit".
        report_label = wx.StaticText(panel, label="&Report:")
        self._report = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2)
        self._report.SetHelpText(
            "Your year in listening, in sentences. Read-only -- arrow through it "
            "line by line, or Copy takes the whole thing."
        )
        root.Add(report_label, 0, wx.LEFT | wx.RIGHT, 10)
        root.Add(self._report, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        copy_btn = wx.Button(panel, label="&Copy")
        copy_btn.SetHelpText("Puts the whole report on the clipboard.")
        save_btn = wx.Button(panel, label="&Save as Text...")
        save_btn.SetHelpText("Saves the report as a plain text file, to keep or send.")
        close_btn = wx.Button(panel, label="Close")
        close_btn.SetHelpText("Closes this window and returns to where you were.")
        from quill.ui.dialog_contract import bind_close_button

        bind_close_button(self.frame, close_btn, modeless=True)
        buttons.Add(copy_btn, 0, wx.RIGHT, 6)
        buttons.Add(save_btn, 0)
        buttons.AddStretchSpacer()
        buttons.Add(close_btn, 0)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)

        panel.SetSizer(root)
        self._year_choice.Bind(wx.EVT_CHOICE, lambda _e: self._refresh(speak=True))
        copy_btn.Bind(wx.EVT_BUTTON, lambda _e: self._copy())
        save_btn.Bind(wx.EVT_BUTTON, lambda _e: self._save())
        self.frame.CentreOnParent()
        self._refresh()

    def focus_target(self) -> Any:
        # Focus on the thing this window is for, not on whatever control happens
        # to come first in it (qc.md 6b: eight windows landed on a filter or a
        # chooser).
        return self._report

    def refresh(self) -> None:
        """Raised again: re-read the sessions, keeping the chosen year."""
        if self._reload is not None:
            self._sessions, self._titles = self._reload()
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
            self.frame,
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
        from quill.ui.outcome_report import report_outcome

        report_outcome(
            self, "Save Year in Review", f"Saved to {Path(destination).name}.", path=destination
        )


def open_year_in_review(
    stats_window: Any, *, focus: bool = True, opener: Any = None
) -> YearInReviewWindow:
    """Open, or raise, the review over whatever the statistics window is holding."""
    from quill.ui.podcasts.peer_window import open_peer

    host = getattr(stats_window, "_host", None) or stats_window

    def _current() -> tuple[list[Any], dict[str, str]]:
        return list(stats_window._sessions), dict(stats_window._show_titles)

    def _make(_owner: Any) -> YearInReviewWindow:
        sessions, titles = _current()
        return YearInReviewWindow(
            getattr(host, "frame", None) or stats_window.frame,
            sessions=sessions,
            show_titles=titles,
            announce_cb=stats_window._announce,
            reload=_current,
        )

    window: YearInReviewWindow = open_peer(
        host, "_year_review_window", _make, focus=focus, opener=opener
    )
    return window
