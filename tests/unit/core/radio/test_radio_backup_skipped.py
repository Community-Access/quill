"""A Radio backup says exactly what it holds and names what it left out.

Reported 2026-10-04 by a listener on Windows 11 whose recordings and backups
live in a OneDrive folder, about to reset two computers: "the application said
some items were skipped ... I'm just hoping I won't lose my favorites or
recordings". These pin the answer:

* favorites, settings and podcast subscriptions are in every backup, or the
  backup fails loudly -- never a success quietly missing them;
* a recording stored only in OneDrive is *read* (which is what downloads it),
  not skipped, unless there is no room to hold it;
* anything left out is a named row with a reason.

No real OneDrive: placeholders are faked through the injectable ``stat``.
"""

from __future__ import annotations

import builtins
import errno
import os
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from quill.core import skipped_files as sf
from quill.core.radio import backup_recordings
from quill.core.radio.backup import (
    BACKUP_SUFFIX,
    RadioBackupError,
    create_backup_report,
    plan_recordings,
    read_manifest,
    restore_backup,
)

_PLENTY = 50 * 1024**3


def _seed(data: Path) -> None:
    data.mkdir(parents=True, exist_ok=True)
    (data / "radio_favorites.json").write_text('{"favorites": ["KEXP"]}', encoding="utf-8")
    (data / "radio_history.json").write_text('{"close_action": "minimize"}', encoding="utf-8")
    (data / "podcasts_library.json").write_text('{"shows": [{"id": "x"}]}', encoding="utf-8")


def _cloud_stat(*cloud_names: str):
    """A stat that reports *cloud_names* as OneDrive placeholders."""

    def _stat(path: Path) -> os.stat_result:
        real = os.stat(path)
        attrs = sf.FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS if Path(path).name in cloud_names else 0
        return SimpleNamespace(st_size=real.st_size, st_file_attributes=attrs)  # type: ignore[return-value]

    return _stat


def _recordings(tmp_path: Path, *names: str) -> Path:
    folder = tmp_path / "OneDrive" / "quill"
    folder.mkdir(parents=True)
    for name in names:
        (folder / name).write_bytes(b"AUDIO-" + name.encode())
    return folder


def test_podcast_subscriptions_are_in_every_backup(tmp_path: Path) -> None:
    data = tmp_path / "data"
    _seed(data)
    report = create_backup_report(data, tmp_path / f"b{BACKUP_SUFFIX}")
    assert "podcasts_library.json" in report.data_files
    with zipfile.ZipFile(report.path) as zf:
        assert zf.read("data/podcasts_library.json") == b'{"shows": [{"id": "x"}]}'
    assert "podcast subscriptions" in report.holds()
    assert "favorite stations" in report.holds()


def test_an_unreadable_favorites_file_fails_the_backup_and_saves_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data = tmp_path / "data"
    _seed(data)
    real = Path.read_bytes

    def _read(self: Path) -> bytes:
        if self.name == "radio_favorites.json":
            error = PermissionError(errno.EACCES, "in use")
            error.winerror = 32  # type: ignore[attr-defined]
            raise error
        return real(self)

    monkeypatch.setattr(Path, "read_bytes", _read)
    dest = tmp_path / f"b{BACKUP_SUFFIX}"
    with pytest.raises(RadioBackupError) as caught:
        create_backup_report(data, dest)
    assert "favorite stations" in str(caught.value)
    assert sf.REASON_IN_USE in str(caught.value)
    assert not dest.exists(), "a backup missing the favorites must not be left behind"


def test_an_unreadable_minor_file_is_named_not_fatal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data = tmp_path / "data"
    _seed(data)
    (data / "quiet-hours.json").write_text("{}", encoding="utf-8")
    real = Path.read_bytes

    def _read(self: Path) -> bytes:
        if self.name == "quiet-hours.json":
            raise OSError(errno.EIO, "io")
        return real(self)

    monkeypatch.setattr(Path, "read_bytes", _read)
    report = create_backup_report(data, tmp_path / f"b{BACKUP_SUFFIX}")
    assert [item.name for item in report.skipped] == ["Your quiet hours"]
    assert "1 file was left out" in report.outcome()


def test_a_onedrive_only_recording_is_downloaded_by_reading_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data = tmp_path / "data"
    _seed(data)
    rec = _recordings(tmp_path, "local.mp3", "cloud.mp3")
    opened: list[str] = []
    real_open = builtins.open

    def _open(file, *args, **kwargs):  # type: ignore[no-untyped-def]
        opened.append(Path(file).name)
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(backup_recordings, "open", _open, raising=False)
    report = create_backup_report(
        data,
        tmp_path / f"b{BACKUP_SUFFIX}",
        recordings_dir=rec,
        include_recordings=True,
        stat=_cloud_stat("cloud.mp3"),
        free_bytes=lambda _p: _PLENTY,
    )
    assert set(report.recordings) == {"local.mp3", "cloud.mp3"}
    assert report.downloaded == 1
    assert not report.skipped
    assert "cloud.mp3" in opened, "the placeholder must be read, not skipped"
    with zipfile.ZipFile(report.path) as zf:
        assert zf.read("recordings/cloud.mp3") == b"AUDIO-cloud.mp3"
    assert "downloaded from OneDrive" in report.outcome()


