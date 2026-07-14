"""ADP Assistant: response-model parsing, table cells, the https guard, and
the unlock gate -- pure, no network, no wx."""

from __future__ import annotations

import pytest

from quill.core.adp.client import AdpError, ask
from quill.core.adp.models import TABLE_COLUMNS, AskResponse, row_cell
from quill.core.features import FeatureManager


def test_ask_response_parses_the_documented_shape() -> None:
    response = AskResponse.from_dict({
        "answer": "I found 2 described comedies on Netflix.",
        "datasets": [
            {
                "tool": "search_titles",
                "input": {"provider": "Netflix", "genre": "Comedy"},
                "result": {
                    "kind": "titles",
                    "count": 2,
                    "rows": [
                        {
                            "title": "The Good Place",
                            "year": 2016,
                            "media_type": "series",
                            "providers": ["Netflix"],
                            "rating": "TV-PG",
                            "genres": ["Comedy"],
                        },
                        {"title": "Bridgerton", "year": 2020},
                    ],
                },
            }
        ],
        "history": [{"role": "user", "content": "q"}],
    })
    assert "described comedies" in response.answer
    assert len(response.datasets) == 1
    dataset = response.datasets[0]
    assert dataset.kind == "titles"
    assert dataset.count == 2
    assert len(dataset.rows) == 2
    assert response.history  # opaque, but must round-trip


def test_unknown_kinds_and_fields_parse_generically() -> None:
    response = AskResponse.from_dict({
        "answer": "ok",
        "datasets": [{"tool": "future_tool", "result": {"kind": "hologram", "novel_field": 1}}],
        "history": [],
    })
    assert response.datasets[0].kind == "hologram"
    assert response.datasets[0].rows == []


def test_garbage_parses_to_empty_answer() -> None:
    assert AskResponse.from_dict(None).answer == ""
    assert AskResponse.from_dict("nope").datasets == []


def test_row_cell_joins_lists_and_falls_through_keys() -> None:
    row = {"providers": ["Netflix", "Hulu"], "program": "Described Show"}
    assert row_cell(row, ("providers",)) == "Netflix, Hulu"
    assert row_cell(row, ("title", "program", "name")) == "Described Show"
    assert row_cell(row, ("missing",)) == ""
    assert len(TABLE_COLUMNS) >= 4


def test_ask_refuses_plain_http() -> None:
    with pytest.raises(AdpError):
        ask("hello", base_url="http://insecure.example")


def test_ask_refuses_safe_mode() -> None:
    with pytest.raises(AdpError):
        ask("hello", safe_mode=True)


def test_feature_is_locked_until_a_signed_code_unlocks_it() -> None:
    manager = FeatureManager()
    assert manager.state_for("future.adp_assistant") == "off"
    assert manager.state_for("future.adp_voice_mode") == "off"
    manager.unlocked_feature_ids = frozenset({"future.adp_assistant", "future.adp_voice_mode"})
    assert manager.state_for("future.adp_assistant") == "on"
    # Voice mode depends on the assistant; both unlocked -> enabled chain holds.
    assert manager.is_enabled("future.adp_voice_mode")
