"""The hosted AI's feature catalogue, read as the remote input it is.

``GET /v1/config``'s ``features`` list lets a new text tool reach both editors
with no release. Every field is validated: a bad entry is dropped on its own, a
bad list is an empty catalogue, and nothing here ever raises -- a catalogue the
client cannot read must never cost the limits that came with it.
"""

from __future__ import annotations

import pytest

from quill.core.ai.gateway_catalogue import (
    MAX_ENTRIES,
    CatalogueFeature,
    extra_features,
    parse_catalogue,
)
from quill.core.ai.gateway_client import GatewayClient, GatewayLimits
from quill.core.ai.writing_tools import ACTIONS


def _entry(**overrides: object) -> dict:
    entry: dict = {
        "id": "find_dates",
        "label": "Find dates",
        "help": "Every date the passage mentions, one per line.",
        "input": "selection",
        "max_input_tokens": 1500,
    }
    entry.update(overrides)
    return entry


def test_a_good_entry_is_read() -> None:
    (feature,) = parse_catalogue([_entry()])
    assert feature == CatalogueFeature(
        "find_dates",
        "Find dates",
        "Every date the passage mentions, one per line.",
        "selection",
        1500,
    )


@pytest.mark.parametrize("raw", [None, {}, "features", 42, {"features": []}])
def test_a_list_that_is_not_a_list_is_an_empty_catalogue(raw: object) -> None:
    assert parse_catalogue(raw) == ()


@pytest.mark.parametrize(
    "bad",
    [
        "not a dict",
        _entry(id="Find-Dates"),
        _entry(id="../etc"),
        _entry(id=""),
        _entry(id=7),
        _entry(id="x" * 41),
        _entry(label=""),
        _entry(label="   "),
        _entry(label=None),
        _entry(label="x" * 61),
        _entry(help=""),
        _entry(help=["a list"]),
        _entry(help="x" * 401),
        _entry(input="image"),
        _entry(input="conversation"),
        _entry(input=None),
    ],
)
def test_a_bad_entry_is_dropped_and_the_rest_kept(bad: object) -> None:
    good = _entry(id="keep_me", label="Keep me")
    assert [f.id for f in parse_catalogue([bad, good])] == ["keep_me"]


def test_unknown_input_kinds_are_skipped_not_guessed() -> None:
    features = parse_catalogue([
        _entry(id="one", label="One", input="selection"),
        _entry(id="two", label="Two", input="prompt"),
        _entry(id="three", label="Three", input="document"),
        _entry(id="four", label="Four", input="spreadsheet"),
    ])
    assert [(f.id, f.input) for f in features] == [
        ("one", "selection"),
        ("two", "prompt"),
        ("three", "document"),
    ]


def test_control_characters_are_removed_from_what_is_read_aloud() -> None:
    (feature,) = parse_catalogue([_entry(label="Find\ndates‮", help="Every\tdate.\x07  Really.")])
    assert feature.label == "Find dates"
    assert feature.help == "Every date. Really."


@pytest.mark.parametrize("tokens", [True, -5, 0, "1500", 1.5, 10**9, None])
def test_an_unusable_input_ceiling_means_the_global_one(tokens: object) -> None:
    (feature,) = parse_catalogue([_entry(max_input_tokens=tokens)])
    assert feature.max_input_tokens == 0


def test_duplicates_keep_the_first() -> None:
    features = parse_catalogue([
        _entry(),
        _entry(label="Another label"),
        _entry(id="other_id", label="FIND DATES"),
    ])
    assert [f.id for f in features] == ["find_dates"]


def test_the_list_is_capped() -> None:
    raw = [_entry(id=f"tool_{n}", label=f"Tool {n}") for n in range(MAX_ENTRIES + 10)]
    assert len(parse_catalogue(raw)) == MAX_ENTRIES


def test_built_in_tools_are_not_offered_twice() -> None:
    built_ids = {fid for fid, _l, _h in ACTIONS}
    built_labels = {label for _f, label, _h in ACTIONS}
    catalogue = parse_catalogue([
        _entry(id="summarize", label="Summarize"),
        _entry(id="summary_two", label="summarize"),
        _entry(),
    ])
    assert [f.id for f in extra_features(catalogue, built_ids, built_labels)] == ["find_dates"]


def test_limits_carry_the_catalogue() -> None:
    limits = GatewayLimits.from_json({"max_input_tokens": 1500, "features": [_entry()]})
    assert [f.id for f in limits.features] == ["find_dates"]


def test_an_older_server_means_no_catalogue() -> None:
    limits = GatewayLimits.from_json({"max_input_tokens": 1500})
    assert limits.features == ()
    assert GatewayLimits().features == ()


def test_a_broken_catalogue_never_costs_the_limits() -> None:
    limits = GatewayLimits.from_json({
        "max_input_tokens": 2400,
        "features": [{"id": None}, "junk", 5, [_entry()]],
    })
    assert limits.max_input_tokens == 2400
    assert limits.features == ()


def test_the_catalogue_comes_from_the_one_config_fetch() -> None:
    """No new call site: the catalogue rides on the existing /v1/config read."""
    asked: list[str] = []

    def opener(url: str, **_kwargs: object) -> dict:
        asked.append(url)
        return {"max_input_tokens": 1500, "features": [_entry()]}

    limits = GatewayClient("https://x", opener=opener).fetch_limits()
    assert asked == ["https://x/v1/config"]
    assert [f.label for f in limits.features] == ["Find dates"]
