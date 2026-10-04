"""Search YouTube with Filters...: the words, then YouTube's own filters, then Browse.

**Video > YouTube > Search YouTube with Filters...** (Ctrl+Alt+Shift+0) asks
for the words and, in the same dialog, what YouTube's Filters menu offers --
type (videos, live now, playlists, channels), upload date, length, sort order
-- or YouTube Music songs instead. The answer lands in Browse Stations' Search
Results branch, exactly where Search YouTube... puts its rows, so every row
plays, opens and has its usual menu.
"""

from __future__ import annotations

from typing import Any

from quill.core.radio import youtube_search_filters as sf

TITLE = "Search YouTube with Filters"


def ask_filters(app: Any) -> tuple[str, sf.Filters] | None:
    """The dialog. ``None`` when cancelled or left empty."""
    import wx

    dialog = wx.Dialog(app.frame, title=TITLE)
    sizer = wx.BoxSizer(wx.VERTICAL)
    grid = wx.FlexGridSizer(cols=2, vgap=6, hgap=8)

    def _label(text: str) -> None:
        grid.Add(wx.StaticText(dialog, label=text), 0, wx.ALIGN_CENTER_VERTICAL)

    _label("&Search for:")
    words = wx.TextCtrl(dialog, size=(320, -1))
    words.SetName("Search for")
    words.SetHelpText("The words to search YouTube for, as you would type them on YouTube.")
    grid.Add(words, 1, wx.EXPAND)
    _label("S&ource:")
    source = wx.Choice(dialog, choices=[label for _v, label in sf.SOURCES])
    source.SetName("Source")
    source.SetHelpText(
        "YouTube, or YouTube Music's songs. With YouTube Music the filters below do not apply."
    )
    grid.Add(source, 1, wx.EXPAND)
    _label("&Type:")
    kind = wx.Choice(dialog, choices=[label for _v, label in sf.TYPES])
    kind.SetName("Type")
    kind.SetHelpText("Videos, only what is live right now, playlists, or channels.")
    grid.Add(kind, 1, wx.EXPAND)
    _label("&Uploaded:")
    date = wx.Choice(dialog, choices=[label for _v, label in sf.DATES])
    date.SetName("Uploaded")
    date.SetHelpText("Only what was uploaded within this time. Any time is no filter.")
    grid.Add(date, 1, wx.EXPAND)
    _label("&Length:")
    length = wx.Choice(dialog, choices=[label for _v, label in sf.DURATIONS])
    length.SetName("Length")
    length.SetHelpText("Only videos of this length. Any length is no filter.")
    grid.Add(length, 1, wx.EXPAND)
    _label("So&rt by:")
    sort = wx.Choice(dialog, choices=[label for _v, label in sf.SORTS])
    sort.SetName("Sort by")
    sort.SetHelpText("The order YouTube puts the answers in. Relevance is YouTube's usual order.")
    grid.Add(sort, 1, wx.EXPAND)
    for choice in (source, kind, date, length, sort):
        choice.SetSelection(0)
    sizer.Add(grid, 0, wx.ALL | wx.EXPAND, 10)
    sizer.Add(dialog.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL), 0, wx.ALL | wx.EXPAND, 10)
    dialog.SetSizerAndFit(sizer)
    try:
        if app._show_modal_dialog(dialog, TITLE) != wx.ID_OK:
            return None
        text = words.GetValue().strip()
        filters = sf.Filters(
            source=sf.SOURCES[max(0, source.GetSelection())][0],
            kind=sf.TYPES[max(0, kind.GetSelection())][0],
            upload_date=sf.DATES[max(0, date.GetSelection())][0],
            duration=sf.DURATIONS[max(0, length.GetSelection())][0],
            sort=sf.SORTS[max(0, sort.GetSelection())][0],
        )
    finally:
        dialog.Destroy()
    return (text, filters) if text else None


def search_with_filters(app: Any) -> None:
    """The command: ask, open Browse Stations, search off-thread, show the rows."""
    if bool(getattr(app, "_safe_mode", False)):
        app._announce("YouTube is not available in Safe Mode.")
        return
    from quill.ui.radio.youtube_ui import ask_youtube_consent

    if hasattr(app, "_radio_history") and not ask_youtube_consent(app):
        return
    asked = ask_filters(app)
    if asked is None:
        return
    text, filters = asked
    opener = getattr(app, "open_browse_stations", None)
    dialog = opener() if callable(opener) else None
    dialog = dialog or getattr(app, "_radio_browse_dialog", None)
    if dialog is None or not getattr(dialog, "_tree", None):
        app._announce("Browse Stations could not be opened, so YouTube was not searched.")
        return
    app._wx.CallAfter(run_in_tree, dialog, text, filters)


def run_in_tree(dialog: Any, text: str, filters: sf.Filters) -> None:
    from quill.core.radio.federated_browse import FederatedBrowse
    from quill.core.radio.youtube_search import TYPE_LABELS, to_node
    from quill.ui.radio import browse_feedback, browse_search_all

    dialog._announce(f"Searching YouTube for {text}, {filters.describe()}...")
    browse_feedback.start_search_notice(dialog, "YouTube", text)

    def _work(**_kwargs: Any) -> object:
        return sf.search(text, filters)

    def _ok(_op: str, found: object) -> None:
        browse_feedback.stop_search_notice(dialog)
        results = list(found) if isinstance(found, list) else []
        merged = FederatedBrowse()
        merged.asked.append("YouTube")
        if results:
            merged.counts[TYPE_LABELS.get(filters.result_kind, "Video")] = len(results)
        merged.rows.extend(to_node(result) for result in results)
        browse_search_all.show_results(dialog, text, merged)

    def _bad(_op: str, error: BaseException) -> None:
        from quill.core.radio.youtube_requests import plain
        from quill.ui.radio.youtube_account_ui import record_problem

        browse_feedback.stop_search_notice(dialog)
        reason = plain(error)
        record_problem(f"Search YouTube for {text}", reason)
        if getattr(dialog, "_tree", None):
            # announce-punctuation: exempt -- each part is a whole sentence
            dialog._announce(f"YouTube could not be searched. {reason}")

    dialog._task_manager.submit("radio-youtube-filtered", _work, on_success=_ok, on_failure=_bad)


__all__ = ["TITLE", "ask_filters", "run_in_tree", "search_with_filters"]
