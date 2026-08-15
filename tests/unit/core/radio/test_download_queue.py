"""The download queue, and where a download lands when it arrives.

Downloading one thing needs no queue. Downloading a forty-chapter book while
listening to something else is the real shape, and these pin the properties that
make that survivable: order, honesty about what failed, nothing lost by
stopping, and a folder somebody can actually navigate afterwards.
"""

from __future__ import annotations

import pytest

from quill.core.radio.download_prefs import (
    FOLDER_BOOKS,
    FOLDER_PODCASTS,
    DownloadPrefs,
    kind_of,
    load,
    plan_destination,
    safe_segment,
    save,
)
from quill.core.radio.download_queue import (
    DONE,
    FAILED,
    RUNNING,
    WAITING,
    DownloadQueue,
)
from quill.core.radio.models import RadioStation


def _chapter(name: str) -> RadioStation:
    return RadioStation(
        name=name, stream_url=f"https://a/{name}.mp3", source="LibriVox", is_recording=True
    )


def _queue(*names: str) -> DownloadQueue:
    queue = DownloadQueue()
    queue.add_all([_chapter(n) for n in names], "D:/x", group="Middlemarch")
    return queue


# -- filing ---------------------------------------------------------------


def test_a_podcast_is_filed_under_its_show() -> None:
    # A podcast is a series you follow; a folder per show is how anybody would
    # file one by hand.
    where = plan_destination(
        DownloadPrefs(root="D:/S"), source="Podcasts (Apple)", work="The Rest Is History"
    )
    assert where.parts[-2:] == (FOLDER_PODCASTS, "The Rest Is History")


def test_a_book_gets_a_folder_because_a_book_is_a_folder() -> None:
    where = plan_destination(DownloadPrefs(root="D:/S"), source="LibriVox", work="Middlemarch")
    assert where.parts[-2:] == (FOLDER_BOOKS, "Middlemarch")


def test_an_author_folder_appears_only_once_there_is_a_second_book() -> None:
    # An author folder holding exactly one book is a folder you open and
    # immediately leave.
    prefs = DownloadPrefs(root="D:/S")
    first = plan_destination(
        prefs, source="LibriVox", work="Middlemarch", author="George Eliot", existing_authors={}
    )
    assert "George Eliot" not in first.parts

    second = plan_destination(
        prefs,
        source="LibriVox",
        work="Silas Marner",
        author="George Eliot",
        existing_authors={"George Eliot": 1},
    )
    assert second.parts[-3:] == (FOLDER_BOOKS, "George Eliot", "Silas Marner")


def test_the_filing_rules_can_each_be_switched_off() -> None:
    flat = DownloadPrefs(root="D:/S", folder_per_book=False, group_books_by_author=False)
    where = plan_destination(flat, source="LibriVox", work="Middlemarch", author="George Eliot")
    assert where.parts[-1] == FOLDER_BOOKS


@pytest.mark.parametrize(
    ("source", "shelf"),
    [
        ("LibriVox", "Books"),
        ("Project Gutenberg", "Books"),
        ("Podcasts (Apple)", "Podcasts"),
        ("ccMixter", "Music"),
        ("Some New Directory", "Recordings"),
    ],
)
def test_every_source_lands_on_a_named_shelf(source: str, shelf: str) -> None:
    assert kind_of(source) == shelf


def test_a_name_windows_cannot_use_is_made_usable() -> None:
    # A reserved name produces a folder that cannot be created at all, and a
    # trailing dot is silently dropped -- turning two books into one folder.
    assert safe_segment("CON") == "CON file"
    assert safe_segment("Middlemarch: A Study/Vol 1.  ") == "Middlemarch A StudyVol 1"
    assert safe_segment("") == "Untitled"


def test_preferences_survive_a_restart(tmp_path) -> None:
    save(tmp_path, DownloadPrefs(root=str(tmp_path), always_ask=True))
    assert load(tmp_path).always_ask is True


def test_a_damaged_preferences_file_reads_as_the_defaults(tmp_path) -> None:
    (tmp_path / "radio_downloads.json").write_text("{not json", encoding="utf-8")
    assert load(tmp_path).folder_per_book is True


# -- the queue ------------------------------------------------------------


def test_the_queue_keeps_the_order_you_asked_in() -> None:
    # In order means a part-finished book is a playable prefix.
    queue = _queue("One", "Two", "Three")
    assert [item.name for item in queue.items] == ["One", "Two", "Three"]
    assert queue.next_waiting().name == "One"


def test_a_finished_row_stays_in_the_list() -> None:
    # "Did that actually download?" is the question asked most, and a queue that
    # empties itself as it succeeds cannot answer it.
    queue = _queue("One")
    item = queue.items[0]
    queue.start(item)
    queue.finish(item, "D:/x/One.mp3")
    assert queue.items == [item]
    assert item.state == DONE
    assert item.path.endswith("One.mp3")


def test_a_row_reads_as_a_sentence_with_its_state_last() -> None:
    queue = _queue("Chapter 4")
    item = queue.items[0]
    assert item.row_label() == "Chapter 4, Middlemarch, waiting"
    queue.fail(item, "the server refused")
    assert item.row_label().endswith("failed, the server refused")


def test_cancelling_leaves_a_finished_row_alone() -> None:
    queue = _queue("One")
    item = queue.items[0]
    queue.finish(item, "D:/x/One.mp3")
    assert queue.cancel(item) is False
    assert item.state == DONE


def test_the_running_row_cannot_be_removed_from_under_the_transfer() -> None:
    queue = _queue("One")
    item = queue.items[0]
    queue.start(item)
    assert queue.remove(item) is False
    assert item.state == RUNNING


def test_clearing_finished_keeps_what_is_still_outstanding() -> None:
    queue = _queue("One", "Two", "Three")
    queue.finish(queue.items[0], "p")
    queue.fail(queue.items[1], "no")
    assert queue.clear_finished() == 2
    assert [i.state for i in queue.items] == [WAITING]


def test_clearing_everything_cancels_rather_than_orphaning() -> None:
    queue = _queue("One", "Two")
    queue.start(queue.items[0])
    cancelled = queue.items[0]
    assert queue.clear_all() == 2
    assert queue.items == []
    # The item object still says it was cancelled, so a transfer reporting back
    # finds a coherent state rather than a row that simply vanished.
    assert cancelled.state == "cancelled"


def test_the_summary_counts_what_is_left_first() -> None:
    queue = _queue("One", "Two", "Three")
    queue.finish(queue.items[0], "p")
    queue.fail(queue.items[1], "no")
    said = queue.summary()
    assert said.startswith("1 to go")
    assert "1 saved" in said and "1 failed" in said
    assert DownloadQueue().summary() == "Nothing in the download queue."


def test_closing_says_what_happens_either_way() -> None:
    # A queue that silently keeps running is exactly as surprising as one that
    # silently stops.
    queue = _queue("One", "Two")
    assert "background" in queue.closing_message(keep_going=True)
    stopped = queue.closing_message(keep_going=False)
    assert "stopped" in stopped
    assert "resume" in stopped


def test_closing_says_nothing_when_there_is_nothing_outstanding() -> None:
    queue = _queue("One")
    queue.finish(queue.items[0], "p")
    assert queue.closing_message(keep_going=True) == ""
    assert queue.closing_message(keep_going=False) == ""


def test_an_item_that_failed_is_over_but_not_successful() -> None:
    queue = _queue("One")
    queue.fail(queue.items[0], "no")
    assert queue.items[0].state == FAILED
    assert queue.items[0].is_finished is True
    assert queue.outstanding == 0
