"""The Player's half of note cues (x.md item 4): anchoring and announcing.

The rule for *which* notes were crossed is tested in
``tests/unit/core/media/test_note_cues.py``. What is tested here is the thing
that decides whether the rule is even asked a sensible question: the anchor --
where playback was a second ago.

Every bug this feature can have on the listener's side comes from a stale
anchor, and they all sound the same from the outside: a note read out for a
stretch of audio they never listened through. So the anchor has to be *reset*,
not merely updated, at each of the moments below.

No wx: the mixin takes a host and calls ``_announce`` on it, so a fake host is
the whole test harness.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.media.bookmarks import BookmarkStore
from quill.ui.media.note_cue_actions import NO_ANCHOR, NoteCuesMixin, announce_reached


class _Host(NoteCuesMixin):
    """A Player stand-in: a bookmark store, a playhead, and a voice."""

    def __init__(self, store: BookmarkStore, book_key: str = "book-1") -> None:
        self._bookmarks = store
        self._book_key = book_key
        self._player = self
        self._playhead = 0
        self.spoken: list[str] = []

    def playhead_ms(self) -> int:
        return self._playhead

    def _announce(self, message: str) -> None:
        self.spoken.append(message)


@pytest.fixture
def store(tmp_path: Path) -> BookmarkStore:
    return BookmarkStore(tmp_path / "bookmarks.json")


class _Event:
    def __init__(self, checked: bool) -> None:
        self._checked = checked

    def IsChecked(self) -> bool:  # noqa: N802 - wx spelling
        return self._checked


# -- the anchor -------------------------------------------------------------


def test_the_first_tick_of_a_book_announces_nothing(store: BookmarkStore) -> None:
    """There is a position but no interval behind it yet. Announcing here would
    read out a note for audio the listener has not reached."""
    store.add("book-1", 5_000, note="early")
    assert announce_reached(_Host(store), store, "book-1", NO_ANCHOR, 60_000) == 60_000


def test_the_first_tick_still_sets_the_anchor(store: BookmarkStore) -> None:
    """Silent, but not inert -- the next tick needs somewhere to measure from."""
    assert announce_reached(_Host(store), store, "book-1", NO_ANCHOR, 4_200) == 4_200


def test_no_book_means_no_anchor(store: BookmarkStore) -> None:
    """Between books the anchor must go, or the first tick of the next book
    would be measured from the last tick of the previous one."""
    assert announce_reached(_Host(store), store, "", 5_000, 6_000) == NO_ANCHOR


def test_a_crossed_note_is_spoken(store: BookmarkStore) -> None:
    store.add("book-1", 5_500, note="the good bit")
    host = _Host(store)

    anchor = announce_reached(host, store, "book-1", 5_000, 6_000)

    assert host.spoken == ["Note: the good bit"]
    assert anchor == 6_000


def test_a_labelled_bookmark_speaks_its_label(store: BookmarkStore) -> None:
    store.add("book-1", 5_500, label="Chapter 4", note="here")
    host = _Host(store)
    announce_reached(host, store, "book-1", 5_000, 6_000)
    assert host.spoken == ["Chapter 4: here"]


def test_a_bookmark_with_no_note_is_silent(store: BookmarkStore) -> None:
    """A bookmark is a place to jump to; announcing one with nothing to say
    would be noise."""
    store.add("book-1", 5_500)
    host = _Host(store)
    announce_reached(host, store, "book-1", 5_000, 6_000)
    assert host.spoken == []


# -- the toggle -------------------------------------------------------------


def test_the_toggle_is_on_by_default(store: BookmarkStore) -> None:
    """Writing the note is the opt-in: somebody who left notes on a book has
    already said they want them."""
    assert _Host(store)._note_cues_on is True


def test_switching_off_stops_announcing_and_drops_the_anchor(store: BookmarkStore) -> None:
    store.add("book-1", 5_500, note="quiet please")
    host = _Host(store)
    host._playhead = 6_000
    host._last_cue_position_ms = 5_000

    host._on_toggle_note_cues(_Event(False))
    host._announce_reached_notes()

    assert host.spoken == ["Reading notes aloud off."]
    assert host._last_cue_position_ms == NO_ANCHOR


def test_switching_back_on_mid_book_does_not_replay_what_you_skipped(
    store: BookmarkStore,
) -> None:
    """The reason the toggle resets rather than keeps the anchor. Otherwise
    turning it on would announce every note between wherever it was last off
    and wherever you are now."""
    store.add("book-1", 30_000, note="passed while off")
    host = _Host(store)
    host._last_cue_position_ms = 10_000
    host._playhead = 3_600_000

    host._on_toggle_note_cues(_Event(True))
    host.spoken.clear()
    host._announce_reached_notes()

    assert host.spoken == [], "a re-anchoring tick must be silent"
    assert host._last_cue_position_ms == 3_600_000


def test_the_tick_announces_during_ordinary_playback(store: BookmarkStore) -> None:
    store.add("book-1", 5_500, note="say this")
    host = _Host(store)
    host._last_cue_position_ms = 5_000
    host._playhead = 6_000

    host._announce_reached_notes()

    assert host.spoken == ["Note: say this"]


def test_a_tick_while_off_keeps_the_anchor_cleared(store: BookmarkStore) -> None:
    host = _Host(store)
    host._note_cues_on = False
    host._last_cue_position_ms = 5_000

    host._announce_reached_notes()

    assert host._last_cue_position_ms == NO_ANCHOR
