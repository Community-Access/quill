"""Imports and exports that run on the computer: SurveyJS, XLSForm and HTML."""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.forms import schema_check
from quill.core.forms.bfl_read import read_form
from quill.core.forms.errors import FormImportError
from quill.core.forms.interop_html import export_html, import_html
from quill.core.forms.interop_surveyjs import export_surveyjs, import_surveyjs
from quill.core.forms.interop_xlsform import (
    export_rows,
    export_xlsform,
    import_rows,
    import_xlsform,
)
from quill.core.forms.model import Field, Section, all_fields
from quill.core.forms.model_json import to_dict

SURVEY = {
    "title": {"default": "Feedback", "fr": "Avis"},
    "locale": "en",
    "completeText": "Send",
    "showProgressBar": "top",
    "pages": [
        {
            "name": "p1",
            "elements": [
                {
                    "type": "radiogroup",
                    "name": "type",
                    "title": "Type",
                    "isRequired": True,
                    "choices": [{"value": "biz", "text": {"default": "Business", "fr": "Entreprise"}}, "person"],  # noqa: E501
                },
                {"type": "text", "name": "company", "title": "Company", "visibleIf": "{type} = 'biz' or {type} anyof ['x']"},  # noqa: E501
                {"type": "text", "inputType": "email", "name": "email", "title": "Email", "autocomplete": "email"},  # noqa: E501
                {"type": "expression", "name": "total", "expression": "{qty} * 2"},
                {"type": "panel", "name": "more", "title": "More", "visibleIf": "{email} notempty", "elements": [  # noqa: E501
                    {"type": "comment", "name": "notes", "title": "Notes", "maxLength": 200},
                ]},
                {"type": "matrixdropdown", "name": "grid", "title": "Grid", "columns": [{"name": "c"}]},  # noqa: E501
                {"type": "text", "name": "odd", "visibleIf": "{a} =~ 'x'"},
            ],
        }
    ],
}  # fmt: skip


def test_surveyjs_import() -> None:
    result = import_surveyjs(SURVEY)
    form = result.form
    assert form.title == "Feedback"
    assert form.translations["fr"]["title"] == "Avis"
    assert form.translations["fr"]["field.type.choice.biz"] == "Entreprise"
    fields = {f.id: f for f in all_fields(form)}
    assert fields["type"].type == "radio" and fields["type"].required
    assert [c.value for c in fields["type"].choices] == ["biz", "person"]
    assert fields["company"].visible_when == '#type is "biz" or #type is one of ("x")'
    assert fields["email"].type == "email" and fields["email"].settings["autocomplete"] == "email"
    assert fields["total"].calculate == "#qty * 2"
    section = form.pages[0].items[4]
    assert isinstance(section, Section) and section.visible_when == "#email is filled"
    assert fields["notes"].type == "textarea"
    # Nothing silently dropped: the report names each thing the model could not hold.
    report = " ".join(result.report)
    assert "matrixdropdown" in report and "showProgressBar" in report and "{a} =~ 'x'" in report
    assert fields["grid"].settings["surveyjs"] == {"columns": [{"name": "c"}]}
    assert schema_check.problems(to_dict(form)) == []


def test_surveyjs_round_trip_keeps_meaning() -> None:
    form = import_surveyjs(SURVEY).form
    again = import_surveyjs(export_surveyjs(form)).form
    assert [(f.id, f.type, f.label, f.visible_when, f.calculate) for f in all_fields(again)] == [
        (f.id, f.type, f.label, f.visible_when, f.calculate) for f in all_fields(form)
    ]
    assert again.translations == form.translations


def test_surveyjs_export_of_bfl() -> None:
    form = read_form(
        'radio #t "Type"\n  + a|A\n\nif #t is "a" and not #x is empty\n  text #c "C"\n'
    )
    data = export_surveyjs(form)
    company = data["pages"][0]["elements"][1]
    assert company["visibleIf"] == "{t} = 'a' and !({x} empty)"


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
    {"type": "calculate", "name": "double", "calculation": "${staff} * 2"},
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
    form = result.form
    assert form.title == "Survey"
    fields = {f.id: f for f in all_fields(form)}
    assert fields["name"].required and form.translations["fr"]["field.name.label"] == "Nom"
    assert fields["kind"].type == "select" and [c.value for c in fields["kind"].choices] == [
        "biz",
        "person",
    ]
    assert form.translations["fr"]["field.kind.choice.biz"] == "Entreprise"
    group = form.pages[0].items[2]
    assert isinstance(group, Section) and group.visible_when == '#kind is "biz"'
    assert fields["double"].calculate == "#staff * 2"
    assert [f.id for f in fields["kids"].fields] == ["kid"]
    assert fields["kid"].visible_when == '#staff > 2 and not #name is ""'
    assert any("geotrace" in r for r in result.report)
    assert any("constraint" in r for r in result.report)


