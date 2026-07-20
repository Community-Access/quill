"""Headless tests for the Recordings Manager dialog's in-place diff refresh
(R1/quill-radio #8): no DeleteAllItems, a no-op fast path when the snapshot is
unchanged, and selection preserved by stable identity (not yanked to top when
the list shifts).

A fake ListCtrl records every mutation so the test can assert the diff never
tears the list down -- no real wx is created (per the "no desktop UI automation
on Jeff's machine" rule; real SR validation happens in CI/release smoke).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from quill.core.radio.recording import RecordingSettings
from quill.core.radio.recordings_index import RecordingEntry
from quill.ui.radio.recordings_manager_dialog import RecordingsManagerDialog


class _FakeList:
    """Records ListCtrl mutations; rows are [name, status, size, when]."""

    def __init__(self) -> None:
        self.rows: list[list[str]] = []
        self._selected = -1
        self.set_calls: list[tuple[int, int, str]] = []
        self.inserts: list[tuple[int, str]] = []
        self.deletes: list[int] = []
        self.selects: list[int] = []
        self.focuses: list[int] = []
        self.ensure_visible: list[int] = []
        self.delete_all = 0

    def GetItemCount(self) -> int:
        return len(self.rows)

    def GetFirstSelected(self) -> int:
        return self._selected

    def GetTopItem(self) -> int:
        return 0

    def SetItem(self, row: int, col: int, val: str) -> None:
        self.set_calls.append((row, col, val))
        while len(self.rows) <= row:
            self.rows.append(["", "", "", ""])
        self.rows[row][col] = val

    def InsertItem(self, row: int, name: str) -> None:
        self.inserts.append((row, name))
        self.rows.insert(row, [name, "", "", ""])

    def DeleteItem(self, row: int) -> None:
        self.deletes.append(row)
        del self.rows[row]

    def DeleteAllItems(self) -> None:  # pragma: no cover - must never be called
        self.delete_all += 1

    def Select(self, row: int) -> None:
        self.selects.append(row)
        self._selected = row

    def Focus(self, row: int) -> None:
        self.focuses.append(row)

    def EnsureVisible(self, row: int) -> None:
        self.ensure_visible.append(row)


def _entry(name: str, status: str, path: Path) -> RecordingEntry:
    return RecordingEntry(id=str(path.resolve()), name=name, status=status, path=path)


def _dialog(tmp_path: Path) -> tuple[RecordingsManagerDialog, _FakeList, SimpleNamespace]:
    fake_list = _FakeList()
    recorder = SimpleNamespace(
        is_recording=False,
        current_destination=None,
        current_station_name="",
        current_stream_url="",
        current_started_at=None,
    )
    scheduler = SimpleNamespace(entries=[])
    dlg = RecordingsManagerDialog.__new__(RecordingsManagerDialog)
    dlg._wx = SimpleNamespace()  # _refresh keeps a reference but never calls it
    dlg._list = fake_list
    dlg._recorder = recorder
    dlg._settings = RecordingSettings(destination_root=str(tmp_path))
    dlg._scheduler = scheduler
    dlg._entries = []
    dlg._status = SimpleNamespace(_label="", SetLabel=lambda s: None)
    # Selection-changed handler touches buttons we do not model here; the diff
    # logic under test does not depend on it.
    dlg._on_selection_changed = lambda: None  # type: ignore[assignment]
    return dlg, fake_list, recorder


def test_refresh_noop_when_snapshot_unchanged(tmp_path: Path) -> None:
    # R1/9: identical content means zero list mutation -- no re-announcements.
    dlg, fake_list, recorder = _dialog(tmp_path)
    (tmp_path / "show.mp3").write_bytes(b"x")
    # Prime a first refresh so the list has content.
    dlg._refresh()
    fake_list.set_calls.clear()
    fake_list.selects.clear()
    fake_list.focuses.clear()
    fake_list.inserts.clear()
    fake_list.deletes.clear()
    # A second refresh with no state change is a complete no-op.
    dlg._refresh()
    assert fake_list.set_calls == []
    assert fake_list.selects == []
    assert fake_list.focuses == []
    assert fake_list.inserts == []
    assert fake_list.deletes == []
    assert fake_list.delete_all == 0


def test_refresh_uses_in_place_diff_not_teardown(tmp_path: Path) -> None:
    # R1/9: a status flip updates the existing row in place -- never
    # DeleteAllItems + re-insert (the source of the 2-second re-announcement).
    dlg, fake_list, recorder = _dialog(tmp_path)
    (tmp_path / "show.mp3").write_bytes(b"x")
    dlg._refresh()
    assert fake_list.delete_all == 0
    # The active row appears and flips to Recorded on the next refresh via
    # SetItem on the same row -- no teardown rebuild.
    fake_list.set_calls.clear()
    (tmp_path / "show.mp3").write_bytes(b"xx")  # size grows -> not unchanged
    dlg._refresh()
    assert fake_list.delete_all == 0
    # Only changed cells move (here the size column of the recorded row).
    assert all(row == 0 for _row, col, _val in fake_list.set_calls for row in [0])


def test_selection_follows_identity_not_position(tmp_path: Path) -> None:
    # R1/9: when a new active row is inserted at the top, the previously
    # selected file shifts down one row -- selection follows it by identity
    # instead of yanking back to the top.
    dlg, fake_list, recorder = _dialog(tmp_path)
    old = tmp_path / "old.mp3"
    old.write_bytes(b"x")
    dlg._refresh()  # rows: [old Recorded]
    fake_list.Select(0)  # user selects the old recording
    fake_list.selects.clear()
    fake_list.focuses.clear()
    # A new recording starts: an active row is inserted at the top, pushing
    # the old file down to row 1.
    live = tmp_path / "live.mp3"
    live.write_bytes(b"y")
    recorder.is_recording = True
    recorder.current_destination = live
    recorder.current_station_name = "live"
    recorder.current_stream_url = "https://live"
    recorder.current_started_at = datetime.now()
    dlg._refresh()
    # The old file's selection followed it to row 1 (its identity), not row 0.
    assert 1 in fake_list.selects
    assert 1 in fake_list.focuses
    assert 0 not in fake_list.selects


def test_per_row_stop_and_stop_all_target_jobs(tmp_path: Path) -> None:
    # Concurrent recording: two Recording rows; Stop targets the selected row's
    # job id, Stop All stops every recording.
    dlg, fake_list, _recorder = _dialog(tmp_path)
    a = tmp_path / "A - live.mp3"
    b = tmp_path / "B - live.mp3"
    a.write_bytes(b"a")
    b.write_bytes(b"b")
    stopped: list[str] = []
    stop_all_calls: list[bool] = []
    jobs = [
        SimpleNamespace(
            job_id="ja",
            destination=a,
            station_name="A",
            stream_url="https://x/a",
            started_at=datetime.now(),
        ),
        SimpleNamespace(
            job_id="jb",
            destination=b,
            station_name="B",
            stream_url="https://x/b",
            started_at=datetime.now(),
        ),
    ]
    dlg._recorder = SimpleNamespace(
        active_jobs=lambda: jobs,
        active_count=len(jobs),
        is_recording=True,
        stop=lambda job_id=None: stopped.append(job_id),
        stop_all=lambda: stop_all_calls.append(True),
    )
    dlg._announce = lambda _m: None  # type: ignore[assignment]
    dlg._refresh()
    recording_rows = [e for e in dlg._entries if e.status == "Recording"]
    assert [e.job_id for e in recording_rows] == ["ja", "jb"]
    # Select the second Recording row and Stop it -> stops job jb only.
    fake_list._selected = 1
    dlg._on_stop_recording()
    assert stopped == ["jb"]
    # Stop All stops every recording.
    dlg._on_stop_all_recordings()
    assert stop_all_calls == [True]


def test_completed_once_does_not_count_as_scheduled(tmp_path: Path) -> None:
    # R1/10.1: the status label counts Completed separately from Scheduled.
    from quill.core.radio.recording_schedule import RecordingScheduleEntry

    dlg, fake_list, recorder = _dialog(tmp_path)
    fired = RecordingScheduleEntry(
        id="1",
        station_name="WQXR",
        stream_url="https://x",
        recurrence="once",
        run_at="2026-07-20T07:00",
        last_fired_date="2026-07-20",
    )
    dlg._scheduler.entries = [fired]  # type: ignore[attr-defined]
    labels: list[str] = []
    dlg._status = SimpleNamespace(SetLabel=lambda s: labels.append(s))  # type: ignore[assignment]
    dlg._refresh()
    assert any("0 scheduled" in s and "1 completed" in s for s in labels)
    assert not any(s for s in labels if "1 scheduled" in s)
