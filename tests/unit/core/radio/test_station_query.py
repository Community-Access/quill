"""Taking a typed station name apart, and asking every directory properly.

These start as the five stations two ACB members asked for on 2026-09-14, and
the four ways the old search lost them:

* ``WDAN 14.90 AM`` -- a frequency nobody writes that way, and a callsign the
  directory does have.
* ``WBGL`` -- the one that already worked, kept here so aggression cannot break
  the easy case.
* ``Sunny 105.7 Gulf Shores Alabama`` -- Radio Browser calls it
  "WCSN 105.7 FM Orange Beach", so the brand name reaches nothing and only the
  frequency *narrowed to the state* finds it.
* ``100.9 the mix`` -- a brand with a frequency, where the frequency is written
  one way and the station writes it the other.
* ``rock 105 fm`` -- where the trailing band word is the thing that loses it.

The rest are the other spellings people use, each one a real shape: a hyphenated
frequency off a billboard, a run-together "Sunny105.7", a European decimal
comma, "play" in front, a lower-case state at the end.

The parse is pure, so all of this is testable without a network.
"""

from __future__ import annotations

import pytest

from quill.core.radio import station_query as sq
from quill.core.radio.models import RadioStation


def _named(*names: str) -> list[RadioStation]:
    return [RadioStation(name=n, stream_url=f"http://example.invalid/{n}") for n in names]


# -- the facts ---------------------------------------------------------------


def test_a_callsign_is_recognised() -> None:
    assert sq.parse("WDAN 14.90 AM").callsign == "WDAN"


def test_a_four_letter_word_is_not_a_callsign() -> None:
    """ "Wind" and "West" start with W and are not stations."""
    assert sq.parse("wind of change radio").callsign == ""


def test_an_am_frequency_written_with_a_decimal_point_is_repaired() -> None:
    """Nobody's radio says 14.90; the directory says 1490."""
    parsed = sq.parse("WDAN 14.90 AM")
    assert parsed.frequency == "1490"
    assert parsed.band == "AM"


def test_an_fm_frequency_keeps_its_decimal_point() -> None:
    parsed = sq.parse("Sunny 105.7 Gulf Shores Alabama")
    assert parsed.frequency == "105.7"
    assert parsed.band == "FM"


def test_a_run_together_fm_frequency_is_punctuated() -> None:
    """A station writes it 100.9 and a listener types 1009."""
    assert sq.parse("1009 the mix").frequency == "100.9"


def test_a_plain_hundreds_number_is_left_alone() -> None:
    """``rock 105`` is a brand, not a mistyped 10.5."""
    assert sq.parse("rock 105 fm").frequency == "105"


@pytest.mark.parametrize(
    "typed",
    ["rock 105-9", "rock 105,9", "rock 105.9", "rock 105 - 9"],
)
def test_every_way_a_frequency_gets_punctuated(typed: str) -> None:
    """A hyphen off a billboard, a European comma, a plain point."""
    assert sq.parse(typed).frequency == "105.9"


@pytest.mark.parametrize("typed", ["Sunny105.7", "sunny 105.7", "SUNNY 105.7 FM"])
def test_a_frequency_run_into_the_name_is_separated(typed: str) -> None:
    parsed = sq.parse(typed)
    assert parsed.frequency == "105.7"
    assert parsed.brand == "sunny"


def test_a_band_word_run_into_the_frequency_is_separated() -> None:
    parsed = sq.parse("1490AM")
    assert parsed.frequency == "1490"
    assert parsed.band == "AM"


@pytest.mark.parametrize("opener", ["play ", "listen to ", "tune in to ", "find ", "search for "])
def test_an_opener_addressed_to_the_app_is_dropped(opener: str) -> None:
    assert sq.parse(opener + "WBGL").callsign == "WBGL"


def test_a_state_name_is_found() -> None:
    assert sq.parse("Sunny 105.7 Gulf Shores Alabama").state == "Alabama"


def test_an_uppercase_state_abbreviation_is_found() -> None:
    assert sq.parse("WBGL Champaign, IL").state == "Illinois"


def test_a_lower_case_state_abbreviation_at_the_end_is_found() -> None:
    """Nobody shouts when they are typing fast."""
    assert sq.parse("sunny 105.7 gulf shores al").state == "Alabama"


