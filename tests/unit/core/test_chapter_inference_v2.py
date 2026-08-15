"""Chapter inference: scored answers, the best one wins, and honest titles.

The change these pin is the one that made the cascade worth having. It used to
run the tiers in cost order and keep the **first** answer, so a weak
transcript segmentation permanently hid a better silence scan and nothing could
compare two answers because nothing scored one.

Now every tier is scored, every tier the budget allows runs, and the best wins --
except that an **authored** answer always beats an inferred one, because a person
wrote those titles and no heuristic produces titles worth more.
"""

from __future__ import annotations

import pytest

from quill.core.podcasts.chapter_cascade import (
    MID_SCAN_REPLY,
    CascadeInputs,
    announce,
    run,
    working_label,
)
from quill.core.podcasts.chapter_naming import (
    clean_title,
    name_sections,
    parse_titles,
    sample_text,
)
from quill.core.podcasts.chapter_scoring import (
    MIN_USEFUL_CONFIDENCE,
    SOURCE_PUBLISHED,
    SOURCE_SHOW_NOTES,
    SOURCE_SILENCE,
    SOURCE_TRANSCRIPT,
    ChapterAnswer,
    best,
    describe,
    score,
)
from quill.core.podcasts.chapters import PodcastChapter
from quill.core.podcasts.inference_budget import (
    DEEP,
    QUICK,
    THOROUGH,
    for_budget,
    from_settings,
    is_enabled,
)
from quill.core.podcasts.models import PodcastSettings
from quill.core.podcasts.show_note_chapters import chapters_from_notes, parse_marks

_HOUR = 60 * 60 * 1000


def _chapters(*starts: int) -> list[PodcastChapter]:
    return [PodcastChapter(start_ms=start, title=f"T{start}") for start in starts]


# -- scoring ---------------------------------------------------------------------


def test_a_published_list_is_certain_by_definition() -> None:
    answer = score(_chapters(0, 600_000), SOURCE_PUBLISHED, total_ms=_HOUR)
    assert answer.confidence == 1.0
    assert answer.is_authored


def test_an_inferred_answer_is_judged_on_its_shape() -> None:
    # One boundary in an hour says almost nothing.
    thin = score(_chapters(0), SOURCE_TRANSCRIPT, total_ms=_HOUR)
    # A hundred says the detector was chasing noise.
    noisy = score(_chapters(*range(0, _HOUR, 30_000)), SOURCE_TRANSCRIPT, total_ms=_HOUR)
    sensible = score(_chapters(0, 900_000, 1_800_000, 2_700_000), SOURCE_TRANSCRIPT, total_ms=_HOUR)
    assert thin.confidence < sensible.confidence
    assert noisy.confidence < sensible.confidence


def test_the_segmenters_own_margin_raises_its_confidence() -> None:
    # Boundaries that sat well below the cohesion threshold are boundaries the
    # segmenter was confident about, and that is the only evidence it has.
    plain = score(_chapters(0, 900_000, 1_800_000), SOURCE_TRANSCRIPT, total_ms=_HOUR)
    confident = score(
        _chapters(0, 900_000, 1_800_000),
        SOURCE_TRANSCRIPT,
        total_ms=_HOUR,
        cohesion_margin=0.4,
    )
    assert confident.confidence > plain.confidence


def test_authored_beats_inferred_however_confident_the_inference() -> None:
    authored = score(_chapters(0, 600_000), SOURCE_SHOW_NOTES, total_ms=_HOUR)
    inferred = ChapterAnswer(
        chapters=tuple(_chapters(0, 600_000, 1_200_000)),
        source=SOURCE_TRANSCRIPT,
        confidence=0.99,
    )
    assert best([inferred, authored]).source == SOURCE_SHOW_NOTES


def test_nothing_useful_is_an_answer_of_its_own() -> None:
    assert best([]) == ChapterAnswer()
    weak = ChapterAnswer(chapters=tuple(_chapters(0, 1)), source=SOURCE_SILENCE, confidence=0.01)
    assert weak.is_useful is False
    assert best([weak]).chapters == ()
    assert MIN_USEFUL_CONFIDENCE > 0


def test_the_report_is_sentences_and_says_who_wrote_the_titles() -> None:
    authored = score(_chapters(0, 600_000), SOURCE_PUBLISHED, total_ms=_HOUR)
    said = describe(authored)
    assert "published by the podcast" in said
    assert "A person wrote these titles" in said

    inferred = score(
        _chapters(0, 900_000, 1_800_000),
        SOURCE_SILENCE,
        total_ms=_HOUR,
        examined="48 minutes of audio",
    )
    said = describe(inferred)
    assert "Examined: 48 minutes of audio" in said
    assert "worked out rather than published" in said
    assert describe(ChapterAnswer()) == "No chapters could be found for this episode."


