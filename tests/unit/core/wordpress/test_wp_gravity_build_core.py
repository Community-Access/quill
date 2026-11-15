"""Building Gravity Forms forms in QUILL: the wx-free core (complete.md WP-C).

The form objects are shaped as Gravity Forms REST API v2 documents them
(``GET gf/v2/forms/{id}``): ``title``, ``description``, ``labelPlacement``,
``button``, ``fields`` (``id``, ``type``, ``label``, ``isRequired``,
``choices`` of ``text``/``value``/``isSelected``, ``inputs`` for complex
fields, ``conditionalLogic``, ``cssClass``, ``description``, ``placeholder``,
``defaultValue``, ``adminLabel``), ``confirmations`` and ``notifications``.
No site is called.
"""

from __future__ import annotations

import copy
from typing import Any

import pytest

from quill.core.forms import model as M
from quill.core.wordpress import gravity_build as gb
from quill.core.wordpress import gravity_build_save as gs
from quill.core.wordpress.gravity_build_checks import check_form
from quill.core.wordpress.gravity_qaf import to_gravity, to_qaf

FORM: dict[str, Any] = {
    "id": "1",
    "title": "Signup",
    "description": "Join the show.",
    "labelPlacement": "top_label",
    "button": {"type": "text", "text": "Join", "imageUrl": ""},
    "nextFieldId": 9,
    "gravityformsmailchimp": {"keep": "me"},
    "confirmations": {
        "c1": {"id": "c1", "name": "Default Confirmation", "isDefault": True, "type": "message",
               "message": "Thanks!"},
    },
    "notifications": {
        "n1": {"id": "n1", "name": "Admin Notification", "toType": "email", "to": "{admin_email}",
               "subject": "New signup", "message": "{all_fields}", "routing": None},
    },
    "fields": [
        {"id": 1, "type": "text", "label": "Name", "isRequired": True, "cssClass": "wide",
         "size": "large", "inputMask": False},
        {"id": 2, "type": "radio", "label": "Show", "choices": [
            {"text": "Morning", "value": "am", "isSelected": False, "price": "$1"},
            {"text": "Evening", "value": "pm", "isSelected": False, "price": ""},
        ]},
        {
            "id": 3,
            "type": "address",
            "label": "Address",
            "inputs": [{"id": "3.1", "label": "Street"}],
        },
        {"id": 4, "type": "fileupload", "label": "Photo", "maxFileSize": 2},
    ],
}  # fmt: skip


def _form() -> dict[str, Any]:
    return copy.deepcopy(FORM)


# --------------------------------------------------------------------------- #
# the model


def test_a_new_form_has_gravity_forms_own_defaults() -> None:
    ids = iter(["c9", "n9"])
    form = gb.new_form("Contact", make_id=lambda: next(ids))
    assert form["title"] == "Contact" and form["fields"] == []
    assert form["button"]["text"] == "Submit" and form["labelPlacement"] == "top_label"
    assert form["confirmations"]["c9"]["isDefault"] is True
    assert form["notifications"]["n9"]["to"] == "{admin_email}"
    assert gb.settings_of(form).notify_subject == "New submission from {form_title}"


@pytest.mark.parametrize("kind", list(gb.FIELD_TYPES))
def test_every_common_field_type_can_be_added_with_its_properties(kind: str) -> None:
    form = _form()
    values = {"label": "Q", "description": "Help", "isRequired": True, "placeholder": "e.g.",
              "defaultValue": "x", "adminLabel": "q", "cssClass": "c",
              "choices": "One\n* Two = 2"}  # fmt: skip
    made = gb.add_field(form, kind, values)
    assert made["type"] == kind and made["id"] == 9  # nextFieldId, never a reused id
    assert form["nextFieldId"] == 10
    assert made["label"] == "Q" and made["adminLabel"] == "q" and made["cssClass"] == "c"
    assert made["isRequired"] is (kind not in gb.DISPLAY_TYPES)
    if kind in gb.CHOICE_TYPES:
        assert [(c["text"], c["value"], c["isSelected"]) for c in made["choices"]] == [
            ("One", "One", False),
            ("Two", "2", True),
        ]
    if kind == "name":
        assert [i["id"] for i in made["inputs"]] == ["9.2", "9.3", "9.4", "9.6", "9.8"]
    if kind == "address":
        assert [i["id"] for i in made["inputs"]] == [f"9.{n}" for n in range(1, 7)]
    if kind == "consent":
        assert made["checkboxLabel"] and len(made["inputs"]) == 3


