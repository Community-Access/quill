"""The show notes name the segments; the transcript says where they start.

The cases that matter here are the two the lab measured and one the cascade
depends on: a running order in prose becomes ordered phrases, a phrase anchors
where its subject *arrives* rather than where it is densest, and an episode
whose notes are a paragraph about the show yields nothing at all rather than a
plausible-looking guess.
"""

from __future__ import annotations

from quill.core.podcasts import note_anchors
from quill.core.podcasts.chapter_cascade import CascadeInputs, run
from quill.core.podcasts.chapter_inference import TimedCue
from quill.core.podcasts.chapter_scoring import SOURCE_NOTE_ANCHORS, SOURCE_TRANSCRIPT
from quill.core.podcasts.chapters import PodcastChapter
from quill.core.podcasts.inference_budget import for_budget

_HOUR_MS = 60 * 60 * 1000

_NOTES = (
    "<p>This week on the programme, Tyler Juranek begins a series of short reviews "
    "he calls Techie Tidbits. Next, we visit with Gerry Chevalier about the newest "
    "release of the Victor Reader Stream. Finally, Matt Roberts brings us a "
    "demonstration on accessing DVR recordings from Dish Network.</p>"
    "<p>Email us at feedback@example.com or subscribe wherever you listen.</p>"
)


def _cues(segments: list[tuple[int, int, str]]) -> list[TimedCue]:
    """Cues every fifteen seconds, each carrying its segment's vocabulary."""
    rows: list[TimedCue] = []
    for start_ms, end_ms, words in segments:
        for position in range(start_ms, end_ms, 15_000):
            rows.append(TimedCue(position, words))
    return rows


def _episode_cues() -> list[TimedCue]:
    return _cues([
        (0, 600_000, "welcome everybody to the programme this evening announcements"),
        (600_000, 1_500_000, "tyler juranek techie tidbits reviews short gadget"),
        (1_500_000, 2_700_000, "gerry chevalier victor reader stream humanware release"),
        (2_700_000, _HOUR_MS, "matt roberts dish network recordings demonstration dvr"),
    ])


def test_topic_phrases_reads_a_running_order_in_order() -> None:
    phrases = note_anchors.topic_phrases(_NOTES)
    assert len(phrases) >= 3
    joined = " | ".join(phrases).lower()
    assert joined.index("tyler") < joined.index("gerry") < joined.index("matt")


def test_topic_phrases_drops_boilerplate() -> None:
    phrases = note_anchors.topic_phrases(_NOTES)
    assert not any("subscribe" in phrase.lower() for phrase in phrases)
    assert not any("@" in phrase for phrase in phrases)


def test_topic_phrases_ignores_markup_and_entities() -> None:
    phrases = note_anchors.topic_phrases("<p>Braille &amp; speech displays.</p>")
    assert phrases == ["Braille & speech displays."]


def test_anchors_land_near_where_each_topic_arrives() -> None:
    rows = note_anchors.anchored_chapters(_NOTES, _episode_cues(), _HOUR_MS)
    starts = [row.start_ms for row in rows]

    assert starts[0] == 0
    assert rows[0].title == "Opening"
    assert starts == sorted(starts)
    assert len(rows) >= 3
    # Each anchor within a minute of the true segment start.
    for expected in (600_000, 1_500_000, 2_700_000):
        assert any(abs(start - expected) <= 60_000 for start in starts), (starts, expected)


def test_titles_are_the_publishers_own_words() -> None:
    rows = note_anchors.anchored_chapters(_NOTES, _episode_cues(), _HOUR_MS)
    titles = " ".join(row.title.lower() for row in rows)
    assert "tyler" in titles
    assert "gerry" in titles


def test_a_topic_anchors_at_its_onset_not_its_densest_point() -> None:
    """Density finds where a topic *is*; a chapter needs where it *begins*.

    The measured failure: a thirty-five minute interview mentions its guest most
    often in the middle, and peak-matching put the segment at 30:00 when it
    began at 1:09.
    """
    cues = _cues([
        (0, 300_000, "opening housekeeping listener mail and announcements"),
        (300_000, 900_000, "chevalier stream victor reader introduction"),
        # The same subject, mentioned far more often, much later.
        (900_000, 1_800_000, "chevalier chevalier chevalier stream stream victor victor"),
        (1_800_000, _HOUR_MS, "roberts dish network recordings demonstration"),
    ])
    notes = (
        "First, some housekeeping and listener mail and announcements. "
        "Then we visit with Gerry Chevalier about the Victor Reader Stream. "
        "Finally, Matt Roberts demonstrates Dish Network recordings."
    )
    rows = note_anchors.anchored_chapters(notes, cues, _HOUR_MS)
    chevalier = next(row for row in rows if "chevalier" in row.title.lower())
    assert chevalier.start_ms <= 600_000, rows


def test_a_paragraph_about_the_show_is_not_a_running_order() -> None:
    assert note_anchors.anchored_chapters("A weekly show.", _episode_cues(), _HOUR_MS) == []


def test_no_transcript_means_no_anchors() -> None:
    assert note_anchors.anchored_chapters(_NOTES, [], _HOUR_MS) == []
    assert note_anchors.anchored_chapters(_NOTES, _episode_cues(), 0) == []


def test_notes_whose_words_never_appear_anchor_nothing() -> None:
    """A description that does not match the episode must not invent boundaries."""
    cues = _cues([(0, _HOUR_MS, "entirely unrelated vocabulary about gardening and compost")])
    rows = note_anchors.anchored_chapters(_NOTES, cues, _HOUR_MS)
    assert rows == []


def test_anchors_beat_a_lexical_segmentation_in_the_cascade() -> None:
    """Authored titles win outright -- they are not scored against a heuristic."""

    def _anchors() -> list[PodcastChapter]:
        return note_anchors.anchored_chapters(_NOTES, _episode_cues(), _HOUR_MS)

    def _transcript() -> list[PodcastChapter]:
        return [
            PodcastChapter(start_ms=index * 300_000, title=f"section {index}")
            for index in range(12)
        ]

    answer = run(
        CascadeInputs(note_anchors=_anchors, transcript=_transcript, total_ms=_HOUR_MS),
        for_budget("thorough"),
    )
    assert answer.source == SOURCE_NOTE_ANCHORS
    assert answer.is_authored


def test_a_cached_answer_is_still_preferred_over_re_anchoring() -> None:
    """The anchor tier needs a transcript; an episode already answered must not pay."""
    from quill.core.podcasts.chapter_scoring import ChapterAnswer

    cached = ChapterAnswer(
        chapters=(PodcastChapter(0, "One"), PodcastChapter(600_000, "Two")),
        source=SOURCE_TRANSCRIPT,
        confidence=0.5,
    )
    called = False

    def _anchors() -> list[PodcastChapter]:
        nonlocal called
        called = True
        return note_anchors.anchored_chapters(_NOTES, _episode_cues(), _HOUR_MS)

    answer = run(
        CascadeInputs(cached=lambda: cached, note_anchors=_anchors, total_ms=_HOUR_MS),
        for_budget("thorough"),
    )
    assert answer is cached
    assert not called
