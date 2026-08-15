"""Everything you started and did not finish, in one list.

QUILL remembered your place in several different things and never showed you
the several together. The rules worth pinning are the ones that decide whether
such a list is trustworthy: nothing offered that cannot be resumed, nothing
counted that is really finished, and one bad source costing the others nothing.
"""

from __future__ import annotations

from quill.core.media.continue_listening import (
    FINISHED_FRACTION,
    MIN_RESUME_MS,
    PROVIDER_LABELS,
    Unfinished,
    from_podcast_library,
    from_resume_store,
    gather,
    spoken_position,
    summarise,
)
from quill.core.podcasts.models import PodcastEpisode, PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary
from quill.core.radio.resume import ResumePoint


def _library() -> PodcastLibrary:
    library = PodcastLibrary()
    library.shows.append(
        PodcastShow(
            id="s1",
            title="The Rest Is History",
            episodes=[
                PodcastEpisode(
                    guid="e1",
                    title="Rome",
                    audio_url="u",
                    duration_seconds=3600,
                    position_ms=1_200_000,
                    published="2026-08-10T10:00:00",
                ),
                PodcastEpisode(
                    guid="e2",
                    title="Nearly over",
                    audio_url="u",
                    duration_seconds=3600,
                    position_ms=3_580_000,
                    published="2026-08-11T10:00:00",
                ),
                PodcastEpisode(
                    guid="e3",
                    title="Barely started",
                    audio_url="u",
                    duration_seconds=3600,
                    position_ms=4_000,
                    published="2026-08-12T10:00:00",
                ),
                PodcastEpisode(
                    guid="e4",
                    title="Already played",
                    audio_url="u",
                    duration_seconds=3600,
                    position_ms=1_000_000,
                    played=True,
                    published="2026-08-13T10:00:00",
                ),
            ],
        )
    )
    return library


class _Store:
    def __init__(self, points):
        self._points = points

    def unfinished(self):
        return self._points


def test_a_podcast_you_are_in_the_middle_of_is_listed() -> None:
    rows = from_podcast_library(_library())
    assert [row.title for row in rows] == ["Rome", "Nearly over"]


def test_the_beginning_is_not_a_place_to_come_back_to() -> None:
    # "Four seconds in" is the beginning, and a row for it is one somebody has
    # to skip past for no gain.
    assert all(row.title != "Barely started" for row in from_podcast_library(_library()))
    assert MIN_RESUME_MS >= 15_000


def test_something_you_finished_is_not_unfinished() -> None:
    rows = gather([lambda: from_podcast_library(_library())])
    assert [row.title for row in rows] == ["Rome"]
    assert FINISHED_FRACTION >= 0.95


def test_something_you_marked_played_is_gone_whatever_its_position_says() -> None:
    assert all(row.title != "Already played" for row in from_podcast_library(_library()))


def test_a_recording_is_listed_with_its_own_name() -> None:
    point = ResumePoint(
        position_ms=600_000,
        duration_ms=7_200_000,
        saved_at=1_000.0,
        label="The Moonstone, chapter 4",
        url="https://a/x.mp3",
    )
    row = from_resume_store(_Store([point]))[0]
    assert row.title == "The Moonstone, chapter 4"
    assert row.provider == "radio"
    assert row.key == "https://a/x.mp3"


def test_newest_first_is_the_only_order() -> None:
    # The question is "what was I doing", and the answer to that is chronological.
    old = Unfinished(title="Old", provider="radio", position_ms=60_000, saved_at=1.0)
    new = Unfinished(title="New", provider="radio", position_ms=60_000, saved_at=99.0)
    assert [row.title for row in gather([lambda: [old, new]])] == ["New", "Old"]


def test_one_broken_source_costs_the_others_nothing() -> None:
    # A podcast library that will not load must not cost you the LibriVox
    # chapter you were halfway through.
    def _explodes():
        raise RuntimeError("no")

    rows = gather([_explodes, lambda: from_podcast_library(_library())])
    assert [row.title for row in rows] == ["Rome"]


def test_every_row_names_its_provider_out_loud() -> None:
    # "The Moonstone, chapter 4" means something different depending on whether
    # Enter starts a podcast, a stream or a file.
    row = from_podcast_library(_library())[0]
    label = row.row_label()
    assert "The Rest Is History" in label
    assert PROVIDER_LABELS["podcast"] in label
    assert "20 minutes in" in label
    assert "33% through" in label


def test_positions_are_spoken_as_words_never_as_a_timecode() -> None:
    assert spoken_position(0) == "0 seconds"
    assert spoken_position(90_000) == "1 minute 30 seconds"
    assert spoken_position(3_725_000) == "1 hour 2 minutes 5 seconds"


def test_the_summary_says_what_it_spans() -> None:
    rows = gather([
        lambda: from_podcast_library(_library()),
        lambda: from_resume_store(
            _Store([
                ResumePoint(
                    position_ms=600_000, duration_ms=7_200_000, saved_at=9e9, label="X", url="u"
                )
            ])
        ),
    ])
    said = summarise(rows)
    assert "2 things" in said
    assert "recordings" in said and "podcasts" in said
    assert summarise([]).startswith("Nothing unfinished")


# -- local files ---------------------------------------------------------


def test_a_local_file_joins_the_list_when_we_know_where_it_is(tmp_path) -> None:
    # The position store keys on contents and holds no path, so the row exists
    # only because the local-only sidecar remembers where the file was seen.
    from quill.core.media.continue_listening import from_position_store
    from quill.core.media.positions import PositionStore

    book = tmp_path / "Chapter 4.mp3"
    book.write_bytes(b"x" * 4096)
    store = PositionStore(tmp_path)
    store.remember(book, 600_000, duration_ms=3_600_000)

    rows = from_position_store(store, tmp_path)
    assert [row.title for row in rows] == ["Chapter 4.mp3"]
    assert rows[0].provider == "file"
    assert rows[0].key == str(book)


def test_a_file_that_has_moved_is_skipped_rather_than_offered(tmp_path) -> None:
    # The position is still perfectly good and will be found again next time
    # the file is played; a row that cannot open is worse than a shorter list.
    from quill.core.media.continue_listening import from_position_store
    from quill.core.media.positions import PositionStore

    book = tmp_path / "Chapter 4.mp3"
    book.write_bytes(b"x" * 4096)
    store = PositionStore(tmp_path)
    store.remember(book, 600_000, duration_ms=3_600_000)
    book.unlink()

    assert from_position_store(store, tmp_path) == []


def test_the_folder_layout_never_reaches_the_synced_record(tmp_path) -> None:
    """A *path* is a fact about one machine and must not travel.

    The bare filename does travel, deliberately -- ``ListeningPosition.label``
    exists so a report can say "2 hours into Chapter 4" rather than into a hash.
    What must never be in there is where the file sits, which is exactly what
    the local-only sidecar is for.
    """
    import json

    from quill.core.media.positions import PositionStore

    book = tmp_path / "Chapter 4.mp3"
    book.write_bytes(b"x" * 4096)
    PositionStore(tmp_path).remember(book, 600_000, duration_ms=3_600_000)

    written = json.dumps(
        json.loads((tmp_path / "listening_positions.json").read_text(encoding="utf-8"))
    )
    assert str(tmp_path) not in written
    assert str(book) not in written
    # ...and the sidecar, which does hold it, is a separate file.
    hint = json.loads((tmp_path / "media_paths.json").read_text(encoding="utf-8"))
    assert str(book) in hint.values()