def test_a_word_like_abbreviation_in_the_middle_is_not_a_state() -> None:
    """``in``, ``or`` and ``me`` are words before they are states."""
    assert sq.parse("rock in the mix").state == ""


def test_a_country_is_found() -> None:
    assert sq.parse("Rock 105 Canada").country == "Canada"


def test_the_brand_is_the_words_before_the_frequency() -> None:
    parsed = sq.parse("Sunny 105.7 Gulf Shores Alabama")
    assert parsed.brand == "sunny"
    assert parsed.place == "gulf shores"


def test_the_brand_is_the_words_after_a_leading_frequency() -> None:
    assert sq.parse("100.9 the mix").brand == "the mix"


def test_a_trailing_band_word_is_not_part_of_the_brand() -> None:
    assert sq.parse("rock 105 fm").brand == "rock"


def test_an_empty_query_parses_to_nothing() -> None:
    assert sq.parse("   ").brand == ""


# -- the variants ------------------------------------------------------------


def test_what_was_typed_is_always_asked_first() -> None:
    """Aggression adds queries; it never replaces the one the user chose."""
    assert sq.variants(sq.parse("rock 105 fm"))[0] == "rock 105 fm"


def test_the_band_word_is_dropped_in_a_variant() -> None:
    assert "rock 105" in sq.variants(sq.parse("rock 105 fm"))


def test_the_callsign_is_asked_on_its_own() -> None:
    assert "WDAN" in sq.variants(sq.parse("WDAN 14.90 AM"))


def test_the_brand_and_frequency_are_asked_together_without_the_place() -> None:
    """The city is what a directory that indexes by name chokes on."""
    assert "sunny 105.7" in sq.variants(sq.parse("Sunny 105.7 Gulf Shores Alabama"))


def test_a_leading_frequency_keeps_its_place_in_the_variant() -> None:
    assert "100.9 the mix" in sq.variants(sq.parse("100.9 the mix"))


def test_both_spellings_of_the_frequency_are_asked() -> None:
    got = sq.variants(sq.parse("100.9 the mix"))
    assert any("1009" in v for v in got)


def test_the_callsign_and_the_brand_are_asked_together() -> None:
    """How a directory files "WGFM ROCK 105"."""
    assert "WGFM rock" in sq.variants(sq.parse("WGFM rock 105"))


def test_variants_are_unique_and_never_empty() -> None:
    for text in ("WBGL", "rock 105 fm", "Sunny 105.7 Gulf Shores Alabama", "100.9 the mix"):
        got = sq.variants(sq.parse(text))
        assert got == tuple(dict.fromkeys(got))
        assert all(v.strip() for v in got)


def test_a_bare_name_asks_once() -> None:
    """Nothing to take apart, nothing to add: one query, as before."""
    assert sq.variants(sq.parse("WBGL")) == ("WBGL",)


# -- the narrowed searches ---------------------------------------------------


def test_the_frequency_is_narrowed_to_the_state() -> None:
    """The one that finds WCSN: Radio Browser's name search has no "Sunny" to
    match, but ``105.7`` inside Alabama has exactly one answer."""
    got = sq.narrowed_searches(sq.parse("Sunny 105.7 Gulf Shores Alabama"))
    assert ("105.7", "Alabama", "") in got


def test_the_brand_is_narrowed_to_the_state_too() -> None:
    got = sq.narrowed_searches(sq.parse("Sunny 105.7 Gulf Shores Alabama"))
    assert ("sunny", "Alabama", "") in got


def test_no_place_means_no_narrowed_search() -> None:
    assert sq.narrowed_searches(sq.parse("100.9 the mix")) == ()


def test_a_country_alone_still_narrows() -> None:
    got = sq.narrowed_searches(sq.parse("Rock 105 Canada"))
    assert ("105", "", "Canada") in got


# -- ranking -----------------------------------------------------------------


def test_the_frequency_and_the_brand_together_beat_either_alone() -> None:
    rows = _named("Sunny 105.7 Canadohta Lake", "Sunny 95", "WCSN 105.7 FM Orange Beach")
    ranked = sq.rank(rows, "Sunny 105.7 Gulf Shores Alabama")
    assert ranked[0].name == "Sunny 105.7 Canadohta Lake"
    assert ranked[1].name == "WCSN 105.7 FM Orange Beach"


