"""Issue Fields... and Delete Issue... on an issue's row."""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.github import issue_admin
from quill.core.github.across_issue_fields import FieldValue
from quill.core.github.items_provider import GitHubItem
from quill.ui.github_workbench_issue_admin import GitHubWorkbenchIssueAdminMixin

ISSUE = GitHubItem(number=4, title="Fix it", state="open", url="u", is_pr=False)


class _Host(GitHubWorkbenchIssueAdminMixin):
    def __init__(self, answers: list[Any]) -> None:
        self.answers, self.said, self.signed_in = answers, [], True
        self.frame = type("F", (), {"reload": lambda self: None})()
        self._say = self.said.append  # type: ignore[assignment]
        self._background = lambda _w, work, done: done(work())  # type: ignore[assignment]
        self._choose = lambda *a, **k: self.answers.pop(0)  # type: ignore[assignment]
        self._ask_text = lambda *a, **k: self.answers.pop(0)  # type: ignore[assignment]
        self._repo_for = lambda _ref: "acme/site"  # type: ignore[assignment]

    def github_api(self) -> Any:
        return object()


def test_delete_needs_the_number_typed(monkeypatch: pytest.MonkeyPatch) -> None:
    deleted: list[int] = []
    monkeypatch.setattr(
        issue_admin, "delete_issue", lambda _a, _r, n: deleted.append(n) or f"#{n} gone."
    )
    host = _Host(["5"])
    host._do_delete_issue(None, ISSUE)
    assert deleted == [] and "nothing was deleted" in host.said[-1]
    host = _Host([""])
    host._do_delete_issue(None, ISSUE)
    assert deleted == [] and host.said == []
    host = _Host(["#4"])
    host._do_delete_issue(None, ISSUE)
    assert deleted == [4]


def test_cancelling_never_clears_a_field(monkeypatch: pytest.MonkeyPatch) -> None:
    due = FieldValue("2", "Due", "date", "value", ("2026-12-01",))
    found = issue_admin.IssueFields((due,), {})
    calls: list[str] = []
    monkeypatch.setattr(issue_admin, "read_issue_fields", lambda *_a: found)
    monkeypatch.setattr(
        issue_admin, "clear_field_value", lambda *_a: calls.append("clear") or "cleared"
    )
    monkeypatch.setattr(issue_admin, "set_field_value", lambda *_a: calls.append("set") or "set")
    _Host([0, 0, ""])._do_issue_fields(None, ISSUE)  # field, Change it..., then Cancel
    assert calls == []
    _Host([0, 1])._do_issue_fields(None, ISSUE)  # field, Clear it
    assert calls == ["clear"]
    _Host([0, 0, "2026-12-31"])._do_issue_fields(None, ISSUE)
    assert calls == ["clear", "set"]
