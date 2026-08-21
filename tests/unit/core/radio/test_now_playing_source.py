"""What's Playing says where the track came from, and whether it is quoted.

Quill Radio reaches for a title in three places -- the ICY block carried with
the audio, the player's own metadata, and the station's status page -- and used
to present all three as one confident sentence. They are not equally direct: a
status page is a snapshot the station publishes for its listing and can lag the
audio by a song.

The second half is the rendering. Stations send ``StreamTitle`` blocks stuffed
with ``text="..."``, advert markers and call signs, and the song and artist are
*read out of* that. Usually right; not always right; and never previously
visible as a reading rather than a quotation.
"""

from __future__ import annotations

from quill.core.radio.now_playing_source import (
    SOURCE_ENGINE,
    SOURCE_ICY,
    SOURCE_NONE,
    SOURCE_STATUS_PAGE,
    NowPlayingFacts,
    describe_source,
)


def test_a_verbatim_title_says_only_where_it_came_from() -> None:
    facts = NowPlayingFacts(
        shown="YOUR SONG by Elton John",
        raw="YOUR SONG by Elton John",
        source=SOURCE_ICY,
    )
    lines = facts.provenance_lines()
    assert len(lines) == 1
    assert "carried with the audio" in lines[0]


def test_a_rendered_title_shows_what_the_station_actually_sent() -> None:
    # THE CASE THIS EXISTS FOR: the shown text is a reading of the raw one.
    facts = NowPlayingFacts(
        shown="YOUR SONG by Elton John",
        raw='text="YOUR SONG by Elton John" song_spot="M" MediaBaseId="0"',
        source=SOURCE_ICY,
    )
    lines = facts.provenance_lines()
    assert any("The station sent:" in line for line in lines)
    assert any('song_spot="M"' in line for line in lines)
    assert any("usually right and is not always right" in line for line in lines)


def test_whitespace_alone_is_tidying_rather_than_interpretation() -> None:
    facts = NowPlayingFacts(shown="Jazz FM", raw="  Jazz FM  ", source=SOURCE_ENGINE)
    assert facts.is_verbatim
    assert len(facts.provenance_lines()) == 1


def test_the_status_page_admits_it_can_lag() -> None:
    facts = NowPlayingFacts(shown="A Song", raw="A Song", source=SOURCE_STATUS_PAGE)
    assert "can run a song behind" in facts.provenance_lines()[0]


def test_the_player_route_names_itself_distinctly() -> None:
    # HLS has no ICY at all, so this route is the only one some stations have.
    facts = NowPlayingFacts(shown="A Song", raw="A Song", source=SOURCE_ENGINE)
    assert "read by the player" in facts.provenance_lines()[0]


def test_no_title_means_no_provenance_block_at_all() -> None:
    # A window explaining where a title it does not have came from is worse
    # than one that does not mention it.
    assert NowPlayingFacts().provenance_lines() == []
    assert NowPlayingFacts(shown="   ", raw="  ", source=SOURCE_ICY).provenance_lines() == []


def test_an_unknown_source_still_reports_the_rendering() -> None:
    # A title with no recorded route (an older session, a route added later)
    # must not claim a source -- but the raw text is still worth showing.
    facts = NowPlayingFacts(shown="A Song", raw='text="A Song"', source=SOURCE_NONE)
    lines = facts.provenance_lines()
    assert not any("Track information from" in line for line in lines)
    assert any("The station sent:" in line for line in lines)


def test_describe_source_is_empty_for_no_source() -> None:
    assert describe_source(SOURCE_NONE) == ""
    assert describe_source("something-else") == ""
    assert describe_source(SOURCE_ICY)
