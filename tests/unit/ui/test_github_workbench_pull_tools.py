"""Open Patch in Editor, Revert Pull Request and Resolve Conflicts in a Worktree (GH-PT)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.github.items_provider import GitHubItem
from quill.ui import github_workbench_pull_tools as tools
from quill.ui.github_workbench_development import DEVELOPMENT_VERBS
from quill.ui.github_workbench_pull_tools import GitHubWorkbenchPullToolsMixin
from tests.unit.core.github_workbench.test_pull_tools import FakeApi


def _pull(**changes: Any) -> GitHubItem:
    fields: dict[str, Any] = {
        "number": 8,
        "title": "Add it",
        "state": "open",
        "url": "https://x/o/r/pull/8",
        "is_pr": True,
        "base_branch": "main",
    }
    fields.update(changes)
    return GitHubItem(**fields)


ISSUE = GitHubItem(number=7, title="An issue", state="open", url="u", is_pr=False)
REF = SimpleNamespace(instance="o/r")


class _Window(GitHubWorkbenchPullToolsMixin):
    signed_in = True

    def __init__(self, api: FakeApi, *, typed: str = "T", confirm: bool = False) -> None:
        self.api = api
        self.said: list[str] = []
        self.asked: list[tuple[str, str]] = []
        self.opened: list[Path] = []
        self.typed, self.confirm = typed, confirm
        self.frame = SimpleNamespace(reload=lambda: self.said.append("(reloaded)"))
        self._open_document = self.opened.append
        self.handed: list[tuple[Any, ...]] = []
        self.resolve_conflicts = lambda *args: self.handed.append(args)

    def github_api(self) -> Any:
        return self.api

    def _say(self, text: str) -> None:
        self.said.append(text)

    def _ask_text(self, title: str, prompt: str, **kw: Any) -> str:
        self.asked.append((title, kw.get("value", "")))
        return self.typed

    def _confirm(self, title: str, question: str) -> bool:
        self.asked.append((title, question))
        return self.confirm

    def _parent(self) -> str:
        return "PARENT"

    def _background(self, _name: str, work: Any, done: Any) -> None:
        done(work())


def test_the_verbs_are_rows_of_the_workbench() -> None:
    for verb in ("open_patch", "revert_pull", "resolve_conflicts"):
        assert verb in DEVELOPMENT_VERBS


def test_which_rows_each_fits() -> None:
    window = _Window(FakeApi())
    assert window._fits_open_patch(_pull()) and not window._fits_open_patch(ISSUE)
    assert window._fits_revert_pull(_pull(state="closed", is_merged=True))
    assert not window._fits_revert_pull(_pull())
    assert window._fits_resolve_conflicts(_pull())
    assert not window._fits_resolve_conflicts(_pull(state="closed"))
    window.resolve_conflicts = None
    assert not window._fits_resolve_conflicts(_pull())
    window.signed_in = False
    assert not window._fits_revert_pull(_pull(is_merged=True))


def test_open_patch_writes_the_diff_and_opens_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "quill.ui.github_workbench_reading.documents_folder", lambda: tmp_path / "docs"
    )
    api = FakeApi(files=[{"filename": "a.py", "status": "modified", "patch": "@@ -1 +1 @@"}])
    window = _Window(api)
    window._do_open_patch(REF, _pull())
    target = tmp_path / "docs" / "r-pr-8.diff"
    assert window.opened == [target]
    assert target.read_text(encoding="utf-8").startswith("diff --git a/a.py b/a.py\n")
    assert window.said == ["Opened the patch of #8. The patch has 1 file."]


def test_open_patch_without_an_editor_saves_and_says_where(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("quill.ui.github_workbench_reading.documents_folder", lambda: tmp_path)
    window = _Window(FakeApi(files=[{"filename": "x", "status": "modified", "patch": "@@"}]))
    window._open_document = None
    window._do_open_patch(REF, _pull())
    assert window.said[0].startswith("Saved the patch of #8 as ")


def test_a_pull_that_changes_nothing_says_so() -> None:
    window = _Window(FakeApi())
    window._do_open_patch(REF, _pull())
    assert window.said == ["#8 changes no files."] and window.opened == []


def test_revert_asks_title_and_draft_then_opens_it() -> None:
    api = FakeApi(pull={"node_id": "PR_8", "merged": True, "title": "Add it"})
    window = _Window(api, typed="Revert the parser", confirm=True)
    window._do_revert_pull(REF, _pull(state="closed", is_merged=True))
    assert window.asked[0] == ("Revert Pull Request", 'Revert "Add it"')
    assert "draft" in window.asked[1][1] and "on main" in window.asked[1][1]
    sent = api.calls[-1][2]
    assert sent["title"] == "Revert the parser" and sent["draft"] is True
    assert window.said == ["Opened draft pull request #99, which reverts #8.", "(reloaded)"]


def test_revert_cancelled_at_the_title_sends_nothing() -> None:
    api = FakeApi(pull={"node_id": "PR_8", "merged": True})
    window = _Window(api, typed="")
    window._do_revert_pull(REF, _pull(is_merged=True))
    assert api.calls == [] and window.said == []


def test_resolve_conflicts_hands_the_branches_to_the_editor() -> None:
    pull = {"head": {"ref": "feature", "repo": {"full_name": "O/R"}}, "base": {"ref": "main"}}
    window = _Window(FakeApi(pull=pull))
    window._do_resolve_conflicts(REF, _pull())
    assert window.handed == [("PARENT", "o/r", 8, "feature", "main")]


def test_resolve_conflicts_on_a_fork_says_why_not() -> None:
    pull = {"head": {"ref": "f", "repo": {"full_name": "me/r"}}, "base": {"ref": "main"}}
    window = _Window(FakeApi(pull=pull))
    window._do_resolve_conflicts(REF, _pull())
    assert window.handed == [] and "comes from me/r" in window.said[0]
    gone = _Window(FakeApi(pull={"head": {"ref": "f", "repo": None}, "base": {"ref": "m"}}))
    gone._do_resolve_conflicts(REF, _pull())
    assert "a fork that no longer exists" in gone.said[0]


def test_every_verb_has_a_reason() -> None:
    assert set(tools.PULL_TOOL_REASONS) == set(tools.PULL_TOOL_VERBS)
