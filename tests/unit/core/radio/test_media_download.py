"""Saving a recording, and saving a whole book.

A book is not one file: a LibriVox novel is forty chapters, each its own
address. So the properties that matter are the ones that make a long, fragile,
interruptible transfer survivable -- resume after a drop, stop within a chunk
rather than at the end of a 90 MB chapter, and one bad address costing one
chapter rather than the whole book.
"""

from __future__ import annotations

import threading

import pytest

from quill.core.radio import media_download
from quill.core.radio.media_download import (
    BookProgress,
    DownloadError,
    download_book,
    download_one,
    summarise,
)
from quill.core.radio.models import RadioStation


def _chapter(name: str, url: str = "https://a/x.mp3", source: str = "LibriVox"):
    return RadioStation(name=name, stream_url=url, source=source, is_recording=True)


@pytest.fixture
def fake_fetch(monkeypatch, tmp_path):
    """Write a file instead of reaching the network, recording each call."""
    calls: list[str] = []

    def _fetch(url, destination, *, cancel=None, on_bytes=None):
        calls.append(url)
        if "broken" in url:
            raise DownloadError("Could not download that file: no.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"audio")
        return destination

    monkeypatch.setattr(media_download, "_fetch_to_file", _fetch)
    return calls


def test_one_chapter_is_saved_under_a_readable_name(fake_fetch, tmp_path) -> None:
    path = download_one(_chapter("Middlemarch, chapter 4"), tmp_path)
    assert path.name == "Middlemarch chapter 4.mp3"
    assert path.read_bytes() == b"audio"


def test_the_rights_check_happens_here_too_not_only_in_the_menu(fake_fetch, tmp_path) -> None:
    # A menu item is a convenience; this is the boundary. Nothing reaches the
    # network until the policy has said yes.
    live = RadioStation(name="WBUR", stream_url="https://a/live", source="Radio Browser")
    with pytest.raises(DownloadError) as caught:
        download_one(live, tmp_path)
    assert "Record Station" in str(caught.value)
    assert fake_fetch == []


def test_a_creative_commons_licence_is_written_beside_the_audio(fake_fetch, tmp_path) -> None:
    # Saving the audio and discarding the terms strips exactly the information
    # the licence exists to travel with.
    row = RadioStation(
        name="Xtended Chords",
        stream_url="https://a/x.ogg",
        source="ccMixter",
        is_recording=True,
        tags=("Attribution Noncommercial (4.0)",),
    )
    path = download_one(row, tmp_path)
    note = path.with_suffix(path.suffix + ".licence.txt")
    assert note.is_file()
    assert "Attribution Noncommercial (4.0)" in note.read_text(encoding="utf-8")


def test_a_book_saves_every_chapter_in_order(fake_fetch, tmp_path) -> None:
    # In order, so a part-finished book is the *first* N chapters -- something
    # you can start listening to, rather than a scattering you cannot.
    chapters = [_chapter(f"Chapter {n}", f"https://a/{n}.mp3") for n in range(1, 5)]
    progress = download_book(chapters, tmp_path)
    assert progress.done == 4
    assert progress.is_complete
    assert fake_fetch == [f"https://a/{n}.mp3" for n in range(1, 5)]


def test_one_bad_chapter_costs_one_chapter(fake_fetch, tmp_path) -> None:
    # Forty chapters and one bad address should leave you thirty-nine chapters
    # and an honest count, not an error and nothing.
    chapters = [
        _chapter("Good one", "https://a/1.mp3"),
        _chapter("Bad one", "https://a/broken.mp3"),
        _chapter("Good two", "https://a/3.mp3"),
    ]
    progress = download_book(chapters, tmp_path)
    assert progress.done == 2
    assert progress.failed == ["Bad one"]
    assert "could not be downloaded" in summarise(progress)


def test_stopping_keeps_what_already_arrived(fake_fetch, tmp_path) -> None:
    cancel = threading.Event()
    chapters = [_chapter(f"Chapter {n}", f"https://a/{n}.mp3") for n in range(1, 6)]

    def _stop_after_two(state: BookProgress) -> None:
        if state.done >= 2:
            cancel.set()

    progress = download_book(chapters, tmp_path, cancel=cancel, on_progress=_stop_after_two)
    assert progress.done == 2
    assert "2 of 5 saved" in summarise(progress, stopped=True)


def test_a_stopped_chapter_is_not_counted_as_a_failure(fake_fetch, tmp_path) -> None:
    # Stopping is a choice, not a fault, and reporting it as one would be
    # telling somebody their download broke when they stopped it.
    cancel = threading.Event()
    cancel.set()
    progress = download_book([_chapter("One")], tmp_path, cancel=cancel)
    assert progress.failed == []


def test_progress_is_counted_in_chapters_a_person_can_hold() -> None:
    # "Chapter 12 of 40" is something you can hold; a byte count is not.
    assert BookProgress(done=12, total=40).spoken() == "12 of 40."
    assert BookProgress(done=40, total=40).spoken() == "Downloaded all 40."
    assert BookProgress().spoken() == "Nothing to download."


def test_the_summary_is_honest_about_every_ending() -> None:
    assert summarise(BookProgress(total=0)) == "There was nothing to download."
    assert summarise(BookProgress(done=3, total=3)) == "Downloaded all 3."
    assert "stopped" in summarise(BookProgress(done=1, total=3), stopped=True).lower()


def test_only_a_web_address_is_ever_fetched(tmp_path) -> None:
    with pytest.raises(DownloadError):
        media_download._fetch_to_file("file:///etc/passwd", tmp_path / "x")


def test_a_chapter_already_on_disk_is_not_transferred_again(monkeypatch, tmp_path) -> None:
    """Re-queueing a stopped book must *resume*: saved chapters answer from
    disk. Files only ever arrive whole (written to .part, then renamed), so an
    existing destination is trustworthy and fetching it again would re-transfer
    a book that is already there."""
    from quill.core.radio import downloadable

    chapter = _chapter("Chapter 1", "https://a/1.mp3")
    existing = tmp_path / downloadable.suggested_filename(chapter, url="https://a/1.mp3")
    existing.write_bytes(b"audio")

    def _explode(request, **_kwargs):  # the network must not be touched
        raise AssertionError("fetched a file that was already saved")

    monkeypatch.setattr(media_download.urllib.request, "urlopen", _explode)
    assert download_one(chapter, tmp_path) == existing


def test_a_finished_partial_the_server_cannot_extend_is_completed(monkeypatch, tmp_path) -> None:
    """HTTP 416 with a resume offset means the .part already holds the whole
    file -- finish the rename instead of failing the same way forever."""
    import urllib.error

    destination = tmp_path / "book.mp3"
    partial = tmp_path / "book.mp3.part"
    partial.write_bytes(b"whole file")

    def _range_not_satisfiable(request, **_kwargs):
        raise urllib.error.HTTPError("https://a/book.mp3", 416, "Range Not Satisfiable", None, None)

    monkeypatch.setattr(media_download.urllib.request, "urlopen", _range_not_satisfiable)
    result = media_download._fetch_to_file("https://a/book.mp3", destination)
    assert result == destination
    assert destination.read_bytes() == b"whole file"
    assert not partial.exists()
