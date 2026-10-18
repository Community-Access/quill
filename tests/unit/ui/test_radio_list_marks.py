"""Marks in Recordings, Browse and the schedule list (xradio2 4.10, todo D.3).

The Favorites marking keys, extended: "." marks the selected row and says the
running count, Delete then acts on every marked row after one question, and
Ctrl+Shift+Delete clears them. Built on real in-memory windows; the yes/no
question is a fake, so nothing modal opens and no input is sent.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from quill.core.radio.browse_nodes import BrowseNode
from quill.core.radio.favorites import RadioFavoritesStore
from quill.core.radio.models import RadioStation
from quill.core.radio.recording import RecordingSettings
from quill.core.radio.recording_schedule import RecordingScheduleEntry
from quill.core.radio.row_marks import RowMarks, ignored_sentence
from tests.wx_session import shared_wx_app

wx = pytest.importorskip("wx")

from quill.ui.radio import (  # noqa: E402
    browse_delete,
    browse_marks,
    marks_shared,
    recordings_marks,
    schedule_marks,
)


@pytest.fixture(scope="module", autouse=True)
def _app():
    return shared_wx_app()


@pytest.fixture(autouse=True)
def _no_real_questions(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every question in these tests is a fake; a real one must never open."""

    def _refuse(*_args: object, **_kwargs: object) -> int:
        pytest.fail("a real message box would have opened")

    monkeypatch.setattr(wx, "MessageBox", _refuse)
    monkeypatch.setattr(wx, "RichMessageDialog", _refuse)


def _key(code: int, *, ctrl: bool = False, shift: bool = False):
    skipped: list[bool] = []
    return SimpleNamespace(
        GetKeyCode=lambda: code,
        ControlDown=lambda: ctrl,
        ShiftDown=lambda: shift,
        AltDown=lambda: False,
        HasAnyModifiers=lambda: ctrl or shift,
        Skip=lambda: skipped.append(True),
        skipped=skipped,
    )


PERIOD = ord(".")


# -- the shared core --------------------------------------------------------------


def test_the_shared_keys_mean_the_same_thing_everywhere() -> None:
    assert marks_shared.mark_action(wx, _key(PERIOD)) == marks_shared.TOGGLE
    assert marks_shared.mark_action(wx, _key(wx.WXK_DELETE)) == marks_shared.ACT
    assert marks_shared.mark_action(wx, _key(wx.WXK_DELETE, ctrl=True, shift=True)) == (
        marks_shared.CLEAR
    )
    assert marks_shared.mark_action(wx, _key(wx.WXK_DELETE, shift=True)) is None
    assert marks_shared.mark_action(wx, _key(ord("A"))) is None


def test_an_action_that_ignored_the_marks_says_so_once_per_set() -> None:
    marks = RowMarks()
    owner = SimpleNamespace(_row_marks=marks)
    assert marks_shared.with_ignored_note(owner, "Playing X.") == "Playing X."
    marks.toggle("a")
    marks.toggle("b")
    first = marks_shared.with_ignored_note(owner, "Playing X.")
    assert first == f"Playing X. {ignored_sentence(2)}"
    assert "2 rows are still marked for Delete" in first
    assert marks_shared.with_ignored_note(owner, "Playing Y.") == "Playing Y."
    marks.toggle("c")  # a new set of marks is explained afresh
    assert "3 rows are still marked" in marks_shared.with_ignored_note(owner, "Playing Z.")


# -- the schedule list --------------------------------------------------------------


def _schedule_entry(index: int) -> RecordingScheduleEntry:
    return RecordingScheduleEntry(
        id=f"s{index}",
        station_name=f"Show {index}",
        stream_url=f"https://s{index}.test/",
        # One-time, on fixed future days: the list sorts by next run, and a
        # daily time that has already passed today moves to tomorrow, so
        # the row order would depend on the clock (CI failed at 01:12).
        recurrence="once",
        run_at=f"2099-01-0{index}T09:00",
    )


@pytest.fixture
def schedule():
    from quill.ui.radio.schedule_recording_dialog import ScheduleRecordingDialog

    removed: list[str] = []
    said: list[str] = []
    dialog = ScheduleRecordingDialog(
        None,
        entries=[_schedule_entry(index) for index in range(1, 6)],
        on_add=lambda _e: None,
        on_remove=lambda entry_id: removed.append(entry_id) or True,
        on_update=lambda _entry: True,
        announce_cb=said.append,
    )
    dialog.removed, dialog.said = removed, said
    yield dialog
    dialog._win.Destroy()