def test_no_room_to_download_names_the_files_and_says_what_to_do(tmp_path: Path) -> None:
    data = tmp_path / "data"
    _seed(data)
    rec = _recordings(tmp_path, "local.mp3", "cloud.mp3")
    report = create_backup_report(
        data,
        tmp_path / f"b{BACKUP_SUFFIX}",
        recordings_dir=rec,
        include_recordings=True,
        stat=_cloud_stat("cloud.mp3"),
        free_bytes=lambda _p: 0,
    )
    assert report.recordings == ("local.mp3",)
    assert report.skipped == (sf.SkippedFile("cloud.mp3", sf.REASON_NO_SPACE_TO_DOWNLOAD),)
    assert "1 of your 2 recordings" in report.outcome()
    manifest = read_manifest(report.path)
    assert manifest.skipped == [{"name": "cloud.mp3", "reason": sf.REASON_NO_SPACE_TO_DOWNLOAD}]


def test_a_recording_in_use_is_named_and_the_rest_are_saved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data = tmp_path / "data"
    _seed(data)
    rec = _recordings(tmp_path, "a.mp3", "busy.mp3")
    real_open = builtins.open

    def _open(file, *args, **kwargs):  # type: ignore[no-untyped-def]
        if Path(file).name == "busy.mp3":
            error = PermissionError(errno.EACCES, "sharing violation")
            error.winerror = 32  # type: ignore[attr-defined]
            raise error
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(backup_recordings, "open", _open, raising=False)
    report = create_backup_report(
        data, tmp_path / f"b{BACKUP_SUFFIX}", recordings_dir=rec, include_recordings=True
    )
    assert report.recordings == ("a.mp3",)
    assert [(item.name, item.reason) for item in report.skipped] == [("busy.mp3", sf.REASON_IN_USE)]
    assert "Close the program" in report.outcome()


def test_backups_in_a_shared_folder_are_not_carried_as_recordings(tmp_path: Path) -> None:
    data = tmp_path / "data"
    _seed(data)
    rec = _recordings(tmp_path, "show.mp3", "old-backup.qrbackup", "desktop.ini")
    dest = rec / f"tonight{BACKUP_SUFFIX}"  # saved into the same OneDrive folder
    report = create_backup_report(data, dest, recordings_dir=rec, include_recordings=True)
    assert report.recordings == ("show.mp3",)
    assert report.recordings_eligible == 1


def test_the_include_question_counts_size_and_onedrive_files(tmp_path: Path) -> None:
    rec = _recordings(tmp_path, "a.mp3", "b.mp3")
    plan = plan_recordings(rec, stat=_cloud_stat("b.mp3"))
    assert len(plan.files) == 2 and plan.cloud_only == 1
    question = plan.question()
    assert "2 recordings" in question
    assert "1 of them are stored only in OneDrive" in question
    assert str(rec) in question


def test_restore_leaves_recordings_already_there_alone(tmp_path: Path) -> None:
    data = tmp_path / "data"
    _seed(data)
    rec = _recordings(tmp_path, "a.mp3", "b.mp3")
    report = create_backup_report(
        data, tmp_path / f"b{BACKUP_SUFFIX}", recordings_dir=rec, include_recordings=True
    )
    (rec / "b.mp3").unlink()
    result = restore_backup(report.path, tmp_path / "new", recordings_dir=rec)
    assert result.recordings == ("b.mp3",)
    assert result.skipped == (sf.SkippedFile("a.mp3", sf.REASON_ALREADY_THERE),)
    assert (tmp_path / "new" / "podcasts_library.json").is_file()


def test_restore_with_no_recordings_folder_names_what_it_did_not_restore(tmp_path: Path) -> None:
    data = tmp_path / "data"
    _seed(data)
    rec = _recordings(tmp_path, "a.mp3")
    report = create_backup_report(
        data, tmp_path / f"b{BACKUP_SUFFIX}", recordings_dir=rec, include_recordings=True
    )
    result = restore_backup(report.path, tmp_path / "new", recordings_dir=None)
    assert [item.name for item in result.skipped] == ["a.mp3"]


def test_an_update_snapshot_never_carries_the_shared_podcast_library(tmp_path: Path) -> None:
    from quill.core.updater import snapshots

    data = tmp_path / "data"
    _seed(data)
    out = snapshots._radio(data, tmp_path / f"s{BACKUP_SUFFIX}", "3.2.0")
    with zipfile.ZipFile(out) as zf:
        assert "data/podcasts_library.json" not in zf.namelist()
        assert "data/radio_favorites.json" in zf.namelist()


def test_the_ui_reads_the_recordings_folder_from_recording_settings(tmp_path: Path) -> None:
    from quill.ui.radio import backup_ui

    frame = SimpleNamespace(
        _radio_recording_settings=SimpleNamespace(destination_root=str(tmp_path / "OneDrive")),
        settings=SimpleNamespace(),  # the app settings have no recordings folder
    )
    assert backup_ui._recordings_dir(frame) == tmp_path / "OneDrive"


def test_the_restore_sentence_counts_what_was_left_alone() -> None:
    from quill.core.radio.backup import RestoreResult
    from quill.ui.radio import backup_ui

    result = RestoreResult(
        ("radio_favorites.json",),
        ("b.mp3",),
        (
            sf.SkippedFile("a.mp3", sf.REASON_ALREADY_THERE),
            sf.SkippedFile("c.mp3", sf.REASON_TOO_LONG),
        ),
    )
    sentence = backup_ui.restore_outcome(result)
    assert "1 recording was already in your recordings folder" in sentence
    assert "1 recording was left out" in sentence
