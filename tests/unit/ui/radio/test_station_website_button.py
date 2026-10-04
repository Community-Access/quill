"""A listener's request: the station's website beside Play and Stop."""

from __future__ import annotations

from types import SimpleNamespace

from quill.ui.radio import station_website_button as site


def _host(playing=None, favorite=None) -> SimpleNamespace:
    said: list[str] = []
    return SimpleNamespace(
        _radio_controller=SimpleNamespace(state=SimpleNamespace(station=playing)),
        _selected_favorite=lambda: favorite,
        _announce=said.append,
        said=said,
    )


def test_the_playing_station_wins_and_its_site_opens() -> None:
    playing = SimpleNamespace(display_name="Double Tap Live", homepage="https://doubletaponair.com")
    other = SimpleNamespace(display_label="Other", station=SimpleNamespace(homepage="https://x"))
    host = _host(playing, other)
    opened: list[str] = []
    assert site.press(host, opener=lambda url: opened.append(url) or True)
    assert opened == ["https://doubletaponair.com"]
    assert host.said == ["Opened the website for Double Tap Live."]


def test_with_nothing_playing_the_selected_favorite_is_used() -> None:
    favorite = SimpleNamespace(
        display_label="KSPN", station=SimpleNamespace(homepage="https://espn.com")
    )
    assert site.target(_host(None, favorite)) == ("KSPN", "https://espn.com")


def test_a_station_without_a_website_says_so() -> None:
    playing = SimpleNamespace(display_name="Mystery FM", homepage="")
    host = _host(playing)
    assert not site.press(host, opener=lambda _url: True)
    assert host.said == ["Mystery FM did not give a website."]


def test_nothing_to_point_at_says_how_to_get_one() -> None:
    host = _host()
    assert not site.press(host, opener=lambda _url: True)
    assert "Favorites" in host.said[0]