def test_a_removed_fields_id_is_never_given_out_again() -> None:
    form = _form()
    form.pop("nextFieldId")
    gb.remove_field(form, 3)  # field 4 out
    made = gb.add_field(form, "text", {"label": "New"}, ever=[1, 2, 3, 4])
    assert made["id"] == 5


def test_checkbox_inputs_skip_multiples_of_ten_and_keep_their_ids_by_position() -> None:
    form = _form()
    made = gb.add_field(form, "checkbox", {"label": "Days", "choices": "\n".join("abcdefghijkl")})
    ids = [i["id"] for i in made["inputs"]]
    assert "9.10" not in ids and ids[-1] == "9.13" and len(ids) == 12
    gb.edit_field(made, {"choices": "A\nB"})
    assert [(i["id"], i["label"]) for i in made["inputs"]] == [("9.1", "A"), ("9.2", "B")]


def test_editing_keeps_every_property_quill_does_not_edit() -> None:
    form = _form()
    name = form["fields"][0]
    changed = gb.edit_field(name, {"label": "Full name", "cssClass": "wide", "placeholder": ""})
    assert changed == ["label"]
    assert name["size"] == "large" and name["inputMask"] is False
    show = form["fields"][1]
    gb.edit_field(show, {"choices": "Morning = am\nEvening = pm\nNight = night"})
    assert show["choices"][0]["price"] == "$1"  # kept by value
    assert show["enableChoiceValue"] is True


def test_a_field_quill_does_not_build_is_never_edited() -> None:
    with pytest.raises(ValueError, match="keeps it as is"):
        gb.edit_field(_form()["fields"][3], {"label": "x"})
    assert "kept as it is" in gb.field_line(_form()["fields"][3], 4)


def test_choices_read_and_write_as_one_a_line() -> None:
    text = gb.choices_to_text(FORM["fields"][1]["choices"])
    assert text == "Morning = am\nEvening = pm"
    assert gb.choices_from_text("* Yes\n\nNo")[0] == {
        "text": "Yes",
        "value": "Yes",
        "isSelected": True,
        "price": "",
    }


def test_moving_and_removing_and_logic_that_named_the_removed_field() -> None:
    form = _form()
    gb.set_condition(form["fields"][0], gb.Condition("show", "2", "is", "am"))
    assert gb.move_field(form, 0, 1) == 1
    assert [f["id"] for f in form["fields"]] == [2, 1, 3, 4]
    assert gb.move_field(form, 0, -1) == 0
    gone = gb.remove_field(form, 0)
    assert gone is not None and gone["id"] == 2
    assert form["fields"][0]["conditionalLogic"] == ""


def test_conditional_logic_one_rule_is_edited_and_richer_logic_is_kept() -> None:
    field = {"id": 5, "type": "text", "label": "Why"}
    gb.set_condition(field, gb.Condition("hide", "2", "isnot", "pm"))
    assert field["conditionalLogic"]["rules"] == [
        {"fieldId": "2", "operator": "isnot", "value": "pm"}
    ]
    assert gb.condition_of(field) == gb.Condition("hide", "2", "isnot", "pm")
    field["conditionalLogic"]["rules"].append({"fieldId": "1", "operator": ">", "value": "3"})
    assert gb.condition_of(field) == "complex"
    with pytest.raises(ValueError):
        gb.set_condition(field, gb.Condition("show", "2", "contains", "x"))


def test_settings_change_only_their_own_keys() -> None:
    form = _form()
    settings = gb.settings_of(form)
    assert (settings.title, settings.button, settings.confirmation) == ("Signup", "Join", "Thanks!")
    gb.apply_settings(
        form,
        gb.Settings(
            title="Sign up",
            description="",
            button="Send",
            label_placement="left_label",
            confirmation="Got it.",
            notify_to="radio@example.com",
            notify_subject="Signup",
        ),
    )
    assert form["notifications"]["n1"]["routing"] is None and form["notifications"]["n1"]["message"]
    assert form["notifications"]["n1"]["to"] == "radio@example.com"
    assert form["confirmations"]["c1"]["message"] == "Got it."
    assert form["labelPlacement"] == "left_label" and form["gravityformsmailchimp"] == {
        "keep": "me"
    }


