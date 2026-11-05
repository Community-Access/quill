"""Follow-ups from the Forms commands helper: first-place inserts, outline rows, choices."""

from __future__ import annotations

import pytest

from quill.core.forms import libraries
from quill.core.forms import model as M
from quill.core.forms.bfl_document import read_bfl, write_bfl
from quill.core.forms.bfl_read import read
from quill.core.forms.summary import outline_rows
from quill.core.forms.translate import localize

NEW = {"id": "z", "type": "text", "label": "Z"}


@pytest.mark.parametrize(
    ("source", "expected", "how"),
    [
        ('text #a "A"\n\ntext #b "B"\n', 'text #z "Z"\n\ntext #a "A"\n\ntext #b "B"\n', "spliced"),
        ('// note\ntext #a "A"\n', '// note\ntext #z "Z"\n\ntext #a "A"\n', "spliced"),
        ('page "P"\n  text #a "A"\n', 'page "P"\n  text #z "Z"\n  text #a "A"\n', "spliced"),
        ("", 'bfl 1\nform ""\n\ntext #z "Z"\n', "canonical"),
    ],
)
def test_a_question_inserted_first_on_a_page_is_written(
    source: str, expected: str, how: str
) -> None:
    doc = read_bfl(source)
    doc.model["pages"][0]["items"].insert(0, dict(NEW))
    written = write_bfl(doc)
    assert written == expected
    assert doc.last_write == how
    assert M.same(read(written).model, doc.model)


def test_a_question_inserted_first_in_a_flat_section() -> None:
    doc = read_bfl('section "S"\ntext #a "A"\n')
    doc.model["pages"][0]["items"][0]["items"].insert(0, dict(NEW))
    written = write_bfl(doc)
    assert M.same(read(written).model, doc.model)
    assert written.startswith('section "S"\n')


def test_a_splice_that_would_lose_an_edit_falls_back_to_canonical(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from quill.core.forms import bfl_document

    doc = read_bfl('text #a "A"\n')
    doc.model["pages"][0]["items"][0]["label"] = "B"
    monkeypatch.setattr(bfl_document._Splice, "run", lambda self: self.src)
    written = write_bfl(doc)
    assert doc.last_write == "canonical"
    assert M.same(read(written).model, doc.model)


FORM = """bfl 1
form "Contact"

page #about "About you"
  section #who "Who"
    text #name "Name"
      @required
  columns 2
    column
      select #country "Country"
        @library "countries"
    column
      rating #stars "Stars"

library #sizes
  + s|Small
  + l|Large

page #more "More"
  select #size "Size"
    @library "sizes"
  radio #how "How"
    + email|By email
    + phone|By phone

translation "fr"
  @title "Contactez-nous"
  page #about
    @title "Vous"
  field #how
    @label "Comment"
    + email|Par courriel
"""


def test_outline_rows_match_the_outline_window() -> None:
    model = read(FORM).model
    rows = outline_rows(model)
    assert rows[0] == ("Page 1, About you, 3 questions", None)
    assert rows[1] == ("  Section, Who, 1 question", "who")
    assert rows[2] == ("    Name, text field, required, page 1", "name")
    assert rows[3][1] == "field_3" and rows[3][0].startswith("  2 columns side by side")
    assert rows[4] == (
        "    Country, drop-down list, choices from the Countries list, page 1",
        "country",
    )
    assert rows[6][1] is None and rows[6][0].startswith("Page 2, More")
    assert (
        "  Size, drop-down list, choices from the form's own sizes list, page 2",
        "size",
    ) in rows


def test_outline_rows_list_islands_last() -> None:
    doc = read_bfl('text #a "A"\n\n=== Old line ===\n')
    rows = outline_rows(doc.model, doc.islands)
    assert rows[-1] == ("Kept as written, not read by QAF: === Old line ===", None)


def test_choices_for_every_source() -> None:
    model = read(FORM).model
    assert libraries.choices_for(M.find(model, "how"), model) == [
        ("email", "By email"),
        ("phone", "By phone"),
    ]  # type: ignore[arg-type]
    assert libraries.choices_for(M.find(model, "size"), model) == [("s", "Small"), ("l", "Large")]  # type: ignore[arg-type]
    country = libraries.choices_for(M.find(model, "country"), model)  # type: ignore[arg-type]
    assert ("US", "United States") in country
    assert libraries.choices_for(M.find(model, "stars"), model)[0] == ("1", "1 out of 5")  # type: ignore[arg-type]
    assert libraries.choices_for({"type": "nps"}) == [(str(n), str(n)) for n in range(11)]
    assert libraries.choices_for({"type": "select", "choice_library": "nope"}) == []
    state = {"type": "select", "cascade": {"from": "country", "library": "states"}}
    assert ("ON", "Ontario") in libraries.choices_for(state, model, "CA")


def test_library_choices_read_as_dicts_and_as_attributes() -> None:
    first = libraries.choices("months")[0]
    assert first["value"] == first.value and first["label"] == first.label
    assert M.same(dict(first), {"value": first.value, "label": first.label})


def test_localize_applies_baf_translations() -> None:
    model = read(FORM).model
    fr = localize(model, "fr")
    assert fr["title"] == "Contactez-nous"
    assert fr["pages"][0]["title"] == "Vous"
    how = M.find(fr, "how")
    assert how is not None and how["label"] == "Comment"
    assert [c["label"] for c in how["choices"]] == ["Par courriel", "By phone"]
    assert M.find(model, "how")["label"] == "How"  # type: ignore[index]
    assert M.same(localize(model, "de"), model)
