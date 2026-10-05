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
from typing import Any

from quill.core.podcasts import stats


def format_report(
    summary: stats.StatsSummary,
    *,
    show_titles: dict[str, str] | None = None,
    max_shows: int = 20,
    streak_line: str = "",
) -> str:
    """The whole report as plain text -- the dialog's content, and the thing
    Copy puts on the clipboard.

    *streak_line* is passed in already decided, and is empty unless the
    listener has switched streaks on. A streak is a nudge; a nudge nobody asked
    for is pressure, so this function never works one out for itself.
    """
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
    if streak_line:
        lines.append(streak_line)
    if summary.saved_by_speed_seconds >= 1 or summary.saved_by_trim_seconds >= 1:
        lines.append(
            f"Content covered in total: {stats.format_duration(summary.total_with_savings_seconds)}"
        )
    lines.append("")
    if summary.shows:
        lines.append("By podcast, most listened first:")
        for index, total in enumerate(summary.shows[:max_shows], start=1):
            name = titles.get(total.show_id) or "(no longer followed)"
            lines.append(
                f"{index}. {name}: {stats.format_duration(total.seconds)}, "
                f"{total.completed} finished"
            )
        hidden = len(summary.shows) - max_shows
        if hidden > 0:
            lines.append(f"...and {hidden} more podcast(s). Export CSV for the full list.")
    return "\n".join(lines).rstrip() + "\n"


