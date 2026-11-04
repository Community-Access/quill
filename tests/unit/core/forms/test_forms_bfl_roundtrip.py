"""BFL documents: every untouched byte written back, edits spliced in, islands kept."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from quill.core.forms import model as M
from quill.core.forms.bfl_document import (
    model_with_islands,
    read_bfl,
    to_bfl_with_islands,
    write_bfl,
)
from quill.core.forms.bfl_read import read
from quill.core.forms.bfl_write import to_bfl

sys.path.insert(0, str(Path(__file__).parent))
from forms_baf_sources import all_sources, baf_root  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"
EXAMPLES = sorted(p.stem for p in FIXTURES.glob("*.bfl"))


def _round_trips(text: str) -> None:
    doc = read_bfl(text)
    assert write_bfl(doc) == text
    assert doc.last_write == "unchanged"
    canonical = to_bfl(doc.model)
    again = read(canonical)
    assert M.same(again.model, doc.model)
    assert to_bfl(again.model) == canonical


@pytest.mark.parametrize("name", EXAMPLES)
def test_guide_examples_read_to_their_models_and_round_trip(name: str) -> None:
    text = (FIXTURES / f"{name}.bfl").read_text(encoding="utf-8")
    expected = json.loads((FIXTURES / f"{name}.model.json").read_text(encoding="utf-8"))
    assert M.same(read(text).model, expected)
    _round_trips(text)


@pytest.mark.skipif(
    baf_root() is None, reason="BAF is not on this machine; the vendored examples still ran."
)
def test_every_baf_guide_and_test_example_round_trips() -> None:
    root = baf_root()
    assert root is not None
    failures = []
    for source in all_sources(root):
        try:
            _round_trips(source.text)
        except AssertionError:
            failures.append(source.origin)
    assert failures == []


def test_crlf_and_byte_order_mark_survive() -> None:
    text = '﻿bfl 1\r\nform "T"\r\n\r\n// note\r\ntext #a "A"\r\n'
    doc = read_bfl(text)
    assert write_bfl(doc) == text
    doc.model["pages"][0]["items"][0]["label"] = "B"
    assert write_bfl(doc) == '﻿bfl 1\r\nform "T"\r\n\r\n// note\r\ntext #a "B"\r\n'


SOURCE = """bfl 1
form "Order"   @ajax

// About the person
text #name "Name" { @required @placeholder "Jane" }

  /* odd spacing kept */
select #size "Size" [
  + Small:10
  + Large:12
]

number #qty "Quantity" begin
  @min 1
end
"""


def test_editing_one_field_keeps_every_other_byte() -> None:
    doc = read_bfl(SOURCE)
    size = M.find(doc.model, "size")
    assert size is not None
    size["choices"].append({"value": "huge", "label": "Huge", "price": 15})
    written = write_bfl(doc)
    assert doc.last_write == "spliced"
    head, tail = SOURCE.split('select #size "Size" [', 1)
    assert written.startswith(head)
    assert written.endswith('number #qty "Quantity" begin\n  @min 1\nend\n')
    assert "  + Huge:15" in written  # BAF's short spelling for a price alone
    assert M.same(read(written).model, doc.model)


def test_removing_and_adding_fields() -> None:
    doc = read_bfl('text #a "A"\n\ntext #b "B"\n\ntext #c "C"\n')
    items = doc.model["pages"][0]["items"]
    del items[1]
    items.append({"id": "d", "type": "email", "label": "D", "required": True})
    written = write_bfl(doc)
    assert written == 'text #a "A"\n\ntext #c "C"\n\nemail #d "D"\n  @required\n'
    assert M.same(read(written).model, doc.model)


def test_changing_the_form_line_and_a_page() -> None:
    text = 'form "Old"\n\npage "One"\ntext #a "A"\n\npage "Two"\ntext #b "B"\n'
    doc = read_bfl(text)
    doc.model["title"] = "New"
    doc.model["pages"][1]["title"] = "Second"
    written = write_bfl(doc)
    assert written == 'form "New"\n\npage "One"\ntext #a "A"\n\npage "Second"\ntext #b "B"\n'
    assert M.same(read(written).model, doc.model)


def test_an_if_block_item_that_changes_becomes_a_when() -> None:
    doc = read_bfl(
        'radio #t "Type"\n  + Business\n  + Person\n\nif #t is "business" {\n  text #co "Company"\n}\n'  # noqa: E501
    )
    company = M.find(doc.model, "co")
    assert company is not None and company["when"] == '#t is "business"'
    company["label"] = "Company name"
    written = write_bfl(doc)
    assert written.startswith('radio #t "Type"\n  + Business\n  + Person\n\n')
    assert 'text #co "Company name"\n  @when #t is "business"' in written
    assert M.same(read(written).model, doc.model)


def test_flat_sections_keep_their_children() -> None:
    doc = read_bfl('section "About"\ntext #a "A"\ntext #b "B"\n')
    section = doc.model["pages"][0]["items"][0]
    assert [i["id"] for i in section["items"]] == ["a", "b"]
    section["label"] = "About you"
    written = write_bfl(doc)
    assert written == 'section #field_1 "About you"\ntext #a "A"\ntext #b "B"\n'
    assert M.same(read(written).model, doc.model)


def test_moves_fall_back_to_canonical() -> None:
    doc = read_bfl('// note\ntext #a "A"\ntext #b "B"\n')
    items = doc.model["pages"][0]["items"]
    items.reverse()
    written = write_bfl(doc)
    assert doc.last_write == "canonical"
    assert written == to_bfl(doc.model)


ISLANDS = [
    "=== Contact details ===",
    'hologram #h "A field type nobody has"',
    "- Option one",
    "* a starred note",
]


@pytest.mark.parametrize("line", ISLANDS)
def test_lines_baf_skips_are_islands_and_survive(line: str) -> None:
    text = f'form "T"\n\ntext #a "A"\n\n{line}\n\ntext #b "B"\n'
    doc = read_bfl(text)
    assert doc.islands == [line]
    assert doc.warnings
    assert [i["id"] for i in doc.model["pages"][0]["items"]] == ["a", "b"]
    assert write_bfl(doc) == text
    M.find(doc.model, "a")["label"] = "Changed"  # type: ignore[index]
    written = write_bfl(doc)
    assert line in written and 'text #a "Changed"' in written
    kept = model_with_islands(doc)
    assert kept["extensions"]["quill"]["islands"] == [line]
    again = read_bfl(to_bfl_with_islands(kept))
    assert again.islands == [line]
    assert M.same(again.model, doc.model)


def test_islands_are_not_in_bafs_model() -> None:
    doc = read_bfl('hologram\ntext #a "A"\n')
    assert "extensions" not in doc.model
    assert M.validate(doc.model) == []


def test_a_newer_bfl_version_is_an_error() -> None:
    result = read('bfl 2\nform "Later"\n')
    assert result.errors and result.errors[0]["line"] == 1
