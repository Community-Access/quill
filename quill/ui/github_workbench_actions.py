"""What the GitHub Workbench does when a menu row, a context-menu row or a key runs.

GitHub PRD sections 4 and 5, Phase 3. One mixin for
:class:`quill.ui.github_workbench_window.GitHubWorkbenchProvider`; every
command goes through :meth:`GitHubWorkbenchActionsMixin.run`, which tries in
order:

1. **What the Workbench does itself**, with the calls GitHub Items and Explore
   GitHub already make (comment, close or reopen, re-run, mark read or done,
   star, favorites, pins, saved searches, folders, the drills that move the
   tree);
2. **The editor's command** of the same job, for the repository and account
   commands both editors already have (fork, rename, branch protection,
   Codespaces, accounts): the Workbench asks the editor that opened it, so
   there is one implementation;
3. **GitHub Items on this one item**, parented to the Workbench, for the item
   actions not yet rebuilt here (merge, jobs and logs, release editing, the
   timeline and the rest). It blocks only the Workbench, never the editor
   (section 3.1), and opens straight on the item.

Anything else is greyed, and :meth:`reason` says why in a sentence: the help
string of the greyed row and what Shift+F1 reads.

Nothing here speaks on its own (GATE-13); what is said is the result of a
write the person asked for, through the frame, so F9 can say it again.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.github.explore_models import ExploreRow
from quill.core.github.item_actions import DELETE_COMMANDS, NEW_HERE
from quill.core.github.items_provider import (
    GitHubBranch,
    GitHubCommit,
    GitHubItem,
    GitHubRelease,
    GitHubTag,
    GitHubWorkflow,
    GitHubWorkflowRun,
)
from quill.core.github.workbench_window_menu import PLACEHOLDER_COMMANDS
from quill.ui.dialog_contract import show_modal_dialog
from quill.ui.github_workbench_writes import GitHubWorkbenchWritesMixin

__all__ = ["REPOSITORY_ACTIONS", "GitHubWorkbenchActionsMixin"]

_P = "github.workbench."

#: The Item model rows GitHub Items can open on directly.
_ITEMS_ROWS = (
    GitHubItem,
    GitHubBranch,
    GitHubCommit,
    GitHubTag,
    GitHubRelease,
    GitHubWorkflow,
    GitHubWorkflowRun,
)

#: Repository > Repository Actions...: (label, editor command or Workbench verb).
REPOSITORY_ACTIONS: tuple[tuple[str, str], ...] = (
    ("Star or Unstar", f"{_P}star"),
    ("Clone Repository...", "github.clone_repository"),
    ("Fork Repository...", "github.fork_repository"),
    ("Browse Files", f"{_P}go_files"),
    ("Dispatch Workflow...", "github.dispatch_workflow"),
    ("Create Release...", "github.create_release"),
    ("Security Alerts...", "github.view_security_alerts"),
    ("Open in Codespaces: list your Codespaces...", "github.list_codespaces"),
    ("Create Codespace... (can cost money; asks first)", "github.create_codespace"),
    ("Rename Repository...", "github.rename_repository"),
    ("Change Visibility...", "github.change_repository_visibility"),
    ("Change Default Branch...", "github.change_default_branch"),
    ("Configure Branch Protection...", "github.configure_branch_protection"),
    ("Delete Branch...", "github.delete_branch"),
    ("Commit Multiple Files...", "github.commit_multiple_files"),
    ("Create Repository...", "github.create_repository"),
    ("Browse Organization Repositories...", "github.browse_organization"),
)

#: The Workbench verbs that are editor commands under another name.
_EDITOR_VERBS = {
    "manage_accounts": "file.github_manage_accounts",
    "run_workflow": "github.dispatch_workflow",
    "new_release": "github.create_release",
}

#: Workbench verbs done natively, and the row kinds (or "any") each needs.
_NATIVE: dict[str, frozenset[str]] = {
    "open": frozenset({"any"}),
    "open_repository": frozenset({"repo"}),
    "open_person": frozenset({"person"}),
    "open_organization": frozenset({"org"}),
    "open_entry": frozenset({"file", "folder"}),
    "open_in_editor": frozenset({"file"}),
    "comment": frozenset({"issue", "pr", "item"}),
    "close_reopen": frozenset({"item"}),
    "rerun": frozenset({"run"}),
    "mark_read": frozenset({"notification"}),
    "mark_done": frozenset({"notification"}),
    "unsubscribe": frozenset({"notification"}),
    "mark_all_read": frozenset({"view"}),
    "star": frozenset({"repo", "view"}),
    "favorite": frozenset({"item", "issue", "pr", "favorite", "any_url"}),
    "pin_repository": frozenset({"repo", "view"}),
    "run_search": frozenset({"saved_search"}),
    "remove_search": frozenset({"saved_search"}),
    "save_search": frozenset({"view"}),
    "label_issues": frozenset({"label"}),
    "milestone_issues": frozenset({"milestone"}),
    "download": frozenset({"any_url"}),
    "copy_name": frozenset({"branch"}),
    "run_admin": frozenset({"admin_action"}),
    "rate_limit": frozenset({"view"}),
    "options": frozenset({"view"}),
    "repository_actions": frozenset({"view"}),
    "new_here": frozenset({"view"}),
    "new_any": frozenset({"view"}),
    "new_issue": frozenset({"view"}),
    "go_to_number": frozenset({"view"}),
    "review": frozenset({"pr_item"}),
    "open_topic": frozenset({"help_topic"}),
    "take_me_there": frozenset({"help_topic"}),
    "undo_change": frozenset({"view"}),
    "redo_change": frozenset({"view"}),
}


def _kind(row: object) -> str:
    """A short name for what *row* is, for the table above."""
    if isinstance(row, ExploreRow):
        return {"repo": "repo"}.get(row.kind, row.kind or "result")
    if isinstance(row, GitHubItem):
        return "item"
    if isinstance(row, GitHubWorkflowRun):
        return "run"
    if isinstance(row, GitHubBranch):
        return "branch"
    return "model" if row is not None else ""


class GitHubWorkbenchActionsMixin(GitHubWorkbenchWritesMixin):
    """The GitHub provider's commands. Runs on the UI thread."""

    items: Any
    frame: Any
    _announce: Callable[[str], None]
    _editor_command: Callable[[str], bool] | None
    _open_file_url: Callable[[str], None] | None
    _folders: dict[str, str]

    # -- can it run here? ------------------------------------------------------

    def _selected(self) -> object | None:
        return self.frame.selected_row() if self.frame is not None else None

    def _editor_has(self, command_id: str) -> bool:
        probe = getattr(self, "_editor_command_available", None)
        return bool(callable(probe) and probe(command_id))

    def _native_applies(self, verb: str, row: object) -> bool:
        """Whether the Workbench does *verb* itself for *row*."""
        needs = _NATIVE.get(verb)
        if needs is None or not callable(getattr(self, f"_do_{verb}", None)):
            return False
        kind = _kind(row)
        if verb == "review":
            return isinstance(row, GitHubItem) and row.is_pr
        if verb == "save_search":
            return self._can_save_search()
        if verb in ("star", "pin_repository"):
            return kind == "repo" or bool(self._current_repository())
        if "view" in needs:
            return True
        if "any" in needs:
            return row is not None
        return kind in needs or ("any_url" in needs and bool(self._row_url(row)))

    def supports(self, command_id: str) -> bool:
        verb = command_id.removeprefix(_P)
        if command_id in PLACEHOLDER_COMMANDS:
            return False
        if verb in _EDITOR_VERBS:
            return self._editor_has(_EDITOR_VERBS[verb])
        row = self._selected()
        return self._native_applies(verb, row) or self._classic_can(row)

    def _classic_can(self, row: object) -> bool:
        return isinstance(row, _ITEMS_ROWS) or (
            isinstance(row, ExploreRow) and row.kind in ("issue", "pr")
        )

    def reason(self, command_id: str) -> str:
        verb = command_id.removeprefix(_P)
        if command_id in PLACEHOLDER_COMMANDS:
            return "This is coming in a later release of the Workbench."
        if verb in _EDITOR_VERBS:
            return "The editor that opened this window does not have this command."
        if verb == "save_search":
            return "Type a search in the filter box first."
        if not self.signed_in and verb in ("comment", "close_reopen", "rerun", "mark_read"):
            return "Sign in to GitHub first: Account, Manage GitHub Accounts."
        if self._selected() is None:
            return "Select a row in the list first."
        return "Not for this kind of row."

    def remove_command(self, row_type: str) -> str:
        return DELETE_COMMANDS.get(row_type, "")

    # -- running ---------------------------------------------------------------

    def run_action(self, command_id: str, ref: Any, row: object) -> bool:
        """The Phase 3 commands; False when this is not one of them."""
        verb = command_id.removeprefix(_P)
        if verb in _EDITOR_VERBS:
            if not self._editor_has(_EDITOR_VERBS[verb]):
                self._say(self.reason(command_id))
                return True
            return self._run_editor(_EDITOR_VERBS[verb])
        if command_id in PLACEHOLDER_COMMANDS:
            return False
        if self._native_applies(verb, row):
            getattr(self, f"_do_{verb}")(ref, row)
            return True
        if self._classic_can(row):
            self._open_classic(ref, row)
            return True
        return False

    def _run_editor(self, command_id: str) -> bool:
        runner = self._editor_command
        if runner is None or not runner(command_id):
            self._say("The editor that opened this window does not have this command.")
            return True
        return True

    def _say(self, text: str) -> None:
        if self.frame is not None:
            self.frame._say(text)
        else:
            self._announce(text)

    def _background(self, name: str, work: Callable[[], Any], done: Callable[[Any], None]) -> None:
        frame = self.frame
        frame._run_background(
            f"Workbench {name}", work, done, lambda error: self._say(f"Could not {name}: {error}")
        )

    def _current_repository(self) -> str:
        current = self.frame.current if self.frame is not None else None
        return current.instance if current is not None and current.template == "repository" else ""

    @staticmethod
    def _row_url(row: object) -> str:
        if isinstance(row, ExploreRow):
            return row.url
        return str(getattr(row, "url", "") or getattr(row, "html_url", "") or "")

    def _ask_text(
        self, title: str, prompt: str, *, multiline: bool = False, value: str = ""
    ) -> str:
        wx = self.frame._wx
        style = wx.OK | wx.CANCEL | (wx.TE_MULTILINE if multiline else 0)
        with wx.TextEntryDialog(self.frame.frame, prompt, title, value, style=style) as dialog:
            dialog.SetName(prompt.rstrip(":"))
            if show_modal_dialog(dialog, title) != wx.ID_OK:
                return ""
            return str(dialog.GetValue()).strip()

    def _confirm(self, title: str, question: str) -> bool:
        wx = self.frame._wx
        with wx.MessageDialog(
            self.frame.frame, question, title, wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION
        ) as dialog:
            return bool(show_modal_dialog(dialog, title) == wx.ID_YES)

    def _choose(self, title: str, prompt: str, labels: list[str]) -> int:
        wx = self.frame._wx
        with wx.SingleChoiceDialog(self.frame.frame, prompt, title, labels) as dialog:
            dialog.SetName(title)
            if show_modal_dialog(dialog, title) != wx.ID_OK:
                return -1
            return int(dialog.GetSelection())

    def _explore_client(self) -> Any:
        if getattr(self, "_explore", None) is None:
            from quill.core.github.explore import GitHubExploreClient

            self._explore = GitHubExploreClient(self.items)
        return self._explore

    # -- moving --------------------------------------------------------------

    def _go_filtered(self, template: str, key: str, instance: str, text: str) -> None:
        from quill.ui.workbench_frame import NodeRef

        frame = self.frame
        if not frame.select(NodeRef(template, key, instance)):
            self._say("That place is not in the tree.")
            return
        if frame.current != NodeRef(template, key, instance):
            frame._show_node(NodeRef(template, key, instance), remember=True)
        frame.filter.ChangeValue(text)
        frame.apply_filter()
        frame.list.SetFocus()

    def _do_open(self, _ref: Any, _row: object) -> None:
        self.frame.details.SetFocus()

    def _do_open_entry(self, ref: Any, row: object) -> None:
        assert isinstance(row, ExploreRow)
        if row.kind == "folder":
            self._folders[ref.instance] = row.key
            self.frame.reload()
            return
        self._do_open_in_editor(ref, row)

    def _do_open_in_editor(self, _ref: Any, row: object) -> None:
        opener = self._open_file_url
        url = self._row_url(row)
        if opener is None or not url:
            self._say("The editor that opened this window cannot open GitHub files.")
            return
        opener(url)

    def _do_open_organization(self, _ref: Any, row: object) -> None:
        assert isinstance(row, ExploreRow)
        self._drill("organization", row.key)

    def _drill(self, template: str, name: str) -> None:
        target = self.add_instance(template, name)  # type: ignore[attr-defined]
        if target is None:
            return
        self.frame.rebuild_tree()
        self.frame.select(target)
        self.frame.tree.SetFocus()

    def _do_label_issues(self, ref: Any, row: object) -> None:
        assert isinstance(row, ExploreRow)
        name = row.title or row.key or row.label
        repository = row.repo or ref.instance
        self._go_filtered("repository", "issues_and_pulls", repository, f'label:"{name}"')

    def _do_milestone_issues(self, ref: Any, row: object) -> None:
        assert isinstance(row, ExploreRow)
        self._go_filtered("repository", "issues_and_pulls", ref.instance, f'milestone:"{row.key}"')

    def _do_run_search(self, _ref: Any, row: object) -> None:
        assert isinstance(row, ExploreRow)
        self._go_filtered("", "search_issues", "", row.key)

    def _do_go_to_number(self, ref: Any, _row: object) -> None:
        repository = self._current_repository()
        if not repository:
            self._say("Open a repository first. Ctrl+L opens one by name or link.")
            return
        text = self._ask_text("Go to Number", f"Issue or pull request number in {repository}:")
        number = text.lstrip("#")
        if not number.isdigit():
            if text:
                self._say("That is not a number.")
            return
        self._open_classic(ref, None, reference=f"https://github.com/{repository}/issues/{number}")

    # -- small things -------------------------------------------------------------

    def _do_download(self, _ref: Any, row: object) -> None:
        import webbrowser

        if not webbrowser.open(self._row_url(row), new=2):
            self._say("Could not open this in your browser.")

    def _do_copy_name(self, _ref: Any, row: object) -> None:
        self.frame.copy_text(str(getattr(row, "name", "")))

    def _do_run_admin(self, _ref: Any, row: object) -> None:
        assert isinstance(row, ExploreRow)
        self._run_editor(row.key)

    def _do_rate_limit(self, _ref: Any, _row: object) -> None:
        from quill.core.github.rate_limits import fetch_rate_limit_report

        token = getattr(self.items, "token", None)
        self._background(
            "read the rate limit",
            lambda: fetch_rate_limit_report(token),
            lambda report: self._say(report.sentence()),
        )

    def _do_options(self, _ref: Any, _row: object) -> None:
        from quill.ui.github_workbench_options import show_workbench_options

        show_workbench_options(self.frame.frame)

    def _do_repository_actions(self, ref: Any, row: object) -> None:
        offered = [
            (label, command)
            for label, command in REPOSITORY_ACTIONS
            if command.startswith(_P) or self._editor_has(command)
        ]
        index = self._choose(
            "Repository Actions",
            f"What to do with {self._current_repository() or 'a repository'}:",
            [label for label, _command in offered],
        )
        if index < 0:
            return
        command = offered[index][1]
        if command.startswith(_P):
            self.frame.run(command)
        else:
            self._run_editor(command)

    def _do_new_here(self, ref: Any, row: object) -> None:
        current = self.frame.current
        command = NEW_HERE.get(current.key if current is not None else "", "")
        if not command:
            self._do_new_any(ref, row)
            return
        self.frame.run(command)

    def _do_new_any(self, ref: Any, row: object) -> None:
        choices = [
            ("Issue...", f"{_P}new_issue"),
            ("Saved Search...", f"{_P}save_search"),
            ("Release...", "github.create_release"),
            ("Repository...", "github.create_repository"),
        ]
        offered = [c for c in choices if c[1].startswith(_P) or self._editor_has(c[1])]
        index = self._choose("New", "What to create:", [label for label, _c in offered])
        if index < 0:
            return
        command = offered[index][1]
        if command == f"{_P}save_search":
            self._do_save_search(ref, row)
        elif command.startswith(_P):
            self.frame.run(command)
        else:
            self._run_editor(command)

    def _do_new_issue(self, _ref: Any, _row: object) -> None:
        repository = self._current_repository()
        if not repository:
            self._say("Open a repository first. Ctrl+L opens one by name or link.")
            return
        fetch = getattr(self.items, "fetch_issue_templates", None)
        if not callable(fetch):
            self._create_issue_from_template(repository, None)
            return

        def read_templates() -> tuple[tuple[Any, ...], str]:
            try:
                return tuple(fetch(repository)), ""
            except Exception as exc:  # noqa: BLE001 - a template failure need not block a blank issue
                return (), str(exc)

        def choose(result: tuple[tuple[Any, ...], str]) -> None:
            templates, problem = result
            if problem:
                self._say(
                    f"Could not load issue templates. A blank issue is still available: {problem}"
                )
            usable = [t for t in templates if t.supported and not t.body_truncated]
            unsupported = [t for t in templates if not t.supported or t.body_truncated]
            if unsupported:
                self._say(
                    "This repository also has structured issue forms or a template too large "
                    "for QUILL to fill. Choose a fillable Markdown template or a blank issue."
                )
            if not usable:
                self._create_issue_from_template(repository, None)
                return
            labels = ["Blank issue", *[f"{t.name}: {t.about}".rstrip(": ") for t in usable]]
            selected = self._choose(
                "New Issue",
                f"Choose a template for {repository}:",
                labels,
            )
            if selected < 0:
                return
            self._create_issue_from_template(
                repository, None if selected == 0 else usable[selected - 1]
            )

        self._background("read issue templates", read_templates, choose)

    def _create_issue_from_template(self, repository: str, template: Any | None) -> None:
        from quill.core.github.issue_templates import GitHubIssueTemplate

        selected = template if isinstance(template, GitHubIssueTemplate) else None
        title = self._ask_text(
            "New Issue",
            f"Title of the new issue in {repository}:",
            value=selected.title if selected else "",
        )
        if not title:
            return
        body = self._ask_text(
            "New Issue",
            "What it is about (you can leave this empty):",
            multiline=True,
            value=selected.body if selected else "",
        )
        labels = selected.labels if selected else ()
        assignees = selected.assignees if selected else ()
        shown_body = body[:2000]
        if len(body) > len(shown_body):
            shown_body += "\n\n[The preview is shortened; the full text will be sent.]"
        preview = (
            f"Create an issue in {repository}?\n\n"
            f"Title: {title}\n"
            f"Template: {selected.name if selected else 'Blank issue'}\n"
            f"Labels: {', '.join(labels) or 'none'}\n"
            f"Assignees: {', '.join(assignees) or 'none'}\n\n"
            f"Body:\n{shown_body or '(empty)'}"
        )
        if not self._confirm("Preview New Issue", preview):
            return
        self._background(
            "create the issue",
            lambda: self.items.create_issue(
                repository, title, body, labels=labels, assignees=assignees
            ),
            lambda item: (self._say(f"Created issue #{item.number}."), self.frame.reload()),
        )

    # -- GitHub Items, on one item ---------------------------------------------------

    def _open_classic(self, ref: Any, row: object, *, reference: str = "") -> None:
        """Show an issue or pull request in its Workbench list, not a second window."""
        from quill.core.github.references import GitHubReferenceError, parse_github_reference

        url = reference or self._row_url(row)
        try:
            parsed = parse_github_reference(url) if url else None
        except GitHubReferenceError:
            parsed = None
        if parsed is None or parsed.kind not in {"issue", "pull_request"} or not parsed.number:
            self.frame.open_in_browser()
            return
        repository = parsed.repository or (ref.instance if ref is not None else "")
        if not repository:
            self._say("Open a repository first. Ctrl+L opens one by name or link.")
            return
        node = "pulls" if parsed.kind == "pull_request" else "issues"
        self._go_filtered("repository", node, repository, f"number:{parsed.number}")
