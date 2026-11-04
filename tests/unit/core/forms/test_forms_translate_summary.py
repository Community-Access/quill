"""Translations side by side, and the spoken summaries the outline reads."""

from __future__ import annotations

from quill.core.forms.bfl_read import read_form
from quill.core.forms.model import Field, Section
from quill.core.forms.summary import field_summary, item_summary, outline
from quill.core.forms.translate import languages, localize, missing, translatable_strings

FORM = """form "Contact" @description "Get in touch"
  @submit_label "Send"
  @translate fr title "Contact"
  @translate fr submit_label "Envoyer"

section "About you"
  @translate fr title "Vous"

text #name "Your name"
  @required
  @autocomplete "name"
  @translate fr label "Votre nom"

email #email "Email address"
  @required
  @autocomplete "email"
  @description "We only use this to reply."

radio #how "How should we reply?"
  + email|By email
  + phone|By phone
  @translate fr choice email "Par courriel"

if #how is "phone"
  phone #phone "Phone number"
    @mask "(999) 999-9999"

select #country "Country"
  @library countries

toggle #x "Unknown"
"""


def test_translation_keys_in_form_order() -> None:
    keys = [k for k, _ in translatable_strings(read_form(FORM))]
    assert keys[:4] == ["title", "description", "settings.submit_label", "section.field_1.title"]
    assert "field.how.choice.phone" in keys


def test_missing_and_languages() -> None:
    form = read_form(FORM)
    assert languages(form) == ["en", "fr"]
    gaps = missing(form, "fr")
    assert "field.name.label" not in gaps
    assert "field.email.label" in gaps
    assert "description" in gaps


def test_localize_uses_translations_and_falls_back() -> None:
    form = read_form(FORM)
    fr = localize(form, "fr")
    assert fr.language == "fr"
    assert fr.settings.submit_label == "Envoyer"
    section = fr.pages[0].items[0]
    assert isinstance(section, Section) and section.title == "Vous"
    fields = {i.id: i for i in section.items if isinstance(i, Field)}
    assert fields["name"].label == "Votre nom"
    assert fields["email"].label == "Email address"  # no translation yet
    assert [c.label for c in fields["how"].choices] == ["Par courriel", "By phone"]
    # The original is untouched.
    assert form.settings.submit_label == "Send"


def test_field_summaries() -> None:
    form = read_form(FORM)
    section = form.pages[0].items[0]
    assert isinstance(section, Section)
    fields = {i.id: i for i in section.items if isinstance(i, Field)}
    assert field_summary(fields["name"]) == "Your name, text field, required, with an autofill hint"
    assert (
        field_summary(fields["email"], page_number=1)
        == "Email address, email field, required, with an autofill hint, with help text, page 1"
    )
    assert field_summary(fields["how"]) == "How should we reply?, choose one, 2 choices"
    assert (
        field_summary(fields["country"])
        == "Country, drop-down list, choices from the Countries list"
    )
    assert field_summary(fields["x"]).startswith("Unknown, on or off field")


def test_outline_reads_rules_as_sentences() -> None:
    rows = outline(read_form(FORM))
    texts = [r.text for r in rows]
    assert texts[0] == "Page 1, 6 questions"
    assert texts[1] == "Section, About you, 6 questions"
    phone = next(t for t in texts if t.startswith("Phone number"))
    assert (
        phone
        == "Phone number, phone number field, with a format rule, shown when How should we reply? is By phone, page 1"  # noqa: E501
    )
    assert [r.level for r in rows][:3] == [0, 1, 2]


def test_island_and_comment_summaries() -> None:
    form = read_form("// keep me\n[columns 1/2 | 1/2]\n")
    rows = [r.text for r in outline(form)]
    assert rows[1] == "Comment: keep me"
    assert rows[2] == "Kept as written, not read by QUILL: [columns 1/2 | 1/2]"
    assert item_summary(form.pages[0].items[1]).startswith("Kept as written")
