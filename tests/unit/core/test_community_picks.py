"""The curated catalogue: what it refuses, what it skips, what it never touches.

Design: docs/design/community-picks.md. This is a file fetched from the web
that causes the app to subscribe to feeds and add stations, so the interesting
tests are all about restraint -- what it declines to do with a document it does
not fully understand.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from quill.core.community_picks import (
    FORMAT,
    KNOWN_TYPES,
    PICKS_URL,
    Catalogue,
    CommunityPicksError,
    load_bundled,
    parse,
)

_BUNDLED = Path(__file__).resolve().parents[3] / "quill" / "core" / "data" / "community_picks.json"
_SCHEMA = (
    Path(__file__).resolve().parents[3] / "quill" / "core" / "schemas" / "community_picks.json"
)


def _doc(*items: dict) -> dict:
    return {
        "format": FORMAT,
        "version": 1,
        "collections": [{"id": "c", "title": "Picks", "items": list(items)}],
    }


def _stream(**over: object) -> dict:
    base = {
        "id": "acb-media-1",
        "type": "stream",
        "title": "ACB Media 1",
        "stream_url": "https://example.com/live",
    }
    base.update(over)
    return base


# -- what it refuses outright --------------------------------------------------


def test_a_document_that_is_not_ours_is_refused() -> None:
    """Valid JSON is not the same as a catalogue. Anything past this point is
    treated as trustworthy-shaped, so the gate has to be here."""
    with pytest.raises(CommunityPicksError):
        parse({"collections": []})
    with pytest.raises(CommunityPicksError):
        parse({"format": "something-else", "collections": []})
    with pytest.raises(CommunityPicksError):
        parse(["not", "even", "an", "object"])


# -- what it skips, quietly ----------------------------------------------------


def test_an_unknown_type_is_skipped_rather_than_guessed_at() -> None:
    """The forward-compatibility promise: a future entry kind must not break a
    client that predates it."""
    catalogue = parse(_doc(_stream(), {"id": "x", "type": "hologram", "title": "Later"}))

    assert [pick.title for pick in catalogue.all_picks] == ["ACB Media 1"]
    assert catalogue.skipped_unknown == 1


def test_the_number_skipped_is_counted_not_hidden() -> None:
    """It is how somebody discovers their app is older than the catalogue."""
    catalogue = parse(_doc({"id": "x", "type": "hologram", "title": "Later"}))

    assert catalogue.skipped_unknown == 1
    assert catalogue.is_empty


def test_the_known_types_are_the_three_the_apps_can_actually_act_on() -> None:
    assert KNOWN_TYPES == {"stream", "podcast", "place"}


def test_an_entry_with_nothing_to_point_at_is_skipped_with_a_warning() -> None:
    catalogue = parse(_doc({"id": "broken", "type": "stream", "title": "No URL"}))

    assert catalogue.is_empty
    assert any("broken" in warning for warning in catalogue.warnings)


def test_a_non_https_url_is_dropped_rather_than_followed() -> None:
    """A catalogue that can point the app at plain HTTP is one that can be
    rewritten by anybody on the path between here and the listener."""
    catalogue = parse(_doc(_stream(stream_url="http://example.com/live")))

    assert catalogue.is_empty


def test_a_malformed_entry_costs_that_entry_and_not_the_window() -> None:
    catalogue = parse(_doc("not a dict", _stream()))  # type: ignore[arg-type]

    assert [pick.title for pick in catalogue.all_picks] == ["ACB Media 1"]


# -- retired: stop offering, never remove --------------------------------------


def test_a_retired_pick_is_not_offered() -> None:
    catalogue = parse(_doc(_stream(), _stream(id="gone", title="Gone", retired=True)))

    assert [pick.title for pick in catalogue.all_picks] == ["ACB Media 1"]
    assert catalogue.skipped_retired == 1


def test_retiring_is_only_ever_about_the_offer() -> None:
    """The boundary that makes this catalogue safe to fetch at all.

    Nothing in this module touches a library or a favorites store -- it returns
    a list of things on offer. Retiring cannot reach into what somebody already
    added because there is no code path from here to their data.
    """
    source = (
        Path(__file__).resolve().parents[3] / "quill" / "core" / "community_picks.py"
    ).read_text(encoding="utf-8")

    for forbidden in ("PodcastLibrary", "RadioFavoritesStore", "save_library", "remove_show"):
        assert forbidden not in source, f"community_picks must not reach {forbidden}"


# -- per-app filtering ---------------------------------------------------------


def test_an_item_can_be_limited_to_one_app() -> None:
    """One file serves Radio and Cast; neither is offered what it cannot play."""
    document = _doc(
        _stream(id="radio-only", title="Radio only", apps=["radio"]),
        _stream(id="cast-only", title="Cast only", apps=["cast"]),
        _stream(id="both", title="Both"),
    )

    radio = [pick.title for pick in parse(document, app="radio").all_picks]
    cast = [pick.title for pick in parse(document, app="cast").all_picks]

    assert radio == ["Radio only", "Both"]
    assert cast == ["Cast only", "Both"]


def test_no_app_named_means_every_pick_is_offered() -> None:
    document = _doc(_stream(id="radio-only", title="Radio only", apps=["radio"]))

    assert len(parse(document).all_picks) == 1


# -- the bundled copy ----------------------------------------------------------


def test_a_copy_ships_with_the_app() -> None:
    """So the picker works on first run, offline, and if the site is down."""
    assert _BUNDLED.is_file()

    catalogue = load_bundled()

    assert not catalogue.is_empty
    assert catalogue.bundled


def test_the_bundled_copy_is_real_acb_data() -> None:
    catalogue = load_bundled()
    kinds = {pick.type for pick in catalogue.all_picks}

    assert {"stream", "podcast"} <= kinds
    assert len(catalogue.all_picks) >= 40


def test_the_bundled_copy_validates_against_the_schema() -> None:
    jsonschema = pytest.importorskip("jsonschema")

    jsonschema.validate(
        json.loads(_BUNDLED.read_text(encoding="utf-8")),
        json.loads(_SCHEMA.read_text(encoding="utf-8")),
    )


def test_every_bundled_id_is_unique_and_url_safe() -> None:
    """ids are stable identity and end up in URLs. str.isalnum() is true for
    "n with tilde", which is how the first generated catalogue produced
    "podcasts-en-espanol" with the tilde still in it."""
    document = json.loads(_BUNDLED.read_text(encoding="utf-8"))
    ids = [item["id"] for collection in document["collections"] for item in collection["items"]]

    assert len(ids) == len(set(ids))
    for value in ids:
        assert value.isascii(), value
        assert value == value.lower(), value


def test_a_missing_or_broken_bundled_copy_is_empty_rather_than_fatal(tmp_path: Path) -> None:
    assert load_bundled(tmp_path / "nope.json") == Catalogue()
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    assert load_bundled(broken) == Catalogue()


# -- the URL contract ----------------------------------------------------------


def test_the_version_lives_in_the_url_path() -> None:
    """So a breaking change moves to /v2/ and a v1 client keeps reading a file
    that still means what it meant."""
    assert "/v1/" in PICKS_URL
    assert PICKS_URL.startswith("https://")
