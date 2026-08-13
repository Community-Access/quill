"""Episode > Listening Statistics... -- how much you listened, and to what.

Shaped after the Player Information dialog, which is already the right answer
for a report a screen-reader user needs to review: one read-only multiline
field you arrow through line by line, select from, and copy. No chart, no
grid, no tab order to negotiate -- the text is the report, not a caption for
a picture of it.

Durations are words, not clock faces. ``3:47:00`` is read as a time of day;
"3 hours, 47 minutes" is read as a length, which is what it is.

One number is deliberately missing unless it is real. Time saved by Smart
Speed appears only when the silence-trimming path actually reported what it
dropped -- an invented figure would flatter the feature and mislead the
listener, so an unmeasured saving is an absent line rather than a confident
zero.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from quill.core.podcasts import stats
from quill.ui.dialog_contract import apply_modal_ids


def format_report(
    summary: stats.StatsSummary,
    *,
    show_titles: dict[str, str] | None = None,
    max_shows: int = 20,
) -> str:
    """The whole report as plain text -- the dialog's content, and the thing
    Copy puts on the clipboard."""
    titles = show_titles or {}
    lines = [f"Listening statistics -- {summary.period_label}", ""]
    if not summary.sessions:
        lines.append(
            "Nothing recorded yet for this period. Statistics start counting the "
            "first time you play an episode."
        )
        return "\n".join(lines) + "\n"
    lines.append(f"Time listened: {stats.format_duration(summary.total_seconds)}")
    if summary.saved_by_speed_seconds >= 1:
        lines.append(
            f"Extra content from faster playback: "
            f"{stats.format_duration(summary.saved_by_speed_seconds)}"
        )
    if summary.trim_measured and summary.saved_by_trim_seconds >= 1:
        lines.append(
            f"Time saved by trimming silence: "
            f"{stats.format_duration(summary.saved_by_trim_seconds)}"
        )
    lines.append(f"Episodes finished: {summary.episodes_completed}")
    lines.append(f"Listening sessions: {summary.sessions}")
    if summary.saved_by_speed_seconds >= 1 or summary.saved_by_trim_seconds >= 1:
        lines.append(
            f"Content covered in total: {stats.format_duration(summary.total_with_savings_seconds)}"
        )
    lines.append("")
    if summary.shows:
        lines.append("By podcast, most listened first:")
        for index, total in enumerate(summary.shows[:max_shows], start=1):
            name = titles.get(total.show_id) or "(no longer subscribed)"
            lines.append(
                f"{index}. {name}: {stats.format_duration(total.seconds)}, "
                f"{total.completed} finished"
            )
        hidden = len(summary.shows) - max_shows
        if hidden > 0:
            lines.append(f"...and {hidden} more podcast(s). Export CSV for the full list.")
    return "\n".join(lines).rstrip() + "\n"


class PodcastStatsDialog:
    """A read-only, arrow-navigable listening report."""

    def __init__(
        self,
        parent: object,
        *,
        sessions: list[stats.ListeningSession],
        show_titles: dict[str, str] | None = None,
        announce_cb: Callable[[str], None] | None = None,
        on_clear: Callable[[], int] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._sessions = sessions
        self._show_titles = show_titles or {}
        self._announce = announce_cb or (lambda _m: None)
        self._on_clear = on_clear

        self.dialog = wx.Dialog(
            parent,
            title="Listening Statistics",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize((580, 520))
        root = wx.BoxSizer(wx.VERTICAL)

        period_row = wx.BoxSizer(wx.HORIZONTAL)
        period_row.Add(
            wx.StaticText(self.dialog, label="&Period:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6
        )
        self._period_choice = wx.Choice(
            self.dialog, choices=[label for _pid, label, _days in stats.PERIODS]
        )
        self._period_choice.SetName("Which period the statistics cover")
        self._period_choice.SetSelection(len(stats.PERIODS) - 1)
        period_row.Add(self._period_choice, 1, wx.EXPAND)
        root.Add(period_row, 0, wx.EXPAND | wx.ALL, 10)

        self._report = wx.TextCtrl(
            self.dialog,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2 | wx.BORDER_SIMPLE,
        )
        self._report.SetName("Listening report; arrow through it line by line")
        root.Add(self._report, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        copy_btn = wx.Button(self.dialog, label="&Copy")
        copy_btn.SetName("Copy the whole report to the clipboard")
        export_btn = wx.Button(self.dialog, label="&Export CSV...")
        export_btn.SetName("Save every listening session as a CSV file")
        clear_btn = wx.Button(self.dialog, label="Clear &Statistics...")
        clear_btn.SetName("Delete the whole listening log")
        clear_btn.Enable(on_clear is not None)
        close_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Close")
        btn_row.Add(copy_btn, 0, wx.RIGHT, 6)
        btn_row.Add(export_btn, 0, wx.RIGHT, 6)
        btn_row.Add(clear_btn, 0, wx.RIGHT, 6)
        btn_row.AddStretchSpacer()
        btn_row.Add(close_btn)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizer(root)
        self._period_choice.Bind(wx.EVT_CHOICE, lambda _e: self._refresh(announce=True))
        copy_btn.Bind(wx.EVT_BUTTON, self._on_copy)
        export_btn.Bind(wx.EVT_BUTTON, self._on_export)
        clear_btn.Bind(wx.EVT_BUTTON, self._on_clear_click)
        self._refresh()

    def show(self) -> None:
        self.dialog.CentreOnParent()
        apply_modal_ids(self.dialog, cancel_id=self._wx.ID_CANCEL, escape_id=self._wx.ID_CANCEL)
        from quill.ui.dialog_contract import show_modal_dialog

        try:
            show_modal_dialog(self.dialog, "Listening Statistics", announce=self._announce)
        finally:
            self.dialog.Destroy()

    def _period_id(self) -> str:
        index = max(0, self._period_choice.GetSelection())
        return stats.PERIODS[index][0]

    def _refresh(self, *, announce: bool = False) -> None:
        summary = stats.summarize(self._sessions, period=self._period_id())
        text = format_report(summary, show_titles=self._show_titles)
        self._report.SetValue(text)
        self._report.SetInsertionPoint(0)
        if announce:
            self._announce(
                f"{summary.period_label}: {stats.format_duration(summary.total_seconds)} listened"
            )

    def _on_copy(self, _event: object) -> None:
        wx = self._wx
        if wx.TheClipboard.Open():
            try:
                wx.TheClipboard.SetData(wx.TextDataObject(self._report.GetValue()))
            finally:
                wx.TheClipboard.Close()
        self._announce("Report copied to the clipboard")

    def _on_export(self, _event: object) -> None:
        wx = self._wx
        with wx.FileDialog(  # dialog_button_contract: exempt
            self.dialog,
            "Export Listening Statistics",
            defaultFile="listening-statistics.csv",
            wildcard="CSV files (*.csv)|*.csv|All files (*.*)|*.*",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return
            path = Path(dialog.GetPath())
        try:
            path.write_text(
                stats.to_csv(self._sessions, show_titles=self._show_titles),
                encoding="utf-8",
                newline="",
            )
        except OSError as error:
            self._announce(f"Could not export the statistics: {error}")
            return
        self._announce(f"Exported {len(self._sessions)} session(s) to {path.name}")

    def _on_clear_click(self, _event: object) -> None:
        from quill.ui.dialog_contract import show_message_box

        wx = self._wx
        if self._on_clear is None:
            return
        answer = show_message_box(
            f"Delete all {len(self._sessions)} recorded listening session(s)? "
            "This only clears the statistics; nothing else about your library changes.",
            "Clear Statistics",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
            self.dialog,
            announce=self._announce,
        )
        if answer != wx.YES:
            return
        self._on_clear()
        self._sessions = []
        self._refresh()
