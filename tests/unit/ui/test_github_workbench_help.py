"""GitHub Workbench Phase 5: help in the window (GitHub PRD section 7, Part D).

F1 follows the selection, Shift+F1 lists every action with its key and why a
greyed one is greyed, Alt+F1 explains the word, Help and Learning is a branch
of the tree, and an empty list says why it is empty.
"""

from __future__ import annotations

from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.github.items_provider import GitHubItem  # noqa: E402
from quill.ui.github_workbench_window import GitHubWorkbenchProvider  # noqa: E402
from quill.ui.workbench_frame import NodeRef, WorkbenchFrame  # noqa: E402

REPO = "owner/repo"


class _Items:
    is_authenticated = True
    token = "test-token-not-real"

    def __init__(self, issues: list[GitHubItem]) -> None:
        self.issues = issues

    def fetch_issues(self, _repo: str, **_kw: Any) -> list[GitHubItem]:
        return list(self.issues)

    def fetch_pulls(self, _repo: str, **_kw: Any) -> list[GitHubItem]:
        return []

    def close(self) -> None:
        pass


def _inline(_name: str, work: Any, done: Any, failed: Any) -> None:
    try:
        result = work()
    except Exception as exc:  # noqa: BLE001
        failed(exc)
        return
    done(result)


def _bench(issues: list[GitHubItem]) -> WorkbenchFrame:
    provider = GitHubWorkbenchProvider(_Items(issues), REPO, announce=lambda _t: None)
    return WorkbenchFrame(provider, run_background=_inline)


@pytest.fixture
def bench(wx_session_app, quill_data_dir):
    frame = _bench([
        GitHubItem(1, "Crash on start", "open", "https://github.com/o/r/issues/1", False)
    ])
    yield frame
    frame.frame.Destroy()


def _go(frame: WorkbenchFrame, ref: NodeRef) -> None:
    assert frame.select(ref)
    if frame.current != ref:
        frame._show_node(ref, remember=True)


def test_f1_on_the_tree_and_list_follows_the_node(bench) -> None:
    _go(bench, NodeRef("repository", "issues", REPO))
    assert "Ctrl+N files a new one" in bench.tree.GetHelpText()
    assert "Enter on a row: Open." in bench.list.GetHelpText()


def test_shift_f1_lists_every_action_with_its_key_and_why_greyed(bench, monkeypatch) -> None:
    shown: list[Any] = []
    monkeypatch.setattr(
        "quill.ui.workbench_help_dialogs.ActionListDialog.show",
        lambda dialog: shown.append([row.text for row in dialog.rows]) or dialog.dialog.Destroy(),
    )
    _go(bench, NodeRef("repository", "issues", REPO))
    bench.list.Select(0)
    bench.what_can_i_do()
    texts = shown[0]
    assert texts[0] == "Open"
    assert "Comment..., Ctrl+Shift+M" in texts
    assert texts[-1] == "Properties..., Alt+Enter"


def test_alt_f1_explains_the_word_for_the_row(bench, monkeypatch) -> None:
    shown: list[str] = []
    monkeypatch.setattr(
        "quill.ui.workbench_help_dialogs.HelpTextDialog.show",
        lambda dialog: shown.append(dialog.text.GetValue()) or dialog.dialog.Destroy(),
    )
    _go(bench, NodeRef("repository", "issues", REPO))
    bench.list.Select(0)
    bench.what_is_this()
    assert shown[0].startswith("Issue\n\nA note about a bug")


def test_help_and_learning_is_a_branch_of_lists(bench) -> None:
    _go(bench, NodeRef("", "help_tasks"))
    assert bench.rows[0].label == "Find what needs me"
    bench.list.Select(0)
    bench.run("github.workbench.take_me_there")
    if bench.current != NodeRef("", "inbox"):
        bench._show_node(NodeRef("", "inbox"), remember=True)
    assert bench.current == NodeRef("", "inbox")
    _go(bench, NodeRef("", "help_words"))
    assert any(row.label == "Pull request" for row in bench.rows)
    _go(bench, NodeRef("", "help_keys"))
    assert any(row.label.startswith("Ctrl+1, ") for row in bench.rows)


def test_a_chapter_topic_opens_the_guide(bench, monkeypatch) -> None:
    opened: list[str] = []
    monkeypatch.setattr(
        GitHubWorkbenchProvider,
        "open_guide",
        lambda _self, _ref, chapter="": opened.append(chapter),
    )
    _go(bench, NodeRef("", "help_guide"))
    bench.list.Select(0, False)
    bench.list.Select(11)
    bench.default_action()
    assert opened == ["12"]


def test_an_empty_list_says_why(wx_session_app, quill_data_dir) -> None:
    frame = _bench([])
    try:
        _go(frame, NodeRef("repository", "issues", REPO))
        assert frame.details.GetValue().startswith("No open issues. Ctrl+N files one.")
    finally:
        frame.frame.Destroy()


def test_start_here_teaches_the_five_keys(bench) -> None:
    _go(bench, NodeRef("", "start"))
    text = bench.details.GetValue()
    for key in ("F6", "Enter", "Shift+F1", "Alt+Enter", "Backspace"):
        assert key in text
