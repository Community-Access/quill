"""Bookmarks that mean the same thing in both apps (list.md section 4).

Four things were true before this, and each is a test here:

* Quill Radio had **no** bookmark store at all (4.1), so a moment in a station,
  a recording or a YouTube row could not be kept.
* A podcast note **required text** (4.2), so a bare "I was here" was not a
  thing you could record -- which is the most common kind.
* Nothing anchored to a ``media_url`` (4.3), so the only bookmarkable things
  were books and podcast episodes.
* The two stores were separate (4.5), so a bookmark made in one app was
  invisible in the other.

The load-bearing test is
:func:`test_both_apps_build_the_same_anchor_for_the_same_episode`. That single
equality is the whole of the sharing: no sync, no merge, no protocol -- two
apps writing the same key into the same file. Break it and the feature silently
becomes two features.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core import bookmark_anchors, bookmark_ops
from quill.core.media.bookmarks import BookmarkStore, MediaBookmark


@pytest.fixture
def store(tmp_path: Path) -> BookmarkStore:
    return BookmarkStore(tmp_path / "media_bookmarks.json")


# -- the anchor vocabulary (4.3) --------------------------------------------------


def test_every_kind_of_playable_thing_has_an_anchor() -> None:
    assert bookmark_anchors.for_episode("the-daily", "ep-412").startswith("podcast:")
    assert bookmark_anchors.for_station("https://s/live").startswith("station:")
    assert bookmark_anchors.for_video("https://youtu.be/x").startswith("video:")
    assert bookmark_anchors.for_recording("C:/rec/a.mp3").startswith("recording:")
    assert bookmark_anchors.for_book("book-1").startswith("book:")
    assert bookmark_anchors.for_media("https://e/thing").startswith("media:")


def test_an_anchor_is_readable_by_a_person() -> None:
    """It is their data, on their disk, and a store you cannot read is a store
    you cannot repair."""
    assert bookmark_anchors.for_episode("the-daily", "ep-412") == "podcast:the-daily|ep-412"


def test_half_an_episode_is_no_anchor_at_all() -> None:
    """An anchor naming a show and no episode would collect every episode's
    bookmarks into one row."""
    assert bookmark_anchors.for_episode("the-daily", "") == ""
    assert bookmark_anchors.for_episode("", "ep-412") == ""


def test_an_empty_address_is_no_anchor() -> None:
    for build in (
        bookmark_anchors.for_station,
        bookmark_anchors.for_video,
        bookmark_anchors.for_recording,
        bookmark_anchors.for_media,
        bookmark_anchors.for_book,
    ):
        assert build("") == ""
        assert build("   ") == ""
        assert build(None) == ""


def test_the_kind_reads_back_off_the_anchor() -> None:
    assert bookmark_anchors.kind_of("podcast:a|b") == bookmark_anchors.PODCAST
    assert bookmark_anchors.kind_of("station:https://s") == bookmark_anchors.STATION


def test_a_kind_from_a_future_version_reads_as_media_not_as_damage() -> None:
    assert bookmark_anchors.kind_of("hologram:whatever") == bookmark_anchors.OTHER
    assert bookmark_anchors.kind_of("") == bookmark_anchors.OTHER


def test_an_episode_anchor_takes_both_halves_back_apart() -> None:
    anchor = bookmark_anchors.for_episode("the-daily", "ep-412")
    assert bookmark_anchors.episode_parts(anchor) == ("the-daily", "ep-412")


def test_a_non_episode_anchor_yields_neither_half() -> None:
    """Both or neither: one half would send a caller looking in no show."""
    assert bookmark_anchors.episode_parts("station:https://s") == ("", "")
    assert bookmark_anchors.episode_parts("podcast:onlyshow") == ("", "")


def test_a_url_with_a_colon_in_it_survives_the_round_trip() -> None:
    url = "https://example.com:8443/live?x=1"
    assert bookmark_anchors.body_of(bookmark_anchors.for_station(url)) == url


def test_a_recording_is_the_one_anchor_that_does_not_travel() -> None:
    """A bookmark in one machine's file is meaningless in another's."""
    assert bookmark_anchors.is_portable(bookmark_anchors.for_recording("C:/a.mp3")) is False
    assert bookmark_anchors.is_portable(bookmark_anchors.for_station("https://s")) is True
    assert bookmark_anchors.is_portable(bookmark_anchors.for_episode("a", "b")) is True


# -- the sharing (4.5) ------------------------------------------------------------


def test_both_apps_build_the_same_anchor_for_the_same_episode() -> None:
    """The whole of 4.5, in one equality.

    Quill Radio holds a show id and a guid; QUILL Cast holds a show id and a
    guid. If the two spellings ever diverge, the shared bookmark list silently
    becomes two lists and nobody gets an error.
    """
    from quill.ui.podcasts import bookmarks_wiring as cast_wiring
    from quill.ui.radio import bookmarks_wiring as radio_wiring

    class _Station:
        show_id = "the-daily"
        episode_guid = "ep-412"
        stream_url = "https://cdn/ep-412.mp3"
        name = "Episode 412"
        source = "Subscribed Podcasts"

    class _State:
        show_id = "the-daily"
        episode_guid = "ep-412"
        title = "Episode 412"

    class _Controller:
        state = _State()

        def position_ms(self) -> int:
            return 90_000

    class _RadioHost:
        _radio_controller = type("_C", (), {"state": type("_S", (), {"station": _Station()})()})()

    class _CastHost:
        _podcast_controller = _Controller()
        _podcast_library = None

    radio_anchor, _radio_pos, _radio_title = radio_wiring.target_for(_RadioHost())
    cast_anchor, cast_pos, _cast_title = cast_wiring.target_for(_CastHost())

    assert radio_anchor == cast_anchor == "podcast:the-daily|ep-412"
    assert cast_pos == 90_000


def test_one_store_holds_every_kind(store: BookmarkStore) -> None:
    store.add(bookmark_anchors.for_episode("d", "1"), 1000, title="An episode")
    store.add(bookmark_anchors.for_station("https://s"), 2000, title="A station")
    store.add(bookmark_anchors.for_recording("C:/a.mp3"), 3000, title="A recording")

    rows = store.all_bookmarks()

    assert len(rows) == 3
    assert {bookmark_anchors.kind_of(anchor) for anchor, _mark in rows} == {
        bookmark_anchors.PODCAST,
        bookmark_anchors.STATION,
        bookmark_anchors.RECORDING,
    }


def test_the_title_rides_on_the_row(store: BookmarkStore) -> None:
    """A shared list has to name a station QUILL Cast never heard of."""
    anchor = bookmark_anchors.for_station("https://s/live")
    store.add(anchor, 5000, title="Main Menu Live")

    assert store.list(anchor)[0].title == "Main Menu Live"


def test_a_title_written_before_this_reads_as_blank_not_as_a_crash(
    store: BookmarkStore, tmp_path: Path
) -> None:
    """An existing media_bookmarks.json has no titles in it at all."""
    import json

    (tmp_path / "media_bookmarks.json").write_text(
        json.dumps({"book:old": [{"position_ms": 42, "note": "here"}]}), encoding="utf-8"
    )
    mark = store.list("book:old")[0]
    assert mark.title == ""
    assert mark.note == "here"


# -- the verbs (4.4) --------------------------------------------------------------


def test_a_bookmark_needs_no_note(store: BookmarkStore) -> None:
    """4.2: "I was here" is the most common kind, and demanding a sentence for
    it was demanding a sentence."""
    anchor = bookmark_anchors.for_station("https://s")
    mark, said = bookmark_ops.add(store, anchor, 61_000, title="Main Menu")

    assert mark is not None
    assert mark.note == "" and mark.label == ""
    assert "1 minute 1 second" in said
    assert "Main Menu" in said


def test_nothing_playing_is_a_sentence_not_a_silent_no_op(store: BookmarkStore) -> None:
    mark, said = bookmark_ops.add(store, "", 1000)
    assert mark is None
    assert said == bookmark_ops.NOTHING_PLAYING


def test_pressing_the_key_twice_does_not_make_two_bookmarks(store: BookmarkStore) -> None:
    anchor = bookmark_anchors.for_station("https://s")
    bookmark_ops.add(store, anchor, 60_000)
    mark, said = bookmark_ops.add(store, anchor, 60_900)

    assert mark is None
    assert "already a bookmark" in said
    assert len(store.list(anchor)) == 1


def test_a_second_bookmark_further_along_is_a_real_one(store: BookmarkStore) -> None:
    anchor = bookmark_anchors.for_station("https://s")
    bookmark_ops.add(store, anchor, 60_000)
    mark, _said = bookmark_ops.add(store, anchor, 600_000)

    assert mark is not None
    assert len(store.list(anchor)) == 2


def test_a_note_makes_a_near_duplicate_worth_keeping(store: BookmarkStore) -> None:
    """Somebody who typed something meant it, whatever the timestamp says."""
    anchor = bookmark_anchors.for_station("https://s")
    bookmark_ops.add(store, anchor, 60_000)
    mark, _said = bookmark_ops.add(store, anchor, 60_500, note="the good bit")

    assert mark is not None


def test_removing_says_where_it_was(store: BookmarkStore) -> None:
    anchor = bookmark_anchors.for_station("https://s")
    bookmark_ops.add(store, anchor, 3_661_000)

    removed, said = bookmark_ops.remove(store, anchor, 3_661_000)

    assert removed is True
    assert "1 hour 1 minute 1 second" in said
    assert store.list(anchor) == []


def test_removing_something_already_gone_says_so(store: BookmarkStore) -> None:
    removed, said = bookmark_ops.remove(store, "station:https://s", 1000)
    assert removed is False
    assert "no longer there" in said


# -- what it says -----------------------------------------------------------------


def test_a_position_is_spoken_in_words_not_punctuation() -> None:
    """A screen reader given "1:02:03" reads punctuation."""
    assert bookmark_ops.spoken_position(0) == "0 seconds"
    assert bookmark_ops.spoken_position(1000) == "1 second"
    assert bookmark_ops.spoken_position(61_000) == "1 minute 1 second"
    assert bookmark_ops.spoken_position(3_600_000) == "1 hour"


def test_a_position_is_written_in_digits_for_the_clipboard() -> None:
    assert bookmark_ops.written_position(61_000) == "1:01"


def test_a_row_leads_with_where_because_that_is_how_a_list_is_scanned() -> None:
    anchor = bookmark_anchors.for_station("https://s")
    mark = MediaBookmark(position_ms=61_000, note="the good bit", title="Main Menu")

    row = bookmark_ops.row_label(anchor, mark)

    assert row.startswith("1 minute 1 second")
    assert "the good bit" in row
    assert "Main Menu" in row
    assert row.endswith("Station")


def test_a_multi_line_note_gives_a_row_its_first_line_only() -> None:
    """A list row that wraps is a list row nobody can arrow through."""
    mark = MediaBookmark(position_ms=1000, note="first line\nsecond line")
    assert "second line" not in bookmark_ops.row_label("media:x", mark)


def test_sharing_carries_where_it_points_not_just_the_note() -> None:
    """The note alone is a fragment nobody can act on."""
    anchor = bookmark_anchors.for_station("https://s/live")
    mark = MediaBookmark(position_ms=61_000, note="the good bit", title="Main Menu")

    text = bookmark_ops.share_text(anchor, mark)

    assert "1:01" in text
    assert "the good bit" in text
    assert "Main Menu" in text
    assert "https://s/live" in text


def test_sharing_a_recording_does_not_paste_somebody_a_local_path() -> None:
    """A path into one machine's disk is not something to hand over."""
    anchor = bookmark_anchors.for_recording("C:/rec/a.mp3")
    text = bookmark_ops.share_text(anchor, MediaBookmark(position_ms=1000, title="A recording"))

    assert "C:/rec/a.mp3" not in text
    assert "A recording" in text


def test_an_empty_list_says_how_to_start_one() -> None:
    said = bookmark_ops.summarise([])
    assert "Bookmark This Moment" in said


def test_a_full_list_counts_both_bookmarks_and_things() -> None:
    rows = [
        ("podcast:a|1", MediaBookmark(position_ms=1)),
        ("podcast:a|1", MediaBookmark(position_ms=2)),
        ("station:https://s", MediaBookmark(position_ms=3)),
    ]
    assert bookmark_ops.summarise(rows) == "3 bookmarks across 2 things."
