"""Is this episode already downloaded, and can one copy be taken back off?

The gap these close: ``download_cleanup`` could count and remove a whole
show's files, and nothing could answer the question a menu actually asks --
*is this one row saved?* -- so Download was offered on files already on disk
and there was no way to remove just one.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.radio import download_prefs, downloaded_media
from quill.core.radio.models import RadioStation


def _episode(name: str = "Episode One") -> RadioStation:
    return RadioStation(
        name=name,
        stream_url="https://pod.example/ep1.mp3",
        homepage="https://pod.example/feed.xml",
        source="Subscribed Podcasts",
        is_recording=True,
    )


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A data dir whose download root is inside the test's own tmp_path."""
    root = tmp_path / "downloads"
    prefs = download_prefs.DownloadPrefs(root=str(root))
    monkeypatch.setattr(download_prefs, "load", lambda _data_dir: prefs)
    return tmp_path


def _write_download(data_dir: Path, station: RadioStation, *, group: str) -> Path:
    """Put a file exactly where a real download of *station* would land."""
    from quill.core.radio import downloadable

    prefs = download_prefs.load(data_dir)
    folder = download_prefs.plan_destination(
        prefs, source=station.source, work=group, author="", existing_authors={}
    )
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / downloadable.suggested_filename(station)
    path.write_bytes(b"audio")
    return path


def test_a_row_with_no_file_is_not_downloaded(data_dir: Path) -> None:
    assert downloaded_media.is_downloaded(data_dir, _episode(), group="My Show") is False
    assert downloaded_media.downloaded_path(data_dir, _episode(), group="My Show") is None


def test_a_saved_file_is_found_where_the_download_put_it(data_dir: Path) -> None:
    episode = _episode()
    written = _write_download(data_dir, episode, group="My Show")

    assert downloaded_media.downloaded_path(data_dir, episode, group="My Show") == written


def test_the_show_matters_because_the_filing_does(data_dir: Path) -> None:
    # Downloads are filed per show; the same episode title under a different
    # show is a different file, and answering otherwise would offer Remove
    # Download for something that is not there.
    episode = _episode()
    _write_download(data_dir, episode, group="My Show")

    assert downloaded_media.is_downloaded(data_dir, episode, group="Another Show") is False


def test_deleting_a_file_by_hand_un_downloads_it(data_dir: Path) -> None:
    # The folder is the record: there is no index to go stale.
    episode = _episode()
    written = _write_download(data_dir, episode, group="My Show")
    written.unlink()

    assert downloaded_media.is_downloaded(data_dir, episode, group="My Show") is False


def test_remove_takes_the_file_and_its_licence_note(data_dir: Path) -> None:
    episode = _episode()
    written = _write_download(data_dir, episode, group="My Show")
    sidecar = written.with_suffix(written.suffix + ".licence.txt")
    sidecar.write_text("CC BY", encoding="utf-8")

    spoken = downloaded_media.remove_download(data_dir, episode, group="My Show")

    assert not written.exists()
    assert not sidecar.exists()
    assert "Episode One" in spoken
    # The folder stays: the rest of the show is in it, and it is where the
    # next download goes.
    assert written.parent.is_dir()


def test_removing_what_is_not_there_says_so_rather_than_failing(data_dir: Path) -> None:
    spoken = downloaded_media.remove_download(data_dir, _episode(), group="My Show")

    assert "nothing to remove" in spoken


def test_a_row_with_no_address_is_never_downloaded(data_dir: Path) -> None:
    # A lazily-resolved row (a TuneIn station, an unresolved show) has no file
    # name to look for, and must not be probed as though it did.
    unresolved = RadioStation(name="Later", stream_url="")

    assert downloaded_media.is_downloaded(data_dir, unresolved) is False
