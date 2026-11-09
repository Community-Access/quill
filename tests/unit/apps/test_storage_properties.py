"""The drive a file is on, in the family's existing properties windows (todo
item 46): Quill Radio's Local Media Item Properties and Quill Converter's File
Properties. Fakes only: no real window is shown and no real drive is needed."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

DRIVE = [
    "Drive: E:\\ (STICK), removable drive, FAT32",
    "Drive capacity: 14.9 GB (16,005,464,064 bytes)",
    "Drive used: 2.00 GB (2,147,483,648 bytes), 13 percent",
    "Drive free: 12.9 GB (13,857,980,416 bytes)",
]


def test_radio_properties_end_with_the_drive(tmp_path: Path) -> None:
    from quill.core.radio.local_media import MediaItem, Playlist
    from quill.ui.radio.local_media_manage import properties_text

    song = tmp_path / "song.mp3"
    song.write_bytes(b"x" * 2048)
    item = MediaItem(id=1, path=str(song), title="Song")
    playlist = Playlist(id="p", name="Mine", items=[item])
    asked: list[Path] = []
    text = properties_text(item, playlist, volume=lambda path: asked.append(path) or DRIVE)
    lines = text.splitlines()
    assert lines[-4:] == DRIVE
    assert lines[0] == "Title: Song" and "File name: song.mp3" in lines
    assert asked == [song]


def test_radio_properties_of_a_missing_file_still_say_the_drive(tmp_path: Path) -> None:
    from quill.core.radio.local_media import MediaItem, Playlist
    from quill.ui.radio.local_media_manage import properties_text

    item = MediaItem(id=1, path=str(tmp_path / "gone.mp3"))
    playlist = Playlist(id="p", name="Mine", items=[item])
    unavailable = ["Drive: not available. The drive could not be found or is not ready."]
    text = properties_text(item, playlist, volume=lambda _p: unavailable)
    assert "On this computer: no, missing" in text
    assert text.endswith(unavailable[0])


def test_radio_properties_read_the_real_drive_by_default(tmp_path: Path) -> None:
    from quill.core.radio.local_media import MediaItem, Playlist
    from quill.ui.radio.local_media_manage import properties_text

    song = tmp_path / "song.mp3"
    song.write_bytes(b"x")
    item = MediaItem(id=1, path=str(song))
    text = properties_text(item, Playlist(id="p", name="Mine", items=[item]))
    assert "Drive: " in text and ("Drive free: " in text or "not available" in text)


class _Converter:
    """Just enough of the Converter window for File Properties."""

    def __init__(self, source: Path | None) -> None:
        from quill.apps.converter_lifecycle import ConverterLifecycleMixin

        self.show = ConverterLifecycleMixin.show_properties.__get__(self)
        self.source = source
        self.said: list[str] = []

    def _preview_source(self) -> Path | None:
        return self.source

    def _announce(self, text: str, **_kwargs: Any) -> None:
        self.said.append(text)

    def _set_status(self, text: str) -> None:
        self.status = text


def test_converter_file_properties_end_with_the_drive(wx_app, monkeypatch, tmp_path) -> None:
    pytest.importorskip("wx")
    from quill.core import volume_info
    from quill.core.audio import media_probe
    from quill.ui import converter_dialogs

    shown: list[tuple[str, str]] = []
    monkeypatch.setattr(media_probe, "probe", lambda path: path)
    monkeypatch.setattr(media_probe, "describe", lambda path: [f"File: {path.name}"])
    monkeypatch.setattr(volume_info, "describe_volume", lambda path: DRIVE)
    monkeypatch.setattr(converter_dialogs, "show_text", lambda _h, t, text: shown.append((t, text)))
    host = _Converter(tmp_path / "talk.mp3")
    jobs = _queued(monkeypatch)
    host.show()
    assert shown == [] and host.status == "Reading talk.mp3."  # off the UI thread
    host.show()  # a second press while it reads starts nothing more
    assert host.said == ["Still reading the file."] and len(jobs) == 1
    work, deliver = jobs[0]
    deliver(work(), None)
    assert shown == [("File Properties", "\n".join(["File: talk.mp3", *DRIVE]))]


def test_converter_file_properties_with_nothing_highlighted(wx_app) -> None:
    host = _Converter(None)
    host.show()
    assert host.said == ["Highlight a file in the queue first."]


def _queued(monkeypatch) -> list:
    from quill.apps import converter_lifecycle

    jobs: list = []
    monkeypatch.setattr(
        converter_lifecycle, "_off_ui_thread", lambda work, deliver: jobs.append((work, deliver))
    )
    return jobs


def test_converter_file_properties_that_cannot_be_read_are_said(
    wx_app, monkeypatch, tmp_path
) -> None:
    host = _Converter(tmp_path / "talk.mp3")
    jobs = _queued(monkeypatch)
    host.show()
    jobs[0][1](None, OSError("the drive went away"))
    assert host.said == ["Could not read talk.mp3: the drive went away"]
    host.show()  # and the next press reads again
    assert len(jobs) == 2
