"""New Form, Insert Field, Check This Form, Fill It In Yourself, Properties, Responses.

Behavioural: each runs the shared command against the fake editor and the
scripted dialogs, and asserts what the document became and what was said.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.forms import model as M
from quill.ui import forms_doc as fd
from quill.ui.forms_commands import RESPONSES_WAIT


def _model(host):
    return fd.read(host.text).model


# -- outside a form document ------------------------------------------------- #


@pytest.mark.parametrize(
    ("run", "name"),
    [
        (lambda f: f.cmd_insert_field(), "Insert Form Field"),
        (lambda f: f.cmd_outline(), "Form Outline"),
        (lambda f: f.cmd_rules(), "Form Rules"),
        (lambda f: f.cmd_check(), "Check This Form"),
        (lambda f: f.cmd_fill_in(), "Fill It In Yourself"),
        (lambda f: f.cmd_properties(), "Form Properties"),
    ],
)
def test_outside_a_form_each_command_says_why_and_opens_nothing(
    forms, forms_host, forms_dialogs, run, name
) -> None:
    forms_host.path = Path("notes.md")
    run(forms)
    assert forms_host.announced == [
        f"{name} works in a form document, a .bfl file. Start one with New Form in the File "
        "menu, or open one."
    ]
    assert forms_dialogs.calls == [] and forms_dialogs.list_windows == []


def test_an_unsaved_document_is_not_a_form(forms, forms_host) -> None:
    forms_host.path = None
    forms.cmd_check()
    assert "works in a form document" in forms_host.said


# -- New Form ---------------------------------------------------------------- #


def test_new_form_cancelled_at_the_first_question_does_nothing(forms, forms_host) -> None:
    forms.cmd_new_form()
    assert forms_host.opened == [] and forms_host.announced == []


def test_new_form_writes_the_template_saves_it_and_opens_it(
    forms, forms_host, forms_dialogs, tmp_path
) -> None:
    target = tmp_path / "Bake sale.bfl"
    forms_dialogs.answer("ask_fields", {"title": "Bake sale", "template": "contact"})
    forms_dialogs.answer("ask_save_path", target)
    forms.cmd_new_form()
    assert forms_host.opened == [target]
    model = fd.read(target.read_text(encoding="utf-8")).model
    assert model["title"] == "Bake sale"
    assert [f["id"] for f in fd.fields(model)] == ["name", "email", "message"]
    assert forms_host.announced == ["Saved Bake sale.bfl, a contact form with 3 questions."]
    asked = forms_dialogs.asked("ask_save_path")[0]
    assert asked["suggested"] == "Bake sale"


def test_new_form_offers_every_template(forms, forms_dialogs) -> None:
    forms.cmd_new_form()
    template = forms_dialogs.asked("ask_fields")[0]["fields"][1]
    assert template.values == [
        "blank", "contact", "event", "membership", "survey", "accessibility", "volunteer",
    ]  # fmt: skip


def test_new_form_cancelled_at_save_writes_nothing(forms, forms_host, forms_dialogs) -> None:
    forms_dialogs.answer("ask_fields", {"title": "X", "template": "blank"})
    forms.cmd_new_form()
    assert forms_host.opened == [] and forms_host.announced == []


def test_new_form_that_cannot_be_saved_says_so(forms, forms_host, forms_dialogs, tmp_path) -> None:
    forms_dialogs.answer("ask_fields", {"title": "X", "template": "blank"})
    forms_dialogs.answer("ask_save_path", tmp_path / "missing folder" / "x.bfl")
    forms.cmd_new_form()
    assert forms_host.opened == []
    assert forms_host.said.startswith("QUILL could not save x.bfl")


# -- Insert Field ------------------------------------------------------------ #


def _pick(kind: str):
    from quill.ui import forms_field_types as ft

    return ft.kinds().index(kind)


def test_insert_field_cancelled_changes_nothing(forms, forms_host) -> None:
    before = forms_host.text
    forms.cmd_insert_field()
    assert forms_host.text == before and forms_host.announced == []


def test_insert_field_lists_every_type_the_core_knows(forms, forms_dialogs) -> None:
    forms.cmd_insert_field()
    asked = forms_dialogs.asked("pick_from_list")[0]
    assert asked["rows"][0].startswith("Section:")
    assert asked["rows"][1].startswith("Page break:")
    assert any(row.startswith("Email:") for row in asked["rows"])
    assert asked["matches"]("date", _pick("date"))
    assert not asked["matches"]("date", _pick("email"))


def test_insert_field_goes_after_the_question_at_the_caret(
    forms, forms_host, forms_dialogs
) -> None:
    forms_host.caret = forms_host.text.index("email #email")
    forms_dialogs.answer("pick_from_list", _pick("phone"))
    forms_dialogs.answer("ask_fields", {"label": "Phone number", "id": "", "required": True})
    forms.cmd_insert_field()
    ids = [f["id"] for f in fd.fields(_model(forms_host))]
    assert ids == ["name", "email", "phone_number", "heard", "heard_other"]
    assert forms_host.announced == ["Inserted Phone number, phone number."]
    assert "#phone_number" in forms_host.line_at_caret()
    # Everything nobody touched is still as it was written.
    assert forms_host.text.startswith(
        'bfl 1\nform "Spring fair"\n\ntext #name "Your name"\n  @required\n'
    )


def test_insert_field_with_choices_and_with_a_library(forms, forms_host, forms_dialogs) -> None:
    forms_dialogs.answer("pick_from_list", _pick("radio"), _pick("select"))
    forms_dialogs.answer(
        "ask_fields",
        {"label": "Size", "id": "size", "choices": "Small\nLarge\n\n"},
        {"label": "Country", "id": "", "choices": "", "library": "countries"},
    )
    forms.cmd_insert_field()
    forms.cmd_insert_field()
    model = _model(forms_host)
    size = M.find(model, "size")
    assert size["choices"] == [
        {"value": "small", "label": "Small"},
        {"value": "large", "label": "Large"},
    ]
    assert M.find(model, "country")["choice_library"] == "countries"


def test_insert_field_asks_only_what_the_kind_needs(forms, forms_dialogs) -> None:
    forms_dialogs.answer("pick_from_list", _pick("text"), _pick("radio"))
    forms.cmd_insert_field()
    forms.cmd_insert_field()
    text_keys, radio_keys = (
        [a.key for a in call["fields"]] for call in forms_dialogs.asked("ask_fields")
    )
    assert text_keys == ["label", "id", "required", "help"]
    assert radio_keys == ["label", "id", "required", "help", "choices", "library"]


def test_insert_section_and_page_break(forms, forms_host, forms_dialogs) -> None:
    forms_host.caret = forms_host.text.index("radio #heard")
    forms_dialogs.answer("pick_from_list", _pick("page_break"))
    forms_dialogs.answer("ask_fields", {"label": "About the day"})
    forms.cmd_insert_field()
    model = _model(forms_host)
    assert [[i["id"] for i in p["items"]] for p in model["pages"]] == [
        ["name", "email", "heard"],
        ["heard_other"],
    ]
    assert model["pages"][1]["title"] == "About the day"
    assert forms_host.announced[-1] == "Page break inserted. Page 2 starts here."
    forms_host.caret = 0
    forms_dialogs.answer("pick_from_list", _pick("section"))
    forms_dialogs.answer("ask_fields", {"label": "About you"})
    forms.cmd_insert_field()
    first = _model(forms_host)["pages"][0]["items"][0]
    assert (first["type"], first["label"]) == ("section", "About you")


# -- Check This Form --------------------------------------------------------- #


def test_check_finds_nothing_in_a_clean_form(forms, forms_host) -> None:
    forms_host.text = 'bfl 1\nform "Clean"\n\ntext #name "Your name"\n  @autocomplete "name"\n'
    forms.cmd_check()
    assert forms_host.announced == ["Check This Form found nothing to fix."]


def test_check_lists_findings_and_go_to_it_moves_the_caret(
    forms, forms_host, forms_dialogs
) -> None:
    forms_host.text = (
        'bfl 1\nform "Join"\n\nemail #email "Email address"\n'
        'text #age "Age *"\n  @when #missing is "x"\n'
    )
    forms.cmd_check()
    rows = forms_dialogs.window["rows"]
    assert any("Email address has no autofill hint" in r for r in rows)
    assert any("asterisk" in r for r in rows)
    assert any("#missing" in r for r in rows)
    index = next(i for i, r in enumerate(rows) if "autofill" in r)
    assert forms_dialogs.press("Go to It", index) is not None
    assert forms_host.line_at_caret().startswith("email #email")


def test_check_again_reads_the_document_afresh(forms, forms_host, forms_dialogs) -> None:
    forms_host.text = 'bfl 1\nform "Join"\n\nemail #email "Email address"\n'
    forms.cmd_check()
    forms_host.text = (
        'bfl 1\nform "Join"\n\nemail #email "Email address"\n  @autocomplete "email"\n'
    )
    assert forms_dialogs.press("Check Again", None) == []


def test_check_includes_where_the_site_reads_it_differently(forms, forms_dialogs) -> None:
    forms.cmd_check()
    assert any(r.startswith("On the site today:") for r in forms_dialogs.window["rows"])


# -- Fill It In Yourself ------------------------------------------------------ #


def test_fill_in_opens_a_session_on_the_form(forms, forms_host, forms_dialogs) -> None:
    forms.cmd_fill_in()
    (session,) = forms_dialogs.fill_sessions
    assert session.model["title"] == "Spring fair"
    assert forms_host.announced == []


def test_fill_in_with_no_questions_says_so(forms, forms_host, forms_dialogs) -> None:
    forms_host.text = 'bfl 1\nform "Empty"\n'
    forms.cmd_fill_in()
    assert forms_host.announced == ["This form has no questions to fill in yet."]
    assert forms_dialogs.fill_sessions == []


# -- Form Properties ---------------------------------------------------------- #


def test_properties_cancelled_changes_nothing(forms, forms_host) -> None:
    before = forms_host.text
    forms.cmd_properties()
    assert forms_host.text == before


def test_properties_shows_what_the_site_decides(forms, forms_dialogs) -> None:
    forms.cmd_properties()
    facts = forms_dialogs.asked("ask_properties")[0]["facts"]
    assert "CAPTCHA: off." in facts and "not published yet" in facts


def test_properties_writes_the_settings(forms, forms_host, forms_dialogs) -> None:
    forms_dialogs.answer(
        "ask_properties",
        {
            "title": "Spring fair 2027",
            "description": "",
            "language": "en",
            "submit_label": "Sign me up",
            "message": "Thank you. See you there.",
            "url": "",
            "save": True,
        },
    )
    forms.cmd_properties()
    model = _model(forms_host)
    assert model["title"] == "Spring fair 2027"
    assert model["settings"] == {"submit_label": "Sign me up", "save_continue_enabled": True}
    assert model["confirmations"] == [
        {"id": "message", "type": "message", "message": "Thank you. See you there."}
    ]
    assert forms_host.announced == ["Form properties saved in the document."]


# -- Responses --------------------------------------------------------------- #


def test_responses_says_it_waits_for_the_connection(forms, forms_host) -> None:
    forms.cmd_responses()
    assert forms_host.announced == [RESPONSES_WAIT]
    assert "BITS Accessible Forms" in RESPONSES_WAIT
