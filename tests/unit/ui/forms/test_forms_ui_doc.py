"""The form-document helpers under every Forms window (quill/ui/forms_doc.py)."""

from __future__ import annotations

import pytest

from quill.core.forms import model as M
from quill.ui import forms_doc as fd
from quill.ui import forms_field_types as ft
from quill.ui.forms_templates import TEMPLATES


def _form(*pages: list[dict]) -> dict:
    return {
        "version": 1,
        "title": "T",
        "pages": [{"id": f"p{n}", "items": items} for n, items in enumerate(pages, 1)],
    }


def test_new_ids_never_repeat() -> None:
    model = _form([{"id": "email", "type": "email"}])
    assert fd.new_id(model, "Email") == "email_2"
    assert fd.new_id(model, "2 things") == "q_2_things"
    assert fd.new_id(model, "  ") == "question"


def test_moving_past_a_page_edge_goes_to_the_next_page() -> None:
    model = _form([{"id": "a", "type": "text"}], [{"id": "b", "type": "text"}])
    assert fd.move(model, "a", 1) == "Moved to page 2."
    assert [i["id"] for i in model["pages"][1]["items"]] == ["a", "b"]
    assert fd.move(model, "a", -1) == "Moved to page 1."
    with pytest.raises(fd.Refused, match="already first"):
        fd.move(model, "a", -1)


def test_removing_a_question_drops_it_from_rules() -> None:
    model = _form([{"id": "a", "type": "text"}, {"id": "b", "type": "text"}])
    model["rules"] = [
        {"action": "hide", "targets": ["a"], "when": "#b is empty"},
        {"action": "hide", "targets": ["a", "b"], "when": "#b is empty"},
    ]
    fd.remove(model, "a")
    assert model["rules"] == [{"action": "hide", "targets": ["b"], "when": "#b is empty"}]


def test_change_id_rewrites_references_and_translations() -> None:
    model = _form([
        {"id": "a", "type": "text"},
        {"id": "b", "type": "text", "when": "#a is filled"},
    ])
    model["translations"] = {"fr": {"fields": {"a": {"label": "Un"}}}}
    fd.change_id(model, "a", "first")
    assert M.find(model, "b")["when"] == "#first is filled"
    assert model["translations"]["fr"]["fields"] == {"first": {"label": "Un"}}
    with pytest.raises(fd.Refused):
        fd.change_id(model, "first", "9lives")


def test_change_type_gives_a_choice_question_a_choice() -> None:
    model = _form([{"id": "a", "type": "text"}])
    fd.change_type(model, "a", "radio")
    assert M.find(model, "a")["choices"] == [{"value": "choice-1", "label": "Choice 1"}]
    fd.change_type(model, "a", "text")
    assert "choices" not in M.find(model, "a")


def test_a_splice_that_would_lose_a_question_is_written_whole() -> None:
    """The guard in forms_doc.write: a new first question must never vanish."""
    text = 'bfl 1\nform "T"\n\n// keep me\ntext #b "B"\n'
    doc = fd.read(text)
    doc.model["pages"][0]["items"].insert(0, {"id": "a", "type": "text", "label": "A"})
    out = fd.write(doc)
    assert [f["id"] for f in fd.fields(fd.read(out).model)] == ["a", "b"]


def test_item_offset_finds_the_line_that_names_it() -> None:
    text = 'bfl 1\nform "T"\n\ntext #a "A"\nemail #b "B"\n'
    doc = fd.read(text)
    assert text[fd.item_offset(doc, "b") :].startswith("email #b")
    assert fd.item_offset(doc, "nothing") is None


@pytest.mark.parametrize("template", TEMPLATES, ids=lambda t: t.id)
def test_every_template_is_a_valid_form_that_reads_back(template) -> None:
    model = template.model("Try")
    assert M.validate(model) == []
    assert M.same(fd.read(fd.canonical(model)).model, model)


def test_insert_field_offers_every_type_but_payment_and_site_parts() -> None:
    kinds = ft.kinds()
    assert kinds[:2] == [ft.SECTION, ft.PAGE_BREAK]
    assert set(kinds[2:]) == set(M.FIELD_TYPES) - ft.LEFT_OUT
    assert "payment" in kinds  # opens the guided payment field dialog
    assert all(ft.describe(k).endswith(".") for k in kinds)
