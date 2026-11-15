"""YAML issue forms: read, validate and write the body GitHub's form would (issue_forms.py)."""

from __future__ import annotations

from quill.core.github.issue_forms import parse_issue_form, render_body, validate

BUG_FORM = """
name: Bug report
description: Something is broken
title: "[Bug]: "
labels: ["bug", "triage"]
assignees:
  - octocat
body:
  - type: markdown
    attributes:
      value: Thanks for taking the time.
  - type: input
    id: version
    attributes:
      label: Version
      placeholder: 1.2.3
    validations:
      required: true
  - type: textarea
    id: what
    attributes:
      label: What happened?
  - type: textarea
    id: logs
    attributes:
      label: Logs
      render: shell
  - type: dropdown
    id: os
    attributes:
      label: Operating system
      multiple: true
      options: [Windows, macOS]
  - type: checkboxes
    id: terms
    attributes:
      label: Code of Conduct
      options:
        - label: I agree to follow this project's Code of Conduct
          required: true
        - label: I searched for duplicates
"""


def test_the_form_reads_with_every_element_kind() -> None:
    form = parse_issue_form(BUG_FORM, "bug.yml")
    assert form.unsupported == ""
    assert (form.name, form.title, form.labels, form.assignees) == (
        "Bug report",
        "[Bug]: ",
        ("bug", "triage"),
        ("octocat",),
    )
    assert [f.kind for f in form.fields] == [
        "markdown",
        "input",
        "textarea",
        "textarea",
        "dropdown",
        "checkboxes",
    ]
    assert form.fields[4].multiple and form.fields[4].options == ("Windows", "macOS")


def test_required_answers_are_named() -> None:
    form = parse_issue_form(BUG_FORM)
    missing = validate(form, {})
    assert missing == [
        "Version is required.",
        'Code of Conduct: check "I agree to follow this project\'s Code of Conduct".',
    ]
    assert validate(form, {"version": "2.0", "terms": [True, False]}) == []


def test_the_body_matches_githubs_own_form_output() -> None:
    form = parse_issue_form(BUG_FORM)
    body = render_body(
        form,
        {
            "version": "2.0",
            "what": "It crashed.",
            "logs": "Traceback",
            "os": ["Windows"],
            "terms": [True, False],
        },
    )
    assert body == (
        "### Version\n\n2.0\n\n"
        "### What happened?\n\nIt crashed.\n\n"
        "### Logs\n\n```shell\nTraceback\n```\n\n"
        "### Operating system\n\nWindows\n\n"
        "### Code of Conduct\n\n"
        "- [X] I agree to follow this project's Code of Conduct\n"
        "- [ ] I searched for duplicates"
    )


def test_an_empty_optional_answer_says_no_response() -> None:
    form = parse_issue_form(BUG_FORM)
    body = render_body(form, {"version": "1"})
    assert "### What happened?\n\n_No response_" in body
    assert "### Logs\n\n_No response_" in body


def test_what_quill_cannot_fill_says_why_rather_than_guessing() -> None:
    assert "not valid YAML" in parse_issue_form("body: [", "x.yml").unsupported
    assert "no body" in parse_issue_form("name: Empty\n").unsupported
    odd = parse_issue_form("body:\n  - type: slider\n    attributes: {label: Volume}\n")
    assert "type QUILL does not know (slider)" in odd.unsupported
    dup = parse_issue_form(
        "body:\n"
        "  - {type: input, id: a, attributes: {label: A}}\n"
        "  - {type: input, id: a, attributes: {label: B}}\n"
    )
    assert "share the id 'a'" in dup.unsupported


def test_listing_reads_yaml_forms_so_quill_can_fill_them() -> None:
    from types import SimpleNamespace

    from quill.core.github.issue_templates import list_issue_templates

    def entry(name: str, text: str, size: int = 0) -> SimpleNamespace:
        return SimpleNamespace(
            type="file",
            name=name,
            html_url=f"https://github.com/o/r/blob/main/.github/ISSUE_TEMPLATE/{name}",
            size=size or len(text),
            decoded_content=text.encode(),
        )

    class _Repo:
        def get_contents(self, _path: str) -> list[SimpleNamespace]:
            return [
                entry("bug.yml", BUG_FORM),
                entry("odd.yml", "body:\n  - type: slider\n    attributes: {label: V}\n"),
                entry("huge.yml", "", size=60_000),
                entry("config.yml", "blank_issues_enabled: false"),
            ]

    bug, odd, huge = list_issue_templates(_Repo())
    assert bug.supported and bug.form is not None and bug.name == "Bug report"
    assert bug.labels == ("bug", "triage") and bug.title == "[Bug]: "
    assert not odd.supported and "slider" in odd.about
    assert not huge.supported and huge.body_truncated
