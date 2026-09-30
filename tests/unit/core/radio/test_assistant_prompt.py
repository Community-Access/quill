"""What Ask QUILL Radio tells the model: the standing instructions and the context."""

from __future__ import annotations

from quill.core.radio.assistant_prompt import (
    RADIO_INSTRUCTIONS,
    context_line,
    instructions_for,
    suggested_questions,
)


def test_the_context_names_the_station_and_the_title_when_known() -> None:
    assert context_line("ACB Media 1", "Blue Moon by Someone") == (
        "Right now the listener is playing ACB Media 1, and the stream says: Blue Moon by Someone."
    )
    assert "has not said what is on" in context_line("ACB Media 1", "")
    assert context_line("", "") == "Nothing is playing right now."
    assert context_line("", "orphan title") == "Nothing is playing right now."


def test_the_instructions_carry_the_context_and_the_search_state() -> None:
    with_search = instructions_for("KEXP", "A song", web_search=True)
    assert with_search.startswith(RADIO_INSTRUCTIONS)
    assert "Context: Right now the listener is playing KEXP" in with_search
    assert "Web search is available" in with_search
    without = instructions_for("KEXP", "A song", web_search=False)
    assert "Web search is not available" in without


def test_the_standing_instructions_are_written_for_a_screen_reader() -> None:
    assert "screen reader" in RADIO_INSTRUCTIONS
    assert "no tables" in RADIO_INSTRUCTIONS
    assert "QUILL Radio" in RADIO_INSTRUCTIONS


def test_suggested_questions_follow_what_is_on() -> None:
    assert suggested_questions("", "") == []
    only_station = suggested_questions("KEXP", "")
    assert len(only_station) == 2
    assert all("station" in q for q in only_station)
    both = suggested_questions("KEXP", "A song")
    assert len(both) == 4
    assert both[0].startswith("What is this song")


# --------------------------------------------------------------------------- #
# Quick questions
# --------------------------------------------------------------------------- #

from quill.core.radio.assistant_prompt import (  # noqa: E402
    NEEDS_FAVORITES,
    NEEDS_LISTENING,
    NEEDS_PLAYING,
    NEEDS_RECENT_SONGS,
    QUICK_QUESTIONS,
    describe_extra,
    extra_context,
)


def test_most_quick_questions_send_only_what_is_playing() -> None:
    needs = [q.needs for q in QUICK_QUESTIONS]
    assert needs.count(NEEDS_PLAYING) == 6
    assert set(needs) == {NEEDS_PLAYING, NEEDS_FAVORITES, NEEDS_RECENT_SONGS, NEEDS_LISTENING}
    assert len({q.id for q in QUICK_QUESTIONS}) == len(QUICK_QUESTIONS)
    assert all(q.label and q.question for q in QUICK_QUESTIONS)


def test_extra_context_is_capped_and_empty_when_there_is_nothing() -> None:
    assert extra_context(NEEDS_PLAYING) == ""
    assert extra_context(NEEDS_FAVORITES) == ""
    many = [(f"Station {i}", "News" if i % 2 else "") for i in range(100)]
    text = extra_context(NEEDS_FAVORITES, favorites=many)
    assert text.startswith("Favorite stations: Station 0; Station 1 (in News)")
    assert "Station 59" in text and "Station 60" not in text
    songs = [f"Song {i} by Band" for i in range(40)]
    text = extra_context(NEEDS_RECENT_SONGS, recent_songs=songs)
    assert "Song 24" in text and "Song 25" not in text
    text = extra_context(NEEDS_LISTENING, listening=[("KEXP", songs), ("Empty", [])])
    assert "KEXP: Song 0 by Band" in text and "Song 5" not in text and "| Empty" in text


def test_the_instructions_carry_the_extra_only_when_chosen() -> None:
    plain = instructions_for("KEXP", "A song", web_search=False)
    assert "chose to send" not in plain
    with_extra = instructions_for("KEXP", "A song", web_search=False, extra="Favorite stations: X")
    assert with_extra.endswith("The listener chose to send this as well:\nFavorite stations: X")


def test_what_each_question_sends_is_said_in_numbers() -> None:
    assert "32 favorite" in describe_extra(NEEDS_FAVORITES, count=32)
    assert "none saved" in describe_extra(NEEDS_FAVORITES, count=0)
    assert "7 songs" in describe_extra(NEEDS_RECENT_SONGS, count=7)
    assert "none yet" in describe_extra(NEEDS_RECENT_SONGS, count=0)
    assert "3 stations" in describe_extra(NEEDS_LISTENING, count=3)
    assert "only the station and title" in describe_extra(NEEDS_PLAYING, count=0)
