"""The Watch Folder queue (the transcription and conversion queue) stays still (FUX-06).

Every queue event cleared the list and reselected the same row *number*, so
after Clear Finished took rows away above the reader, Retry or Open acted on
another file, and a reader on the last row went back to the top.
"""

from __future__ import annotations

from types import SimpleNamespace

from quill.core.watch_queue import QueueItem
from quill.ui.main_frame_watch_folder import WatchFolderRuntimeMixin


class _ListBox:
    def __init__(self) -> None:
        self.rows: list[str] = []
        self.selection = -1
        self.cleared = 0

    def GetCount(self) -> int:  # noqa: N802
        return len(self.rows)

    def GetSelection(self) -> int:  # noqa: N802
        return self.selection

    def GetString(self, row: int) -> str:  # noqa: N802
        return self.rows[row]

    def SetString(self, row: int, text: str) -> None:  # noqa: N802
        self.rows[row] = text

    def Insert(self, text: str, row: int) -> None:  # noqa: N802
        self.rows.insert(row, text)
        if 0 <= row <= self.selection:
            self.selection += 1

    def Delete(self, row: int) -> None:  # noqa: N802
        del self.rows[row]
        if row == self.selection:
            self.selection = -1
        elif row < self.selection:
            self.selection -= 1

    def SetSelection(self, row: int) -> None:  # noqa: N802
        self.selection = row

    def Clear(self) -> None:  # noqa: N802
        self.cleared += 1
        self.rows.clear()
        self.selection = -1


def _item(name: str, state: str = "queued") -> QueueItem:
    return QueueItem(
        item_id=name, source_path=f"C:/in/{name}.wav", profile_id="p", action_id="a", state=state
    )


def _host(items: list[QueueItem]) -> WatchFolderRuntimeMixin:
    host = WatchFolderRuntimeMixin.__new__(WatchFolderRuntimeMixin)
    host._watch_queue_monitor = object()
    host._watch_queue_listbox = _ListBox()
    host._watch_service = SimpleNamespace(
        queue_items=lambda: list(items),
        queue_counts=lambda: {},
        queue=SimpleNamespace(is_paused=lambda: False),
        primed_count=lambda: 0,
    )
    return host


def test_clear_finished_above_the_reader_keeps_them_on_their_file() -> None:
    items = [_item("one", "done"), _item("two", "done"), _item("three"), _item("four")]
    host = _host(items)
    host._refresh_watch_queue_monitor()
    host._watch_queue_listbox.SetSelection(3)  # four.wav
    del items[:2]  # Clear Finished
    host._refresh_watch_queue_monitor()
    box = host._watch_queue_listbox
    assert box.rows[box.selection].endswith("four.wav")
    assert host._watch_queue_items_cache[box.selection].item_id == "four"
    assert box.cleared == 0


def test_the_monitor_opens_on_its_first_file() -> None:
    host = _host([_item("one"), _item("two")])
    host._refresh_watch_queue_monitor()
    assert host._watch_queue_listbox.selection == 0


def test_a_state_change_rewrites_only_that_row() -> None:
    items = [_item("one"), _item("two")]
    host = _host(items)
    host._refresh_watch_queue_monitor()
    host._watch_queue_listbox.SetSelection(1)
    items[0] = _item("one", "processing")
    host._refresh_watch_queue_monitor()
    box = host._watch_queue_listbox
    assert box.rows[0].startswith("Processing")
    assert box.selection == 1