def test_xlsform_workbook_round_trip(tmp_path: Path) -> None:
    form = import_rows(SURVEY_ROWS, CHOICE_ROWS, {"form_title": "Survey"}).form
    path = tmp_path / "survey.xlsx"
    export_xlsform(form, path)
    again = import_xlsform(path).form
    assert again.title == "Survey"
    ours = [
        (f.id, f.type, f.label, f.required, f.visible_when, f.calculate) for f in all_fields(form)
    ]
    theirs = [
        (f.id, f.type, f.label, f.required, f.visible_when, f.calculate) for f in all_fields(again)
    ]
    assert theirs == ours


def test_xlsform_export_rows_from_bfl() -> None:
    form = read_form(
        'form "T"\n\ncheckbox #c "C"\n  + a|A\n  + b|B\n\nif #c is one of ("a", "b")\n  textarea #t "T"\n'  # noqa: E501
    )
    survey, choices, settings = export_rows(form)
    assert survey[0]["type"] == "select_multiple c"
    assert survey[1]["relevant"] == "(selected(${c}, 'a') or selected(${c}, 'b'))"
    assert survey[1]["appearance"] == "multiline"
    assert [c["name"] for c in choices] == ["a", "b"]
    assert settings["form_title"] == "T"


def test_xlsform_needs_a_survey_sheet(tmp_path: Path) -> None:
    import openpyxl

    path = tmp_path / "empty.xlsx"
    book = openpyxl.Workbook()
    book.active.title = "other"
    book.save(path)
    with pytest.raises(FormImportError, match="survey"):
        import_xlsform(path)


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

if #how is "phone"
  phone #phone "Phone"
"""


def test_html_export_is_accessible() -> None:
    page = export_html(read_form(BFL), action="https://example.org/send")
    assert page.startswith("<!doctype html>")
    assert '<label for="name">Your name <span class="required">(required)</span></label>' in page
    assert 'autocomplete="name"' in page and " required" in page
    assert 'aria-describedby="email-help"' in page and 'id="email-help"' in page
    assert "<fieldset" in page and "<legend>Reply by</legend>" in page
    assert '<label for="how-1">Email</label>' in page
    assert 'data-visible-when="#how is &quot;phone&quot;"' in page
    assert '<button type="submit">Send</button>' in page


def test_html_round_trip() -> None:
    result = import_html(export_html(read_form(BFL)))
    fields = {f.id: f for f in all_fields(result.form)}
    assert result.form.title == "Contact"
    assert fields["name"].label == "Your name" and fields["name"].required
    assert fields["name"].settings["autocomplete"] == "name"
    assert fields["email"].type == "email"
    how = fields["how"]
    assert how.type == "radio" and how.label == "Reply by"
    assert [(c.value, c.label) for c in how.choices] == [("email", "Email"), ("phone", "Phone")]
    assert result.form.settings.submit_label == ""  # a <button>, not an input, so not read


def test_html_import_of_a_plain_page() -> None:
    page = """<html><head><title>Join</title></head><body><form>
    <label for="n">Name</label><input id="n" name="n" required>
    <label for="c">Colour</label><select id="c" name="c">
    <option value="r">Red</option><option>Blue</option></select>
    <input type="week" name="w"><input name="unlabelled">
    <script>alert(1)</script><input type="submit" value="Join now">
    </form></body></html>"""
    result = import_html(page)
    fields = {f.id: f for f in all_fields(result.form)}
    assert result.form.title == "Join"
    assert fields["n"].label == "Name" and fields["n"].required
    assert [(c.value, c.label) for c in fields["c"].choices] == [("r", "Red"), ("Blue", "Blue")]
    assert result.form.settings.submit_label == "Join now"
    report = " ".join(result.report)
    assert "week" in report and "<script>" in report and "unlabelled has no label" in report
    assert isinstance(fields["w"], Field)