def test_a_station_carrying_the_frequency_beats_one_that_does_not() -> None:
    ranked = sq.rank(_named("Mix Lite", "Mix 100.9 | 99.3"), "100.9 the mix")
    assert ranked[0].name == "Mix 100.9 | 99.3"


def test_the_run_together_spelling_still_counts_as_the_frequency() -> None:
    ranked = sq.rank(_named("Some Other Station", "Hot 1009"), "100.9 the mix")
    assert ranked[0].name == "Hot 1009"


def test_an_exact_name_wins_outright() -> None:
    ranked = sq.rank(_named("WBGL Uplifting", "WBGL"), "WBGL")
    assert ranked[0].name == "WBGL"


def test_the_callsign_matches_as_a_word_not_as_a_substring() -> None:
    """ "wdan" is inside "NewDanceRadio", and that is not a match."""
    ranked = sq.rank(_named("NewDanceRadio", "WDAN-AM"), "WDAN 14.90 AM")
    assert ranked[0].name == "WDAN-AM"


def test_the_state_in_a_tag_breaks_a_tie() -> None:
    near = RadioStation(
        name="105.7 FM", stream_url="http://a.invalid", tags=("alabama", "classic hits")
    )
    far = RadioStation(name="105.7 FM", stream_url="http://b.invalid", tags=("oregon",))
    assert sq.rank([far, near], "Sunny 105.7 Alabama")[0] is near


def test_a_dead_stream_sinks_below_an_equally_good_live_one() -> None:
    dead = RadioStation(name="Rock 105", stream_url="http://a.invalid", last_check_ok=False)
    live = RadioStation(name="Rock 105", stream_url="http://b.invalid", last_check_ok=True)
    assert sq.rank([dead, live], "rock 105")[0] is live


def test_votes_break_a_tie_between_equally_good_matches() -> None:
    quiet = RadioStation(name="Rock 105", stream_url="http://a.invalid", votes=2)
    loved = RadioStation(name="Rock 105", stream_url="http://b.invalid", votes=900)
    assert sq.rank([quiet, loved], "rock 105")[0] is loved


def test_ranking_is_stable_for_equal_scores() -> None:
    rows = _named("Alpha", "Beta", "Gamma")
    assert [s.name for s in sq.rank(rows, "nothing matches this")] == ["Alpha", "Beta", "Gamma"]


def test_an_empty_query_changes_nothing() -> None:
    rows = _named("Alpha", "Beta")
    assert sq.rank(rows, "") == rows


def test_a_station_beats_a_programme_that_merely_names_it() -> None:
    """Both carry the callsign; only one of them is a radio station."""
    rows = _named("7-14-26 Bloomdaddy, Sam & Otis - Bloomdaddy wDan Veroni", "WDAN-AM")
    assert sq.rank(rows, "WDAN 14.90 AM")[0].name == "WDAN-AM"


def test_the_length_penalty_never_reorders_rows_that_matched_nothing() -> None:
    rows = _named("A Very Long Station Name Indeed", "Short")
    assert [s.name for s in sq.rank(rows, "zzz qqq")] == [
        "A Very Long Station Name Indeed",
        "Short",
    ]


def test_a_row_found_in_the_named_place_outranks_a_better_worded_one() -> None:
    """The WCSN case. "Sunny 105.7 Canadohta Lake" shares two words with the
    query and is in Pennsylvania; "WCSN 105.7 FM Orange Beach" shares one and is
    the station -- and the only thing that says so is that Radio Browser
    returned it from a search narrowed to Alabama."""
    wrong = RadioStation(name="Sunny 105.7 Canadohta Lake", stream_url="http://a.invalid")
    right = RadioStation(
        name="WCSN 105.7 FM Orange Beach", stream_url="http://b.invalid", place_confirmed=True
    )
    assert sq.rank([wrong, right], "Sunny 105.7 Gulf Shores Alabama")[0] is right


def test_place_confirmation_cannot_rescue_a_row_that_matched_nothing() -> None:
    noise = RadioStation(name="Talk 1200", stream_url="http://a.invalid", place_confirmed=True)
    match = RadioStation(name="Sunny 105.7", stream_url="http://b.invalid")
    assert sq.rank([noise, match], "Sunny 105.7 Alabama")[0] is match
