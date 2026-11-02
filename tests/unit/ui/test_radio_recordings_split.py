"""Split into Songs in the Recordings window.

Built on a real in-memory Recordings window. The split itself is a fake
(the core cut has its own tests, with a fake ffmpeg); the task manager is a
fake that runs the work inline and hands the result back, as the real one does
on the UI thread. Nothing modal opens and no input is sent.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.radio.recording import RecordingSettings
from quill.core.radio.recording_song_log import NO_SONG_CHANGES, sidecar_path
from quill.core.radio.recording_split import SplitOutcome
from tests.wx_session import shared_wx_app

wx = pytest.importorskip("wx")

from quill.ui.radio import recordings_marks, recordings_split  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def _app():
    return shared_wx_app()


class _InlineTasks:
    """Runs the work at once and delivers the result, like the real manager."""

    def __init__(self) -> None:
        self.names: list[str] = []

    def submit(self, name: str, func: Any, *, on_success: Any, on_failure: Any, **_: Any) -> None:
        self.names.append(name)
        try:
            result = func()
        except Exception as error:  # noqa: BLE001 - delivered, as the real one does
            on_failure("op", error)
            return
        on_success("op", result)


def _key(code: int, *, ctrl: bool = False, alt: bool = False, shift: bool = False):
    skipped: list[bool] = []
    return SimpleNamespace(
        GetKeyCode=lambda: code,
        ControlDown=lambda: ctrl,
        ShiftDown=lambda: shift,
        AltDown=lambda: alt,
        HasAnyModifiers=lambda: ctrl or shift or alt,
        Skip=lambda: skipped.append(True),
        skipped=skipped,
    )


@pytest.fixture
def recordings(tmp_path: Path):
    from quill.ui.radio.recordings_manager_dialog import RecordingsManagerDialog

    for index in range(3):
        (tmp_path / f"Show {index}.mp3").write_bytes(b"\xff" * 2048)
    said: list[str] = []
    tasks = _InlineTasks()
    dialog = RecordingsManagerDialog(
        None,
        recorder=SimpleNamespace(active_jobs=lambda: [], is_recording=False),
        settings=RecordingSettings(destination_root=str(tmp_path)),
        scheduler=SimpleNamespace(entries=[]),
        controller=SimpleNamespace(state=SimpleNamespace(station=None, state=None)),
        announce_cb=said.append,
        app_host=SimpleNamespace(_task_manager=tasks),
    )
    dialog._timer.Stop()
    dialog.said, dialog.tasks = said, tasks
    yield dialog
    dialog._timer.Stop()
    dialog._win.Destroy()


def _select_row(dialog, row: int) -> None:
    for other in range(dialog._list.GetItemCount()):
        dialog._list.Select(other, False)
    dialog._list.Select(row)
    dialog._list.Focus(row)


def _fake_split(seen: list[Path], songs: int = 4):
    def split(path: Path) -> SplitOutcome:
        seen.append(path)
        folder = path.with_name(f"{path.stem} songs")
        return SplitOutcome(True, path, tuple(folder / f"s{i}.mp3" for i in range(songs)))

    return split


def test_split_cuts_the_selected_recording_off_the_ui_thread_and_says_once(
    recordings,
) -> None:
    seen: list[Path] = []
    _select_row(recordings, 1)
    before = len(recordings.said)
    assert recordings_split.split_into_songs(recordings, split=_fake_split(seen))
    assert seen == [recordings._entries[1].path]
    assert recordings.tasks.names == ["radio-split-recording"]
    # One sentence, at the end, with the count.
    assert recordings.said[before:] == [
        f"Split {seen[0].name} into 4 songs, in the folder {seen[0].stem} songs."
    ]
    assert not recordings._splitting


def test_with_recordings_marked_every_marked_one_is_split(recordings) -> None:
    for row in (0, 2):
        _select_row(recordings, row)
        recordings._on_key(_key(ord(".")))
    _select_row(recordings, 1)
    seen: list[Path] = []
    recordings_split.split_into_songs(recordings, split=_fake_split(seen, songs=3))
    assert seen == [recordings._entries[0].path, recordings._entries[2].path]
    assert recordings.said[-1] == "Split 2 of 2 recordings into 6 songs."


def test_a_recording_with_no_song_changes_says_so_plainly(recordings) -> None:
    _select_row(recordings, 0)
    recordings_split.split_into_songs(
        recordings, split=lambda path: SplitOutcome(False, path, (path,), NO_SONG_CHANGES)
    )
    assert recordings.said[-1].endswith(
        "has no song changes recorded, so there is nothing to split it at."
    )


def test_a_failure_in_the_work_is_said_and_the_window_can_split_again(recordings) -> None:
    def boom(_path: Path) -> SplitOutcome:
        raise OSError("disk gone")

    _select_row(recordings, 0)
    recordings_split.split_into_songs(recordings, split=boom)
    assert recordings.said[-1] == "The recording could not be split. It is unchanged."
    assert not recordings._splitting


def test_alt_shift_t_on_the_list_splits(recordings, monkeypatch: pytest.MonkeyPatch) -> None:
    started: list[object] = []
    monkeypatch.setattr(recordings_split, "split_into_songs", started.append)
    _select_row(recordings, 0)
    event = _key(ord("T"), alt=True, shift=True)
    recordings._on_key(event)
    assert started == [recordings]
    assert event.skipped == []
    plain = _key(ord("T"))
    recordings._on_key(plain)
    assert started == [recordings]
    assert plain.skipped == [True]


def test_nothing_selected_says_what_to_do(recordings) -> None:
    for row in range(recordings._list.GetItemCount()):
        recordings._list.Select(row, False)
    assert not recordings_split.split_into_songs(recordings, split=_fake_split([]))
    assert recordings.said[-1] == "Select a finished recording to split it into songs."


def test_deleting_a_marked_recording_takes_its_song_log_with_it(
    recordings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(recordings_marks, "yes_no_asker", lambda _p, _t: lambda _q: True)
    path = recordings._entries[0].path
    log = sidecar_path(path)
    log.write_text('{"version": 1}', encoding="utf-8")
    _select_row(recordings, 0)
    recordings._on_key(_key(ord(".")))
    recordings._on_key(_key(wx.WXK_DELETE))
    assert not path.exists()
    assert not log.exists()
    assert recordings.said[-1].startswith("Deleted 1 recording.")


def test_the_context_menu_offers_split_with_its_key(recordings, monkeypatch) -> None:
    shown: list[list[str]] = []

    def popup(menu: Any, *_args: Any) -> bool:
        shown.append([item.GetItemLabel() for item in menu.GetMenuItems()])
        return True

    monkeypatch.setattr(recordings._list, "PopupMenu", popup)
    _select_row(recordings, 0)
    recordings_split.show_context_menu(recordings)
    labels = shown[0]
    assert recordings_split.MENU_LABEL in labels
    assert "&Delete...\tDelete" in labels
    # One claimant per key: with a row marked, Delete belongs to the marked rows.
    recordings._on_key(_key(ord(".")))
    recordings_split.show_context_menu(recordings)
    assert "&Delete...\tDelete" not in shown[1]
    assert any(label.startswith("&Remove 1 Marked") for label in shown[1])
