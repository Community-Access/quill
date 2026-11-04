"""Translations side by side, and the spoken summaries the outline reads."""

from __future__ import annotations

from quill.core.forms import model as M
from quill.core.forms.bfl_document import read_bfl
from quill.core.forms.bfl_read import read
from quill.core.forms.summary import item_summary, outline
from quill.core.forms.translate import (
    languages,
    localize,
    lookup,
    missing,
    set_translation,
    translatable_strings,
)

FORM = """bfl 1
form "Contact"
  @language "en"
  @submit_label "Send"

section #about "About you"
  text #name "Your name"
    @required
    @autocomplete "name"
  email #email "Email address"
    @required
    @description "We only use this to reply."
    @autocomplete "email"
  radio #how "How should we reply?"
    + email|By email
    + phone|By phone
  phone #phone "Phone number"
    @mask "(999) 999-9999"
    @when #how is "phone"
  select #country "Country"
    @library "countries"

translation "fr"
  @title "Contact"
  field #name
    @label "Votre nom"
  field #how
    + email|Par courriel
"""


def test_the_form_reads_cleanly() -> None:
    result = read(FORM)
    assert result.errors == [] and result.warnings == []
    assert M.validate(result.model) == []


def test_translations() -> None:
    model = read(FORM).model
    assert languages(model) == ["en", "fr"]
    places = [p for p, _ in translatable_strings(model)]
    assert ("fields", "how", "choices/phone") in places
    assert ("fields", "email", "label") in missing(model, "fr")
    fr = localize(model, "fr")
    name = M.find(fr, "name")
    how = M.find(fr, "how")
    assert name is not None and name["label"] == "Votre nom"
    assert how is not None and [c["label"] for c in how["choices"]] == ["Par courriel", "By phone"]
    assert M.find(model, "name")["label"] == "Your name"  # type: ignore[index]
    set_translation(model, "es", ("fields", "name", "label"), "Su nombre")
    assert lookup(model, "es", ("fields", "name", "label")) == "Su nombre"
    assert M.validate(model) == []


def test_summaries() -> None:
    model = read(FORM).model
    assert (
        item_summary(M.find(model, "name"), model)
        == "Your name, text field, required, with an autofill hint"
    )  # type: ignore[arg-type]
    assert (
        item_summary(M.find(model, "email"), model, page_number=1)  # type: ignore[arg-type]
        == "Email address, email field, required, with an autofill hint, with help text, page 1"
    )
    assert (
        item_summary(M.find(model, "phone"), model)  # type: ignore[arg-type]
        == "Phone number, phone number field, with a format rule, shown when How should we reply? is By phone"  # noqa: E501
    )
    assert (
        item_summary(M.find(model, "country"), model)
        == "Country, drop-down list, choices from the Countries list"
    )  # type: ignore[arg-type]


def test_outline_with_islands() -> None:
    doc = read_bfl('text #a "A"\n\n=== Old export line ===\n')
    rows = [r.text for r in outline(doc.model, doc.islands)]
    assert rows[0] == "Page 1, 1 question"
    assert rows[1] == "A, text field, page 1"
    assert rows[-1] == "Kept as written, not read by BAF: === Old export line ==="
