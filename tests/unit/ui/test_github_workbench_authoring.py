"""Workflow editor, Dependabot, CODEOWNERS and Compare Configuration (PRD 22.1).

The commands are called on a stand-in window with recorded answers: nothing
reaches GitHub, and every write is asked about first.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.github.explore_models import ExploreRow  # noqa: E402
from quill.core.github.item_actions import GITHUB_ACTIONS  # noqa: E402
from quill.core.github.items_provider import GitHubItem  # noqa: E402
from quill.core.github.workflow_authoring import job_ids, load_workflow  # noqa: E402
from quill.core.github.workflows import GitHubWorkflow  # noqa: E402
from quill.core.github.write_requirements import COMMAND_REQUIREMENTS  # noqa: E402
from quill.ui.github_workbench_actions import REPOSITORY_ACTIONS  # noqa: E402
from quill.ui.github_workbench_authoring import GitHubWorkbenchAuthoringMixin  # noqa: E402
from quill.ui.github_workbench_development import DEVELOPMENT_VERBS  # noqa: E402
from tests.unit.core.github_workbench.test_config_compare import SOURCE, FakeRepo  # noqa: E402

REF = SimpleNamespace(instance="o/r")
CI = (
    "# The tests.\nname: CI\non:\n  push:\n    branches: [main]\njobs:\n  test:\n"
    "    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n"
)


class _Items:
    def __init__(self, repos: dict[str, FakeRepo]) -> None:
        self.repos = repos
        self.comments: list[tuple[str, int, str]] = []

    def template_repository(self, name: str) -> FakeRepo:
        return self.repos[name]

    def create_comment(self, repository: str, number: int, body: str) -> dict[str, str]:
        self.comments.append((repository, number, body))
        return {"id": "1"}


class _Window(GitHubWorkbenchAuthoringMixin):
    signed_in = True

    def __init__(self, repos: dict[str, FakeRepo], *, yes: bool = True) -> None:
        self.items = _Items(repos)
        self.yes = yes
        self.said: list[str] = []
        self.asked: list[str] = []
        self.typed: list[str] = []
        self.picks: list[int] = []
        self.frame = SimpleNamespace(reload=lambda: self.said.append("(reloaded)"), frame=None)

    def account_name(self) -> str:
        return "jeff"

    def _current_repository(self) -> str:
        return "o/r"

    def _say(self, text: str) -> None:
        self.said.append(text)

    def _confirm(self, _title: str, question: str) -> bool:
        self.asked.append(question)
        return self.yes

    def _ask_text(self, *_args: Any, **_kwargs: Any) -> str:
        return self.typed.pop(0) if self.typed else ""

    def _choose(self, _title: str, _prompt: str, choices: list[str]) -> int:
        self.choices = choices
        return self.picks.pop(0) if self.picks else -1

    def _background(self, _name: str, work: Any, done: Any) -> None:
        done(work())


def test_every_command_is_registered_declared_and_on_its_rows() -> None:
    for verb in (
        "edit_workflow",
        "new_workflow",
        "dependabot_command",
        "who_owns",
        "compare_config",
    ):
        assert verb in DEVELOPMENT_VERBS
    for verb in ("edit_workflow", "new_workflow", "dependabot_command", "compare_config"):
        assert f"github.workbench.{verb}" in COMMAND_REQUIREMENTS
    commands = {
        row_type: [r.command_id for r in GITHUB_ACTIONS.rows_for(row_type)]
        for row_type in ("workflow", "pull_request", "file", "folder")
    }
    assert "github.workbench.edit_workflow" in commands["workflow"]
    assert "github.workbench.dependabot_command" in commands["pull_request"]
    assert "github.workbench.who_owns" in commands["file"]
    assert "github.workbench.who_owns" in commands["folder"]
    assert commands["file"][-1] == "github.workbench.properties"
    actions = dict((command, label) for label, command in REPOSITORY_ACTIONS)
    for verb in ("new_workflow", "who_owns", "compare_config"):
        assert f"github.workbench.{verb}" in actions


class _Editor:
    """Stands in for the workflow editor window: hands back what it is given."""

    answers: list[str | None] = []
    seen: list[dict[str, Any]] = []

    def __init__(
        self, _parent: Any, draft: Any, *, path: str, protected: bool, announce: Any
    ) -> None:
        _Editor.seen.append({"draft": draft, "path": path, "protected": protected})
        self.use_pull_request = False

    def show(self) -> str | None:
        return _Editor.answers.pop(0)


@pytest.fixture
def editor(monkeypatch: pytest.MonkeyPatch) -> type[_Editor]:
    monkeypatch.setattr("quill.ui.github_workflow_editor_dialog.WorkflowEditorDialog", _Editor)
    _Editor.answers, _Editor.seen = [], []
    return _Editor


def test_edit_workflow_saves_after_asking_and_naming_the_account(editor: Any) -> None:
    repo = FakeRepo({".github/workflows/ci.yml": CI})
    window = _Window({"o/r": repo})
    editor.answers = [CI.replace("main]", "main, release]")]
    window._do_edit_workflow(REF, GitHubWorkflow(5, "CI", ".github/workflows/ci.yml", "active"))
    assert editor.seen[0]["path"] == ".github/workflows/ci.yml"
    assert list(editor.seen[0]["draft"].data["jobs"]) == ["test"]
    assert window.asked[0].startswith("Saving replaces .github/workflows/ci.yml in o/r on main")
    assert "next run it starts" in window.asked[0] and window.asked[0].endswith(" as jeff")
    assert [(branch, path) for branch, path, _t in repo.writes] == [
        ("main", ".github/workflows/ci.yml")
    ]
    assert "release" in repo.branches["main"][".github/workflows/ci.yml"]
    assert window.said[0] == "Saved .github/workflows/ci.yml to main in o/r, and checked it."


def test_a_protected_branch_saves_through_a_pull_request(editor: Any) -> None:
    repo = FakeRepo({".github/workflows/ci.yml": CI}, protected=True)
    window = _Window({"o/r": repo})
    editor.answers = [CI + "# more\n"]
    window._do_edit_workflow(REF, GitHubWorkflow(5, "CI", ".github/workflows/ci.yml", "active"))
    assert editor.seen[0]["protected"] is True
    assert "a new branch with a pull request into main" in window.asked[0]
    assert all(branch != "main" for branch, _p, _t in repo.writes)
    assert repo.pulls[0]["body"].startswith("Changes the workflow `.github/workflows/ci.yml`")
    assert "opened pull request #41" in window.said[0]


def test_saying_no_or_changing_nothing_writes_nothing(editor: Any) -> None:
    repo = FakeRepo({".github/workflows/ci.yml": CI})
    flow = GitHubWorkflow(5, "CI", ".github/workflows/ci.yml", "active")
    editor.answers = [CI]
    _Window({"o/r": repo})._do_edit_workflow(REF, flow)
    no = _Window({"o/r": repo}, yes=False)
    editor.answers = [CI + "# x\n"]
    no._do_edit_workflow(REF, flow)
    assert repo.writes == []


def test_a_conflict_keeps_the_draft_and_opens_the_editor_again(editor: Any) -> None:
    repo = FakeRepo({".github/workflows/ci.yml": CI})
    window = _Window({"o/r": repo})
    original = repo.get_contents

    def changed_meanwhile(path: str, ref: str | None = None) -> Any:
        found = original(path, ref)
        if ref is not None:
            found.sha = "somebody-else"
        return found

    repo.get_contents = changed_meanwhile  # type: ignore[method-assign]
    editor.answers = [CI + "# mine\n", None]
    window._do_edit_workflow(REF, GitHubWorkflow(5, "CI", ".github/workflows/ci.yml", "active"))
    assert "Your draft is kept" in window.said[0]
    assert len(editor.seen) == 2
    assert editor.seen[1]["draft"].original_text == CI + "# mine\n"
    assert repo.writes == []


def test_new_workflow_starts_from_a_starter_and_refuses_one_that_exists(editor: Any) -> None:
    repo = FakeRepo({".github/workflows/ci.yml": CI})
    window = _Window({"o/r": repo})
    window.typed = ["docs-build"]
    editor.answers = [None]
    window._do_new_workflow(REF, None)
    draft = editor.seen[0]["draft"]
    assert editor.seen[0]["path"] == ".github/workflows/docs-build.yml"
    assert draft.data["name"] == "Docs Build" and job_ids(draft) == ["build"]
    window.typed = ["ci"]
    window._do_new_workflow(REF, None)
    assert (
        window.said[-1]
        == ".github/workflows/ci.yml already exists; edit it from Actions, Workflows."
    )


def _pull(author: str, state: str = "open") -> GitHubItem:
    return GitHubItem(12, "Bump requests", state, "https://github.com/o/r/pull/12", True, author)


def test_dependabot_commands_are_offered_only_on_its_open_pull_requests() -> None:
    window = _Window({})
    assert window._fits_dependabot_command(_pull("dependabot[bot]"))
    assert not window._fits_dependabot_command(_pull("jeff"))
    assert not window._fits_dependabot_command(_pull("dependabot[bot]", "closed"))


def test_a_dependabot_command_is_posted_as_a_comment_after_asking() -> None:
    window = _Window({})
    window.picks = [1]
    window._do_dependabot_command(REF, _pull("dependabot[bot]"))
    assert window.choices[0].startswith("Rebase: ")
    assert window.asked[0].startswith(
        'Post "@dependabot recreate" on pull request #12 in o/r as jeff?'
    )
    assert window.items.comments == [("o/r", 12, "@dependabot recreate")]
    assert window.said == ["Posted @dependabot recreate on #12. Dependabot answers in the thread."]
    no = _Window({}, yes=False)
    no.picks = [0]
    no._do_dependabot_command(REF, _pull("dependabot[bot]"))
    assert no.items.comments == []


def test_who_owns_a_file_or_a_typed_path() -> None:
    repo = FakeRepo({".github/CODEOWNERS": "* @all\n/docs/ @writers\n"})
    window = _Window({"o/r": repo})
    row = ExploreRow("guide.md", "", "", "o/r", "file", "docs/guide.md")
    assert window._fits_who_owns(row)
    window._do_who_owns(REF, row)
    assert window.said[0].startswith("@writers own docs/guide.md: line 2 of .github/CODEOWNERS")
    window._do_who_owns(REF, ExploreRow("docs", "", "", "o/r", "folder", "docs"))
    assert window.said[1].startswith("@writers own the files in docs/: line 2")
    window.typed = ["src/app.py"]
    window._do_who_owns(REF, None)
    assert window.said[2].startswith("@all own src/app.py: line 1")
    empty = _Window({"o/r": FakeRepo({})})
    empty._do_who_owns(REF, row)
    assert empty.said[0].startswith("This repository has no CODEOWNERS file")


def test_github_s_codeowners_problems_reach_the_sheet() -> None:
    window = _Window({})
    window.github_api = lambda: (_ for _ in ()).throw(RuntimeError("offline"))  # type: ignore[method-assign]
    got: list[list[str]] = []
    window._codeowners_errors_reader("o/r")(got.append)
    assert got == [["GitHub's own check could not be read: offline"]]


def test_compare_configuration_proposes_one_pull_request(monkeypatch: pytest.MonkeyPatch) -> None:
    target = FakeRepo({".github/workflows/ci.yml": "name: old\n"})
    window = _Window({"o/r": target, "o/.github": FakeRepo(SOURCE)})
    shown: list[Any] = []

    class _Compare:
        def __init__(
            self, _parent: Any, repository: str, source: str, diffs: Any, **_k: Any
        ) -> None:
            shown.append((repository, source, diffs))
            self.diffs = diffs

        def show(self) -> list[Any]:
            return [d for d in self.diffs if d.can_update][:2]

    monkeypatch.setattr("quill.ui.github_config_compare_dialog.ConfigCompareDialog", _Compare)
    window.typed = ["o/.github"]
    window._do_compare_config(REF, None)
    assert shown[0][:2] == ("o/r", "o/.github")
    assert window.asked[0].startswith(
        "Open one pull request in o/r as jeff that takes 2 files from o/.github?"
    )
    assert len(target.pulls) == 1 and all(b != "main" for b, _p, _t in target.writes)
    assert window.said == ["Opened pull request #41 in o/r with 2 files from o/.github."]


def test_nothing_to_compare_is_said_once() -> None:
    same = {".github/CODEOWNERS": "* @a\n"}
    window = _Window({"o/r": FakeRepo(same), "o/s": FakeRepo(same)})
    window.typed = ["o/s"]
    window._do_compare_config(REF, None)
    assert window.said == ["Nothing to update: o/r already matches o/s (1 file the same)."]


# -- the windows themselves ---------------------------------------------------------------


@pytest.fixture
def help_ready(wx_session_app: Any) -> None:
    from quill.ui.app_context_help import ensure_help_provider

    ensure_help_provider(wx)


def test_the_workflow_editor_reads_and_builds_linear_pieces(help_ready: Any) -> None:
    from quill.ui.github_workflow_editor_dialog import WorkflowEditorDialog

    said: list[str] = []
    window = WorkflowEditorDialog(None, load_workflow(CI), path="ci.yml", announce=said.append)
    try:
        assert window.trigger_rows.box.GetStrings() == ["On a push, branches main"]
        assert window.order.GetValue() == "First test."
        assert window.checks.GetValue() == "GitHub would take this file."
        answers: list[dict[str, Any] | None] = [
            {
                "id": "build",
                "name": "Build",
                "runs-on": "ubuntu-latest",
                "needs": ["test"],
                "if": "",
            },
        ]
        window.ask = lambda _title, _fields: answers.pop(0)  # type: ignore[method-assign]
        window.add_job()
        assert window.job_rows.box.GetStrings()[1] == (
            "Build (build), runs on ubuntu-latest, runs after test, 1 step"
        )
        assert window.order.GetValue() == "First test. Then Build."
        window.job_rows.box.SetSelection(0)
        answers.append({"id": "unit", "name": "", "runs-on": "", "needs": [], "if": ""})
        window.edit_job()
        assert "Job unit: it has no runs-on" in window.checks.GetValue()
        assert window.draft.data["jobs"]["build"]["needs"] == ["unit"]
        text, problem = window.build()
        assert text is None and problem.startswith("GitHub would reject this file (1 problem).")
        window.job_rows.box.SetSelection(0)
        answers.append({
            "id": "unit",
            "name": "",
            "runs-on": "windows-latest",
            "needs": [],
            "if": "",
        })
        window.edit_job()

        text, problem = window.build()
        assert problem == "" and text.startswith("# The tests.\n\nname: CI\n")
        assert "needs:\n      - unit" in text
    finally:
        window.dialog.Destroy()


def test_the_editor_s_triggers_steps_and_permissions(help_ready: Any) -> None:
    from quill.ui.github_workflow_editor_dialog import WorkflowEditorDialog
    from quill.ui.github_workflow_parts import EVENT_CHOICES, PERMISSION_MODES

    window = WorkflowEditorDialog(None, load_workflow(CI), path="ci.yml", protected=True)
    try:
        assert not window.pull.IsEnabled() and window.use_pull_request
        dispatch = [e for _r, e in EVENT_CHOICES].index("workflow_dispatch")
        window.choose = lambda *_a: dispatch  # type: ignore[method-assign]
        window.ask_items = lambda dialog: [  # type: ignore[method-assign]
            ("target", {"type": "choice", "options": ["a", "b"]})
        ]
        window.add_trigger()
        assert window.trigger_rows.box.GetStrings()[1] == "Run by hand, 1 input"
        window.job_rows.box.SetSelection(0)
        window.ask_items = lambda dialog: [  # type: ignore[method-assign]
            *dialog.items,
            {"name": "Test", "run": "pytest -q"},
        ]
        window.edit_steps()
        assert window.job_rows.box.GetStrings()[0].endswith("2 steps")
        values = {"mode": PERMISSION_MODES[4][0], "contents": "read", "pull-requests": "write"}
        window.ask = lambda _t, fields: {  # type: ignore[method-assign]
            f.key: values.get(f.key, "not listed") for f in fields
        }
        window.edit_permissions(None)
        assert window.draft.data["permissions"] == {"contents": "read", "pull-requests": "write"}
        assert "contents read, pull-requests write" in window.permissions.GetLabel()
    finally:
        window.dialog.Destroy()


def test_the_dependabot_sheet_adds_an_entry_and_refuses_what_dependabot_would(
    help_ready: Any,
) -> None:
    from quill.ui.github_config_sheets_dialog import DependabotDialog, entry_fields

    window = DependabotDialog(None, "version: 2\nupdates: []\n")
    try:
        assert window.checks.GetValue() == "Updates: there are none, so Dependabot checks nothing."
        assert window.build()[0] is None
        fields = {f.key: f.value for f in entry_fields({})}
        fields.update({"package-ecosystem": "pip", "directories": "/, /docs", "day": "friday"})
        window.ask = lambda _t, _f: dict(fields)  # type: ignore[method-assign]
        window.add()
        assert window.rows.box.GetStrings() == ["pip in / and /docs, weekly on Friday"]
        text, problem = window.build()
        assert problem == "" and "directories:\n      - /\n      - /docs" in text
    finally:
        window.dialog.Destroy()


def test_the_codeowners_table_edits_moves_and_shows_github_s_problems(help_ready: Any) -> None:
    from quill.ui.github_config_sheets_dialog import CodeownersDialog

    started: list[Any] = []
    window = CodeownersDialog(None, "* @all\n/docs/ @writers # docs\n", errors=started.append)
    try:
        assert window.table.GetItemCount() == 2
        assert window.table.GetItemText(1, 1) == "/docs/"
        started[0](["Line 2: Unknown owner."])
        assert "GitHub reports: Line 2: Unknown owner." in window.findings.GetValue()
        window.table.Select(1)
        window.ask = lambda _t, _f: {"pattern": "/docs/", "owners": "@writers, @editors"}  # type: ignore[method-assign]
        window.edit()
        assert window.build()[0] == "* @all\n/docs/ @writers @editors # docs\n"
        window.table.Select(1)
        window.move(-1)
        assert window.build()[0].startswith("/docs/ @writers @editors # docs\n* @all")
        window.path.SetValue("docs/a.md")
        assert window.look_up().startswith("@all own docs/a.md: line 2 of this file")
    finally:
        window.dialog.Destroy()


def test_the_compare_window_checks_every_file_it_can_update(help_ready: Any) -> None:
    from quill.core.github.config_compare import compare_files
    from quill.ui.github_config_compare_dialog import ConfigCompareDialog

    diffs = compare_files(
        FakeRepo(SOURCE), "o/s", FakeRepo({".github/CODEOWNERS": "* @x\n"}), "o/r"
    )
    window = ConfigCompareDialog(None, "o/r", "o/s", diffs)
    try:
        assert len(window.checked()) == 5
        # FUX-12: marked in words, with where each change is, not a raw diff.
        shown = window.diff.GetValue()
        assert shown.startswith("Comparing the source with this repository's copy")
        assert "Removed: * @x" in shown
        window.files[0].SetValue(False)
        assert len(window.checked()) == 4
        assert (
            window.others.GetLabel() == "Also: 0 files the same, and 0 only in o/r, which are kept."
        )
    finally:
        window.dialog.Destroy()