# -- the cascade -----------------------------------------------------------------


def test_the_best_answer_wins_not_the_first() -> None:
    # The whole point. A one-boundary transcript answer used to short-circuit
    # the scan; now both run and the better one is kept.
    inputs = CascadeInputs(
        transcript=lambda: _chapters(0),
        silence_scan=lambda: _chapters(0, 900_000, 1_800_000, 2_700_000),
        total_ms=_HOUR,
    )
    assert run(inputs, for_budget(THOROUGH)).source == SOURCE_SILENCE


def test_an_authored_answer_short_circuits_everything_below_it() -> None:
    called: list[str] = []

    def _scan() -> list[PodcastChapter]:
        called.append("scan")
        return _chapters(0, 900_000, 1_800_000)

    inputs = CascadeInputs(
        published=lambda: _chapters(0, 600_000),
        silence_scan=_scan,
        total_ms=_HOUR,
    )
    assert run(inputs, for_budget(DEEP)).source == SOURCE_PUBLISHED
    assert called == []  # nothing expensive ran at all


def test_quick_never_scans_and_never_fetches() -> None:
    reached: list[str] = []

    def _fetch() -> list[PodcastChapter]:
        reached.append("fetch")
        return _chapters(0, 900_000)

    def _scan() -> list[PodcastChapter]:
        reached.append("scan")
        return _chapters(0, 900_000)

    inputs = CascadeInputs(fetch_transcript=_fetch, silence_scan=_scan, total_ms=_HOUR)
    assert run(inputs, for_budget(QUICK)).chapters == ()
    assert reached == []


def test_a_cold_transcript_cache_is_fetched_when_the_budget_allows() -> None:
    # The single biggest gap in the old cascade: an episode publishing a
    # perfectly good transcript fell through to the slow audio scan because
    # nobody had opened it yet.
    inputs = CascadeInputs(
        transcript=lambda: [],
        fetch_transcript=lambda: _chapters(0, 900_000, 1_800_000),
        total_ms=_HOUR,
    )
    assert run(inputs, for_budget(THOROUGH)).source == SOURCE_TRANSCRIPT


def test_a_short_episode_runs_nothing_at_all() -> None:
    reached: list[str] = []
    inputs = CascadeInputs(
        published=lambda: reached.append("p") or _chapters(0, 60_000),
        total_ms=5 * 60 * 1000,
    )
    assert run(inputs, for_budget(DEEP)).chapters == ()
    assert reached == []


def test_a_tier_that_raises_is_simply_a_tier_without_an_answer() -> None:
    def _broken() -> list[PodcastChapter]:
        raise OSError("no transcript here")

    inputs = CascadeInputs(
        transcript=_broken,
        silence_scan=lambda: _chapters(0, 900_000, 1_800_000),
        total_ms=_HOUR,
    )
    assert run(inputs, for_budget(THOROUGH)).source == SOURCE_SILENCE


def test_every_chapter_carries_its_own_provenance() -> None:
    inputs = CascadeInputs(published=lambda: _chapters(0, 600_000), total_ms=_HOUR)
    answer = run(inputs, for_budget(THOROUGH))
    first = answer.chapters[0]
    assert first.source == SOURCE_PUBLISHED
    assert first.end_ms == 600_000  # an honest end, so "four minutes long" is sayable
    assert first.reason
    assert answer.chapters[-1].end_ms == _HOUR  # the last chapter ends with the episode


def test_the_announcement_is_short_and_the_menu_explains_itself() -> None:
    answer = run(
        CascadeInputs(published=lambda: _chapters(0, 600_000), total_ms=_HOUR), for_budget(THOROUGH)
    )
    assert announce(answer) == "2 chapters found."
    assert announce(ChapterAnswer()) == "No chapters could be found in this episode."
    # Disabled-and-explained beats enabled-and-does-nothing: the state is in the
    # label, so a screen reader reads it as part of the item.
    assert working_label() == "Chapters (working them out...)"
    assert "I will say when they are ready" in MID_SCAN_REPLY


# -- the budget ------------------------------------------------------------------


def test_a_tier_switched_off_is_disabled_not_deprioritised() -> None:
    # Somebody who said "never scan the audio" has said something specific.
    budget = from_settings(PodcastSettings(chapters_effort="deep", chapters_scan_audio=False))
    assert budget.name == DEEP
    assert budget.may_scan_audio is False
    assert budget.may_transcribe is False


def test_an_unknown_effort_reads_as_the_default_not_as_more_work() -> None:
    assert for_budget("ludicrous").name == THOROUGH
    assert PodcastSettings.from_dict({"chapters_effort": "ludicrous"}).chapters_effort == "thorough"


