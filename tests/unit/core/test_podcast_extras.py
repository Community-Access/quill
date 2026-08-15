"""What the Podcasting 2.0 tags mean to a listener: rows, sentences, actions.

These pin the words, because the words are the feature. A row that reads as two
columns, a count that says "1 recommended", a button that says OK on something
it cannot do -- each is a small failure that only shows up in speech.
"""

from __future__ import annotations

from quill.core.podcasts.extras import (
    ACTION_NONE,
    ACTION_OPEN,
    ACTION_PLAY,
    ACTION_SUBSCRIBE,
    build,
    has_extras,
    spoken_length,
    spoken_position,
    summary,
)
from quill.core.podcasts.namespace_tags import parse

_SHOW = """
<channel>
  <podcast:person role="Host">Alice Adams</podcast:person>
  <podcast:funding url="https://support.example">Buy us a coffee</podcast:funding>
  <podcast:podroll><podcast:remoteItem feedUrl="https://one.example/feed"/></podcast:podroll>
  <podcast:liveItem status="live"><title>Live tonight</title>
    <enclosure url="https://live.example/stream"/></podcast:liveItem>
</channel>
"""

_EPISODE = """
<item>
  <podcast:person role="Guest" href="https://bob.example">Bob Brown</podcast:person>
  <podcast:soundbite startTime="3725" duration="90">The good bit</podcast:soundbite>
  <podcast:alternateEnclosure type="audio/mpeg" bitrate="32000" title="Low bandwidth">
    <podcast:source uri="https://low.example/ep1.mp3"/></podcast:alternateEnclosure>
  <podcast:location>Kansas City, Missouri</podcast:location>
</item>
"""


def _built():
    return build(show_tags=parse(_SHOW), episode_tags=parse(_EPISODE), show_title="The Show")


def test_a_section_exists_only_when_it_has_something_in_it() -> None:
    # No empty People tab on a podcast that publishes no credits: arrowing
    # through tabs that all say "none" is a worse way to learn there is nothing.
    assert build().is_empty
    only_people = build(episode_tags=parse('<podcast:person role="host">A</podcast:person>'))
    assert [section.key for section in only_people.sections] == ["people"]


def test_a_host_belongs_to_the_show_and_a_guest_to_the_episode() -> None:
    people = _built().section("people")
    assert people is not None
    assert people.rows[0].label == "Bob Brown, guest (this episode)"
    assert people.rows[1].label == "Alice Adams, host (this podcast)"


def test_a_person_with_no_link_says_there_is_nothing_to_open() -> None:
    # A control that silently declines is worse than one not offered.
    people = _built().section("people")
    assert people is not None
    assert people.rows[0].action == ACTION_OPEN  # Bob has a link
    assert people.rows[1].action == ACTION_NONE  # Alice does not
    assert people.rows[1].is_actionable is False
    assert people.rows[1].button_label == "Nothing to Open"


def test_a_marked_moment_is_spoken_as_words_not_a_timecode() -> None:
    highlights = _built().section("highlights")
    assert highlights is not None
    assert highlights.rows[0].label == "The good bit -- 1 hour 2 minutes in, 1 minute long"
    assert spoken_position(0) == "0 seconds in"
    assert spoken_position(90_000) == "1 minute in"
    assert spoken_length(45_000) == "45 seconds long"


def test_highlights_do_not_offer_a_second_way_to_jump() -> None:
    # Jumping belongs in the chapter list, where every other jump already lives.
    # Two places to do the same thing is how a keyboard user learns neither.
    highlights = _built().section("highlights")
    assert highlights is not None
    assert all(row.action == ACTION_NONE for row in highlights.rows)
    assert "chapter list" in highlights.heading


def test_a_live_stream_plays_and_one_that_has_ended_does_not() -> None:
    live = _built().section("live")
    assert live is not None
    assert live.rows[0].action == ACTION_PLAY
    assert live.rows[0].target == "https://live.example/stream"
    ended = build(
        show_tags=parse(
            '<podcast:liveItem status="ended"><title>Over</title>'
            '<enclosure url="https://x"/></podcast:liveItem>'
        )
    ).section("live")
    assert ended is not None
    assert ended.rows[0].action == ACTION_NONE
    assert "not on air" in ended.rows[0].label


def test_a_podroll_entry_offers_a_real_subscribe() -> None:
    recommended = _built().section("recommended")
    assert recommended is not None
    assert recommended.rows[0].action == ACTION_SUBSCRIBE
    assert "reads its real name" in recommended.heading


def test_the_support_section_says_QUILL_takes_no_part() -> None:
    support = _built().section("support")
    assert support is not None
    assert support.rows[0].action == ACTION_OPEN
    assert "nothing to do with what happens there" in support.heading


def test_other_audio_is_offered_as_something_to_play() -> None:
    audio = _built().section("audio")
    assert audio is not None
    assert audio.rows[0].label == "Low bandwidth, 32 kbps"
    assert audio.rows[0].action == ACTION_PLAY


def test_a_place_is_text_and_does_nothing() -> None:
    place = _built().section("location")
    assert place is not None
    assert place.rows[0].label == "Kansas City, Missouri"
    assert place.rows[0].action == ACTION_NONE


def test_the_summary_counts_things_in_words_a_person_would_use() -> None:
    said = summary(_built())
    assert "1 person" not in said  # two people: one host, one guest
    assert "2 people" in said
    assert "1 marked moment" in said
    assert "1 recommended podcast" in said
    assert "1 support link" in said


def test_nothing_published_is_said_plainly_rather_than_shown_as_an_empty_window() -> None:
    assert summary(build()) == "This podcast published no extra details for this episode."


def test_the_command_is_only_worth_offering_when_there_is_something() -> None:
    assert has_extras() is False
    assert has_extras(parse(_SHOW), None) is True
    assert has_extras(None, parse(_EPISODE)) is True
