"""Radio's live lists stay still (FUX-06).

The Recordings window refreshes every two seconds and Find Stations fills from
answers that arrive whenever the network sends them. Neither may move the
reader, select a second row behind their back, or let an out-of-date answer
replace a newer one.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

from quill.core.media.list_columns import ColumnLayouts
from quill.core.radio.list_columns import SURFACES
from quill.core.radio.models import RadioStation
from quill.core.radio.recording import RecordingSettings
from quill.core.radio.recordings_index import STATUS_RECORDING, STATUS_SCHEDULED, RecordingEntry
from quill.ui.list_stay_still import capture_report, follow_report
from quill.ui.media.list_columns_view import set_row
from quill.ui.radio import library_search
from quill.ui.radio.recordings_manager_dialog import RecordingsManagerDialog
from quill.ui.radio.recordings_row_view import SURFACE as RECORDINGS
from quill.ui.radio.results_view import SURFACE as RESULTS
from quill.ui.radio.station_browser_dialog import _CATEGORIES, _SEARCH_RESULTS, StationBrowserDialog
from tests.unit.ui.report_list_fake import WX, FakeReportList

# -- the shared pieces --------------------------------------------------------------


def test_follow_report_moves_the_one_selection_to_the_readers_item() -> None:
    rows = FakeReportList()
    rows.fill(["b", "c"])
    rows.Select(0)
    rows.Focus(0)
    anchor = capture_report(rows)
    rows.InsertItem(0, "a")  # an arrival above: the native item moves down with its state
    assert follow_report(WX, rows, anchor, ["a", "b", "c"], "b") is True
    assert rows.selected_rows() == [1] and rows.focused_row() == 1
    assert rows.took_focus is False


def test_set_row_writes_only_the_cells_that_changed() -> None:
    rows = FakeReportList()
    rows.fill(["Show"])
    columns = ColumnLayouts.defaults(SURFACES).columns(RECORDINGS)
    set_row(rows, 0, columns, {"name": "Show", "status": "Recording"})
    rows.set_calls.clear()
    set_row(rows, 0, columns, {"name": "Show", "status": "Recording"})
    assert rows.set_calls == []


# -- the download queue -------------------------------------------------------------------


class _ListBox:
    """A single-selection list box that keeps each row's own identity."""

    def __init__(self) -> None:
        self.rows: list[list[str]] = []
        self.selection = -1
        self.set_selections: list[int] = []

    def GetSelection(self) -> int:  # noqa: N802
        return self.selection

    def GetString(self, row: int) -> str:  # noqa: N802
        return self.rows[row][0]

    def SetString(self, row: int, text: str) -> None:  # noqa: N802
        self.rows[row][0] = text

    def Insert(self, text: str, row: int) -> None:  # noqa: N802
        self.rows.insert(row, [text])
        if 0 <= row <= self.selection:
            self.selection += 1

    def Delete(self, row: int) -> None:  # noqa: N802
        del self.rows[row]
        if row == self.selection:
            self.selection = -1
        elif row < self.selection:
            self.selection -= 1

    def SetSelection(self, row: int) -> None:  # noqa: N802
        self.set_selections.append(row)
        self.selection = row

    def Set(self, _labels: list[str]) -> None:  # noqa: N802 - must never be called
        raise AssertionError("a full refill drops the reader at the top")


def _downloads(queue: Any) -> Any:
    from quill.ui.radio.download_queue_dialog import DownloadQueueDialog

    dlg = DownloadQueueDialog.__new__(DownloadQueueDialog)
    dlg._queue = queue
    dlg._rows = []
    dlg._list = _ListBox()
    for name in ("_heading", "_surface", "_dialog"):
        setattr(dlg, name, SimpleNamespace(SetLabel=lambda _s: None, Layout=lambda: None))
    dlg._sync_buttons = lambda: None
    return dlg


