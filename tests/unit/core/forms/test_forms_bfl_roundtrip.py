"""BFL to model to BFL: exact, for every BAF example, with islands for the rest."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from quill.core.forms import schema_check
from quill.core.forms.bfl_read import read_bfl, read_form
from quill.core.forms.bfl_write import to_bfl, write_bfl
from quill.core.forms.errors import FormVersionError
from quill.core.forms.model import Choice, Field, Island, islands
from quill.core.forms.model_json import dumps, from_dict, loads, to_dict

sys.path.insert(0, str(Path(__file__).parent))
from forms_baf_sources import all_sources, baf_root  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"
VENDORED = sorted(p.stem for p in FIXTURES.glob("*.bfl"))
NO_BAF = "BAF is not on this machine; the vendored fixtures still ran."


def _check_round_trips(text: str) -> None:
    doc = read_bfl(text)
    # 1. read and write straight back: byte for byte.
    assert write_bfl(doc) == text
    data = to_dict(doc.form)
    # 2. the model fits the schema.
    assert schema_check.problems(data) == []
    # 3. model -> JSON -> model.
    assert from_dict(json.loads(json.dumps(data))) == doc.form
    # 4. model -> canonical BFL -> model, and canonical BFL is a fixed point.
    canonical = to_bfl(doc.form)
    again = read_bfl(canonical)
    assert to_dict(again.form) == data
    assert to_bfl(again.form) == canonical
    assert write_bfl(again) == canonical


@pytest.mark.parametrize("name", VENDORED)
def test_vendored_fixture_round_trips(name: str) -> None:
    _check_round_trips((FIXTURES / f"{name}.bfl").read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", VENDORED)
def test_vendored_fixture_reads_to_its_expected_model(name: str) -> None:
    text = (FIXTURES / f"{name}.bfl").read_text(encoding="utf-8")
    expected = json.loads((FIXTURES / f"{name}.model.json").read_text(encoding="utf-8"))
    assert to_dict(read_form(text)) == expected


@pytest.mark.skipif(baf_root() is None, reason=NO_BAF)
def test_every_baf_example_round_trips() -> None:
    root = baf_root()
    assert root is not None
    failures = []
    for source in all_sources(root):
        try:
            _check_round_trips(source.text)
        except AssertionError:
            failures.append(source.origin)
    assert failures == []


@pytest.mark.skipif(baf_root() is None, reason=NO_BAF)
def test_baf_guide_islands_are_only_the_documented_mistakes() -> None:
    root = baf_root()
    assert root is not None
    from forms_baf_sources import guide_sources

    found = {}
    for source in guide_sources(root):
        for island in islands(read_form(source.text)):
            if island.reason != "comment":
                found.setdefault(source.origin, []).append(island.text.split()[0])
    # The guide's "wrong" examples, its second and third alternative form
    # lines, and its "...fields..." placeholder; nothing it teaches as right.
    assert set(found) == {"guide:9", "guide:22", "guide:23", "guide:36"}


# -- islands -------------------------------------------------------------------------

ISLAND_CASES = [
    # BAF's exporter writes a dialect its own parser cannot read.
    ('name: text @required @placeholder(Jane) "Name"', "name: text"),
    ("[columns 1/2 | 1/2]", "[columns"),
    ("=== Page one ===", "==="),
    ("## A section @help(Some help)", "##"),
    ('hologram #h "A field type nobody has"\n  @required', "hologram"),
    ('text #a "A" stray words', "text #a"),
    ('if #a ??? "b"\n  text #b "B"', "if #a"),
    ('select "Department" + Sales', "select"),
    ('columns 2 {\n  text #x "not in a column"\n}', "columns 2"),
]


@pytest.mark.parametrize(("text", "start"), ISLAND_CASES)
def test_unknown_constructs_become_protected_islands(text: str, start: str) -> None:
    source = f'form "T"\n\ntext #before "Before"\n\n{text}\n\ntext #after "After"\n'
    doc = read_bfl(source)
    found = [i for i in islands(doc.form) if i.reason != "comment"]
    assert len(found) == 1
    assert found[0].text == text
    assert found[0].text.startswith(start)
    assert found[0].reason
    ids = [f.id for f in doc.form.pages[0].items if isinstance(f, Field)]
    assert ids == ["before", "after"]
    _check_round_trips(source)


def test_island_survives_json_and_editing_its_neighbours() -> None:
    source = 'form "T"\n\ntext #a "A"\n\n[columns 1/2 | 1/2]\n\ntext #b "B"\n'
    doc = read_bfl(source)
    first = doc.form.pages[0].items[0]
    assert isinstance(first, Field)
    first.label = "Changed"
    written = write_bfl(doc)
    assert "[columns 1/2 | 1/2]" in written
    assert 'text #a "Changed"' in written
    again = loads(dumps(read_form(written)))
    assert [i.text for i in islands(again)] == ["[columns 1/2 | 1/2]"]
    assert "[columns 1/2 | 1/2]" in to_bfl(again)


def test_comments_are_islands_and_kept() -> None:
    source = '// a note\n/* a\n block */\ntext #a "A"\n'
    form = read_form(source)
    assert [i.reason for i in islands(form)] == ["comment", "comment"]
    assert to_bfl(form).count("// a note") == 1


# -- editing only touches what changed ----------------------------------------------------


def test_editing_one_field_keeps_every_other_byte() -> None:
    source = (
        'form "Order"   @ajax\n\n'
        'text #name "Name" { @required @placeholder "Jane" }\n\n\n'
        'select #size "Size" [\n  + Small:10\n  + Large:12\n]\n'
        'number #qty "Quantity" begin\n  @min 1\nend\n'
    )
    doc = read_bfl(source)
    size = doc.form.pages[0].items[1]
    assert isinstance(size, Field)
    size.choices.append(Choice("huge", "Huge", "15"))
    written = write_bfl(doc)
    assert written.startswith(
        'form "Order"   @ajax\n\ntext #name "Name" { @required @placeholder "Jane" }\n\n\n'
    )
    assert written.endswith('number #qty "Quantity" begin\n  @min 1\nend\n')
    assert "+ Huge:15" in written
    assert to_dict(read_form(written)) == to_dict(doc.form)


def test_removing_and_adding_fields() -> None:
    doc = read_bfl('text #a "A"\n\ntext #b "B"\n\ntext #c "C"\n')
    items = doc.form.pages[0].items
    del items[1]
    items.append(Field(id="d", type="email", label="D", required=True))
    written = write_bfl(doc)
    assert written == 'text #a "A"\n\ntext #c "C"\n\nemail #d "D"\n  @required\n'


def test_changing_a_condition_rewrites_its_block() -> None:
    doc = read_bfl(
        'radio #t "Type"\n  + Business\n  + Person\n\nif #t is "business" {\n  text #co "Company"\n}\n'  # noqa: E501
    )
    field = doc.form.pages[0].items[1]
    assert isinstance(field, Field)
    assert field.visible_when == '#t is "business"'
    field.visible_when = '#t is one of ("business", "charity")'
    written = write_bfl(doc)
    assert 'if #t is one of ("business", "charity")\n  text #co "Company"' in written
    assert written.startswith('radio #t "Type"\n  + Business\n  + Person\n\n')


# -- the extended spellings ------------------------------------------------------------------


EXTENDED = """// bfl-version 1
form "Quiz" @description "Three questions"
  @submit_label "Finish"
  @translate fr title "Questionnaire"

