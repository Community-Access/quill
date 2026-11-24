"""Quill Radio and Media Player: saves and exports say the file and its folder, once,
and stay reachable in Activity with Open Folder (FUX-04)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from quill.core import activity


class _Host:
    def __init__(self) -> None:
        self.said: list[str] = []

    def _announce(self, text: str, **_kw: Any) -> None:
        self.said.append(text)


def _latest() -> activity.ActionResult:
    return activity.LOG.recent()[0]


# -- the download queue -----------------------------------------------------------------


def _queue(tmp_path: Path, *names: str):
    from quill.core.radio.download_queue import DownloadQueue

    queue = DownloadQueue()
    queue.add_all(
        [SimpleNamespace(name=n, stream_url=f"https://x/{n}") for n in names],
        str(tmp_path / "Middlemarch"),
        group="Middlemarch",
    )
    return queue


def test_a_finished_book_says_which_folder_it_is_in(tmp_path: Path) -> None:
    from quill.ui.radio.download_runner import drained_sentence

    queue = _queue(tmp_path, "One", "Two", "Three")
    book = tmp_path / "Audiobooks" / "Middlemarch"
    queue.finish(queue.items[0], str(book / "01.mp3"))
    queue.finish(queue.items[1], str(book / "02.mp3"))
    queue.fail(queue.items[2], "gone")
    said, folder = drained_sentence(queue)
    assert said == "2 saved, 1 failed. Saved in Middlemarch in Audiobooks."
    assert folder == book


def test_downloads_in_several_folders_are_counted_not_listed(tmp_path: Path) -> None:
    from quill.ui.radio.download_runner import drained_sentence

    queue = _queue(tmp_path, "One", "Two")
    queue.finish(queue.items[0], str(tmp_path / "a" / "01.mp3"))
    queue.finish(queue.items[1], str(tmp_path / "b" / "02.mp3"))
    assert drained_sentence(queue) == ("2 saved.", None)


def test_the_drained_queue_is_kept_with_open_folder(tmp_path: Path) -> None:
    from quill.ui.radio import download_runner

    host = _Host()
    queue = _queue(tmp_path, "One", "Two")
    for index, item in enumerate(queue.items):
        queue.finish(item, str(tmp_path / "Book" / f"{index}.mp3"))
    download_runner._on_queue_drained(host, queue)
    assert host.said == ["2 saved. Saved in Book in " + tmp_path.name + "."]
    kept = _latest()
    assert kept.summary == host.said[0] and kept.has("open_folder")


def test_one_download_names_its_file_and_folder_not_a_whole_path(tmp_path: Path) -> None:
    from quill.ui.radio import download_runner

    host = _Host()
    host._download_batch_size = 1
    queue = _queue(tmp_path, "Chapter 1")
    item = queue.items[0]
    queue.finish(item, str(tmp_path / "Middlemarch" / "chapter-01.mp3"))
    download_runner._after(host, queue, item)
    # Said once: the end-of-queue count does not follow it with "1 saved."
    assert host.said == ["Saved Chapter 1 as chapter-01.mp3 in Middlemarch."]
    assert str(tmp_path) not in host.said[0]
    assert _latest().has("open_folder")


# -- exports ------------------------------------------------------------------------------


def test_the_backup_names_its_folder(tmp_path: Path) -> None:
    from quill.core.radio.backup import BackupReport

    report = BackupReport(path=tmp_path / "Backups" / "radio.qrbackup")
    assert report.outcome().startswith("Backup saved to radio.qrbackup in Backups.")


def test_a_finished_backup_is_kept_in_activity(tmp_path: Path) -> None:
    from quill.core.radio.backup import BackupReport
    from quill.ui.radio import backup_ui

    host = _Host()
    host._set_status = lambda _t: None
    report = BackupReport(path=tmp_path / "radio.qrbackup")
    backup_ui._backup_done(host, report)
    assert host.said == [report.outcome()]
    kept = _latest()
    assert kept.action == "Back Up" and kept.has("open_folder")


def test_a_snapshot_names_its_folder_and_is_kept(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.core.radio import recordings_index
    from quill.ui.radio import video_commands

    monkeypatch.setattr(recordings_index, "recordings_dir", lambda _s=None: tmp_path / "Rec")
    engine = SimpleNamespace(attach_video=None, take_snapshot=lambda _p: True)
    host = _Host()
    host._radio_controller = SimpleNamespace(_engine=engine, _youtube_stream=None)
    host._video_window = object()
    video_commands.take_snapshot(host)
    assert host.said == ["Snapshot saved as video snapshot 1.png in Rec."]
    assert _latest().has("open_folder")


def test_a_folder_playlist_export_names_its_folder_and_is_kept(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import wx

    from quill.core.radio.favorites import FavoriteStation
    from quill.core.radio.models import RadioStation
    from quill.ui.radio import favorite_folder_actions

    target = tmp_path / "Lists" / "news.m3u"
    target.parent.mkdir()

    class _Chooser:
        def __init__(self, *_a: Any, **_k: Any) -> None:
            pass

        def __enter__(self) -> _Chooser:
            return self

        def __exit__(self, *_a: Any) -> None:
            pass

        def ShowModal(self) -> int:  # noqa: N802
            return wx.ID_OK

        def GetPath(self) -> str:  # noqa: N802
            return str(target)

    monkeypatch.setattr(wx, "FileDialog", _Chooser)
    station = FavoriteStation(station=RadioStation(name="News", stream_url="https://x/n"))
    monkeypatch.setattr(
        favorite_folder_actions.folder_actions, "stations_in_folder", lambda _s, _f: [station]
    )
    host = _Host()
    assert favorite_folder_actions.export_folder(host, "News", store=object())
    assert host.said == ["Exported 1 station to news.m3u in Lists."]
    assert _latest().has("open_folder")


# -- Media Player bookmarks ----------------------------------------------------------------


def test_bookmark_exports_name_the_file_and_folder_and_are_kept(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.core.media.bookmarks import BookmarkStore, MediaBookmark
    from quill.ui.media import bookmark_actions

    target = tmp_path / "Notes" / "marks.md"
    target.parent.mkdir()
    monkeypatch.setattr(bookmark_actions, "_save_path", lambda *_a: str(target))
    host = _Host()
    marks = [MediaBookmark(position_ms=1000, label="One")]
    bookmark_actions.export_bookmarks_markdown(host, "Book", marks)
    assert host.said == ["Exported 1 bookmark to marks.md in Notes."]
    assert target.is_file() and _latest().has("open_folder")

    bundle = tmp_path / "Notes" / "sync.json"
    monkeypatch.setattr(bookmark_actions, "_save_path", lambda *_a: str(bundle))
    store = BookmarkStore(tmp_path / "store.json")
    bookmark_actions.export_sync_bundle(host, store)
    assert host.said[-1] == "Exported the bookmark sync bundle to sync.json in Notes."