def test_a_finished_download_cleared_above_keeps_the_reader_on_theirs() -> None:
    from quill.core.radio.download_queue import DownloadQueue

    queue = DownloadQueue()
    first, second, third = (queue.add(SimpleNamespace(name=n), ".") for n in "ABC")
    dlg = _downloads(queue)
    dlg.refresh()
    dlg._list.SetSelection(2)
    dlg._list.set_selections.clear()
    queue.remove(first)
    dlg.refresh()
    assert dlg.selected() is third
    assert dlg._list.set_selections == []  # still the same row: nothing re-read
    queue.remove(third)
    dlg.refresh()
    assert dlg.selected() is second  # the neighbour, not the top


# -- Recordings ------------------------------------------------------------------------


def _recordings(entries: list[RecordingEntry]) -> tuple[Any, FakeReportList, list[str]]:
    rows = FakeReportList()
    dlg = RecordingsManagerDialog.__new__(RecordingsManagerDialog)
    dlg._wx = WX
    dlg._list = rows
    dlg._settings = RecordingSettings(destination_root=".")
    dlg._columns = ColumnLayouts.defaults(SURFACES).columns(RECORDINGS)
    dlg._entries = []
    dlg._status = SimpleNamespace(SetLabel=lambda _s: None)
    dlg._on_selection_changed = lambda: None
    dlg._advance_queue_if_finished = lambda: None
    dlg._active_recordings = lambda: []
    dlg._scheduler = SimpleNamespace(entries=[])
    said: list[str] = []
    dlg._announce = said.append
    dlg.snapshot = list(entries)
    return dlg, rows, said


def _refresh(dlg: Any, entries: list[RecordingEntry], **kwargs: Any) -> None:
    import quill.ui.radio.recordings_manager_dialog as module

    original = module.list_recordings
    module.list_recordings = lambda *_a, **_k: list(entries)
    try:
        dlg._refresh(**kwargs)
    finally:
        module.list_recordings = original


def _rec(name: str, status: str = "Recorded", ident: str = "") -> RecordingEntry:
    return RecordingEntry(id=ident or f"/r/{name}", name=name, status=status, path=Path(name))


def test_a_recording_starting_above_leaves_exactly_the_readers_row_selected() -> None:
    old, other = _rec("Old show"), _rec("Other")
    dlg, rows, said = _recordings([])
    _refresh(dlg, [old, other])
    rows.Select(1)  # the reader is on "Other"
    rows.Focus(1)
    _refresh(dlg, [_rec("Live", STATUS_RECORDING), old, other], say_gone=True)
    # Before FUX-06 row 1 stayed selected too, and Remove acted on "Old show".
    assert rows.selected_rows() == [2]
    assert dlg._selected().name == "Other"
    assert said == []


def test_a_shift_selection_and_the_row_the_cursor_is_on_both_survive_a_tick() -> None:
    a, b, c = _rec("A"), _rec("B"), _rec("C")
    dlg, rows, said = _recordings([])
    _refresh(dlg, [a, b, c])
    rows.Select(1)
    rows.Select(2)
    rows.Focus(2)  # the cursor is on C, the lower of the two
    _refresh(dlg, [_rec("Live", STATUS_RECORDING), a, b, c])
    assert rows.selected_rows() == [2, 3]
    assert rows.focused_row() == 3


def test_a_schedule_that_fires_takes_the_reader_to_its_recording_row() -> None:
    sched = _rec("Jazz Night", STATUS_SCHEDULED, ident="schedule:7")
    dlg, rows, said = _recordings([])
    _refresh(dlg, [_rec("Earlier"), sched])
    rows.Select(1)
    rows.Focus(1)
    _refresh(dlg, [_rec("Jazz Night", STATUS_RECORDING), _rec("Earlier")], say_gone=True)
    assert dlg._selected().status == STATUS_RECORDING
    assert said == []


def test_a_recording_removed_elsewhere_is_said_once_and_the_next_row_chosen() -> None:
    a, b, c = _rec("A"), _rec("B"), _rec("C")
    dlg, rows, said = _recordings([])
    _refresh(dlg, [a, b, c])
    rows.Select(1)
    rows.Focus(1)
    _refresh(dlg, [a, c], say_gone=True)
    assert dlg._selected().name == "C"
    assert said == ["B is no longer in the list."]
    _refresh(dlg, [a, c], say_gone=True)  # nothing changed: nothing said again
    assert said == ["B is no longer in the list."]


