"""GitHub issue forms to and from the form language (GitHub PRD 21.4, GH-R-072).

The round trip is checked against real forms: QUILL's own issue templates,
read into the model, written as BFL, read back and saved as YAML, must come
out as the same form GitHub reads. Nothing a GitHub form has may be lost on
the way, and nothing the form language has may be dropped without a sentence.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from quill.core.forms import model as M
from quill.core.forms.bfl_read import to_model
from quill.core.forms.bfl_write import to_bfl
from quill.core.forms.errors import FormImportError
from quill.core.forms.interop_github import (
    export_github_draft,
    export_github_issue_form,
    import_github_issue_form,
)

ROOT = Path(__file__).resolve().parents[4]
REAL_FORMS = sorted(
    p for p in (ROOT / ".github" / "ISSUE_TEMPLATE").glob("*.yml") if p.name != "config.yml"
)


def _through_bfl(text: str) -> str:
    imported = import_github_issue_form(text)
    assert M.validate(imported.model) == []
    out, report = export_github_issue_form(to_model(to_bfl(imported.model)))
    assert report == []
    return out


def test_there_are_real_forms_to_check() -> None:
    assert len(REAL_FORMS) >= 5


@pytest.mark.parametrize("path", REAL_FORMS, ids=lambda p: p.name)
def test_a_real_issue_form_survives_bfl_and_back(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    assert yaml.safe_load(_through_bfl(text)) == yaml.safe_load(text)


def test_an_issue_form_reads_as_the_form_language() -> None:
    text = """name: Bug report
description: Something is broken.
title: "[Bug]: "
labels: [bug, triage]
body:
  - type: markdown
    attributes:
      value: Thanks for **reporting**.
  - type: input
    id: app-version
    attributes:
      label: Version
      placeholder: "1.2.3"
    validations:
      required: true
  - type: textarea
    id: logs
    attributes:
      label: Log output
      render: shell
  - type: dropdown
    id: os
    attributes:
      label: System
      options: [Windows 11, Windows 10]
      default: 1
  - type: checkboxes
    id: terms
    attributes:
      label: Code of Conduct
      options:
        - label: I agree
          required: true
"""
    imported = import_github_issue_form(text)
    bfl = to_bfl(imported.model)
    assert 'form "Bug report"' in bfl
    assert 'text #app_version "Version"' in bfl
    assert 'textarea #logs "Log output"' in bfl
    assert 'select #os "System"' in bfl
    assert 'checkbox #terms "Code of Conduct"' in bfl
    assert "@html" in bfl and "@extensions" in bfl
    assert imported.model["pages"][0]["items"][3]["default"] == "windows-10"
    assert imported.report == ["Kept for saving back to GitHub: labels, title."]
    kept = imported.model["extensions"]["github"]
    assert kept["form"] == {"title": "[Bug]: ", "labels": ["bug", "triage"]}
    assert kept["fields"]["app_version"] == {"id": "app-version"}
    assert kept["fields"]["logs"] == {"attributes": {"render": "shell"}}
    assert yaml.safe_load(_through_bfl(text)) == yaml.safe_load(text)


def test_check_boxes_where_only_some_must_be_checked_say_so_and_come_back() -> None:
    text = """name: Pick
description: d
body:
  - type: checkboxes
    id: checks
    attributes:
      label: Before you send
      options:
        - label: I searched
          required: true
        - label: I would like to help
"""
    imported = import_github_issue_form(text)
    assert any("only I searched must be checked" in line for line in imported.report)
    assert yaml.safe_load(_through_bfl(text)) == yaml.safe_load(text)


def test_a_field_with_no_id_and_an_explicit_not_required_come_back_as_they_were() -> None:
    text = """name: N
description: d
body:
  - type: textarea
    attributes:
      label: Details
    validations:
      required: false
