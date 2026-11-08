"""TuneIn's category pages: Music, Talk, Sports and Local, and their paging.

A hand-made Browse.ashx reply in the shape TuneIn answered with on 2026-11-07:
grouped "Local Stations" and "Stations" (one station in both), a "More
Stations" link carrying the offset, and a "Shows" group. No network.
"""

from __future__ import annotations

import json

import pytest

from quill.core.radio import browse_sources, tunein

ROOT = {
    "head": {"title": "Browse", "status": "200"},
    "body": [
        {
            "type": "link",
            "text": key.title(),
            "key": key,
            "URL": f"http://opml.radiotime.com/Browse.ashx?c={key}",
        }
        for key in ("local", "music", "talk", "sports")
    ],
}

COUNTRY = {
    "head": {"title": "Country", "status": "200"},
    "body": [
        {
            "text": "Local Stations (1)",
            "key": "local",
            "children": [
                {
                    "type": "audio",
                    "item": "station",
                    "text": "KiiM-FM 99.5",
                    "guide_id": "s33121",
                    "URL": "http://opml.radiotime.com/Tune.ashx?id=s33121",
                },
            ],
        },
        {
            "text": "Stations",
            "key": "stations",
            "children": [
                {
                    "type": "audio",
                    "item": "station",
                    "text": "KiiM-FM 99.5",
                    "guide_id": "s33121",
                    "URL": "http://opml.radiotime.com/Tune.ashx?id=s33121",
                },
                {
                    "type": "audio",
                    "item": "station",
                    "text": "Radio Free Americana",
                    "guide_id": "s96727",
                    "URL": "http://opml.radiotime.com/Tune.ashx?id=s96727",
                },
                {
                    "type": "link",
                    "text": "More Stations",
                    "key": "nextStations",
                    "URL": "http://opml.radiotime.com/Browse.ashx?offset=26&id=c57940"
                    "&formats=mp3,aac,ogg,hls&filter=s",
                },
            ],
        },
    ],
}


def test_the_root_offers_the_four_categories(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tunein, "_fetch", lambda url: json.dumps(ROOT))
    labels = [node.label for node in browse_sources.browse("tunein")]
    assert labels == ["Local", "Music", "Talk", "Sports"]


def test_a_station_in_two_groups_is_listed_once() -> None:
    rows = tunein.parse_browse_level(json.dumps(COUNTRY))
    stations = [r.guide_id for r in rows if r.is_station]
    assert stations == ["s33121", "s96727"]


def test_more_stations_pages_through_the_offset(monkeypatch: pytest.MonkeyPatch) -> None:
    asked: list[str] = []

    def fetch(url: str) -> str:
        asked.append(url)
        return json.dumps(COUNTRY)

    monkeypatch.setattr(tunein, "_fetch", fetch)
    nodes = browse_sources.browse("tunein:http://opml.radiotime.com/Browse.ashx?id=c57940")
    more = nodes[-1]
    assert more.label == "More Stations" and more.is_folder
    assert [n.is_leaf for n in nodes[:-1]] == [True, True]
    browse_sources.browse(more.node_id)
    assert asked[-1].startswith("https://opml.radiotime.com/Browse.ashx?offset=26&id=c57940")
    assert asked[-1].endswith("&render=json")
