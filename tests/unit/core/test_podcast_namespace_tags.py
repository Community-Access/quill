"""The Podcasting 2.0 tags Cast was downloading and throwing away.

Six tags, each already published by real shows and each answering a question a
listener asks out loud. The tests that matter here are the tolerance ones: a
feed is somebody else's input, and one malformed tag must never cost somebody
their whole podcast.
"""

from __future__ import annotations

import json

import pytest

from quill.core.podcasts.namespace_tags import (
    NamespaceTags,
    parse,
    parse_alternates,
    parse_funding,
    parse_live_items,
    parse_people,
    parse_podroll,
    parse_soundbites,
)

_ITEM = """
<item>
  <title>Ep 1</title>
  <podcast:person role="Host" href="https://alice.example"
   img="https://a.png">Alice Adams</podcast:person>
  <podcast:person role="Guest">Bob Brown</podcast:person>
  <podcast:soundbite startTime="1800.5" duration="42.25">The good bit</podcast:soundbite>
  <podcast:soundbite startTime="60" duration="30" />
  <podcast:location geo="geo:39.09,-94.57">Kansas City, Missouri</podcast:location>
  <podcast:funding url="https://support.example">Buy us a coffee</podcast:funding>
  <podcast:podroll>
    <podcast:remoteItem feedUrl="https://one.example/feed"/>
    <podcast:remoteItem feedUrl="https://two.example/feed"/>
  </podcast:podroll>
  <podcast:alternateEnclosure type="audio/mpeg" bitrate="64000" title="Low bandwidth">
    <podcast:source uri="https://low.example/ep1.mp3"/>
  </podcast:alternateEnclosure>
  <podcast:liveItem status="live" start="2026-08-14T20:00">
    <title>Live tonight</title>
    <enclosure url="https://live.example/stream" type="audio/mpeg"/>
  </podcast:liveItem>
</item>
"""


def test_people_carry_their_role_and_read_as_a_sentence() -> None:
    people = parse_people(_ITEM)
    # "Jane Smith, guest" rather than a Name column and a Role column: a list
    # that makes you arrow right to learn she is the guest costs two keystrokes
    # for one fact.
    assert [person.display for person in people] == ["Alice Adams, host", "Bob Brown, guest"]
    assert people[0].link_url == "https://alice.example"
    assert people[1].link_url == ""


def test_soundbites_are_ordered_by_when_they_happen() -> None:
    # Positions in one episode, so the order somebody expects is the order they
    # occur in -- not the order the publisher happened to write them.
    bites = parse_soundbites(_ITEM)
    assert [bite.start_ms for bite in bites] == [60_000, 1_800_500]
    assert bites[1].title == "The good bit"
    assert bites[1].end_ms == 1_800_500 + 42_250


def test_a_soundbite_with_no_length_is_not_a_mark() -> None:
    # A start with no duration marks nothing, and inventing an end would be
    # claiming knowledge the feed did not publish.
    assert parse_soundbites('<podcast:soundbite startTime="10"/>') == []


def test_live_items_carry_their_stream_and_whether_it_is_on() -> None:
    items = parse_live_items(_ITEM)
    assert items[0].title == "Live tonight"
    assert items[0].is_live is True
    assert items[0].stream_url == "https://live.example/stream"
    assert (
        parse_live_items('<podcast:liveItem status="ended"><title>Over</title></podcast:liveItem>')[
            0
        ].is_live
        is False
    )


def test_a_podroll_yields_feed_addresses_not_resolved_shows() -> None:
    # Resolving is a network act, and this module never performs one.
    assert parse_podroll(_ITEM) == ["https://one.example/feed", "https://two.example/feed"]


def test_funding_is_a_link_and_a_label_and_nothing_else() -> None:
    links = parse_funding(_ITEM)
    assert links[0].url == "https://support.example"
    assert links[0].display == "Buy us a coffee"
    assert parse_funding('<podcast:funding url="https://x"></podcast:funding>')[0].display == (
        "Support this podcast"
    )


def test_an_alternate_enclosure_says_what_it_is_for() -> None:
    alternates = parse_alternates(_ITEM)
    assert alternates[0].url == "https://low.example/ep1.mp3"
    assert alternates[0].display == "Low bandwidth, 64 kbps"


def test_a_location_is_text_and_no_map_is_offered() -> None:
    assert parse(_ITEM).location == "Kansas City, Missouri"


def test_entities_are_resolved_so_a_name_reads_as_a_name() -> None:
    tags = parse('<podcast:person role="host">Ren&#233;e O&amp;apos;Hara</podcast:person>')
    assert tags.people[0].name.startswith("Renée")


@pytest.mark.parametrize(
    "junk",
    [
        "",
        "<item><title>Nothing here</title></item>",
        "<podcast:person role=",
        '<podcast:soundbite startTime="abc" duration="xyz">Broken</podcast:soundbite>',
        "<podcast:alternateEnclosure><podcast:source/></podcast:alternateEnclosure>",
    ],
)
def test_a_bad_tag_costs_nothing_rather_than_raising(junk: str) -> None:
    # One malformed tag in one episode must never cost somebody their feed.
    assert parse(junk).is_empty


def test_nothing_found_writes_nothing_to_disk() -> None:
    # A library of feeds that publish none of this pays nothing for the feature
    # existing.
    assert NamespaceTags().to_dict() == {}


def test_it_survives_a_round_trip_through_json() -> None:
    tags = parse(_ITEM)
    restored = NamespaceTags.from_dict(json.loads(json.dumps(tags.to_dict())))
    assert [p.display for p in restored.people] == [p.display for p in tags.people]
    assert [b.start_ms for b in restored.soundbites] == [b.start_ms for b in tags.soundbites]
    assert restored.podroll == tags.podroll
    assert restored.location == tags.location
    assert [a.display for a in restored.alternates] == [a.display for a in tags.alternates]


@pytest.mark.parametrize("junk", [None, [], "nope", 7, {"people": "not a list"}])
def test_a_damaged_record_reads_as_an_absent_one(junk: object) -> None:
    assert NamespaceTags.from_dict(junk).is_empty


def test_a_record_from_a_newer_build_drops_only_what_it_cannot_build() -> None:
    restored = NamespaceTags.from_dict({
        "people": [{"name": "Alice", "role": "host", "invented_field": 1}],
        "soundbites": [{"start_ms": 10, "duration_ms": 20}, "not a row"],
    })
    assert restored.people[0].name == "Alice"
    assert len(restored.soundbites) == 1