def test_period_marks_a_schedule_and_the_row_says_so(schedule) -> None:
    schedule._list.SetSelection(1)
    schedule._on_list_key(_key(PERIOD))
    assert schedule.said[-1] == "Marked. 1 marked."
    assert schedule._list.GetString(1).endswith(" (marked)")
    schedule._on_list_key(_key(PERIOD))
    assert schedule.said[-1] == "Unmarked. Nothing marked."
    assert not schedule._list.GetString(1).endswith(" (marked)")


def test_delete_removes_every_marked_schedule_after_one_question(
    schedule, monkeypatch: pytest.MonkeyPatch
) -> None:
    asked: list[str] = []
    monkeypatch.setattr(
        schedule_marks, "yes_no_asker", lambda _p, _t: lambda q: asked.append(q) or True
    )
    for row in (0, 2, 3):
        schedule._list.SetSelection(row)
        schedule._on_list_key(_key(PERIOD))
    schedule._list.SetSelection(2)
    schedule._on_list_key(_key(wx.WXK_DELETE))
    assert asked == ["Delete 3 schedules?"]
    assert sorted(schedule.removed) == ["s1", "s3", "s4"]
    assert schedule.said[-1] == "Deleted 3 schedules."
    assert [entry.id for entry in schedule._entries] == ["s2", "s5"]
    # The cursor lands on the survivor after the row it was on, not the top.
    assert schedule._entries[schedule._list.GetSelection()].id == "s5"
    assert not any("(marked)" in schedule._list.GetString(i) for i in range(2))


