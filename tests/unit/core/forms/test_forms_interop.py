"""Imports and exports that run on the computer: SurveyJS, XLSForm and HTML."""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.forms import model as M
from quill.core.forms.bfl_read import read
from quill.core.forms.errors import FormImportError
from quill.core.forms.interop_html import export_html, import_html
from quill.core.forms.interop_surveyjs import export_surveyjs, import_surveyjs
from quill.core.forms.interop_xlsform import (
    export_rows,
    export_xlsform,
    import_rows,
    import_xlsform,
)

SURVEY = {
    "title": {"default": "Feedback", "fr": "Avis"},
    "locale": "en",
    "completeText": "Send",
    "showProgressBar": "top",
    "pages": [{"name": "p1", "elements": [
        {"type": "radiogroup", "name": "type", "title": "Type", "isRequired": True,
         "choices": [{"value": "biz", "text": {"default": "Business", "fr": "Entreprise"}}, "person"]},  # noqa: E501
        {"type": "text", "name": "company", "title": "Company", "visibleIf": "{type} = 'biz' or {type} anyof ['x']"},  # noqa: E501
        {"type": "text", "inputType": "email", "name": "email", "title": "Email", "autocomplete": "email"},  # noqa: E501
        {"type": "expression", "name": "total", "expression": "{qty} * 2"},
        {"type": "text", "name": "qty", "title": "Qty"},
        {"type": "panel", "name": "more", "title": "More", "visibleIf": "{email} notempty",
         "elements": [{"type": "comment", "name": "notes", "title": "Notes", "maxLength": 200}]},
        {"type": "matrixdropdown", "name": "grid", "title": "Grid", "columns": [{"name": "c"}]},
        {"type": "text", "name": "odd", "visibleIf": "{a} =~ 'x'"},
    ]}],
}  # fmt: skip


def test_surveyjs_import() -> None:
    result = import_surveyjs(SURVEY)
    model = result.model
    assert model["title"] == "Feedback" and model["translations"]["fr"]["title"] == "Avis"
    assert model["translations"]["fr"]["fields"]["type"]["choices"]["biz"] == "Entreprise"
    fields = M.fields(model)
    assert fields["type"]["type"] == "radio" and fields["type"]["required"] is True
    assert fields["company"]["when"] == '#type is "biz" or #type is one of ["x"]'
    assert (
        fields["email"]["type"] == "email" and fields["email"]["props"]["autocomplete"] == "email"
    )
    assert fields["total"]["calculation"] == "#qty * 2"
    assert M.find(model, "more")["when"] == "#email is not empty"  # type: ignore[index]
    report = " ".join(result.report)
    assert "matrixdropdown" in report and "showProgressBar" in report and "=~" in report
    assert model["extensions"]["surveyjs"]["grid"] == {"columns": [{"name": "c"}]}
    assert M.validate(model) == []


def test_surveyjs_round_trip_keeps_meaning() -> None:
    model = import_surveyjs(SURVEY).model
    again = import_surveyjs(export_surveyjs(model)).model
    keys = ("id", "type", "label", "when", "calculation", "required")
    assert [{k: f.get(k) for k in keys} for f in M.fields(again).values()] == [
        {k: f.get(k) for k in keys} for f in M.fields(model).values()
    ]
    assert M.same(again["translations"], model["translations"])


def test_surveyjs_rejects_garbage() -> None:
    with pytest.raises(FormImportError):
        import_surveyjs("not json")
    with pytest.raises(FormImportError):
        import_surveyjs("[1]")


SURVEY_ROWS = [
    {
        "type": "text",
        "name": "name",
        "label": "Name",
        "label::French (fr)": "Nom",
        "required": "yes",
    },
    {"type": "select_one kinds", "name": "kind", "label": "Kind", "appearance": "minimal"},
    {
        "type": "begin group",
        "name": "biz",
        "label": "Business",
        "relevant": "selected(${kind}, 'biz')",
    },
    {"type": "integer", "name": "staff", "label": "Staff", "constraint": ". > 0"},
    {"type": "calculate", "name": "double", "label": "Double", "calculation": "${staff} * 2"},
    {"type": "end group", "name": "biz"},
    {"type": "begin repeat", "name": "kids", "label": "Children"},
    {
        "type": "text",
        "name": "kid",
        "label": "Child",
        "relevant": "${staff} > 2 and not(${name} = '')",
    },
    {"type": "end repeat"},
    {"type": "geotrace", "name": "route", "label": "Route"},
]
CHOICE_ROWS = [
    {"list_name": "kinds", "name": "biz", "label": "Business", "label::French (fr)": "Entreprise"},
    {"list_name": "kinds", "name": "person", "label": "Person"},
]