@pytest.mark.parametrize(
    ("mode", "downloaded", "expected"),
    [
        ("off", True, False),
        ("always", False, True),
        ("when_downloaded", False, False),
        ("when_downloaded", True, True),
    ],
)
def test_when_chapters_are_worked_out_at_all(mode: str, downloaded: bool, expected: bool) -> None:
    assert is_enabled(PodcastSettings(chapters_auto=mode), downloaded=downloaded) is expected


# -- show notes ------------------------------------------------------------------


def test_the_shapes_publishers_actually_write() -> None:
    notes = "\n".join([
        "1. 00:00 Introduction",
        "2. [04:11] - The interview begins",
        "3) 12.34 | Questions",
        "Closing thoughts — 1:02:03",
    ])
    chapters = chapters_from_notes(notes, total_ms=2 * _HOUR)
    assert [c.title for c in chapters] == [
        "Introduction",
        "The interview begins",
        "Questions",
        "Closing thoughts",
    ]
    # The words beside the timestamp are the title, and a person wrote them.
    assert all(c.confidence == 1.0 for c in chapters)
    assert all(c.source == SOURCE_SHOW_NOTES for c in chapters)


def test_html_show_notes_are_read_rather_than_skipped() -> None:
    # Show notes usually arrive as markup, and a text-only reader was skipping
    # most of the internet.
    html_notes = "<ul><li>00:00 Intro</li><li>10:00 Middle</li><li>20:00 End</li></ul>"
    assert [c.title for c in chapters_from_notes(html_notes, total_ms=_HOUR)] == [
        "Intro",
        "Middle",
        "End",
    ]


def test_spelled_out_durations_count() -> None:
    assert parse_marks("1h05m The long bit")[0][0] == 3_900_000


@pytest.mark.parametrize(
    "notes",
    [
        "10:00 Later\n05:00 Earlier",  # out of order
        "10:00 Only one",  # a single mark
        "45:00 Starts too late\n50:00 Second",  # not this episode's list
    ],
)
def test_a_page_that_merely_contains_times_is_refused(notes: str) -> None:
    assert chapters_from_notes(notes, total_ms=2 * _HOUR) == []


# -- naming ----------------------------------------------------------------------


def test_a_model_title_is_cleaned_and_clamped() -> None:
    assert clean_title('  "1. The Interview Begins."  ') == "The Interview Begins"
    assert clean_title("Title: A guest arrives") == "A guest arrives"
    assert len(clean_title(" ".join(["word"] * 30)).split()) == 8


def test_a_declined_title_leaves_the_chapter_alone() -> None:
    # "I could not tell" must never become a plausible invention.
    assert clean_title("-") == ""
    chapters = [PodcastChapter(0, "and so we"), PodcastChapter(60_000, "well then")]
    named = name_sections(
        chapters, ["a", "b"], lambda _p: "The interview begins\n-", budget=for_budget(THOROUGH)
    )
    assert named[0].title == "The interview begins"
    assert named[1].title == "well then"


def test_naming_is_one_batched_call_never_one_per_chapter() -> None:
    calls: list[str] = []

    def _ask(prompt: str) -> str:
        calls.append(prompt)
        return "One\nTwo\nThree"

    chapters = [PodcastChapter(i * 60_000, f"raw {i}") for i in range(3)]
    named = name_sections(chapters, ["a", "b", "c"], _ask, budget=for_budget(THOROUGH))
    assert len(calls) == 1
    assert "Section 1" in calls[0] and "Section 3" in calls[0]
    assert [c.title for c in named] == ["One", "Two", "Three"]


def test_a_failed_naming_call_changes_nothing() -> None:
    def _boom(_prompt: str) -> str:
        raise OSError("the provider is down")

    chapters = [PodcastChapter(0, "original")]
    assert name_sections(chapters, ["a"], _boom, budget=for_budget(THOROUGH))[0].title == "original"


def test_a_short_reply_is_padded_rather_than_failing() -> None:
    # Eleven good titles and one gap beats no list at all.
    assert parse_titles("One\nTwo", 4) == ["One", "Two", "", ""]


def test_sampling_only_happens_when_the_text_is_not_already_here() -> None:
    long_text = " ".join(f"w{i}" for i in range(4000))
    budget = for_budget(THOROUGH)
    whole = sample_text(long_text, budget=budget, whole=True)
    sampled = sample_text(long_text, budget=budget, whole=False)
    assert len(whole.split()) == 4000
    assert len(sampled.split()) < 500
    # Never only the opening: a section's first minute is often the tail of the
    # previous topic, so a probe from the middle comes with it.
    assert "..." in sampled
