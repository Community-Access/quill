"""ADP Assistant: response-model parsing, table cells, the https guard, and
the unlock gate -- pure, no network, no wx."""

from __future__ import annotations

import pytest

import quill.core.adp.client as adp_client
from quill.core.adp.client import DEFAULT_BASE_URL, AdpError, ask, load_client_key
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


def test_default_base_url_is_the_hosted_backend_over_https() -> None:
    # The direct FastAPI backend (docs/OPERATIONS.md), not the old bitsinfo host
    # and not the WordPress site (bits-acb.org, which only fronts the status gate).
    assert DEFAULT_BASE_URL == "https://adp.csedesigns.com"
    assert DEFAULT_BASE_URL.startswith("https://")
    assert "bitsinfo" not in DEFAULT_BASE_URL


def test_client_key_prefers_the_user_override_then_the_bundled_key(monkeypatch) -> None:
    # Vault override wins so a paste in ADP Settings is always a rotation lever.
    monkeypatch.setattr(adp_client, "stored_client_key", lambda: "user-override")
    monkeypatch.setattr(adp_client, "_bundled_client_key", lambda: "baked-in")
    assert load_client_key() == "user-override"

    # No override -> fall back to the key baked into the build.
    monkeypatch.setattr(adp_client, "stored_client_key", lambda: "")
    assert load_client_key() == "baked-in"

    # Neither -> "" (a dev checkout, or a server with client-auth off).
    monkeypatch.setattr(adp_client, "_bundled_client_key", lambda: "")
    assert load_client_key() == ""


def test_bundled_client_key_is_empty_without_the_generated_module() -> None:
    # In an unbuilt checkout quill/_adp_client_key.py does not exist; the import
    # failure must read as "no bundled key," never raise.
    assert adp_client._bundled_client_key() == ""


def test_adp_assistant_is_ungated_but_voice_mode_still_needs_a_code() -> None:
    manager = FeatureManager()
    # The ADP Assistant is un-gated for pre-release testing (its locked_off flag
    # was lifted in feature_catalog.py): available by default, no code required.
    assert manager.state_for("future.adp_assistant") == "on"
    assert manager.is_enabled("future.adp_assistant")
    # ADP Voice Mode stays locked_off -- reachable only via a signed unlock code.
    assert manager.state_for("future.adp_voice_mode") == "off"
    manager.unlocked_feature_ids = frozenset({"future.adp_voice_mode"})
    # Voice mode depends on the (now available) assistant; unlocking it enables
    # the whole chain.
    assert manager.state_for("future.adp_voice_mode") == "on"
    assert manager.is_enabled("future.adp_voice_mode")
