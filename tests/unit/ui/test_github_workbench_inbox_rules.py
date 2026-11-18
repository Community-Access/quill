"""Item > Inbox Rules...: list, make and delete rules (GitHub PRD 22.12)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.github import inbox_rules
from quill.core.github.explore_models import ExploreRow
from quill.core.github.inbox_rules import InboxRule
from quill.ui.github_workbench_development import DEVELOPMENT_VERBS
from quill.ui.github_workbench_inbox_rules import GitHubWorkbenchInboxRulesMixin
from tests.unit.core.github_workbench.test_inbox_rules import NOTES


class _Window(GitHubWorkbenchInboxRulesMixin):
    signed_in = True

    def __init__(self, choices: list[int], texts: list[str], yes: bool = True) -> None:
        self.choices, self.texts, self.yes = choices, texts, yes
        self.said: list[str] = []
        self.asked: list[tuple[str, Any]] = []
        row = ExploreRow("x", "y", "", "octo/app", "notification", "1")
        self.frame = SimpleNamespace(selected_row=lambda: row)

    def _explore_client(self) -> Any:
        return SimpleNamespace(loaded_notifications=lambda: NOTES)

    def _say(self, text: str) -> None:
        self.said.append(text)

    def _choose(self, title: str, prompt: str, labels: list[str]) -> int:
        self.asked.append(("choose", labels))
        return self.choices.pop(0)

    def _ask_text(self, title: str, prompt: str, **kw: Any) -> str:
        self.asked.append(("text", kw.get("value", "")))
        return self.texts.pop(0)

    def _confirm(self, title: str, question: str) -> bool:
        self.asked.append(("confirm", question))
        return self.yes


@pytest.fixture
def path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    target = tmp_path / "rules.json"
    monkeypatch.setattr(inbox_rules, "rules_path", lambda: target)
    return target


def test_registered() -> None:
    assert "inbox_rules" in DEVELOPMENT_VERBS


def test_a_new_rule_is_asked_previewed_and_saved(path: Path) -> None:
    # New Rule..., Mark it done, repository, Any reason, Pull request, words
    window = _Window([0, 0, 0, 1], ["octo/*", "Bump"])
    window._do_inbox_rules(None, None)
    assert window.asked[0] == ("choose", ["New Rule..."])
    assert window.asked[2] == ("text", "octo/app")  # the selected notification's repository
    preview = window.asked[-1][1]
    assert "When a notification is from octo/*, about a pull request" in preview
    assert "It matches 1 of the 4 notifications loaded today" in preview
    assert inbox_rules.load_rules(path) == [
        InboxRule("mark_done", repository="octo/*", subject="PullRequest", title_contains="Bump")
    ]
    assert window.said[-1].startswith("Saved. When a notification")


def test_a_rule_with_no_condition_is_refused(path: Path) -> None:
    window = _Window([0, 1, 0, 0], ["", ""])
    window._do_inbox_rules(None, None)
    assert "nothing was saved" in window.said[-1]
    assert not path.exists()


def test_no_at_the_preview_saves_nothing(path: Path) -> None:
    window = _Window([0, 2, 0, 0], ["octo/*", ""], yes=False)
    window._do_inbox_rules(None, None)
    assert not path.exists() and window.said == []


def test_choosing_a_rule_deletes_it_after_asking(path: Path) -> None:
    rules = [InboxRule("mark_done", repository="a/*"), InboxRule("to_top", reason="mention")]
    inbox_rules.save_rules(rules, path)
    window = _Window([1], [])
    window._do_inbox_rules(None, None)
    assert window.asked[0][1][:2] == [rule.sentence for rule in rules]
    assert "Delete this rule? When a notification is because" in window.asked[1][1]
    assert inbox_rules.load_rules(path) == rules[:1]
    assert window.said == ["Deleted the rule."]
