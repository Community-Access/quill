"""LibriVox recordings as library results -- the join that never existed.

Quill Radio finds the recording and the Library finds the text, and until this
bridge they were two searches in two places with nothing knowing they were the
same book.
"""

from __future__ import annotations

from quill.core.library.audio_sources import from_librivox, from_librivox_books
from quill.core.library.model import Book
from quill.core.library.works import group
from quill.core.media.librivox import LibriVoxBook, LibriVoxSection


def _recording(**kwargs) -> LibriVoxBook:
    base = {
        "book_id": "42",
        "title": "Middlemarch",
        "authors": "Eliot, George",
        "sections": (
            LibriVoxSection(index=1, title="Chapter 1", url="https://a.example/1.mp3"),
            LibriVoxSection(index=2, title="Chapter 2", url="https://a.example/2.mp3"),
        ),
    }
    base.update(kwargs)
    return LibriVoxBook(**base)


def test_a_recording_becomes_one_result_not_one_per_chapter() -> None:
    # Dozens of section links would bury the book. Playing the whole thing in
    # order is Quill Radio's job, and it already does it well.
    book = from_librivox(_recording())
    assert set(book.formats) == {"audio"}
    assert book.formats["audio"] == "https://a.example/1.mp3"
    assert book.source == "librivox"


def test_authors_are_split_the_way_LibriVox_writes_them() -> None:
    book = from_librivox(_recording(authors="Eliot, George; Lewes, George Henry"))
    assert book.authors == ("Eliot, George", "Lewes, George Henry")


def test_a_recording_with_no_playable_file_is_still_a_record() -> None:
    # LibriVox occasionally lists a work whose files have moved, and "we know
    # this recording exists" beats dropping it silently.
    book = from_librivox(_recording(sections=()))
    assert book.formats == {}
    assert book.site_url


def test_the_recording_and_the_text_land_on_one_row() -> None:
    text = Book(
        book_id="pg",
        title="Middlemarch",
        authors=("George Eliot",),
        source="gutenberg",
        formats={"epub": "u"},
    )
    works = group([text, *from_librivox_books([_recording()])])
    assert len(works) == 1
    assert works[0].has_text and works[0].has_audio
    assert "read or listen" in works[0].row_label()
