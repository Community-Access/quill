"""Draft a Form, Plain Language, Suggest Autofill Hints, Summarise Responses (17a.9)."""

from __future__ import annotations

import json
from typing import Any

QAF = "/wp-json/qaf/v1"

DRAFT = """Here is your form:
```
bfl 1
form "Book club"

text #name "Your name"
  @required
email #email "Email"
```
"""


def test_draft_a_form_says_what_it_sends_and_proposes(fp, pub_dialogs, pub_host):
    pub_host.ai.service.answers.append(DRAFT)
    pub_dialogs.answer("ask_text", "A book club sign-up").answer("confirm", True)

    fp.cmd_draft_form()

    assert "sends your description, and nothing else" in pub_host.announced[0]
    assert pub_host.ai.service.requires == [("text",)]
    assert "A book club sign-up" in pub_host.ai.service.prompts[0]
    assert pub_dialogs.reports[0]["text"].startswith('bfl 1\nform "Book club"')
    assert pub_host.text.startswith('bfl 1\nform "Book club"')
    assert pub_host.replaced == 1


def test_draft_declined_changes_nothing(fp, pub_dialogs, pub_host):
    before = pub_host.text
    pub_host.ai.service.answers.append(DRAFT)
    pub_dialogs.answer("ask_text", "A book club sign-up")

    fp.cmd_draft_form()

    assert pub_dialogs.reports
    assert pub_host.text == before


def test_draft_outside_a_form_saves_a_new_one(fp, pub_dialogs, pub_host, tmp_path):
    pub_host.path = tmp_path / "notes.txt"
    pub_host.ai.service.answers.append(DRAFT)
    target = tmp_path / "club.qaf"
    pub_dialogs.answer("ask_text", "club").answer("confirm", True).answer("ask_save_path", target)

    fp.cmd_draft_form()

    assert target.read_text(encoding="utf-8").startswith("bfl 1")
    assert pub_host.opened == [target]


def test_draft_that_is_not_a_form_changes_nothing(fp, pub_dialogs, pub_host):
    before = pub_host.text
    pub_host.ai.service.answers.append("Sorry, I cannot help with that.")
    pub_dialogs.answer("ask_text", "anything")

    fp.cmd_draft_form()

    assert "could not be read as a form" in pub_host.said
    assert pub_host.text == before


def test_ai_is_off_in_safe_mode(fp, pub_dialogs, pub_host):
    pub_host.ai._safe_mode = True

    fp.cmd_draft_form()

    assert "off in Safe Mode" in pub_host.said
    assert not pub_host.ai.service.prompts


def test_ai_not_ready_sends_nothing(fp, pub_dialogs, pub_host):
    pub_host.ai.ready = False

    fp.cmd_plain_language()

    assert not pub_host.ai.service.prompts


def test_plain_language_proposes_then_applies_as_one_step(fp, pub_dialogs, pub_host):
    answer = {"heard": {"label": "Where did you hear about us?"}, "name": {"label": "Your name"}}
    pub_host.ai.service.answers.append(json.dumps(answer))
    pub_dialogs.answer("confirm", True)

    fp.cmd_plain_language()

    sent = pub_host.ai.service.prompts[0]
    assert "How did you hear about us?" in sent
    assert "No answers are sent." in pub_host.announced[0]
    assert "Plainer: Where did you hear about us?" in pub_dialogs.reports[0]["text"]
    assert 'radio #heard "Where did you hear about us?"' in pub_host.text
    assert pub_host.replaced == 1
    assert "1 rewordings applied" in pub_host.said


def test_plain_language_declined_changes_nothing(fp, pub_dialogs, pub_host):
    before = pub_host.text
    pub_host.ai.service.answers.append(json.dumps({"heard": {"label": "Where from?"}}))

    fp.cmd_plain_language()

    assert pub_host.text == before


def test_plain_language_answer_arriving_after_the_form_left_changes_nothing(
    fp, pub_dialogs, pub_host, tmp_path
):
    pub_dialogs.answer("confirm", True)

    def leave(*_a: Any, **kw: Any) -> None:
        pub_host.path = tmp_path / "other.qaf"
        kw["on_done"](json.dumps({"heard": {"label": "Where from?"}}), None)

    pub_host.ai.service.ask = leave  # type: ignore[method-assign]

    fp.cmd_plain_language()

    assert "no longer in front" in pub_host.said
    assert pub_host.replaced == 0


def test_suggest_autofill_sends_only_flagged_questions(fp, pub_dialogs, pub_host):
    pub_host.ai.service.answers.append(json.dumps({"phone": {"autocomplete": "tel"}}))
    pub_dialogs.answer("confirm", True)

    fp.cmd_suggest_autofill()

    sent = pub_host.ai.service.prompts[0]
    assert '"phone"' in sent and '"email"' not in sent
    assert '@autocomplete "tel"' in pub_host.text
    assert "1 suggestions applied" in pub_host.said


def test_suggest_autofill_rejects_card_and_made_up_tokens(fp, pub_dialogs, pub_host):
    pub_host.ai.service.answers.append(json.dumps({"phone": {"autocomplete": "cc-number"}}))

    fp.cmd_suggest_autofill()

    assert "nothing usable" in pub_host.said
    assert not pub_dialogs.asked("confirm")


def test_suggest_autofill_with_nothing_flagged_sends_nothing(fp, pub_host):
    pub_host.text = 'bfl 1\nform "F"\n\nemail #e "Email"\n  @autocomplete "email"\n'

    fp.cmd_suggest_autofill()

    assert "Nothing to suggest" in pub_host.said
    assert not pub_host.ai.service.prompts


def _responses_window(
    fp: Any, pub_dialogs: Any, pub_site: Any, make_form: Any, make_entry: Any
) -> None:
    pub_site.on("GET", f"{QAF}/forms", [make_form(12)])
    pub_site.on("GET", f"{QAF}/forms/12", make_form(12))
    pub_site.on(
        "GET",
        f"{QAF}/entries",
        [
            make_entry(2, "2026-11-03 10:00:00", name="Ann", city="Leeds"),
            make_entry(1, "2026-11-02 10:00:00", name="Bo"),
        ],
    )
    pub_dialogs.answer("ask_choice", 0)
    fp.cmd_form_responses()


def test_summarise_asks_every_time_with_the_count(
    fp, pub_dialogs, pub_site, pub_host, make_form, make_entry
):
    _responses_window(fp, pub_dialogs, pub_site, make_form, make_entry)
    pub_host.ai.service.answers.append("Two people replied.")
    pub_dialogs.answer("confirm", True)

    pub_dialogs.press("Summarise...")

    asked = pub_dialogs.asked("confirm")[0]
    assert asked["yes_label"] == "Send 2"
    assert "may include names" in asked["message"]
    assert "Your name: Ann" in pub_host.ai.service.prompts[0]
    assert pub_dialogs.reports[-1]["text"] == "Two people replied."

    pub_dialogs.press("Summarise...")
    assert len(pub_dialogs.asked("confirm")) == 2


def test_summarise_declined_sends_nothing(
    fp, pub_dialogs, pub_site, pub_host, make_form, make_entry
):
    _responses_window(fp, pub_dialogs, pub_site, make_form, make_entry)

    pub_dialogs.press("Summarise...")

    assert not pub_host.ai.service.prompts
