"""Roles in, and Rulesets in, an organization: the windows' behaviour."""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.github.org_admin import Holder, Role, RulesetRow

wx = pytest.importorskip("wx")

from quill.ui import github_org_admin_dialog as mod  # noqa: E402

ROLE = Role(8, "all_repo_write")
RULES = RulesetRow(5, "Protect main", "branch", "active")


class _Api:
    def __init__(self) -> None:
        self.calls: list[tuple[Any, ...]] = []
        self.people = [Holder("person", "jeff"), Holder("person", "kim", "indirect", ("docs",))]

    def holders(self, _org: str, _role: Role) -> list[Holder]:
        return list(self.people)

    def assign(self, *a: Any) -> None:
        self.calls.append(("assign", *a))

    def unassign(self, *a: Any) -> None:
        self.calls.append(("unassign", *a))

    def unassign_all(self, *a: Any) -> None:
        self.calls.append(("unassign_all", *a))

    def ruleset_summary(self, *_a: Any) -> str:
        return "On the default branch: deletions are blocked"

    def rulesets(self, _org: str) -> list[RulesetRow]:
        return [RULES]

    def set_enforcement(self, *a: Any) -> None:
        self.calls.append(("enforce", *a))

    def delete_ruleset(self, *a: Any) -> None:
        self.calls.append(("delete", *a))

    def history(self, *_a: Any) -> list[str]:
        return ["Version 1"]

    def insights(self, *_a: Any) -> list[str]:
        return []


@pytest.fixture(autouse=True)
def _inline(monkeypatch: pytest.MonkeyPatch) -> None:
    def run(self: Any, _doing: str, work: Any, done: Any) -> None:
        self._done(work(), done)

    monkeypatch.setattr(mod._OrgWindow, "_run", run)


def test_roles_window_gives_and_takes_and_refuses_an_inherited_one(wx_session_app: Any) -> None:
    api, said = _Api(), []
    answers: list[Any] = ["sam", 0]
    win = mod.OrgRolesDialog(
        None,
        api,
        org="acme",
        roles=[ROLE],
        announce_cb=said.append,
        ask_text=lambda *_a: answers.pop(0),
        choose=lambda *_a: answers.pop(0),
    )
    try:
        assert win._holder_list.GetStrings() == ["Person: jeff", "Person: kim, through docs"]
        win.give("person")
        assert api.calls[-1] == ("assign", "acme", "person", "sam", ROLE)
        assert said[-1] == "sam now has all_repo_write."
        win._holder_list.SetSelection(1)
        win.take_away()
        assert "take it from that team" in said[-1]
        win._holder_list.SetSelection(0)
        win.take_away()
        assert api.calls[-1] == ("unassign", "acme", "person", "jeff", ROLE)
    finally:
        win.dialog.Destroy()


def test_rulesets_window_reads_enforces_and_deletes_only_with_the_name(wx_session_app: Any) -> None:
    api, said = _Api(), []
    answers: list[Any] = [1, "protect main", "Protect main"]
    win = mod.OrgRulesetsDialog(
        None,
        api,
        org="acme",
        rulesets=[RULES],
        announce_cb=said.append,
        ask_text=lambda *_a: answers.pop(0),
        choose=lambda *_a: answers.pop(0),
    )
    try:
        assert win._details.GetStrings() == ["On the default branch: deletions are blocked"]
        win.change_enforcement()
        assert api.calls[-1] == ("enforce", "acme", RULES, "evaluate")
        assert said[-1] == "Protect main is now Evaluate."
        win.delete_selected()
        assert not [c for c in api.calls if c[0] == "delete"]
        win.delete_selected()
        assert api.calls[-1] == ("delete", "acme", RULES)
    finally:
        win.dialog.Destroy()
