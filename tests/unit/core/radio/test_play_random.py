"""Play Random: never the same station twice in a row, one plain sentence."""

from __future__ import annotations

from types import SimpleNamespace

from quill.core.radio import play_random as pr


def _s(name: str, uuid: str = "", url: str = "") -> SimpleNamespace:
    return SimpleNamespace(
        display_name=name, station_uuid=uuid, stream_url=url or f"http://x/{name}"
    )


def test_pick_index_empty_is_minus_one() -> None:
    assert pr.pick_index([]) == -1


def test_never_repeats_when_there_is_a_choice() -> None:
    keys = ["a", "b", "c"]
    for last in keys:
        for r in range(3):
            index = pr.pick_index(keys, last, rng=lambda n, r=r: r % n)
            assert keys[index] != last


def test_one_station_plays_again() -> None:
    assert pr.pick_index(["a"], "a", rng=lambda n: 0) == 0


def test_duplicate_rows_of_the_last_station_are_all_set_aside() -> None:
    assert pr.pick_index(["a", "a", "b"], "a", rng=lambda n: 0) == 2


def test_choose_remembers_and_alternates() -> None:
    state = pr.PlayRandom()
    stations = [_s("one"), _s("two")]
    first = state.choose(stations, rng=lambda n: 0)
    second = state.choose(stations, rng=lambda n: 0)
    third = state.choose(stations, rng=lambda n: 0)
    assert first is not second and third is first


def test_identity_prefers_directory_id_then_stream() -> None:
    assert pr.station_identity(_s("x", uuid="U")) == "id:U"
    assert pr.station_identity(_s("x", url="HTTP://A/b")) == "url:http://a/b"


def test_sentences() -> None:
    assert pr.chosen_sentence("KEXP", pr.POOL_FAVORITES, 12) == (
        "Playing KEXP, picked at random from 12 favorites."
    )
    assert pr.chosen_sentence("KEXP", pr.POOL_FAVORITES, 1) == (
        "Playing KEXP, the only favorite there is."
    )
    assert "no favorites" in pr.empty_sentence(pr.POOL_FAVORITES)
    assert "no streams" in pr.empty_sentence(pr.POOL_STREAMS)
    assert "no stations" in pr.empty_sentence(pr.POOL_STATIONS)
    for text in (
        pr.chosen_sentence("A", pr.POOL_STREAMS, 3),
        pr.empty_sentence(pr.POOL_FAVORITES),
    ):
        assert "—" not in text and "tick" not in text.lower()