class PodcastStatsWindow:
    """A read-only, arrow-navigable listening report, as a peer window.

    A peer rather than a dialog (qc.md section 6, Phase 4): the report is
    something to keep open beside the library and come back to, so it is made
    once, raised and refreshed when asked for again, and Escape hides it and
    returns focus to whatever opened it (``peer_window``).
    """

    TITLE = "Listening Statistics"
    MENU_TITLE = "Statis&tics"

    def __init__(
        self,
        parent: object,
        *,
        sessions: list[stats.ListeningSession],
        show_titles: dict[str, str] | None = None,
        announce_cb: Callable[[str], None] | None = None,
        on_clear: Callable[[], int] | None = None,
        streaks_enabled: bool = False,
        reload: Callable[[], tuple[list[stats.ListeningSession], dict[str, str], bool]]
        | None = None,
        host: Any = None,
    ) -> None:
        import wx

        self._wx = wx
        self._host = host
        self._sessions = sessions
        self._show_titles = show_titles or {}
        self._announce = announce_cb or (lambda _m: None)
        self._on_clear = on_clear
        self._reload = reload
        # Opt-in, and off unless the listener asked. See _streak_line.
        self._streaks_enabled = streaks_enabled

        self.frame = wx.Frame(parent, title="Listening Statistics", size=(620, 560))
        self.frame.SetMinSize((580, 520))
        panel = wx.Panel(self.frame, style=wx.TAB_TRAVERSAL)
        root = wx.BoxSizer(wx.VERTICAL)

        period_row = wx.BoxSizer(wx.HORIZONTAL)
        period_row.Add(
            wx.StaticText(panel, label="&Period:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6
        )
        self._period_choice = wx.Choice(
            panel, choices=[label for _pid, label, _days in stats.PERIODS]
        )
        self._period_choice.SetName("Which period the statistics cover")
        self._period_choice.SetHelpText(
            "Which stretch of time the report covers. The report below changes as "
            "soon as you choose."
        )
        self._period_choice.SetSelection(len(stats.PERIODS) - 1)
        period_row.Add(self._period_choice, 1, wx.EXPAND)
        root.Add(period_row, 0, wx.EXPAND | wx.ALL, 10)

        # Created immediately before the field, because that adjacency in
        # creation order is the accessible name on wxMSW. The "Period:" label
        # above names the combo that follows it and nothing else, so this field
        # had only a SetName and announced as a bare read-only "edit".
        report_label = wx.StaticText(panel, label="Listening &report:")
        self._report = wx.TextCtrl(
            panel,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2 | wx.BORDER_SIMPLE,
        )
        self._report.SetHelpText(
            "Your listening figures for the chosen period. Read-only -- arrow "
            "through it line by line, or Copy takes the whole thing."
        )
        root.Add(report_label, 0, wx.LEFT | wx.RIGHT, 10)
        root.Add(self._report, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        copy_btn = wx.Button(panel, label="&Copy")
        copy_btn.SetName("Copy the whole report to the clipboard")
        copy_btn.SetHelpText("Puts the whole report on the clipboard.")
        export_btn = wx.Button(panel, label="&Export CSV...")
        export_btn.SetName("Save every listening session as a CSV file")
        export_btn.SetHelpText("Saves every listening session as a CSV file, for a spreadsheet.")
        year_btn = wx.Button(panel, label="&Year in Review...")
        year_btn.SetName("A few sentences about your listening year, to read or keep")
        year_btn.SetHelpText(
            "Opens Year in Review: a few sentences about your listening year, to "
            "read or keep. It opens beside this window."
        )
        clear_btn = wx.Button(panel, label="Clear &Statistics...")
        clear_btn.SetName("Delete the whole listening log")
        clear_btn.SetHelpText(
            "Deletes the whole listening log, after asking. Nothing else about your "
            "library changes."
        )
        clear_btn.Enable(on_clear is not None)
        close_btn = wx.Button(panel, label="Close")
        close_btn.SetHelpText("Closes this window and returns to where you were.")
        from quill.ui.dialog_contract import bind_close_button

        bind_close_button(self.frame, close_btn, modeless=True)
        btn_row.Add(copy_btn, 0, wx.RIGHT, 6)
        btn_row.Add(export_btn, 0, wx.RIGHT, 6)
        btn_row.Add(year_btn, 0, wx.RIGHT, 6)
        btn_row.Add(clear_btn, 0, wx.RIGHT, 6)
        btn_row.AddStretchSpacer()
        btn_row.Add(close_btn)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)

        panel.SetSizer(root)
        self._period_choice.Bind(wx.EVT_CHOICE, lambda _e: self._refresh(announce=True))
        copy_btn.Bind(wx.EVT_BUTTON, self._on_copy)
        export_btn.Bind(wx.EVT_BUTTON, self._on_export)
        year_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_year_in_review())
        clear_btn.Bind(wx.EVT_BUTTON, self._on_clear_click)
        self.frame.CentreOnParent()
        self._refresh()

    def focus_target(self) -> Any:
        # Focus on the thing this window is for, not on whatever control happens
        # to come first in it (qc.md 6b: eight windows landed on a filter or a
        # chooser).
        return self._report

    def refresh(self) -> None:
        """Raised again: read the log afresh, keeping the chosen period."""
        if self._reload is not None:
            self._sessions, self._show_titles, self._streaks_enabled = self._reload()
        self._refresh()

    def _period_id(self) -> str:
        index = max(0, self._period_choice.GetSelection())
        return stats.PERIODS[index][0]

    def _streak_line(self) -> str:
        """The streak sentence, or "" -- opt-in, and off unless asked for.

        A streak is a nudge, and a nudge nobody asked for is pressure. Nobody
        opening a statistics window to see how much they listened should be
        told how many days in a row they have managed.
        """
        if not getattr(self, "_streaks_enabled", False):
            return ""
        from quill.core.podcasts.year_in_review import streaks

        return streaks(self._sessions).describe()

    def _refresh(self, *, announce: bool = False) -> None:
        summary = stats.summarize(self._sessions, period=self._period_id())
        text = format_report(
            summary, show_titles=self._show_titles, streak_line=self._streak_line()
        )
        self._report.SetValue(text)
        self._report.SetInsertionPoint(0)
        if announce:
            self._announce(
                f"{summary.period_label}: {stats.format_duration(summary.total_seconds)} listened"
            )

    def _on_year_in_review(self) -> None:
        """The year as a paragraph -- see ui/podcasts/year_review_dialog."""
        from quill.ui.podcasts.year_review_dialog import open_year_in_review

        open_year_in_review(self)

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
            self.frame,
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
        from quill.ui.outcome_report import report_outcome

        report_outcome(
            self,
            "Export Listening Statistics",
            f"Exported {len(self._sessions)} session(s) to {path.name}.",
            path=path,
        )

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
            self.frame,
            announce=self._announce,
        )
        if answer != wx.YES:
            return
        self._on_clear()
        self._sessions = []
        self._refresh()


def _load(host: Any) -> tuple[list[stats.ListeningSession], dict[str, str], bool]:
    """(sessions, show titles, streaks switched on) as the host has them now."""
    from quill.core.paths import app_data_dir

    library = host._podcast_library
    return (
        stats.load_sessions(app_data_dir()),
        {show.id: show.title for show in library.shows},
        bool(getattr(library.settings, "stats_streaks_enabled", False)),
    )


def open_statistics_window(
    host: Any, *, focus: bool = True, opener: Any = None
) -> PodcastStatsWindow:
    """Open, or raise and refresh, the host's Listening Statistics window."""
    from quill.ui.podcasts.peer_window import open_peer

    def _make(owner: Any) -> PodcastStatsWindow:
        sessions, titles, streaks_on = _load(owner)
        return PodcastStatsWindow(
            owner.frame,
            sessions=sessions,
            show_titles=titles,
            announce_cb=owner._announce,
            on_clear=owner._podcast_clear_statistics,
            streaks_enabled=streaks_on,
            reload=lambda: _load(owner),
            host=owner,
        )

    window: PodcastStatsWindow = open_peer(
        host, "_podcast_stats_window", _make, focus=focus, opener=opener
    )
    return window
