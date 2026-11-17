"""Save As GitHub Issue Form and Open GitHub Issue Form (GitHub PRD 21.4, GH-R-072).

The shared Forms commands both editors reach, on the harness the exports use:
a form document in front (``pub_host``), every dialog scripted
(``pub_dialogs``), and unscripted questions answering cancel.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

ISSUE_FORM = """name: Bug report
description: Something is broken.
title: "[Bug]: "
labels: [bug]
body:
  - type: input
    id: app-version
    attributes:
      label: Version
    validations:
      required: true
  - type: textarea
    id: what
    attributes:
      label: What happened?
"""


@pytest.fixture
def commands(pub_host: Any, pub_dialogs: Any) -> Any:
    from quill.ui.forms_commands import FormsCommands

    return FormsCommands(pub_host)


@pytest.fixture
def pick(monkeypatch: pytest.MonkeyPatch, pub_dialogs: Any) -> Any:
    from quill.ui import wordpress_route_dialogs as rdlg

    pub_dialogs.CANCEL = {**pub_dialogs.CANCEL, "pick_file": None}
    monkeypatch.setattr(rdlg, "pick_file", pub_dialogs.entry("pick_file"))
    return pub_dialogs


def test_save_as_issue_form_lists_what_changes_then_saves(
    commands, pub_dialogs, pub_host, tmp_path
) -> None:
    pub_dialogs.answer("save_as", tmp_path / "fair")

    commands.cmd_save_github_issue_form()

    data = yaml.safe_load((tmp_path / "fair.yml").read_text(encoding="utf-8"))
    assert data["name"] == "Spring fair"
    labels = [f["attributes"]["label"] for f in data["body"]]
    assert labels == [
        "Your name",
        "Email address",
        "Phone",
        "How did you hear about us?",
        "Anything else?",
    ]
    report = pub_dialogs.reports[0]
    assert report["title"] == "Save As GitHub Issue Form: what changes"
    assert "becomes a drop-down list" in report["text"]
    assert (
        "Saved fair.yml, a GitHub issue form with 5 questions; 1 change was listed before saving"
        in pub_host.said
    )


def test_save_as_issue_form_cancelled_writes_nothing(commands, pub_dialogs, tmp_path) -> None:
    commands.cmd_save_github_issue_form()

    assert pub_dialogs.asked("save_as")
    assert not list(tmp_path.glob("*.yml"))


def test_save_as_issue_form_says_when_github_would_refuse_it(
    commands, pub_dialogs, pub_host, tmp_path
) -> None:
    pub_host.text = 'bfl 1\nform "Twice"\n\ntext #a "Same"\ntext #b "Same"\n'
    pub_dialogs.answer("save_as", tmp_path / "twice.yml")

    commands.cmd_save_github_issue_form()

    assert (tmp_path / "twice.yml").exists()
    assert "GitHub will refuse it until" in pub_host.said


def test_save_as_issue_form_needs_a_form_in_front(commands, pub_dialogs, pub_host) -> None:
    pub_host.path = Path("notes.txt")

    commands.cmd_save_github_issue_form()

    assert "works in a form document" in pub_host.said
    assert not pub_dialogs.asked("save_as")


def test_open_issue_form_saves_it_as_a_form_and_opens_it(
    commands, pick, pub_host, tmp_path
) -> None:
    source = tmp_path / "bug.yml"
    source.write_text(ISSUE_FORM, encoding="utf-8")
    pick.answer("pick_file", source).answer("ask_save_path", tmp_path / "bug.qaf")

    commands.cmd_open_github_issue_form()

    text = (tmp_path / "bug.qaf").read_text(encoding="utf-8")
    assert text.startswith("bfl 1\n") and 'text #app_version "Version"' in text
    assert "@extensions" in text
    assert pub_host.opened == [tmp_path / "bug.qaf"]
    assert pick.asked("ask_save_path")[0]["suggested"] == "Bug report"
    assert (
        "Saved bug.qaf, bug.yml as a form with 2 questions. "
        "Kept for saving back to GitHub: labels, title." in pub_host.said
    )


def test_open_then_save_gives_github_back_its_form(commands, pick, pub_host, tmp_path) -> None:
    source = tmp_path / "bug.yml"
    source.write_text(ISSUE_FORM, encoding="utf-8")
    pick.answer("pick_file", source).answer("ask_save_path", tmp_path / "bug.qaf")
    commands.cmd_open_github_issue_form()
    pub_host.path = tmp_path / "bug.qaf"
    pub_host.text = pub_host.path.read_text(encoding="utf-8")
    pick.answer("save_as", tmp_path / "again.yml")

    commands.cmd_save_github_issue_form()

    again = yaml.safe_load((tmp_path / "again.yml").read_text(encoding="utf-8"))
    assert again == yaml.safe_load(ISSUE_FORM)
    assert not pick.reports


def test_open_issue_form_refuses_yaml_that_is_not_a_form(commands, pick, pub_host, tmp_path):
    source = tmp_path / "ci.yml"
    source.write_text("on: [push]\nbody: 3\n", encoding="utf-8")
    pick.answer("pick_file", source)

    commands.cmd_open_github_issue_form()

    assert "ci.yml is not a GitHub form QUILL can read" in pub_host.said
    assert not pick.asked("ask_save_path")


def test_open_issue_form_cancelled_does_nothing(commands, pick, pub_host) -> None:
    commands.cmd_open_github_issue_form()

    assert pick.asked("pick_file") and not pub_host.opened and not pub_host.announced


def test_a_discussion_form_is_read_as_one() -> None:
    from quill.ui.forms_github_commands import form_kind

    assert form_kind(Path("repo/.github/DISCUSSION_TEMPLATE/ideas.yml")) == "discussion_form"
    assert form_kind(Path("repo/.github/ISSUE_TEMPLATE/bug.yml")) == "issue_form"