def test_a_redirect_confirmation_and_a_routed_notification_are_left_alone() -> None:
    form = _form()
    form["confirmations"]["c1"].update(type="redirect", url="https://x.example")
    form["notifications"]["n1"].update(toType="field", to="7")
    settings = gb.settings_of(form)
    assert not settings.confirmation_editable and not settings.notify_to_editable
    from dataclasses import replace

    gb.apply_settings(form, replace(settings, confirmation="No", notify_to="a@b.example"))
    assert (
        form["confirmations"]["c1"]["message"] == "Thanks!"
        and form["notifications"]["n1"]["to"] == "7"
    )


# --------------------------------------------------------------------------- #
# checks


def _ids(form: dict[str, Any]) -> list[tuple[str, str | None]]:
    return [(f.text, f.field_id) for f in check_form(form)]


def test_a_well_made_form_has_no_findings() -> None:
    assert check_form(_form()) == []


def test_the_checks_find_what_a_listener_would_trip_over() -> None:
    form = gb.new_form("")
    form["button"]["text"] = ""
    gb.add_field(form, "page", {})
    gb.add_field(form, "text", {"placeholder": "Your name"})
    gb.add_field(form, "email", {"label": "Email *"})
    gb.add_field(form, "radio", {"label": "Pick"})
    gb.add_field(form, "text", {"label": "email *"})
    gb.add_field(form, "section", {"label": "End"})
    gb.add_field(form, "consent", {"label": "Terms", "checkboxLabel": ""})
    late = gb.add_field(form, "text", {"label": "Later"})
    gb.set_condition(late, gb.Condition("show", "99", "is", "x"))
    found = " | ".join(f.text for f in check_form(form))
    for words in (
        "has no title",
        "submit button has no text",
        "starts with a page break",
        "only a placeholder",
        "asterisk",
        "Pick has no choices",
        "Two questions are both called",
        "no text beside its check box",
        "depends on field 99",
    ):
        assert words in found, words
    assert ("Pick has no choices. Add some, one a line.", "4") in _ids(form)


def test_page_and_section_structure() -> None:
    form = gb.new_form("Pages")
    gb.add_field(form, "text", {"label": "A"})
    gb.add_field(form, "section", {"label": "Empty"})
    gb.add_field(form, "page", {})
    gb.add_field(form, "page", {})
    found = " | ".join(f.text for f in check_form(form))
    assert "Section Empty has nothing in it" in found
    assert "Two page breaks in a row" in found and "ends with a page break" in found


# --------------------------------------------------------------------------- #
# saving


class Api:
    def __init__(self, form: dict[str, Any] | None = None) -> None:
        self.form = copy.deepcopy(form) if form else None
        self.calls: list[tuple[str, str, Any]] = []
        self.on_read: Any = None
        self.keep: Any = None

    def get(self, route: str, **_p: Any) -> Any:
        if self.on_read:
            self.on_read(self.form)
            self.on_read = None
        return copy.deepcopy(self.form)

    def request(self, method: str, route: str, **kw: Any) -> Any:
        body = kw.get("json_body")
        self.calls.append((method, route, copy.deepcopy(body)))
        if method == "POST":
            self.form = {**copy.deepcopy(body), "id": "7"}
        elif method == "PUT":
            self.form = copy.deepcopy(self.keep(body) if self.keep else body)

        class _R:
            payload = copy.deepcopy(self.form)

        return _R()


def test_change_lines_name_every_change_and_that_entries_are_untouched() -> None:
    after = _form()
    gb.edit_field(after["fields"][0], {"label": "Full name", "isRequired": False})
    gb.add_field(after, "email", {"label": "Email"})
    gb.remove_field(after, 2)
    after["title"] = "Sign up"
    lines = gs.change_lines(FORM, after)
    assert "Title: Sign up (was Signup)." in lines
    assert "Change Full name: label, required." in lines
    assert "Add field 4: Email, Email." in lines
    assert "Remove Address. Answers already given to it stay in the entries." in lines
    assert lines[-1] == gs.ENTRIES_LINE
    assert gs.change_lines(FORM, _form())[0] == "Nothing changes."


def test_an_edit_puts_the_whole_form_after_checking_it_has_not_changed() -> None:
    api = Api(FORM)
    edited = _form()
    gb.edit_field(edited["fields"][0], {"label": "Full name"})
    saved = gs.update(api, "gf/v2/forms/1", FORM, edited)
    assert api.calls == [("PUT", "gf/v2/forms/1", edited)]
    assert saved.problems == () and saved.stored == edited
    assert all(method != "DELETE" and "entries" not in route for method, route, _ in api.calls)


