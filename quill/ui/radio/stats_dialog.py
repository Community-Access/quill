"""Listening Statistics for Quill Radio: how long, on what, in what.

A Radio-shaped window rather than Cast's with rows suppressed. Suppression would
mean editing a Cast dialog to serve Radio -- the exact dependency the Radio-first
release order exists to avoid -- and the suppressed version is *more* code than
the honest one, because every hidden row is a condition.

**One read-only text box, not a grid.** Everything here is a short sentence, and
a two-column table read aloud is two columns to arrow across for information
that fits on one line. The listener arrows through the text the way they would
through any other document.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.media_stats import PERIODS
from quill.ui.dialog_contract import apply_modal_ids

TITLE = "Listening Statistics"


class RadioStatsDialog:
    """Totals by station and by network, for a period the listener chooses."""

    def __init__(
        self,
        parent: object,
        *,
        data_dir: Any,
        station_names: dict[str, str] | None = None,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._data_dir = data_dir
        self._names = station_names or {}
        self._announce = announce_cb or (lambda _m: None)

        self.dialog = wx.Dialog(
            parent, title=TITLE, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize((560, 480))
        root = wx.BoxSizer(wx.VERTICAL)

        period_row = wx.BoxSizer(wx.HORIZONTAL)
        period_row.Add(
            wx.StaticText(self.dialog, label="&Period:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self._period = wx.Choice(self.dialog, choices=[label for _pid, label, _d in PERIODS])
        self._period.SetName("How far back to total")
        self._period.SetSelection(len(PERIODS) - 1)
        period_row.Add(self._period, 1, wx.EXPAND)
        root.Add(period_row, 0, wx.EXPAND | wx.ALL, 10)

        self._report = wx.TextCtrl(
            self.dialog, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2
        )
        self._report.SetName("Your listening, by station and by network")
        root.Add(self._report, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        copy_btn = wx.Button(self.dialog, label="&Copy")
        export_btn = wx.Button(self.dialog, label="&Save as CSV...")
        clear_btn = wx.Button(self.dialog, label="&Delete My History...")
        clear_btn.SetName("Remove every listening session Quill Radio has recorded")
        close_btn = wx.Button(self.dialog, wx.ID_CANCEL, "C&lose")
        for widget in (copy_btn, export_btn, clear_btn):
            buttons.Add(widget, 0, wx.RIGHT, 6)
        buttons.AddStretchSpacer()
        buttons.Add(close_btn, 0)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizer(root)

        self._period.Bind(wx.EVT_CHOICE, lambda _e: self._refresh(speak=True))
        copy_btn.Bind(wx.EVT_BUTTON, lambda _e: self._copy())
        export_btn.Bind(wx.EVT_BUTTON, lambda _e: self._export())
        clear_btn.Bind(wx.EVT_BUTTON, lambda _e: self._clear())
        self._refresh()

    # -- content ---------------------------------------------------------

    def _period_id(self) -> str:
        index = max(0, self._period.GetSelection())
        return PERIODS[index][0]

    def _refresh(self, *, speak: bool = False) -> None:
        from quill.core.radio import stats

        summary = stats.summarize(self._data_dir, period=self._period_id())
        lines = stats.describe(summary, self._names)
        self._report.SetValue("\n".join(lines))
        if speak:
            self._announce(lines[1] if len(lines) > 1 else lines[0])

    def _copy(self) -> None:
        wx = self._wx
        text = self._report.GetValue()
        if not text:
            return
        if wx.TheClipboard.Open():
            try:
                wx.TheClipboard.SetData(wx.TextDataObject(text))
            finally:
                wx.TheClipboard.Close()
            self._announce("Copied.")

    def _export(self) -> None:
        wx = self._wx
        from quill.core import media_stats
        from quill.core.radio import stats

        sessions = stats.load_sessions(self._data_dir)
        if not sessions:
            self._announce("There is nothing to save yet.")
            return
        with wx.FileDialog(
            self.dialog,
            "Save listening history",
            defaultFile="quill-radio-listening.csv",
            wildcard="CSV file (*.csv)|*.csv|All files (*.*)|*.*",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as file_dialog:
            if file_dialog.ShowModal() != wx.ID_OK:
                return
            destination = file_dialog.GetPath()
        from pathlib import Path

        try:
            Path(destination).write_text(
                media_stats.to_csv(
                    sessions,
                    titles=self._names,
                    key_header="Station",
                    item_header="Programme",
                ),
                encoding="utf-8",
            )
        except OSError as error:
            self._announce(f"Could not save that file: {error}.")
            return
        self._announce(f"Saved {len(sessions)} sessions to {Path(destination).name}.")

    def _clear(self) -> None:
        wx = self._wx
        from quill.ui.dialog_contract import show_message_box

        # Confirmed, because it is the one action here that cannot be undone
        # and there is no other copy of this history anywhere. NO_DEFAULT for
        # the same reason: somebody pressing Enter reflexively on a dialog they
        # have not finished hearing must not lose their history by doing so.
        answer = show_message_box(
            "Delete every listening session Quill Radio has recorded? This cannot be undone.",
            "Delete My History",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
            self.dialog,
            announce=self._announce,
        )
        if answer != wx.YES:
            return
        from quill.core.radio import stats

        removed = stats.clear_sessions(self._data_dir)
        self._refresh()
        self._announce(
            f"Deleted {removed} session{'' if removed == 1 else 's'}."
            if removed
            else "There was nothing to delete."
        )

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


def open_for_host(host: Any) -> None:
    """Listening Statistics..., opened from a Radio frame.

    Here rather than on the frame because everything it needs can be handed to
    it -- the data folder, the favorites store for the station names, and a
    voice -- and ``main_frame_radio`` is at its GATE-11 ceiling.
    """
    from quill.core.paths import app_data_dir

    store = getattr(host, "_radio_favorites", None)
    names = (
        {favorite.key: favorite.display_label for favorite in store.favorites}
        if store is not None
        else {}
    )
    RadioStatsDialog(
        getattr(host, "frame", None) or host,
        data_dir=app_data_dir(),
        station_names=names,
        announce_cb=getattr(host, "_announce", None),
    ).show()