def test_xlsform_rows_import() -> None:
    result = import_rows(
        SURVEY_ROWS, CHOICE_ROWS, {"form_title": "Survey", "default_language": "English"}
    )
    model = result.model
    fields = M.fields(model)
    assert fields["name"]["required"] is True
    assert model["translations"]["fr"]["fields"]["name"]["label"] == "Nom"
    assert fields["kind"]["type"] == "select"
    assert M.find(model, "biz")["when"] == '#kind contains "biz"'  # type: ignore[index]
    assert fields["double"]["calculation"] == "#staff * 2"
    assert [i["id"] for i in fields["kids"]["items"]] == ["kid"]
    assert fields["kid"]["when"] == '#staff > 2 and not #name is ""'
    assert model["extensions"]["xlsform"]["constraints"] == {"staff": ". > 0"}
    assert any("geotrace" in r for r in result.report)
    assert M.validate(model) == []


def test_xlsform_workbook_round_trip(tmp_path: Path) -> None:
    pytest.importorskip("openpyxl")  # an optional dependency, absent in some CI images
    model = import_rows(SURVEY_ROWS, CHOICE_ROWS, {"form_title": "Survey"}).model
    path = tmp_path / "survey.xlsx"
    export_xlsform(model, path)
    again = import_xlsform(path).model
    keys = ("id", "type", "label", "required", "when", "calculation")
    assert [{k: f.get(k) for k in keys} for f in M.fields(again).values()] == [
        {k: f.get(k) for k in keys} for f in M.fields(model).values()
    ]


def test_xlsform_export_rows_from_bfl() -> None:
    model = read(
        'form "T"\ncheckbox #c "C"\n  + a|A\n  + b|B\ntextarea #t "T"\n  @when #c is one of ["a", "b"]\n'  # noqa: E501
    ).model
    survey, choices, settings = export_rows(model)
    assert survey[0]["type"] == "select_multiple c"
    assert survey[1]["relevant"] == "(selected(${c}, 'a') or selected(${c}, 'b'))"
    assert [c["name"] for c in choices] == ["a", "b"] and settings["form_title"] == "T"


BFL = """form "Contact" @description "Write to us"
  @submit_label "Send"
text #name "Your name"
  @required
  @autocomplete "name"
email #email "Email"
  @description "We reply within a day."
radio #how "Reply by"
  + email|Email
  + phone|Phone
phone #phone "Phone"
  @when #how is "phone"
"""


def test_html_export_is_accessible() -> None:
    page = export_html(read(BFL).model, action="https://example.org/send")
    assert page.startswith("<!doctype html>")
    assert '<label for="name">Your name <span class="required">(required)</span></label>' in page
    assert 'autocomplete="name"' in page and " required" in page
    assert 'aria-describedby="email-help"' in page and 'id="email-help"' in page
    assert "<legend>Reply by</legend>" in page and '<label for="how-1">Email</label>' in page
    assert 'data-when="#how is &quot;phone&quot;"' in page
    assert '<button type="submit">Send</button>' in page


def test_html_round_trip() -> None:
    result = import_html(export_html(read(BFL).model))
    fields = M.fields(result.model)
    assert result.model["title"] == "Contact"
    assert fields["name"]["label"] == "Your name" and fields["name"]["required"] is True
    assert fields["name"]["props"]["autocomplete"] == "name"
    assert fields["how"]["label"] == "Reply by"
    assert [(c["value"], c["label"]) for c in fields["how"]["choices"]] == [
        ("email", "Email"),
        ("phone", "Phone"),
    ]
    assert M.validate(result.model) == []


def test_html_import_of_a_plain_page() -> None:
    page = """<html><head><title>Join</title></head><body><form>
    <label for="n">Name</label><input id="n" name="n" required>
    <label for="c">Colour</label><select id="c" name="c">
    <option value="r">Red</option><option>Blue</option></select>
    <input type="week" name="w"><input name="unlabelled">
    <script>alert(1)</script><input type="submit" value="Join now">
    </form></body></html>"""
    result = import_html(page)
    fields = M.fields(result.model)
    assert (
        result.model["title"] == "Join" and result.model["settings"]["submit_label"] == "Join now"
    )
    assert fields["n"]["label"] == "Name" and fields["n"]["required"] is True
    assert [(c["value"], c["label"]) for c in fields["c"]["choices"]] == [
        ("r", "Red"),
        ("Blue", "Blue"),
    ]
    report = " ".join(result.report)
    assert "week" in report and "<script>" in report and "unlabelled has no label" in report
