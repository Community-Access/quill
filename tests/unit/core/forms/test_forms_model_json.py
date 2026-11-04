"""The form model's JSON: compact, versioned, upgradable, and checked by its schema."""

from __future__ import annotations

import json
from typing import Any

import pytest

from quill.core.forms import model_json, schema_check
from quill.core.forms.errors import FormModelError, FormVersionError
from quill.core.forms.model import (
    MODEL_VERSION,
    Cascade,
    Choice,
    Columns,
    Field,
    Form,
    Island,
    Outcome,
    Page,
    Section,
    all_fields,
    find_field,
)
from quill.core.forms.model_json import dumps, from_dict, loads, to_dict


def _sample() -> Form:
    form = Form(title="Fair", description="Spring fair", language="en-GB")
    form.settings.submit_label = "Sign me up"
    form.settings.honeypot = True
    form.settings.extra["notifications"] = [{"to": "a@example.org"}]
    form.pages = [
        Page(
            id="page_1",
            title="You",
            items=[
                Field(
                    id="name",
                    type="text",
                    label="Name",
                    required=True,
                    settings={"autocomplete": "name"},
                ),
                Section(
                    id="s1",
                    title="Contact",
                    visible_when="#name is filled",
                    items=[
                        Field(
                            id="how",
                            type="radio",
                            label="How",
                            choices=[Choice("email", "Email", score=1.0), Choice("phone", "Phone")],
                        ),
                        Columns(
                            id="c1",
                            count=2,
                            columns=[[Field(id="a", type="text")], [Island("x y z", "test")]],
                        ),
                    ],
                ),
            ],
        ),
        Page(
            id="page_2",
            visible_when='#how is "email"',
            items=[
                Field(id="country", type="select", choice_library="countries"),
                Field(
                    id="state",
                    type="select",
                    cascade=Cascade("country", "states", "Pick a country"),
                ),
                Field(
                    id="kids", type="repeater", fields=[Field(id="kid", type="text", label="Kid")]
                ),
                Field(id="total", type="calculation", calculate="#a * 2", default_expr="today + 1"),
            ],
        ),
    ]
    form.translations = {"fr": {"title": "Fête", "field.name.label": "Nom"}}
    form.outcomes = [Outcome("quiz.score >= 1", "Thanks")]
    return form


def test_round_trip_through_json() -> None:
    form = _sample()
    assert loads(dumps(form)) == form
    assert from_dict(json.loads(json.dumps(to_dict(form)))) == form


def test_written_json_leaves_out_defaults() -> None:
    data = to_dict(Form(pages=[Page(id="page_1", items=[Field(id="a", type="text")])]))
    assert data == {
        "model": "baf-form",
        "version": MODEL_VERSION,
        "language": "en",
        "pages": [{"id": "page_1", "items": [{"kind": "field", "id": "a", "type": "text"}]}],
    }


def test_sample_fits_the_schema() -> None:
    assert schema_check.problems(to_dict(_sample())) == []


def test_helpers_find_fields_everywhere() -> None:
    form = _sample()
    assert [f.id for f in all_fields(form)] == [
        "name",
        "how",
        "a",
        "country",
        "state",
        "kids",
        "kid",
        "total",
    ]
    found = find_field(form, "kid")
    assert found is not None and found.label == "Kid"
    assert find_field(form, "nope") is None


@pytest.mark.parametrize(
    ("change", "fragment"),
    [
        (lambda d: d.pop("pages"), "missing 'pages'"),
        (lambda d: d.__setitem__("colour", "red"), "'colour'"),
        (lambda d: d["pages"][0]["items"][0].__setitem__("type", "hologram"), "allowed values"),
        (lambda d: d["pages"][0]["items"][0].__setitem__("visible_when", "#a is"), "does not read"),
        (lambda d: d["pages"][0]["items"][0].__setitem__("id", "has space"), "expected form"),
        (lambda d: d["pages"][0]["items"][0].__setitem__("required", "yes"), "boolean"),
        (lambda d: d.__setitem__("translations", {"fr": {"field.a.colour": "x"}}), "expected form"),
        (lambda d: d["pages"][0]["items"].append({"kind": "widget"}), "kind"),
    ],
)
def test_schema_finds_problems(change: Any, fragment: str) -> None:
    data = to_dict(Form(pages=[Page(id="page_1", items=[Field(id="a", type="text")])]))
    change(data)
    found = schema_check.problems(data)
    assert any(fragment in p for p in found), found
    with pytest.raises(FormModelError) as caught:
        schema_check.check(data)
    assert caught.value.problems == found


def test_schema_file_is_a_2020_12_schema() -> None:
    schema = schema_check.load_schema()
    assert schema["$schema"].endswith("2020-12/schema")
    assert schema["$id"] == "urn:baf:form-model:1"
    assert schema["properties"]["model"]["const"] == model_json.MODEL_NAME
    field_types = schema["$defs"]["field"]["properties"]["type"]["enum"]
    from quill.core.forms.model import FIELD_TYPES

    assert sorted(field_types) == sorted(FIELD_TYPES)


def test_newer_versions_are_refused_in_a_sentence() -> None:
    data = to_dict(Form())
    data["version"] = MODEL_VERSION + 1
    with pytest.raises(FormVersionError, match="Update QUILL"):
        from_dict(data)


def test_migration_hook_upgrades_one_step_at_a_time(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []

    def one_to_two(data: dict[str, Any]) -> dict[str, Any]:
        calls.append(1)
        return {**data, "version": 2, "title": data["title"].upper()}

    def two_to_three(data: dict[str, Any]) -> dict[str, Any]:
        calls.append(2)
        return {**data, "version": 3}

    monkeypatch.setattr(model_json, "MIGRATIONS", {})
    model_json.migration(1)(one_to_two)
    model_json.migration(2)(two_to_three)
    out = model_json.upgrade({"version": 1, "title": "old"}, target=3)
    assert out == {"version": 3, "title": "OLD"}
    assert calls == [1, 2]


def test_missing_or_broken_migration_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(model_json, "MIGRATIONS", {})
    with pytest.raises(FormVersionError, match="no way"):
        model_json.upgrade({"version": 1}, target=2)
    model_json.migration(1)(lambda d: d)
    with pytest.raises(FormVersionError, match="did not reach"):
        model_json.upgrade({"version": 1}, target=2)


def test_bad_json_and_wrong_models_are_refused() -> None:
    with pytest.raises(FormModelError, match="not valid JSON"):
        loads("{")
    with pytest.raises(FormModelError, match="object"):
        loads("[]")
    with pytest.raises(FormModelError, match="not a form model"):
        from_dict({"model": "something-else"})
    with pytest.raises(FormModelError, match="kind"):
        from_dict({"pages": [{"id": "p", "items": [{"kind": "widget"}]}]})


def test_error_codes() -> None:
    assert FormModelError.code.startswith("QUILL-FORMS-")
    assert FormVersionError.code == "QUILL-FORMS-MODEL-VERSION"
