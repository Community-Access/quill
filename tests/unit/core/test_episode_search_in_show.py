"""Section 5: episode search inside one show.

Between "filter by state" and the cross-library Search Everywhere there was
nothing, so "which episode of *this* show was the one about the harbour" had
no answer except arrowing two hundred rows.
"""

from __future__ import annotations

from quill.core.podcasts.filtering import (
    filter_episodes,
    filter_episodes_by_text,
    search_summary,
)
from quill.core.podcasts.models import PodcastEpisode


def _episodes() -> list[PodcastEpisode]:
    return [
        PodcastEpisode(
            guid="1",
            title="Episode 412",
            audio_url="https://example.com/412.mp3",
            description="The harbour, and its ferries.",
        ),
        PodcastEpisode(
            guid="2",
            title="Episode 413",
            audio_url="https://example.com/413.mp3",
            description="Bridges.",
            played=True,
        ),
        PodcastEpisode(
            guid="3",
            title="Harbour lights",
            audio_url="https://example.com/hl.mp3",
            description="A song.",
        ),
    ]


def test_it_searches_descriptions_as_well_as_titles() -> None:
    """A show that numbers its episodes is exactly where titles alone fail."""
    found = filter_episodes_by_text(_episodes(), "harbour")
    assert [e.guid for e in found] == ["1", "3"]


def test_it_is_case_insensitive() -> None:
    assert len(filter_episodes_by_text(_episodes(), "HARBOUR")) == 2


def test_an_empty_query_matches_everything() -> None:
    assert len(filter_episodes_by_text(_episodes(), "   ")) == 3


def test_it_composes_with_the_heard_filter_rather_than_replacing_it() -> None:
    """5.2: Find narrows what the filter already chose."""
    unplayed = filter_episodes(_episodes(), "unplayed")
    assert [e.guid for e in filter_episodes_by_text(unplayed, "harbour")] == ["1", "3"]
    played = filter_episodes(_episodes(), "played")
    assert filter_episodes_by_text(played, "harbour") == []


def test_the_summary_counts_matches_out_of_what_was_searched() -> None:
    assert search_summary(2, 40, "harbour") == (
        "2 of 40 episodes match 'harbour', by title or description."
    )


def test_one_match_out_of_one_agrees_with_itself() -> None:
    assert search_summary(1, 1, "x") == "1 of 1 episode match 'x', by title or description."


def test_no_matches_says_what_was_searched_and_what_may_be_narrowing_it() -> None:
    """5.3, and the house rule: never announce a bare zero."""
    spoken = search_summary(0, 40, "harbour")
    assert "No episode matches 'harbour'" in spoken
    assert "40 episodes were searched, titles and descriptions" in spoken
    assert "a filter above may be narrowing the list" in spoken


def test_clearing_the_query_says_the_list_is_whole_again() -> None:
    assert search_summary(3, 3, "") == "Search cleared. Showing all 3 episodes."


def test_the_radio_side_searches_a_rows_description_too() -> None:
    """Radio's Find in this folder matches the label and the show notes."""
    from quill.core.radio.models import RadioStation
    from quill.ui.radio.browse_find import searchable_text

    node = type(
        "Node",
        (),
        {
            "label": "Episode 412",
            "station": RadioStation(
                name="Episode 412",
                stream_url="https://example.com/412.mp3",
                notes="The harbour, and its ferries.",
            ),
        },
    )()
    assert "harbour" in searchable_text(node)
    assert "episode 412" in searchable_text(node)


def test_a_row_with_no_station_still_answers() -> None:
    from quill.ui.radio.browse_find import searchable_text

    node = type("Node", (), {"label": "Some Folder", "station": None})()
    assert searchable_text(node) == "some folder"
