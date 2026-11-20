"""Help that uses what is in front of you (GitHub PRD D14, GH-R-109)."""

from __future__ import annotations

from types import SimpleNamespace

from quill.core.github.help_examples import ROW_EXAMPLES, Situation, example_for


def test_the_example_names_your_repository_and_your_row() -> None:
    said = example_for(
        Situation(repository="Community-Access/quill", row_kind="issue", row="#42 Crash on start")
    )
    assert said.startswith("For example, here: On Community-Access/quill, #42 Crash on start")
    assert "owner/name" not in said


def test_without_a_row_it_names_the_repository_then_the_account_then_nothing() -> None:
    assert "You are on o/r" in example_for(Situation(repository="o/r", row_kind="issue"))
    assert "Me in a filter means ada" in example_for(Situation(login="ada"))
    assert example_for(Situation()) == ""


def test_every_row_example_uses_only_the_persons_own_values() -> None:
    for kind, template in ROW_EXAMPLES.items():
        said = example_for(Situation(repository="o/r", row_kind=kind, row="R1"))
        assert "o/r" in said and "R1" in said, kind
        assert "{" not in said, template


def test_f1_in_the_workbench_ends_with_the_example() -> None:
    """The provider's hook reads only the window's own state: no request is made."""
    from quill.ui.github_workbench_help import GitHubWorkbenchHelpMixin, _row_name

    class GitHubItem(SimpleNamespace):
        pass

    row = GitHubItem(number=42, title="Crash on start")
    provider = GitHubWorkbenchHelpMixin()
    provider.frame = SimpleNamespace(
        selected_row=lambda: row, current="ref", node=lambda _ref: "node"
    )
    provider.row_type = lambda _node, _row: "issue"  # type: ignore[attr-defined]
    provider.current_repository_name = lambda: "o/r"  # type: ignore[attr-defined]
    provider.account_name = lambda: "ada"  # type: ignore[attr-defined]
    assert provider.help_example() == (
        "For example, here: "
        + ROW_EXAMPLES["issue"].format(repository="o/r", row="#42 Crash on start")
    )
    assert _row_name(SimpleNamespace(name="main")) == "main"
    assert _row_name(None) == ""
