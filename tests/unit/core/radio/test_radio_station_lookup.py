"""Finding stations by what is known about them: tags, your tags, flagships."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from quill.core.radio import sports_flagships, station_lookup
from quill.core.radio import station_tags as tags_mod
from quill.core.radio.favorites import RadioFavoritesStore
from quill.core.radio.models import RadioStation

_DATA = {
    "teams": [
        {
            "team": "Detroit Tigers",
            "league": "MLB",
            "sport": "baseball",
            "aliases": ["Tigers", "Detroit baseball"],
            "source": "https://example.invalid/tigers",
            "stations": [
                {
                    "name": "97.1 The Ticket",
                    "call_sign": "WXYT-FM",
                    "city": "Detroit, MI",
                    "homepage": "https://example.invalid/971",
                    "notes": "",
                }
            ],
        },
        {
            "team": "Colorado Rockies",
            "league": "MLB",
            "sport": "baseball",
            "aliases": ["Rockies"],
            "stations": [{"name": "850 KOA", "call_sign": "KOA"}],
        },
        {"team": "No Stations FC", "league": "MLS", "sport": "soccer", "stations": []},
        "not a team",
    ]
}

WXYT = RadioStation(name="97.1 The Ticket WXYT", stream_url="http://s/wxyt", tags=("sports",))
WXYZ = RadioStation(name="WXYZ Oldies", stream_url="http://s/wxyz")
KOA = RadioStation(name="News Radio 850 KOA", stream_url="http://s/koa")


@pytest.fixture
def teams(tmp_path: Path) -> tuple[sports_flagships.Team, ...]:
    path = tmp_path / "flagships.json"
    path.write_text(json.dumps(_DATA), encoding="utf-8")
    sports_flagships.clear_cache()
    loaded = sports_flagships.load_teams(path)
    yield loaded
    sports_flagships.clear_cache()


@pytest.fixture
def use_teams(monkeypatch: pytest.MonkeyPatch, teams):
    """Make every module-level lookup read the synthetic list."""
    monkeypatch.setattr(sports_flagships, "load_teams", lambda path=None: teams)
    return teams


def test_malformed_entries_are_skipped(teams) -> None:
    assert [t.team for t in teams] == ["Detroit Tigers", "Colorado Rockies"]


@pytest.mark.parametrize(
    "query",
    ["Tigers", "tiger", "Detroit baseball", "WXYT", "detroit tigers radio", "97.1 The Ticket"],
)
def test_team_names_aliases_and_call_signs_match(teams, query: str) -> None:
    assert [t.team for t in sports_flagships.teams_matching(query, teams)] == ["Detroit Tigers"]


def test_league_lists_every_flagship(teams) -> None:
    assert len(sports_flagships.teams_matching("MLB", teams)) == 2


@pytest.mark.parametrize("query", ["rock", "classic rock", "sports", "", "the"])
def test_unrelated_or_empty_words_match_nothing(teams, query: str) -> None:
    assert sports_flagships.teams_matching(query, teams) == []


def test_missing_or_broken_file_is_an_empty_list(tmp_path: Path) -> None:
    sports_flagships.clear_cache()
    assert sports_flagships.load_teams(tmp_path / "absent.json") == ()
    broken = tmp_path / "broken.json"
    broken.write_text("{ nope", encoding="utf-8")
    assert sports_flagships.load_teams(broken) == ()
    wrong = tmp_path / "wrong.json"
    wrong.write_text(json.dumps({"teams": {"a": 1}}), encoding="utf-8")
    assert sports_flagships.load_teams(wrong) == ()
    sports_flagships.clear_cache()


def test_loading_is_cached(tmp_path: Path) -> None:
    path = tmp_path / "f.json"
    path.write_text(json.dumps(_DATA), encoding="utf-8")
    sports_flagships.clear_cache()
    first = sports_flagships.load_teams(path)
    path.write_text("{}", encoding="utf-8")
    assert sports_flagships.load_teams(path) is first
    sports_flagships.clear_cache()


def test_reason_text() -> None:
    team = sports_flagships.Team("Detroit Tigers", "MLB", "baseball")
    other = sports_flagships.Team("Detroit Lions", "NFL", "football")
    assert sports_flagships.reason_for([team]) == "carries the Detroit Tigers"
    assert sports_flagships.reason_for([team, other]) == (
        "carries the Detroit Tigers and the Detroit Lions"
    )
    many = [sports_flagships.Team(f"T{i}", "", "") for i in range(5)]
    assert sports_flagships.reason_for(many) == "carries the T0, the T1 and 3 more teams"
    assert sports_flagships.reason_for([]) == ""


def test_station_matching_by_call_sign_homepage_or_distinct_name() -> None:
    flagship = sports_flagships.FlagshipStation(
        "97.1 The Ticket", "WXYT-FM", homepage="https://www.example.invalid/971/"
    )
    assert sports_flagships.station_matches(WXYT, flagship)
    assert not sports_flagships.station_matches(WXYZ, flagship)
    by_site = RadioStation(name="Ticket", stream_url="x", homepage="http://example.invalid/971")
    assert sports_flagships.station_matches(by_site, flagship)
    vague = sports_flagships.FlagshipStation("The Fan", "")
    assert not sports_flagships.station_matches(
        RadioStation(name="Sports Radio The Fan", stream_url="x"), vague
    )


def test_flagship_rows_resolve_through_find_and_say_why(use_teams) -> None:
    asked: list[str] = []

    def find(text: str) -> list[RadioStation]:
        asked.append(text)
        return [WXYZ, WXYT] if text == "WXYT" else []

    rows = station_lookup.flagship_rows("Tigers", find=find)
    assert [r.name for r in rows] == [WXYT.name]
    assert rows[0].match_reason == "carries the Detroit Tigers"
    assert asked == ["WXYT"]
    # The directory's own row is not modified.
    assert WXYT.match_reason == ""


def test_flagship_rows_fall_back_to_the_name_and_survive_a_failing_find(use_teams) -> None:
    def find(text: str) -> list[RadioStation]:
        if text == "KOA":
            raise OSError("offline")
        return [KOA] if text == "850 KOA" else []

    rows = station_lookup.flagship_rows("Rockies", find=find)
    assert [r.name for r in rows] == [KOA.name]


def test_lane_rows_put_your_tags_first(use_teams) -> None:
    favorites = RadioFavoritesStore()
    mine = RadioStation(name="Hockey Night", stream_url="http://s/hn")
    favorites.add(mine)
    favorites.favorites[0].user_tags = ("Red Wings", "Detroit")
    rows = station_lookup.lane_rows(
        "Detroit", favorites=favorites, store=tags_mod.StationTagStore(), find=lambda t: [WXYT]
    )
    assert [r.name for r in rows] == ["Hockey Night", WXYT.name]
    assert rows[0].match_reason == "has your tag Detroit"
    assert rows[1].match_reason == "carries the Detroit Tigers"
    assert station_lookup.lane_rows("  ", favorites=None, store=None, find=lambda t: []) == []


def test_favorites_filter_matches_names_tags_your_tags_and_flagships(use_teams) -> None:
    store = RadioFavoritesStore()
    store.add(WXYT)
    store.add(RadioStation(name="Jazz FM", stream_url="http://s/jazz", tags=("smooth jazz",)))
    store.add(RadioStation(name="Talk", stream_url="http://s/talk"))
    store.favorites[2].user_tags = ("Michigan politics",)

    def names(query: str) -> list[str]:
        return [f.station.name for f in store.search(query)]

    assert names("jazz fm") == ["Jazz FM"]  # name
    assert names("smooth") == ["Jazz FM"]  # directory tag
    assert names("politics michigan") == ["Talk"]  # your tags, any word order
    assert names("Tigers") == [WXYT.name]  # flagship team
    assert names("Detroit baseball") == [WXYT.name]  # alias words
    assert names("MLB") == [WXYT.name]  # league
    assert len(names("")) == 3


def test_favorite_label_says_why_and_where(use_teams) -> None:
    store = RadioFavoritesStore()
    store.add(WXYT, folder="Sports")
    favorite = store.favorites[0]
    assert station_lookup.favorite_label(favorite, "Tigers") == (
        f"{WXYT.display_name} -- carries the Detroit Tigers -- in Sports"
    )
    favorite.user_tags = ("ballgame",)
    assert station_lookup.favorite_reason(favorite, "ballgame") == "has your tag ballgame"
    assert station_lookup.favorite_label(favorite, "WXYT").endswith("-- in Sports")


def test_ranking_floats_a_reasoned_row_and_merge_keeps_the_reason() -> None:
    from dataclasses import replace

    from quill.core.radio.directory_search import merge_and_rank

    tagged = replace(WXYT, match_reason="carries the Detroit Tigers")
    noise = RadioStation(name="Tigers Talk Podcast Hour", stream_url="http://s/noise")
    plain_copy = replace(WXYT)
    merged = merge_and_rank([[noise, plain_copy], [tagged]], "Tigers")
    assert merged[0].stream_url == WXYT.stream_url
    assert merged[0].match_reason == "carries the Detroit Tigers"


def test_details_text_says_why_it_was_found() -> None:
    from dataclasses import replace

    text = replace(WXYT, match_reason="carries the Detroit Tigers").details_text
    assert text.split("\n")[1] == "Found because it carries the Detroit Tigers"


def test_the_shipped_list_loads_and_records_a_source_for_every_team() -> None:
    sports_flagships.clear_cache()
    teams = sports_flagships.load_teams()
    assert len(teams) > 100
    assert all(team.source.startswith("https://") for team in teams)
    assert {team.league for team in teams} <= {"MLB", "NFL", "NBA", "NHL", "MLS", "WNBA"}
    raw = json.loads(sports_flagships.DATA_PATH.read_text(encoding="utf-8"))
    # Call signs and names only: never a stream address, which would go stale.
    for entry in raw["teams"]:
        for station in entry["stations"]:
            assert set(station) <= {"name", "call_sign", "city", "homepage", "notes"}
    sports_flagships.clear_cache()