def test_a_removal_the_reader_made_is_not_announced_twice() -> None:
    a, b = _rec("A"), _rec("B")
    dlg, rows, said = _recordings([])
    _refresh(dlg, [a, b])
    rows.Select(0)
    _refresh(dlg, [b])  # Remove's own refresh; Remove says "Removed recording A."
    assert said == []


# -- Find Stations ------------------------------------------------------------------------


def _station(name: str, source: str = "") -> RadioStation:
    return RadioStation(name=name, stream_url=f"https://example.com/{name}", source=source)


class _Choice:
    def __init__(self, selection: int = 0, text: str = "All sources") -> None:
        self.selection, self.text = selection, text

    def GetSelection(self) -> int:  # noqa: N802
        return self.selection

    def GetStringSelection(self) -> str:  # noqa: N802
        return self.text


def _finder() -> Any:
    d = StationBrowserDialog.__new__(StationBrowserDialog)
    d._wx = WX
    d._results = FakeReportList()
    d._result_column_defs = ColumnLayouts.defaults(SURFACES).columns(RESULTS)
    d._source_facet = _Choice()
    d._category_list = _Choice(_CATEGORIES.index(_SEARCH_RESULTS))
    d._current_results = []
    d._all_results = []
    d._fill_status = ""
    for name in ("_status", "_details"):
        setattr(d, name, SimpleNamespace(SetLabel=lambda _s: None, SetValue=lambda _s: None))
    for name in ("_play_btn", "_favorite_btn", "_search_btn", "_more_btn"):
        setattr(d, name, SimpleNamespace(Enable=lambda _on: None))
    d._said = []
    d._announce = d._said.append
    d._row_values = lambda station: {"name": station.name, "source": station.source}
    d._show_category = lambda _cat: d._render_results()
    d._search_rb, d._search_extras, d._search_query = [], [], ""
    return d


def _show(d: Any, stations: list[RadioStation]) -> None:
    d._all_results = stations
    d._render_results()


def test_library_rows_arriving_keep_the_reader_on_the_same_native_row() -> None:
    d = _finder()
    first = [_station("Alpha"), _station("Bravo"), _station("Charlie")]
    _show(d, first)
    d._results.Select(0, on=False)
    d._results.Select(2)
    d._results.Focus(2)
    item = d._results.item(2)
    d._results.events.clear()
    d._all_results = [_station("Book", "LibriVox"), *first]
    d._search_results = d._all_results
    d._show_category_for_library_results()
    assert d._results.selected_rows() == [3]
    assert d._results.item(3) == item  # the same native row: nothing to re-read
    assert d._results.events == []


def test_library_rows_do_not_pull_the_reader_away_from_favorites() -> None:
    d = _finder()
    calls: list[str] = []
    d._show_category = calls.append
    d._category_list.selection = 0  # Favorites
    d._show_category_for_library_results()
    assert calls == []


def test_a_library_answer_for_an_older_search_is_dropped() -> None:
    d = _finder()
    d._task_manager = SimpleNamespace(submit=lambda *_a, **k: answers.append(k["on_success"]))
    d._safe_mode = False
    answers: list[Any] = []
    d._search_request = 1
    library_search._submit(d, "librivox", "dickens", 1)
    d._search_request = 2  # the listener searched again
    d._library_pending = 1
    answers[0]("op", [_station("Old Book", "LibriVox")])
    assert d._search_extras == []
    assert d._library_pending == 1


def test_a_late_search_answer_does_not_replace_the_newer_one() -> None:
    d = _finder()
    d._search_request = 2
    d._on_search_done(([_station("Stale")], []), None, 1)
    assert d._current_results == []