page "Start"
  @translate fr title "Début"

section "About you"
  @when #age >= 18

number #age "Age"
  @translate fr label "Âge"

radio #capital "Capital of France"
  + paris|Paris
  + lyon|Lyon
  @score #capital is "paris"
  @choice_score paris 2
  @translate fr choice paris "Paris (FR)"

text #total "Total"
  @calculate #age * 2 + 1
  @smart_default today + 7

toggle #news "Newsletter"

repeater #kids "Children" {
  @max_rows 4
  text #kid_name "Name"
    @required
}

if #age is within 30 days of today or not (#news is filled)
  nps #recommend "Would you recommend us?"

outcome "Well done"
  @when quiz.score >= 3
"""


def test_extended_spellings_read_and_round_trip() -> None:
    form = read_form(EXTENDED)
    assert form.version == 1
    assert form.settings.submit_label == "Finish"
    assert form.translations["fr"]["title"] == "Questionnaire"
    assert form.translations["fr"]["page.page_1.title"] == "Début"
    assert form.translations["fr"]["field.capital.choice.paris"] == "Paris (FR)"
    page = form.pages[0]
    assert page.title == "Start"
    section = page.items[0]
    assert section.visible_when == "#age >= 18"  # type: ignore[union-attr]
    fields = {f.id: f for f in section.items if isinstance(f, Field)}  # type: ignore[union-attr]
    assert fields["capital"].score == '#capital is "paris"'
    assert fields["capital"].choices[0].score == 2.0
    assert fields["total"].calculate == "#age * 2 + 1"
    assert fields["total"].default_expr == "today + 7"
    assert fields["news"].type == "toggle"
    assert [f.id for f in fields["kids"].fields] == ["kid_name"]
    assert (
        fields["recommend"].visible_when == "#age is within 30 days of today or not #news is filled"
    )
    assert form.outcomes[0].message == "Well done"
    _check_round_trips(EXTENDED)


def test_a_newer_bfl_version_is_refused() -> None:
    with pytest.raises(FormVersionError):
        read_bfl('// bfl-version 99\ntext #a "A"\n')


def test_to_bfl_writes_choices_before_modifiers_for_baf() -> None:
    form = read_form('select #d "D" {\n  @required\n  + A\n  + x|B\n}\n')
    text = to_bfl(form)
    assert text.index("+ A") < text.index("@required")
    assert "+ x|B" in text


def test_islands_are_never_parsed_inside_strings() -> None:
    form = read_form('text #a "has // no comment and { no block"\n')
    assert islands(form) == []
    assert isinstance(form.pages[0].items[0], Field)
    assert not isinstance(form.pages[0].items[0], Island)
