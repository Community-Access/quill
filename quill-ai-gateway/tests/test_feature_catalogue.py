"""``GET /v1/config``'s ``features``: the catalogue that lets a new text tool
reach every installed client with no client release.

Three promises, each one a test: every shipped feature is described (a template
with no catalogue entry is a tool nobody can find); a feature switched off is
not offered (a row that only answers with a refusal is worse than no row); and
the keys older clients read are exactly where they were.
"""

from __future__ import annotations

import pytest
from app.models import FeatureFlag
from app.prompts import (
    CATALOGUE,
    DEFERRED_FEATURES,
    INPUT_KINDS,
    SHIPPED_FEATURES,
    TEMPLATES,
    build_prompt,
)

from tests.conftest import seed_config_rows, seed_feature_flags

_ENTRY_KEYS = {"id", "label", "help", "input", "max_input_tokens"}


@pytest.fixture()
def seeded(db):
    seed_config_rows(db.session)
    seed_feature_flags(db.session)
    return db


def test_every_shipped_feature_has_a_catalogue_entry():
    assert set(SHIPPED_FEATURES) <= set(CATALOGUE)
    for feature in SHIPPED_FEATURES:
        meta = CATALOGUE[feature]
        assert meta["label"].strip(), feature
        assert meta["help"].strip().endswith("."), feature
        assert meta["input"] in INPUT_KINDS, feature
        # Plain text only: the client puts these in a list a screen reader
        # reads, and a stray ampersand or bracket is read aloud.
        for text in (meta["label"], meta["help"]):
            assert "&" not in text and "<" not in text, feature


def test_deferred_features_are_not_described():
    for feature in DEFERRED_FEATURES:
        assert feature not in CATALOGUE


def test_config_lists_every_enabled_feature_in_order(client, seeded):
    body = client.get("/v1/config").get_json()
    features = body["features"]
    assert [entry["id"] for entry in features] == list(SHIPPED_FEATURES)
    limit = body["max_input_tokens"]
    for entry in features:
        assert set(entry) == _ENTRY_KEYS
        assert entry["label"] == CATALOGUE[entry["id"]]["label"]
        assert entry["help"] == CATALOGUE[entry["id"]]["help"]
        assert entry["input"] == CATALOGUE[entry["id"]]["input"]
        assert entry["max_input_tokens"] == limit


def test_a_switched_off_feature_leaves_the_catalogue(client, seeded):
    seeded.session.get(FeatureFlag, "shorten").enabled = False
    seeded.session.commit()
    body = client.get("/v1/config").get_json()
    assert "shorten" not in [entry["id"] for entry in body["features"]]
    assert body["feature_flags"]["shorten"] is False


def test_a_paused_service_offers_nothing(client, seeded):
    seeded.session.get(FeatureFlag, "hosted_ai").enabled = False
    seeded.session.commit()
    body = client.get("/v1/config").get_json()
    assert body["hosted_ai_enabled"] is False
    assert body["features"] == []


def test_older_clients_keys_are_unchanged(client, seeded):
    """Backward compatibility: everything an older client reads is still there,
    with the same types. ``features`` is additive and ignorable."""
    body = client.get("/v1/config").get_json()
    for key in (
        "max_input_tokens",
        "max_output_tokens",
        "max_chunks_per_request",
        "max_image_bytes",
        "max_image_edge_px",
    ):
        assert isinstance(body[key], int), key
    assert isinstance(body["hosted_ai_enabled"], bool)
    assert isinstance(body["feature_flags"], dict)
    assert isinstance(body["features"], list)


def test_config_with_no_rows_still_answers_with_a_catalogue(client):
    """No feature-flag rows at all (a fresh database): shipped features default
    on, so the catalogue is the full shipped list rather than an error."""
    features = client.get("/v1/config").get_json()["features"]
    assert [entry["id"] for entry in features] == list(SHIPPED_FEATURES)


def test_a_new_document_tool_needs_only_a_template(monkeypatch):
    """A catalogue feature whose input is "document" gets its excerpts through
    a {context} slot, with no change to build_prompt."""
    monkeypatch.setitem(
        TEMPLATES, "find_dates", "List every date in these excerpts.\n{context}\n\nFocus: {prompt}"
    )
    built = build_prompt("find_dates", "deadlines", ["Due 3 May.", "Paid 9 June."])
    assert "Due 3 May.\n\n---\n\nPaid 9 June." in built
    assert built.endswith("Focus: deadlines")


def test_document_qna_still_fills_its_excerpts():
    built = build_prompt("document_qna", "When?", ["It opens at nine."])
    assert "Excerpts:\nIt opens at nine." in built
    assert built.endswith("Question: When?")
