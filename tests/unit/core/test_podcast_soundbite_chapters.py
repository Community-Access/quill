"""Soundbites as chapter marks: authored, ranked last of the authored tiers.

A ``podcast:soundbite`` is a chapter marker in all but name -- a person chose
the moment and wrote its title -- so it belongs in the cascade rather than in a
side list nothing consults. But it is a **highlight, not a partition**: two of
them in an hour answers "what is the good bit" completely and "how is this laid
out" barely at all. Both halves of that are pinned here.
"""

from __future__ import annotations

from quill.core.podcasts.chapter_cascade import CascadeInputs, run
from quill.core.podcasts.chapter_scoring import (
    SOURCE_PUBLISHED,
    SOURCE_SOUNDBITES,
    SOURCE_TRANSCRIPT,
)
from quill.core.podcasts.chapter_sources import (
    AUTHORED_SOURCES,
    SOURCE_LABELS,
    chapter_cascade,
    episode_has_possible_chapters,
    soundbite_chapters,
)
from quill.core.podcasts.chapters import PodcastChapter
from quill.core.podcasts.inference_budget import InferenceBudget
from quill.core.podcasts.models import PodcastEpisode
from quill.core.podcasts.namespace_tags import parse

_HOUR = 60 * 60 * 1000

_WITH_BITES = """
<item>
  <podcast:soundbite startTime="1800" duration="90">The good bit</podcast:soundbite>
  <podcast:soundbite startTime="600" duration="60">The earlier bit</podcast:soundbite>
  <podcast:soundbite startTime="3000" duration="45"/>
</item>
"""


def _episode(fragment: str = _WITH_BITES) -> PodcastEpisode:
    return PodcastEpisode(
        guid="e1",
        title="Ep 1",
        audio_url="https://example/ep1.mp3",
        duration_seconds=3600,
        tags=parse(fragment),
    )


def test_a_soundbite_becomes_a_chapter_with_the_publisher_s_own_title() -> None:
    chapters = soundbite_chapters(_episode())
    assert [c.title for c in chapters] == ["The earlier bit", "The good bit", "Highlight 3"]
    assert [c.start_ms for c in chapters] == [600_000, 1_800_000, 3_000_000]


def test_a_highlight_keeps_its_own_end_rather_than_running_to_the_next_one() -> None:
    # The difference between "this podcast marked two moments" and a chapter
    # list that quietly claims to cover the whole episode.
    chapters = soundbite_chapters(_episode())
    assert chapters[0].end_ms == 660_000  # 10 minutes in, one minute long
    assert chapters[1].end_ms == 1_890_000


def test_an_untitled_mark_is_named_rather_than_dropped() -> None:
    # The mark is still a place worth jumping to, and "Highlight 3" is honest
    # about knowing nothing more than that.
    assert soundbite_chapters(_episode()).pop().title == "Highlight 3"


def test_an_episode_with_no_tags_yields_nothing_and_does_not_raise() -> None:
    assert soundbite_chapters(None) == []
    assert soundbite_chapters(_episode("<item><title>Plain</title></item>")) == []


def test_soundbites_are_authored_and_labelled_as_what_they_are() -> None:
    assert "soundbites" in AUTHORED_SOURCES
    assert SOURCE_LABELS["soundbites"] == "Moments this podcast marked"


def test_a_published_chapter_list_still_wins() -> None:
    # Soundbites are highlights; a published list is the layout. Where a feed
    # has both, the layout is the answer to "what are the chapters".
    found = chapter_cascade(
        published=lambda: [
            PodcastChapter(start_ms=0, title="Intro"),
            PodcastChapter(start_ms=600_000, title="Interview"),
        ],
        soundbites=soundbite_chapters(_episode()),
        total_ms=_HOUR,
    )
    assert found.source == "published"


def test_soundbites_win_when_nothing_better_was_published() -> None:
    found = chapter_cascade(soundbites=soundbite_chapters(_episode()), total_ms=_HOUR)
    assert found.source == "soundbites"
    assert [c.title for c in found.chapters][0] == "The earlier bit"


def test_one_marked_moment_is_enough() -> None:
    # Unlike the tiers above it, this one has no floor of two: one mark is still
    # a place worth jumping to, and the label carries the meaning.
    one = _episode(
        '<item><podcast:soundbite startTime="60" duration="30">One</podcast:soundbite></item>'
    )
    found = chapter_cascade(soundbites=soundbite_chapters(one), total_ms=_HOUR)
    assert [c.title for c in found.chapters] == ["One"]


def test_chapters_are_worth_offering_for_an_episode_that_only_has_soundbites() -> None:
    bare = PodcastEpisode(guid="g", title="t", audio_url="u", tags=parse(_WITH_BITES))
    assert episode_has_possible_chapters(bare) is True


def test_the_scored_cascade_treats_them_as_authored_and_short_circuits() -> None:
    answer = run(
        CascadeInputs(
            soundbites=lambda: soundbite_chapters(_episode()),
            transcript=lambda: [
                PodcastChapter(start_ms=0, title="A"),
                PodcastChapter(start_ms=1000, title="B"),
            ],
            total_ms=_HOUR,
        ),
        InferenceBudget(),
    )
    assert answer.source == SOURCE_SOUNDBITES
    assert answer.is_authored is True
    assert answer.source != SOURCE_TRANSCRIPT


def test_a_feed_with_real_chapters_never_reaches_the_soundbite_tier() -> None:
    answer = run(
        CascadeInputs(
            published=lambda: [
                PodcastChapter(start_ms=0, title="Intro"),
                PodcastChapter(start_ms=600_000, title="Interview"),
            ],
            soundbites=lambda: soundbite_chapters(_episode()),
            total_ms=_HOUR,
        ),
        InferenceBudget(),
    )
    assert answer.source == SOURCE_PUBLISHED