def test_an_edit_to_a_form_changed_meanwhile_sends_nothing() -> None:
    api = Api(FORM)
    api.on_read = lambda form: form.__setitem__("title", "Theirs")
    with pytest.raises(gs.FormChanged, match="Nothing was sent"):
        gs.update(api, "gf/v2/forms/1", FORM, _form())
    assert api.calls == []


def test_a_save_that_reads_back_differently_says_so() -> None:
    api = Api(FORM)
    api.keep = lambda body: {**body, "fields": copy.deepcopy(FORM["fields"])}
    edited = _form()
    gb.edit_field(edited["fields"][1], {"label": "Programme", "choices": "Morning = am"})
    saved = gs.update(api, "gf/v2/forms/1", FORM, edited)
    assert "Programme's label reads back as 'Show'." in saved.problems
    assert "Programme's choices read back differently." in saved.problems


def test_a_new_form_is_posted_read_back_and_undone_into_the_trash() -> None:
    api = Api()
    form = gb.new_form("Contact")
    gb.add_field(form, "text", {"label": "Name"})
    saved = gs.create(api, form)
    assert (saved.form_id, saved.route, saved.problems) == ("7", "gf/v2/forms/7", ())
    assert api.calls[0][:2] == ("POST", "gf/v2/forms")
    gs.trash(api, saved.route)
    assert api.calls[-1] == ("DELETE", "gf/v2/forms/7", None)


def test_undo_puts_the_previous_form_back_only_over_what_the_save_left() -> None:
    api = Api(FORM)
    edited = _form()
    edited["title"] = "Mine"
    api.form = copy.deepcopy(edited)
    gs.put_back(api, "gf/v2/forms/1", edited, FORM)
    assert api.form == FORM
    with pytest.raises(gs.FormChanged):
        gs.put_back(api, "gf/v2/forms/1", edited, FORM)


# --------------------------------------------------------------------------- #
# QAF and back


def test_a_gravity_form_converts_to_a_valid_qaf_model_naming_what_is_lost() -> None:
    form = _form()
    gb.add_field(form, "page", {"label": "Two"})
    gb.add_field(form, "section", {"label": "More"})
    late = gb.add_field(form, "select", {"label": "When", "choices": "Now\nLater"})
    gb.set_condition(late, gb.Condition("hide", "2", "is", "am"))
    converted = to_qaf(form)
    assert M.validate(converted.form) == []
    pages = converted.form["pages"]
    assert len(pages) == 2 and pages[1]["title"] == "Two"
    section = pages[1]["items"][0]
    assert section["type"] == "section" and section["items"][0]["when"] == 'not #field_2 is "am"'
    lost = " | ".join(converted.lost)
    assert "Photo is a fileupload field" in lost and "CSS class" in lost
    assert "button text Join" in lost


def test_a_qaf_model_converts_to_gravity_forms_and_back() -> None:
    model = M.create("Survey")
    model["pages"][0]["items"] = [
        {"id": "colour", "type": "radio", "label": "Colour", "required": True,
         "choices": [{"value": "r", "label": "Red"}, {"value": "b", "label": "Blue"}]},
        {"id": "why", "type": "textarea", "label": "Why", "when": '#colour is "b"'},
        {"id": "stars", "type": "rating", "label": "Stars"},
        {"id": "odd", "type": "text", "label": "Odd", "when": "#colour is \"r\" and #why is \"x\""},
    ]  # fmt: skip
    model["confirmations"] = [{"id": "c", "type": "message", "message": "Ta"}]
    converted = to_gravity(model)
    fields = converted.form["fields"]
    assert [f["type"] for f in fields] == ["radio", "textarea", "text"]
    assert fields[0]["isRequired"] is True and fields[0]["choices"][1]["value"] == "b"
    assert gb.condition_of(fields[1]) == gb.Condition("show", "1", "is", "b")
    assert fields[2]["conditionalLogic"] == ""
    lost = " | ".join(converted.lost)
    assert "Stars is a rating" in lost and "Odd: its rule" in lost
    assert gb.settings_of(converted.form).confirmation == "Ta"
    again = to_qaf(converted.form)
    assert M.validate(again.form) == []
