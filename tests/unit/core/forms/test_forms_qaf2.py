"""BAF's second round: plain-digit numbers, PHP's JSON floats, and GET forms/{id}'s model."""

from __future__ import annotations

import pytest

from quill.core.forms import expr as E
from quill.core.forms import model as M
from quill.core.forms.bfl_read import read
from quill.core.forms.bfl_write import choice_line, to_bfl
from quill.core.forms.qaf_site import form_from_payload


@pytest.mark.parametrize(
    ("value", "canonical", "spoken", "php_json"),
    [
        (1e17, "100000000000000000.0", "100000000000000000", "1.0e+17"),
        (1e-5, "0.00001", "0.00001", "1.0e-5"),
        (2.5, "2.5", "2.5", "2.5"),
        (3.0, "3.0", "3", "3"),
        (-0.0, "-0.0", "-0", "-0"),
        (12345678901234567.0, "12345678901234568.0", "12345678901234568", "12345678901234568"),
    ],
)
def test_number_forms(value: float, canonical: str, spoken: str, php_json: str) -> None:
    assert E.literal_text(value) == canonical
    assert E.number_text(value, False) == spoken
    assert E.php_json_float(value) == php_json
    assert E.canonical(canonical) == canonical  # canonical text always reads back


def test_json_values_in_bfl_are_written_as_baf_writes_them() -> None:
    assert M.encode({"a": [1.0, 1e17, "é/x", [], {}]}) == '{"a":[1.0,1.0e+17,"é/x",[],{}]}'
    assert M.encode({"a": [1]}, pretty=True) == '{\n    "a": [\n        1\n    ]\n}'


def test_short_priced_choices() -> None:
    assert choice_line({"value": "large", "label": "Large", "price": 20.0}) == "+ Large:20.0"
    assert choice_line({"value": "credit", "label": "Credit", "price": -5}) == "+ Credit:-5"
    assert choice_line({"value": "l", "label": "Large", "price": 20}) == '+ "l" | "Large" @price 20'
    assert choice_line({"value": "large", "label": "Large", "price": 2, "points": 1}).startswith(
        '+ "large"'
    )


def test_library_keyword_after_the_label() -> None:
    model = read('select "Country" countries @required\nradio #m "Month" months\n').model
    country, month = model["pages"][0]["items"]
    assert country["choice_library"] == "countries" and country["required"] is True
    assert month["choice_library"] == "months"
    assert '@library "countries"' in to_bfl(model)


def test_get_form_reads_the_model_beside_config() -> None:
    model = M.create("Join")
    form = form_from_payload({"id": 4, "title": "Join", "config": {"fields": []}, "model": model})
    assert form.model() == model
    stored = M.create("Stored")
    form = form_from_payload({"id": 4, "config": {"form_model": stored}, "model": model})
    assert form.model() == stored  # config's own form_model wins
    assert form_from_payload({"id": 1, "config": None}).model() is None