"""
    assert yaml.safe_load(_through_bfl(text)) == yaml.safe_load(text)


def test_an_edit_in_the_form_language_reaches_github() -> None:
    path = next(p for p in REAL_FORMS if p.name == "bug_report.yml")
    imported = import_github_issue_form(path.read_text(encoding="utf-8"))
    bfl = to_bfl(imported.model).replace('form "Bug report"', 'form "Bug report, edited"')
    out = yaml.safe_load(export_github_issue_form(to_model(bfl))[0])
    assert out["name"] == "Bug report, edited"
    assert out["labels"] == ["bug"]


def test_a_discussion_form_stays_a_discussion_form() -> None:
    text = "body:\n  - type: textarea\n    id: idea\n    attributes:\n      label: Idea\n"
    imported = import_github_issue_form(text, kind="discussion_form")
    draft, report = export_github_draft(to_model(to_bfl(imported.model)))
    assert draft.kind == "discussion_form" and "name" not in draft.top
    assert report == []


def test_an_element_github_does_not_have_is_named_and_left_out() -> None:
    text = (
        "name: N\ndescription: d\nbody:\n  - type: slider\n    id: s\n"
        "  - type: input\n    id: a\n    attributes: {label: A}\n"
    )
    imported = import_github_issue_form(text)
    assert [i["id"] for i in imported.model["pages"][0]["items"]] == ["a"]
    assert any("'slider'" in line and "left out" in line for line in imported.report)


def test_yaml_that_is_not_a_form_is_refused_with_the_reason() -> None:
    with pytest.raises(FormImportError, match="not valid YAML"):
        import_github_issue_form("name: [unclosed")
    with pytest.raises(FormImportError, match="body is not a list"):
        import_github_issue_form("name: N\nbody: nope\n")


FULL = """bfl 1
form "Signup"
  @description "Join the club."

page #one "About you"
text #name "Your name"
  @required
radio #size "T-shirt"
  + Small
  + Large
number #age "Age"
  @min 18
  @when name != ""
signature #sig "Sign here"

page #two "More"
checkbox #ok "Agreed"
  @required
  + yes|Yes
"""


def test_a_form_written_in_bfl_says_everything_github_cannot_hold() -> None:
    out, report = export_github_issue_form(to_model(FULL))
    data = yaml.safe_load(out)
    assert data["name"] == "Signup" and data["description"] == "Join the club."
    kinds = [(f["type"], f.get("attributes", {}).get("label")) for f in data["body"]]
    assert kinds == [
        ("input", "Your name"),
        ("dropdown", "T-shirt"),
        ("input", "Age"),
        ("checkboxes", "Agreed"),
    ]
    assert data["body"][0]["validations"] == {"required": True}
    assert data["body"][3]["attributes"]["options"] == [{"label": "Yes", "required": True}]
    text = "\n".join(report)
    assert "T-shirt: becomes a drop-down list" in text
    assert "Age: its condition is left out" in text
    assert "Age: its limits" in text
    assert "Sign here: GitHub forms have no signature field; left out." in text
    assert "2 pages become one page" in text
    assert "GitHub will refuse" not in text


def test_a_form_github_would_refuse_says_so() -> None:
    model = M.create("")
    model["pages"][0]["items"] = [
        {"id": "a", "type": "text", "label": "Same"},
        {"id": "b", "type": "text", "label": "Same"},
    ]
    _out, report = export_github_issue_form(model)
    assert any(line.startswith("GitHub will refuse this: ") for line in report)


def test_a_form_with_no_questions_gets_a_details_box_and_says_so() -> None:
    model = M.create("Note")
    model["pages"][0]["items"] = [{"id": "intro", "type": "html", "props": {"html": "Hi"}}]
    draft, report = export_github_draft(model)
    assert [f["type"] for f in draft.fields] == ["markdown", "textarea"]
    assert draft.fields[0]["attributes"]["value"] == "Hi"
    assert any("Details box was added" in line for line in report)


def test_template_convert_uses_this_export() -> None:
    from quill.core.github.template_convert import qaf_to_draft

    model = to_model(FULL)
    assert qaf_to_draft(model)[0].fields == export_github_draft(model)[0].fields