def test_a_source_filter_keeps_the_station_or_says_it_is_hidden() -> None:
    d = _finder()
    d._save_search_prefs = lambda: None
    stations = [_station("WNYC", "TuneIn"), _station("KEXP", "Radio Browser")]
    _show(d, stations)
    d._results.Select(0, on=False)
    d._results.Select(1)
    d._results.Focus(1)
    d._source_facet.text = "Radio Browser"
    d._apply_source_facet = lambda all_rows: [s for s in all_rows if s.source == "Radio Browser"]
    d._on_source_facet(None)
    assert d._current_results[d._results.GetFirstSelected()].name == "KEXP"
    assert "not shown" not in d._said[-1]
    d._results.Select(0, on=False)
    d._results.Select(0)
    d._apply_source_facet = lambda all_rows: [s for s in all_rows if s.source == "TuneIn"]
    d._on_source_facet(None)
    assert d._said[-1].endswith("KEXP is not shown with this filter.")


# -- the main window's Favorites tree ----------------------------------------------------


def test_the_favorites_tree_keeps_a_folder_and_a_closed_folder_and_lands_on_a_neighbour() -> None:
    import wx

    from quill.apps.radio_favorites_tree import RadioFavoritesTreeMixin, _tree_rows
    from quill.core.radio.favorites import RadioFavoritesStore
    from quill.core.radio.history import RadioHistory
    from tests.wx_session import shared_wx_app

    shared_wx_app()
    frame = wx.Frame(None)
    try:
        host = RadioFavoritesTreeMixin()
        host._favorites_tree = wx.TreeCtrl(frame, style=wx.TR_HIDE_ROOT | wx.TR_HAS_BUTTONS)
        store = RadioFavoritesStore()
        for name, folder in (("Alpha", ""), ("Bravo", ""), ("Charlie", ""), ("Jazz", "Music")):
            store.add(RadioStation(name=name, stream_url=f"https://x/{name}"), folder=folder)
        store.add_folder("Talk")
        host._radio_favorites = store
        host._radio_history = RadioHistory()
        tree = host._favorites_tree
        host._reload_favorites_tree()

        def select(data: tuple[str, str]) -> None:
            tree.SelectItem(next(item for d, item in _tree_rows(tree) if d == data))

        music = next(item for d, item in _tree_rows(tree) if d == ("folder", "Music"))
        tree.Collapse(music)
        select(("folder", "Talk"))
        host._reload_favorites_tree()
        # Before FUX-06 a folder was dropped for the first row, and every
        # folder opened again.
        assert host._selected_tree_data() == ("folder", "Talk")
        music = next(item for d, item in _tree_rows(tree) if d == ("folder", "Music"))
        assert not tree.IsExpanded(music)
        keys = [d for d, _item in _tree_rows(tree)]
        bravo = next(d for d in keys if d[0] == "station" and "Bravo" in d[1])
        select(bravo)
        after_bravo = keys[keys.index(bravo) + 1]
        store.remove(bravo[1])  # removed from another window
        host._reload_favorites_tree()
        assert host._selected_tree_data() == after_bravo
        # A save that changed nothing (radio.py saves and then reloads again)
        # leaves the tree alone: the reader's row is not destroyed and re-read.
        item = tree.GetSelection()
        host._reload_favorites_tree()
        assert tree.GetSelection() == item
    finally:
        frame.Destroy()


# -- the Media Player's bookmarks ----------------------------------------------------------


def test_media_player_bookmarks_keep_the_reader_through_add_edit_and_remove(
    tmp_path: Path,
) -> None:
    from quill.apps.player_bookmarks import PlayerBookmarksMixin
    from quill.core.media.bookmarks import BookmarkStore

    host = PlayerBookmarksMixin()
    host._bookmarks = BookmarkStore(tmp_path / "marks.json")
    host._book_key = "book"
    host._bookmarks_list = _ListBox()
    for position in (1000, 2000, 3000):
        host._bookmarks.add("book", position)
    host._refresh_bookmarks()
    host._bookmarks_list.SetSelection(1)  # the 2 second mark
    host._bookmarks.add("book", 500)  # a new mark above
    host._refresh_bookmarks()
    assert host._selected_bookmark().position_ms == 2000
    host._bookmarks.add("book", 2000, note="chorus")  # an edit
    host._refresh_bookmarks()
    assert host._selected_bookmark().note == "chorus"
    host._bookmarks.remove("book", 2000)
    host._refresh_bookmarks()
    assert host._selected_bookmark().position_ms == 3000
