"""Watched Folders in the real QUILL Cast window (qc.md 5d, C2-02).

The core rules -- once, never twice, settled files, groups -- are tested in
``tests/unit/core/podcasts/test_watched_folders.py``. This drives what a
listener meets: the menu row, the window and its verbs, the settings page,
what is said when files arrive, and the live watcher's settle tick.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

wx = pytest.importorskip("wx")

#: Serialized onto one worker under ``-n --dist loadgroup``: this file builds a
#: real QUILL Cast window, which registers the system-wide global hotkeys
#: (RegisterHotKey is per-desktop, not per-process).
#: See ``pytest_collection_modifyitems`` in ``tests/conftest.py``.
pytestmark = pytest.mark.machine_global


@pytest.fixture
def cast(quill_data_dir: Path):
    app = wx.App()
    from quill.apps.podcasts import PodcastsAppFrame
    from quill.ui.dialog_contract import set_transition_announcement_policy

    frame = PodcastsAppFrame()
    said: list[str] = []
    frame._announce = lambda message, **_kw: said.append(str(message))
    frame.said = said
    try:
        yield frame
    finally:
        set_transition_announcement_policy(None)
        try:
            frame.frame.Destroy()
        except Exception:  # noqa: BLE001
            pass
        del app


def _audio(path: Path, payload: bytes = b"audio") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    old = time.time() - 60
    os.utime(path, (old, old))
    return path


def _menu_labels(frame) -> list[str]:
    bar = frame.frame.GetMenuBar()
    labels: list[str] = []
    for index in range(bar.GetMenuCount()):
        labels += [item.GetItemLabel() for item in bar.GetMenu(index).GetMenuItems()]
    return labels


def test_ctrl_alt_w_is_the_watched_folders_window(cast) -> None:
    assert "&Watched Folders...\tCtrl+Alt+W" in _menu_labels(cast)
    cast.open_watched_folders()
    window = cast._watched_folders_window
    assert window.frame.IsShown()
    assert window._list.GetString(0).startswith("No folders yet")


def test_add_folder_settings_and_arrival_are_spoken(cast, tmp_path: Path, monkeypatch) -> None:
    from quill.core.podcasts import watched_folders as wf
    from quill.ui.podcasts import folder_watch

    source = tmp_path / "Voice Memos"
    _audio(source / "Tuesday meeting.mp3")

    class _Chooser:
        def __init__(self, *_a, **_k) -> None: ...
        def __enter__(self):
            return self

        def __exit__(self, *_a) -> None: ...
        def ShowModal(self) -> int:
            return wx.ID_OK

        def GetPath(self) -> str:
            return str(source)

    monkeypatch.setattr(wx, "DirDialog", _Chooser)
    monkeypatch.setattr(
        "quill.ui.podcasts.watched_folder_settings.edit_folder_settings",
        lambda _host, _parent, folder: setattr(folder, "min_seconds", 0) or True,
    )
    scans: list[str] = []
    monkeypatch.setattr(
        folder_watch.FolderWatchMixin,
        "scan_watched_folder_now",
        lambda self, folder_id, **_k: scans.append(folder_id),
    )
    folder = cast.add_watched_folder()
    assert folder is not None and cast._podcast_library.watched_folders == [folder]
    assert scans == [folder.id]
    assert any(s.startswith("Watching Voice Memos.") for s in cast.said)

    plan = wf.plan(folder, wf.known_hashes(cast._podcast_library), dest_root=tmp_path / "m")
    cast._apply_folder_plan(plan)
    assert cast.said[-1] == "New in Voice Memos: Tuesday meeting."
    group = cast._podcast_library.find_show(folder.show_id)
    assert group is not None and group.is_local and len(group.episodes) == 1


def test_a_missing_folder_is_said_once(cast, tmp_path: Path) -> None:
    from quill.core.podcasts import watched_folders as wf

    folder = wf.WatchedFolder(path=str(tmp_path / "gone"), name="Lectures")
    cast._podcast_library.watched_folders.append(folder)
    for _ in range(2):
        cast._apply_folder_plan(wf.plan(folder, set(), dest_root=tmp_path / "m"))
    spoken = [s for s in cast.said if "Lectures is unavailable" in s]
    assert len(spoken) == 1 and spoken[0].endswith("Still watching.")


def test_remove_keeps_the_files_and_pause_says_so(cast, tmp_path: Path, monkeypatch) -> None:
    from quill.core.podcasts import watched_folders as wf

    folder = wf.WatchedFolder(path=str(tmp_path), name="Lectures")
    cast._podcast_library.watched_folders.append(folder)
    cast.pause_watched_folder(folder.id, True)
    assert folder.paused and cast.said[-1].startswith("Paused Lectures.")
    monkeypatch.setattr("quill.ui.dialog_contract.show_message_box", lambda *_a, **_k: wx.NO)
    assert not cast.remove_watched_folder(folder.id)
    monkeypatch.setattr("quill.ui.dialog_contract.show_message_box", lambda *_a, **_k: wx.YES)
    assert cast.remove_watched_folder(folder.id)
    assert cast._podcast_library.watched_folders == []
    assert "Its files stay in Personal Audio" in cast.said[-1]


def test_the_settings_page_writes_what_it_shows(cast, tmp_path: Path) -> None:
    from quill.core.podcasts import watched_folders as wf
    from quill.ui.podcasts.watched_folder_settings import WatchedFolderSettingsDialog

    folder = wf.WatchedFolder(path=str(tmp_path), name="Books")
    page = WatchedFolderSettingsDialog(cast.frame, folder)
    try:
        page._name.SetValue("Audiobooks")
        page._original.SetSelection(2)
        page._tell.SetSelection(1)
        page._groups.SetValue(True)
        page._speed.SetSelection(5)  # 1.5x
        for box in page._types:
            box.SetValue(box.GetLabel() == ".m4b")
        page.read()
    finally:
        page.dialog.Destroy()
    assert (folder.name, folder.original, folder.tell) == ("Audiobooks", "reference", "batch")
    assert folder.subfolder_groups and folder.speed == 1.5
    assert folder.extensions == (".m4b",)


def test_a_settled_file_starts_a_look_at_its_folder(cast, tmp_path: Path, monkeypatch) -> None:
    from quill.core.podcasts import watched_folders as wf
    from quill.ui.podcasts import folder_watch

    folder = wf.WatchedFolder(path=str(tmp_path), name="Recorder")
    cast._podcast_library.watched_folders.append(folder)
    clock = [0.0]
    cast._settle_tracker = wf.SettleTracker(5.0, clock=lambda: clock[0])
    scans: list[str] = []
    monkeypatch.setattr(
        folder_watch.FolderWatchMixin,
        "scan_watched_folder_now",
        lambda self, folder_id, **_k: scans.append(folder_id),
    )
    path = _audio(tmp_path / "take.mp3")

    class _Event:
        def GetNewPath(self) -> str:
            return str(path)

        def GetPath(self) -> str:
            return str(path)

    cast._on_folder_change(_Event())
    cast._on_settle_tick()
    assert scans == []
    clock[0] = 6.0
    cast._on_settle_tick()
    assert scans == [folder.id]
    cast._settle_timer.Stop()
