"""The stored model: one schema with BAF, versions, migrations, and the rules beyond the schema."""

from __future__ import annotations

import json
from typing import Any

import pytest

from quill.core.forms import model as M
from quill.core.forms import model_json, schema_check
from quill.core.forms.errors import FormModelError, FormVersionError
from quill.core.forms.model_json import dumps, loads


def _form() -> M.Model:
    return {
        "version": 1,
        "title": "Join",
        "pages": [
            {
                "id": "page_1",
                "items": [
                    {"id": "type", "type": "radio", "label": "Joining as",
                     "choices": [{"value": "person", "label": "An individual"}, {"value": "business", "label": "A business"}]},  # noqa: E501
                    {"id": "company", "type": "text", "label": "Company", "when": '#type is "business"'},  # noqa: E501
                ],
            }
        ],
    }  # fmt: skip


def test_round_trip_and_valid() -> None:
    form = _form()
    assert M.same(loads(dumps(form)), form)
    assert M.validate(form) == []
    assert dumps(form).endswith("\n")


def test_the_schema_is_qafs() -> None:
    schema = schema_check.load_schema()
    assert schema["$id"].startswith("https://bits-acb.org/qaf/schema/")
    assert set(schema["$defs"]["field_type"]["enum"]) == set(M.FIELD_TYPES)


@pytest.mark.parametrize(
    ("change", "path"),
    [
        (lambda d: d.pop("version"), "/"),
        (lambda d: d.__setitem__("colour", "red"), "/colour"),
        (
            lambda d: d["pages"][0]["items"][1].__setitem__("when", "#nobody is 1"),
            "/pages/0/items/1/when",
        ),
        (lambda d: d["pages"][0]["items"][1].__setitem__("id", "type"), "/pages/0/items/1/id"),
        (
            lambda d: d["pages"][0]["items"][0]["choices"].append({
                "value": "person",
                "label": "Again",
            }),
            "/pages/0/items/0/choices/2/value",
        ),
    ],
)
def test_problems_are_reported_at_their_path(change: Any, path: str) -> None:
    form = _form()
    change(form)
    found = M.validate(form)
    assert any(p["path"] == path for p in found), found
    with pytest.raises(FormModelError):
        schema_check.check(form)


def test_same_keeps_true_apart_from_one() -> None:
    assert M.same({"a": 1, "b": [2.0]}, {"b": [2], "a": 1})
    assert not M.same({"a": True}, {"a": 1})


def test_newer_versions_are_refused() -> None:
    with pytest.raises(FormVersionError, match="Update QUILL"):
        loads(json.dumps({**_form(), "version": 2}))


def test_migrations_run_one_step_at_a_time(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(model_json, "MIGRATIONS", {})
    model_json.migration(1)(lambda d: {**d, "version": 2, "title": d["title"].upper()})
    model_json.migration(2)(lambda d: {**d, "version": 3})
    assert model_json.upgrade({"version": 1, "title": "old"}, target=3) == {
        "version": 3,
        "title": "OLD",
    }
    monkeypatch.setattr(model_json, "MIGRATIONS", {})
    with pytest.raises(FormVersionError, match="no way"):
        model_json.upgrade({"version": 1}, target=2)


def test_bad_json_is_refused() -> None:
    with pytest.raises(FormModelError, match="not valid JSON"):
        loads("{")
    with pytest.raises(FormModelError, match="object"):
        loads("[]")


def test_slug_matches_baf() -> None:
    assert M.slug("Credit Card!") == "credit-card"
    assert M.slug("  T-Shirt (large) ") == "t-shirt-large"
