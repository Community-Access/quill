"""Chapter auto-skip decisions and the loop guard (1.1.0).

The loop guard is the test that matters: without it a seek's own position
update re-reports the chapter it just left, the skip fires again, and
playback is pinned at one point forever.
"""

from __future__ import annotations

from quill.core.podcasts.chapter_skip import (
    ChapterSkipState,
    active_chapter_index,
    decide,
    should_auto_skip,
)
from quill.core.podcasts.chapters import PodcastChapter

CHAPTERS = [
    PodcastChapter(start_ms=0, title="Intro"),
    PodcastChapter(start_ms=60_000, title="Sponsor"),
    PodcastChapter(start_ms=120_000, title="Interview"),
    PodcastChapter(start_ms=600_000, title="Outro"),
]


class TestActiveChapterIndex:
    def test_before_the_first_chapter_starts_there_is_none(self) -> None:
        chapters = [PodcastChapter(start_ms=5_000, title="Later")]

        assert active_chapter_index(chapters, 1_000) is None

    def test_a_position_inside_a_chapter_finds_it(self) -> None:
        assert active_chapter_index(CHAPTERS, 90_000) == 1

    def test_exactly_on_a_boundary_belongs_to_the_new_chapter(self) -> None:
        assert active_chapter_index(CHAPTERS, 60_000) == 1

    def test_past_the_last_chapter_stays_on_the_last(self) -> None:
        assert active_chapter_index(CHAPTERS, 9_999_999) == 3

    def test_no_chapters_means_no_active_chapter(self) -> None:
        assert active_chapter_index([], 1_000) is None


class TestDecide:
    def test_an_unmarked_chapter_is_left_alone(self) -> None:
        assert decide(CHAPTERS, {1}, 2).kind == "none"

    def test_a_marked_chapter_seeks_to_the_next_one(self) -> None:
        decision = decide(CHAPTERS, {1}, 1)

        assert decision.kind == "seek"
        assert decision.target_index == 2
        assert decision.target_start_ms == 120_000
        assert decision.skipped_title == "Sponsor"

    def test_consecutive_marked_chapters_are_all_stepped_over(self) -> None:
        decision = decide(CHAPTERS, {1, 2}, 1)

        assert decision.target_index == 3
        assert decision.target_title == "Outro"

    def test_marking_the_rest_of_the_episode_ends_it(self) -> None:
        decision = decide(CHAPTERS, {2, 3}, 2)

        assert decision.kind == "end"
        assert decision.skipped_title == "Interview"

    def test_marking_the_last_chapter_ends_the_episode(self) -> None:
        assert decide(CHAPTERS, {3}, 3).kind == "end"

    def test_no_active_chapter_decides_nothing(self) -> None:
        assert decide(CHAPTERS, {0}, None).kind == "none"

    def test_an_out_of_range_index_decides_nothing(self) -> None:
        assert decide(CHAPTERS, {0}, 99).kind == "none"


class TestLoopGuard:
    def test_fires_the_first_time(self) -> None:
        assert should_auto_skip(1, {1}, None) is True

    def test_does_not_fire_again_from_the_same_chapter(self) -> None:
        assert should_auto_skip(1, {1}, 1) is False

    def test_fires_again_once_the_chapter_has_moved_on(self) -> None:
        assert should_auto_skip(3, {3}, 1) is True

    def test_never_fires_for_an_unmarked_chapter(self) -> None:
        assert should_auto_skip(2, {1}, None) is False


class TestChapterSkipState:
    def test_toggling_marks_and_unmarks(self) -> None:
        state = ChapterSkipState()

        assert state.toggle(1) is True
        assert state.skipped == {1}
        assert state.toggle(1) is False
        assert state.skipped == set()

    def test_changing_episode_drops_the_marks(self) -> None:
        state = ChapterSkipState()
        state.retarget("s1", "e1")
        state.toggle(1)

        state.retarget("s1", "e2")

        assert state.skipped == set()

    def test_retargeting_the_same_episode_keeps_the_marks(self) -> None:
        state = ChapterSkipState()
        state.retarget("s1", "e1")
        state.toggle(1)

        state.retarget("s1", "e1")

        assert state.skipped == {1}

    def test_evaluate_does_nothing_when_nothing_is_marked(self) -> None:
        assert ChapterSkipState().evaluate(CHAPTERS, 90_000).kind == "none"

    def test_evaluate_seeks_once_then_holds(self) -> None:
        state = ChapterSkipState()
        state.toggle(1)

        first = state.evaluate(CHAPTERS, 90_000)
        # The seek's own position report still lands inside chapter 1.
        second = state.evaluate(CHAPTERS, 90_000)

        assert first.kind == "seek"
        assert second.kind == "none"

    def test_a_later_marked_chapter_still_fires(self) -> None:
        state = ChapterSkipState()
        state.toggle(1)
        state.toggle(3)
        state.evaluate(CHAPTERS, 90_000)  # arms the guard on index 1

        # Nothing to skip to after 3, so the episode is effectively over.
        assert state.evaluate(CHAPTERS, 700_000).kind == "end"

    def test_clear_unmarks_everything_and_rearms(self) -> None:
        state = ChapterSkipState()
        state.toggle(1)
        state.evaluate(CHAPTERS, 90_000)

        state.clear()
        state.toggle(1)

        assert state.evaluate(CHAPTERS, 90_000).kind == "seek"