def test_answering_no_deletes_nothing(schedule, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(schedule_marks, "yes_no_asker", lambda _p, _t: lambda _q: False)
    schedule._list.SetSelection(0)
    schedule._on_list_key(_key(PERIOD))
    schedule._on_list_key(_key(wx.WXK_DELETE))
    assert schedule.removed == []
    assert schedule.said[-1] == "Nothing was deleted."


def test_ctrl_shift_delete_clears_the_marks(schedule) -> None:
    for row in (0, 1):
        schedule._list.SetSelection(row)
        schedule._on_list_key(_key(PERIOD))
    schedule._on_list_key(_key(wx.WXK_DELETE, ctrl=True, shift=True))
    assert schedule.said[-1] == "Cleared 2 marks."
    assert not any("(marked)" in schedule._list.GetString(i) for i in range(5))


def test_with_nothing_marked_delete_removes_the_selected_schedule(schedule) -> None:
    schedule._list.SetSelection(0)
    schedule._on_list_key(_key(wx.WXK_DELETE))
    assert schedule.removed == ["s1"]


def test_toggling_a_schedule_while_others_are_marked_explains_itself(schedule) -> None:
    schedule._list.SetSelection(0)
    schedule._on_list_key(_key(PERIOD))
    schedule._list.SetSelection(3)
    schedule._on_toggle_click(None)
    assert schedule.said[-1].endswith("1 row is still marked for Delete.")


# -- Recordings -----------------------------------------------------------------------


@pytest.fixture
def recordings(tmp_path: Path):
    from quill.ui.radio.recordings_manager_dialog import RecordingsManagerDialog

    for index in range(4):
        (tmp_path / f"Show {index}.mp3").write_bytes(b"\xff" * 2048)
    said: list[str] = []
    dialog = RecordingsManagerDialog(
        None,
        recorder=SimpleNamespace(active_jobs=lambda: [], is_recording=False),
        settings=RecordingSettings(destination_root=str(tmp_path)),
        scheduler=SimpleNamespace(entries=[]),
        controller=SimpleNamespace(state=SimpleNamespace(station=None, state=None)),
        announce_cb=said.append,
    )
    dialog._timer.Stop()
    dialog.said = said
    yield dialog
    dialog._timer.Stop()
    dialog._win.Destroy()


def _select_row(dialog, row: int) -> None:
    for other in range(dialog._list.GetItemCount()):
        dialog._list.Select(other, False)
    dialog._list.Select(row)
    dialog._list.Focus(row)


def test_period_marks_a_finished_recording(recordings) -> None:
    assert len(recordings._entries) == 4
    _select_row(recordings, 1)
    recordings._on_key(_key(PERIOD))
    assert recordings.said[-1] == "Marked. 1 marked."
    assert recordings._list.GetItemText(1).endswith(" (marked)")


def test_delete_removes_every_marked_recording_after_one_question(
    recordings, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    asked: list[str] = []
    monkeypatch.setattr(
        recordings_marks, "yes_no_asker", lambda _p, _t: lambda q: asked.append(q) or True
    )
    for row in (0, 2):
        _select_row(recordings, row)
        recordings._on_key(_key(PERIOD))
    names = {recordings._entries[row].name for row in (0, 2)}
    recordings._on_key(_key(wx.WXK_DELETE))
    assert asked == ["Delete 2 recordings?"]
    assert recordings.said[-1].startswith("Deleted 2 recordings.")
    left = {path.stem for path in tmp_path.glob("*.mp3")}
    assert not (left & names)
    assert len(recordings._entries) == 2
    assert recordings._list.GetFirstSelected() >= 0  # the cursor landed on a real row


def test_a_scheduled_row_cannot_be_marked_and_says_why(recordings) -> None:
    from quill.core.radio.recordings_index import STATUS_SCHEDULED, RecordingEntry

    recordings._entries.insert(
        0,
        RecordingEntry(
            id="schedule:x",
            name="Later",
            status=STATUS_SCHEDULED,
            path=None,
            modified=datetime(2026, 10, 17),
        ),
    )
    recordings._list.InsertItem(0, "Later")
    _select_row(recordings, 0)
    recordings._on_key(_key(PERIOD))
    assert recordings.said[-1] == "Only finished recordings can be marked."


def test_open_in_folder_while_marked_explains_the_marks(
    recordings, monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.ui.radio import recordings_manager_dialog

    monkeypatch.setattr(recordings_manager_dialog.subprocess, "Popen", lambda *_a, **_k: None)
    _select_row(recordings, 0)
    recordings._on_key(_key(PERIOD))
    _select_row(recordings, 1)
    recordings._on_open_in_folder()
    assert recordings.said[-1].endswith("1 row is still marked for Delete.")


# -- Browse --------------------------------------------------------------------------


@pytest.fixture
def browse():
    from quill.ui.radio.browse_tree_dialog import BrowseTreeDialog

    store = RadioFavoritesStore()
    stations = [RadioStation(name=f"Fav {i}", stream_url=f"https://f{i}.test/") for i in range(3)]
    for station in stations:
        store.add(station)
    said: list[str] = []
    dialog = BrowseTreeDialog(
        None,
        controller=SimpleNamespace(state=SimpleNamespace(volume_percent=100, muted=False)),
        favorites_store=store,
        task_manager=SimpleNamespace(),
        safe_mode=True,
        announce_cb=said.append,
    )
    tree = dialog._tree
    branch = tree.AppendItem(tree.GetRootItem(), "Test rows")
    rows = []
    for index, station in enumerate(stations):
        item = tree.AppendItem(branch, station.name)
        tree.SetItemData(item, {"node_id": f"fav:{index}", "station": station})
        rows.append(item)
    plain = tree.AppendItem(branch, "A country  (12 items)")
    tree.SetItemData(plain, {"node_id": "country:fr"})
    rows.append(plain)
    dialog.rows, dialog.said, dialog.store = rows, said, store
    yield dialog
    dialog._win.Destroy()


def test_period_marks_a_removable_browse_row(browse) -> None:
    browse._tree.SelectItem(browse.rows[1])
    assert browse_marks.handle_key(browse, _key(PERIOD))
    assert browse.said[-1] == "Marked. 1 marked."
    assert browse._tree.GetItemText(browse.rows[1]) == "Fav 1 (marked)"
    # And the single-row Delete still names the row without the mark.
    assert browse_delete._label(browse, browse.rows[1]) == "Fav 1"


def test_a_row_delete_cannot_remove_cannot_be_marked(browse) -> None:
    browse._tree.SelectItem(browse.rows[3])
    assert browse_marks.handle_key(browse, _key(PERIOD))
    assert browse.said[-1] == browse_marks.CANNOT_MARK


def test_delete_removes_every_marked_browse_row(browse, monkeypatch: pytest.MonkeyPatch) -> None:
    asked: list[str] = []
    monkeypatch.setattr(browse_delete, "confirm", lambda _d, q: asked.append(q) or True)
    for row in (0, 2):
        browse._tree.SelectItem(browse.rows[row])
        browse_marks.handle_key(browse, _key(PERIOD))
    assert browse_marks.handle_key(browse, _key(wx.WXK_DELETE))
    assert asked == ["Delete 2 items?"]
    assert [f.station.name for f in browse.store.favorites] == ["Fav 1"]
    assert browse.said[-1] == "Deleted 2 items."


def test_with_nothing_marked_delete_is_left_to_the_row(browse) -> None:
    browse._tree.SelectItem(browse.rows[0])
    assert not browse_marks.handle_key(browse, _key(wx.WXK_DELETE))


def test_a_marked_row_keeps_its_mark_when_its_branch_is_rebuilt(browse) -> None:
    browse._tree.SelectItem(browse.rows[0])
    browse_marks.handle_key(browse, _key(PERIOD))
    child = BrowseNode(node_id="fav:0", label="Fav 0", note="from a test")
    assert browse._row_label(child) == "Fav 0 (marked)  (from a test)"
    other = BrowseNode(node_id="fav:9", label="Fav 9")
    assert "(marked)" not in browse._row_label(other)
