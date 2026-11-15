"""The issue-form window: labelled controls, required answers, GitHub's body (issue_forms.py)."""

from __future__ import annotations

from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.github.issue_forms import parse_issue_form  # noqa: E402
from quill.ui.github_issue_form_dialog import IssueFormDialog  # noqa: E402

FORM = """
name: Bug report
title: "[Bug]: "
body:
  - type: markdown
    attributes: {value: Thanks.}
  - type: input
    id: version
    attributes: {label: Version, description: Which build}
    validations: {required: true}
  - type: dropdown
    id: os
    attributes: {label: OS, options: [Windows, macOS]}
  - type: checkboxes
    id: terms
    attributes:
      label: Conduct
      options:
        - {label: I agree, required: true}
"""


class _Event:
    skipped = False

    def Skip(self) -> None:  # noqa: N802 - wx's name
        self.skipped = True


@pytest.fixture
def form_window(wx_session_app):
    from quill.ui.app_context_help import ensure_help_provider

    ensure_help_provider(wx)  # SetHelpText stores nothing without one
    said: list[str] = []
    window = IssueFormDialog(None, parse_issue_form(FORM), repository="o/r", announce=said.append)
    window.said = said  # type: ignore[attr-defined]
    yield window
    window.dialog.Destroy()


def test_required_fields_say_so_in_their_names(form_window) -> None:
    controls: Any = form_window._controls
    assert controls["version"].GetName() == "Version (required)"
    assert controls["version"].GetHelpText() == "Which build"
    assert controls["os"].GetString(0) == "(none)"
    assert controls["terms"][0].GetLabel() == "I agree (required)"


def test_a_missing_answer_is_said_once_and_nothing_is_returned(form_window) -> None:
    event = _Event()
    form_window._on_create(event)
    assert not event.skipped and form_window.result is None
    assert form_window.said == ["Version is required."]


def test_complete_answers_give_githubs_body(form_window) -> None:
    controls: Any = form_window._controls
    controls["version"].SetValue("2.0")
    controls["os"].SetStringSelection("macOS")
    controls["terms"][0].SetValue(True)
    event = _Event()
    form_window._on_create(event)
    assert event.skipped
    title, body = form_window.result
    assert title == "[Bug]:"
    assert body == "### Version\n\n2.0\n\n### OS\n\nmacOS\n\n### Conduct\n\n- [X] I agree"
