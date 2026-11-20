"""Workflow authoring, Dependabot commands, Who Owns This?, and Compare Configuration (PRD 22.1).

* **Edit Workflow...** on a workflow's row reads its file and opens the
  workflow editor (:mod:`quill.ui.github_workflow_editor_dialog`); **New
  Workflow...** (Repository Actions, Ctrl+Shift+G) starts one from a starter.
  Save asks, naming the file, the repository and the account, then commits
  through the template save path: the default branch, or a new branch and
  pull request when it is protected or asked for. A file changed on GitHub
  since it was opened stops the save; a failed save reopens the editor with
  the draft.
* **Dependabot Commands...** on a pull request Dependabot opened lists its
  ``@dependabot`` commands, each with what it does; the one chosen is posted
  as a comment after asking.
* **Who Owns This?** on a file or folder in the repository's files, or from
  Repository Actions for any typed path, reads the CODEOWNERS file GitHub
  uses and says the winning rule (the last that matches).
* **Compare Configuration...** (Repository Actions) compares this
  repository's workflows, templates, community files, Dependabot file and
  CODEOWNERS with another repository or the owner's ``.github``, shows each
  difference to read, and proposes the chosen ones as one pull request --
  never a direct push.

Every read and write runs through the frame's background runner (GATE-13).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.github.explore_models import ExploreRow
from quill.core.github.items_provider import GitHubItem
from quill.core.github.workflows import GitHubWorkflow

__all__ = [
    "AUTHORING_ACTIONS",
    "AUTHORING_REASONS",
    "AUTHORING_VERBS",
    "GitHubWorkbenchAuthoringMixin",
]

_P = "github.workbench."

AUTHORING_VERBS: dict[str, frozenset[str]] = {
    "edit_workflow": frozenset({"workflow"}),
    "new_workflow": frozenset({"view"}),
    "dependabot_command": frozenset({"item"}),
    "who_owns": frozenset({"file", "folder", "view"}),
    "compare_config": frozenset({"view"}),
}

AUTHORING_REASONS: dict[str, str] = {
    "edit_workflow": "Edit Workflow is for a workflow with a file, while you are signed in.",
    "new_workflow": "Open a repository first. Ctrl+L opens one by name or link.",
    "dependabot_command": "Dependabot's commands are for a pull request Dependabot opened.",
    "who_owns": "Who Owns This? is for a file or folder of a repository.",
    "compare_config": "Open a repository first. Ctrl+L opens one by name or link.",
}

#: Rows of Repository > Repository Actions... (Ctrl+Shift+G).
AUTHORING_ACTIONS: tuple[tuple[str, str], ...] = (
    ("New Workflow...", f"{_P}new_workflow"),
    ("Who Owns This Path?...", f"{_P}who_owns"),
    ("Compare Configuration With Another Repository...", f"{_P}compare_config"),
)

_WORKFLOW_NOTE = "A workflow change takes effect from the next run it starts."


def _error_text(exc: BaseException) -> str:
    return str(exc.args[0]) if exc.args else str(exc)


class GitHubWorkbenchAuthoringMixin:
    items: Any
    frame: Any
    signed_in: bool
    _say: Callable[[str], None]
    _background: Callable[[str, Callable[[], Any], Callable[[Any], None]], None]
    _confirm: Callable[[str, str], bool]
    _ask_text: Callable[..., str]
    _current_repository: Callable[[], str]

    def github_api(self) -> Any:
        raise NotImplementedError

    def _authoring_account(self) -> str:
        name = getattr(self, "account_name", None)
        login = name() if callable(name) else ""
        return f" as {login}" if login else ""

    def _authoring_parent(self) -> Any:
        return getattr(self.frame, "frame", None) if self.frame is not None else None

    def _authoring_repo(self, name: str) -> Any:
        return self.items.template_repository(name)

    # -- workflows -----------------------------------------------------------------------

    def _fits_edit_workflow(self, row: object) -> bool:
        return self.signed_in and isinstance(row, GitHubWorkflow) and bool(row.path)

    def _fits_new_workflow(self, _row: object) -> bool:
        return self.signed_in and bool(self._current_repository())

    def _do_edit_workflow(self, ref: Any, row: object) -> None:
        assert isinstance(row, GitHubWorkflow)
        repository, path = ref.instance, row.path

        def read() -> tuple[str, str, Any]:
            from quill.core.github.template_catalog import read_entry_text
            from quill.core.github.template_save import plan_save

            repo = self._authoring_repo(repository)
            text, sha = read_entry_text(repo, path)
            return text, sha, plan_save(repo, repository, path)

        self._background(
            f"read {path}",
            read,
            lambda found: self.open_workflow_editor(repository, path, *found),
        )

    def _do_new_workflow(self, _ref: Any, _row: object) -> None:
        repository = self._current_repository()
        if not repository:
            self._say(AUTHORING_REASONS["new_workflow"])
            return
        name = self._ask_text(
            "New Workflow", f"File name for the workflow in {repository}:", value="ci"
        )
        stem = name.strip().removesuffix(".yml").removesuffix(".yaml").strip("/ ")
        if not stem:
            return
        path = f".github/workflows/{stem}.yml"

        def read() -> Any:
            from quill.core.github.template_save import plan_save

            return plan_save(self._authoring_repo(repository), repository, path)

        def opened(plan: Any) -> None:
            from quill.core.github.workflow_authoring import dump_workflow, new_workflow

            if plan.current_sha:
                self._say(f"{path} already exists; edit it from Actions, Workflows.")
                return
            text = dump_workflow(new_workflow(stem.replace("-", " ").title()))
            self.open_workflow_editor(repository, path, text, "", plan)

        self._background("read the default branch", read, opened)

    def open_workflow_editor(
        self, repository: str, path: str, text: str, sha: str, plan: Any
    ) -> None:
        """The editor, then the save; a failed save opens it again with the draft."""
        from quill.core.github.actions_yaml import ActionsYamlError
        from quill.core.github.workflow_authoring import load_workflow
        from quill.ui.github_workflow_editor_dialog import WorkflowEditorDialog

        try:
            draft = load_workflow(text)
        except ActionsYamlError as exc:
            self._say(f"{_error_text(exc)} Open it in the editor from the repository's files.")
            return
        window = WorkflowEditorDialog(
            self._authoring_parent(),
            draft,
            path=path,
            protected=bool(plan.needs_pull_request),
            announce=self._say,
        )
        saved = window.show()
        if saved is None:
            return
        if saved == text and sha:
            self._say("Nothing changed.")
            return
        use_pull = window.use_pull_request or bool(plan.needs_pull_request)
        question = plan.sentence(use_pull_request=use_pull, note=_WORKFLOW_NOTE)
        if not self._confirm("Save Workflow", question + self._authoring_account()):
            return

        def work() -> tuple[Any, str]:
            from quill.core.github.template_save import save_template

            try:
                return save_template(
                    self._authoring_repo(repository),
                    plan,
                    saved,
                    expected_sha=sha,
                    use_pull_request=use_pull,
                    body=f"Changes the workflow `{path}`, from QUILL's GitHub Workbench. "
                    + _WORKFLOW_NOTE,
                ), ""
            except Exception as exc:  # noqa: BLE001 - the draft is kept and offered again
                return None, _error_text(exc)

        def done(result: tuple[Any, str]) -> None:
            made, problem = result
            if made is not None:
                self._say(made.sentence())
                self.frame.reload()
                return
            self._say(f"{problem} Your draft is kept; the editor opens again with it.")
            self.open_workflow_editor(repository, path, saved, sha, plan)

        self._background("save the workflow", work, done)

    # -- Dependabot ----------------------------------------------------------------------

    def _fits_dependabot_command(self, row: object) -> bool:
        from quill.core.github.dependabot_config import is_dependabot

        return (
            self.signed_in
            and isinstance(row, GitHubItem)
            and row.is_pr
            and row.state.casefold() == "open"
            and is_dependabot(row.author)
        )

    def _do_dependabot_command(self, ref: Any, row: object) -> None:
        from quill.core.github.dependabot_config import COMMANDS

        assert isinstance(row, GitHubItem)
        choose = getattr(self, "_choose", None)
        index = (
            choose(
                "Dependabot Commands",
                f"What Dependabot should do with #{row.number}:",
                [f"{c.label}: {c.help}" for c in COMMANDS],
            )
            if callable(choose)
            else -1
        )
        if index < 0:
            return
        command = COMMANDS[index]
        repository = ref.instance
        if not self._confirm(
            "Dependabot Commands",
            f'Post "{command.comment}" on pull request #{row.number} in {repository}'
            f"{self._authoring_account()}? {command.help} Dependabot answers in the thread.",
        ):
            return
        self._background(
            "post the Dependabot command",
            lambda: self.items.create_comment(repository, row.number, command.comment),
            lambda _made: self._say(
                f"Posted {command.comment} on #{row.number}. Dependabot answers in the thread."
            ),
        )

    # -- Who Owns This? ------------------------------------------------------------------

    def _fits_who_owns(self, row: object) -> bool:
        if isinstance(row, ExploreRow) and row.kind in ("file", "folder"):
            return bool(row.repo)
        return bool(self._current_repository())

    def _do_who_owns(self, ref: Any, row: object) -> None:
        if isinstance(row, ExploreRow) and row.kind in ("file", "folder") and row.repo:
            repository, path = row.repo, row.key
            if row.kind == "folder" and path:
                path = path.rstrip("/") + "/"
        else:
            repository = self._current_repository()
            path = self._ask_text(
                "Who Owns This Path?", f"Path in {repository}, such as docs/guide.md:"
            )
        if not repository or not path.strip():
            return

        def work() -> str:
            from quill.core.github.codeowners_table import read_codeowners, who_owns

            where, text = read_codeowners(self._authoring_repo(repository))
            return who_owns(where, text, path)

        self._background("read CODEOWNERS", work, self._say)

    def _codeowners_errors_reader(self, repository: str) -> Callable[[Any], None]:
        """For the CODEOWNERS sheet: read GitHub's problems for the file, off the UI thread."""

        def start(done: Callable[[list[str]], None]) -> None:
            def work() -> list[str]:
                from quill.core.github.codeowners_table import codeowners_errors

                try:
                    return codeowners_errors(self.github_api(), repository)
                except Exception as exc:  # noqa: BLE001 - said in the sheet, not raised
                    return [f"GitHub's own check could not be read: {_error_text(exc)}"]

            self._background("read GitHub's CODEOWNERS problems", work, done)

        return start

    # -- Compare Configuration -----------------------------------------------------------

    def _fits_compare_config(self, _row: object) -> bool:
        return self.signed_in and bool(self._current_repository())

    def _do_compare_config(self, _ref: Any, _row: object) -> None:
        repository = self._current_repository()
        if not repository:
            self._say(AUTHORING_REASONS["compare_config"])
            return
        owner = repository.split("/", 1)[0]
        source = self._ask_text(
            "Compare Configuration",
            f"Compare {repository} with which repository? owner/name; {owner}/.github holds "
            "the owner's defaults:",
            value=f"{owner}/.github",
        ).strip()
        if not source or "/" not in source:
            return

        def work() -> list[Any]:
            from quill.core.github.config_compare import compare_files

            return compare_files(
                self._authoring_repo(source),
                source,
                self._authoring_repo(repository),
                repository,
            )

        self._background(
            f"compare with {source}", work, lambda found: self._compared(repository, source, found)
        )

    def _compared(self, repository: str, source: str, diffs: list[Any]) -> None:
        from quill.ui.github_config_compare_dialog import ConfigCompareDialog

        if not any(d.can_update for d in diffs):
            same = sum(1 for d in diffs if d.state == "same")
            self._say(
                f"Nothing to update: {repository} already matches {source} "
                f"({same} file{'s' if same != 1 else ''} the same)."
            )
            return
        chosen = ConfigCompareDialog(
            self._authoring_parent(), repository, source, diffs, announce=self._say
        ).show()
        if not chosen:
            return
        names = "; ".join(d.sentence() for d in chosen)
        if not self._confirm(
            "Propose Update",
            f"Open one pull request in {repository}{self._authoring_account()} that takes "
            f"{len(chosen)} file{'s' if len(chosen) != 1 else ''} from {source}? Nothing "
            f"changes until it is merged. {names}",
        ):
            return

        def work() -> tuple[Any, str]:
            from quill.core.github.config_compare import propose_update

            try:
                return propose_update(
                    self._authoring_repo(repository), repository, source, chosen
                ), ""
            except Exception as exc:  # noqa: BLE001 - said once, nothing half-done
                return None, _error_text(exc)

        def done(result: tuple[Any, str]) -> None:
            made, problem = result
            if made is None:
                self._say(problem)
                return
            self._say(
                f"Opened pull request #{made.pull_request_number} in {repository} with "
                f"{len(chosen)} file{'s' if len(chosen) != 1 else ''} from {source}."
            )

        self._background("propose the update", work, done)
