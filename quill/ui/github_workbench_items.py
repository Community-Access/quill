"""Issue, pull request and commit actions the GitHub Workbench does itself.

GitHub PRD section 5. The rows GitHub Items used to answer for the Workbench:
Merge, File Differences, View Timeline, Summarize Discussion, Assign to
Copilot, Transfer Issue, Reorder Sub-issues, Start in Local Worktree, Commit
Comments, and New Issue's one form. Each calls the same provider method or
opens the same window GitHub Items did, parented to the Workbench, so there is
still one implementation of each.

A write that cannot be undone asks first (a merge asks for the number typed
back); every write runs off the UI thread and says one outcome. Nothing is
said on opening a window (GATE-13).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.github.items_provider import GitHubCommit, GitHubItem, GitHubTag

__all__ = ["ITEM_REASONS", "ITEM_VERBS", "GitHubWorkbenchItemsMixin"]

#: The verbs here, and the row kinds each is for (``_kind`` in the actions mixin).
ITEM_VERBS: dict[str, frozenset[str]] = {
    "merge": frozenset({"item"}),
    "diff": frozenset({"item"}),
    "timeline": frozenset({"item"}),
    "summarize": frozenset({"item"}),
    "assign_copilot": frozenset({"item"}),
    "transfer": frozenset({"item"}),
    "sub_issues": frozenset({"item"}),
    "start_worktree": frozenset({"item"}),
    "commit_comments": frozenset({"commit", "tag"}),
}

#: Why each is greyed when the row is the right kind but the rest is not.
ITEM_REASONS: dict[str, str] = {
    "merge": "Merge is for an open pull request that is not merged yet.",
    "diff": "File Differences is for a pull request.",
    "assign_copilot": "Assign to Copilot is for an issue.",
    "transfer": "Transfer is for an issue; a pull request cannot move.",
    "sub_issues": "Sub-issues belong to an issue.",
    "commit_comments": "Commit Comments is for a commit or a tag.",
    "summarize": (
        "The editor that opened this window has not given it an AI connection, "
        "so Summarize Discussion is not available here. Use it from the editor's AI menu."
    ),
    "start_worktree": (
        "The editor that opened this window has not given it local Git, so Start in "
        "Local Worktree is not available here."
    ),
}

_MERGE_METHODS = (("Squash and merge", "squash"), ("Merge commit", "merge"), ("Rebase", "rebase"))


def _noun(item: GitHubItem) -> str:
    return "pull request" if item.is_pr else "issue"


class GitHubWorkbenchItemsMixin:
    """Issue, pull request and commit actions for the GitHub provider."""

    items: Any
    frame: Any
    signed_in: bool
    _say: Callable[[str], None]
    _background: Callable[[str, Callable[[], Any], Callable[[Any], None]], None]
    _confirm: Callable[[str, str], bool]
    _choose: Callable[[str, str, list[str]], int]
    _ask_text: Callable[..., str]
    #: ``() -> summarize(text) | None``, from the editor (its AI connection), or None.
    ai_summarizer: Callable[[], Callable[[str], str] | None] | None = None
    #: ``(parent, repository, number, title, is_pr)``, from the editor, or None.
    start_worktree: Callable[[object, str, int, str, bool], None] | None = None

    # -- can it run? -----------------------------------------------------------

    def _fits_merge(self, row: object) -> bool:
        return (
            self.signed_in
            and isinstance(row, GitHubItem)
            and row.is_pr
            and not row.is_merged
            and row.state == "open"
        )

    def _fits_diff(self, row: object) -> bool:
        return isinstance(row, GitHubItem) and row.is_pr

    def _fits_issue_write(self, row: object) -> bool:
        return self.signed_in and isinstance(row, GitHubItem) and not row.is_pr

    _fits_assign_copilot = _fits_issue_write
    _fits_transfer = _fits_issue_write
    _fits_sub_issues = _fits_issue_write

    def _fits_summarize(self, row: object) -> bool:
        return isinstance(row, GitHubItem) and self.ai_summarizer is not None

    def _fits_start_worktree(self, row: object) -> bool:
        return isinstance(row, GitHubItem) and self.start_worktree is not None

    def _repo_for(self, ref: Any) -> str:
        instance = str(getattr(ref, "instance", "") or "")
        return instance or str(self.current_repository_name())  # type: ignore[attr-defined]

    def _parent(self) -> Any:
        return self.frame.frame

    # -- pull requests -------------------------------------------------------------

    def _do_merge(self, ref: Any, row: object) -> None:
        """Merge: read why it can or cannot, then merge only the commit that was read (GH-MR)."""
        from quill.core.github.merge_readiness import load_readiness

        assert isinstance(row, GitHubItem)
        repo, api = self._repo_for(ref), self.github_api()  # type: ignore[attr-defined]
        self._background(
            f"check #{row.number} can merge",
            lambda: load_readiness(api, repo, row.number),
            lambda ready: self._merge_checked(repo, row, ready),
        )

    def _merge_checked(self, repo: str, row: GitHubItem, ready: Any) -> None:
        from quill.core.github.merge_readiness import merge_at

        if not ready.can_merge:
            self._say(ready.sentence)
            return
        index = self._choose(
            "Merge Pull Request",
            f"How to merge #{row.number} into {ready.base or 'its base branch'}:",
            [label for label, _method in _MERGE_METHODS],
        )
        if index < 0:
            return
        from quill.ui.github_repo_admin_dialogs import TypedConfirmDialog

        if not TypedConfirmDialog(
            self._parent(),
            title="Confirm Merge",
            message=(
                f"Merge pull request #{row.number} ({row.title!r}) into "
                f"{ready.base or 'its base branch'!r} in {repo}, as of commit "
                f"{ready.short_head}? If anyone pushes before it goes in, nothing is merged. "
                "This changes the target branch for everyone and cannot be undone from "
                "QUILL. Type the number to confirm."
            ),
            expected=str(row.number),
        ).show():
            return
        method, number, api = _MERGE_METHODS[index][1], row.number, self.github_api()  # type: ignore[attr-defined]

        def merged(sha: str) -> None:
            self._say(f"Merged #{number} ({str(sha)[:7]}).")
            self.frame.reload()

        self._background(
            "merge the pull request",
            lambda: merge_at(api, repo, number, method, ready.head),
            merged,
        )

    def _do_diff(self, ref: Any, row: object) -> None:
        assert isinstance(row, GitHubItem)
        repo, number = self._repo_for(ref), row.number

        def show(diff: Any) -> None:
            if not getattr(diff, "files", None):
                self._say("This pull request has no changed files to compare.")
                return
            from quill.ui.github_pr_diff_dialog import GitHubPullDiffDialog

            GitHubPullDiffDialog(
                self._parent(),
                self.items,
                repo,
                diff,
                announce_cb=self._say,
                ai_acquire=self.ai_summarizer,
            ).show()

        self._background(
            "read the changed files", lambda: self.items.fetch_pull_diff(repo, number), show
        )

    # -- reading -----------------------------------------------------------------

    def _do_timeline(self, ref: Any, row: object) -> None:
        assert isinstance(row, GitHubItem)
        from quill.ui.github_timeline_dialog import GitHubTimelineDialog

        GitHubTimelineDialog(
            self._parent(),
            self.items,
            self._repo_for(ref),
            row.number,
            kind=_noun(row),
            announce_cb=self._say,
        ).show()

    def _do_summarize(self, ref: Any, row: object) -> None:
        assert isinstance(row, GitHubItem)
        acquire = self.ai_summarizer
        summarize = acquire() if acquire is not None else None
        if summarize is None:
            self._say("AI is not set up, so there is no summary.")
            return
        repo, item = self._repo_for(ref), row

        def work() -> str:
            from quill.core.github.thread_summary import compose_thread_text

            try:
                comments = self.items.fetch_issue_comments(repo, item.number)
            except Exception:  # noqa: BLE001 - the body alone still summarizes
                comments = []
            return str(summarize(compose_thread_text(item.title, item.author, item.body, comments)))

        def show(summary: str) -> None:
            details = self.frame.details
            details.ChangeValue(f"AI summary of #{item.number}:\n{summary}\n\nSource: {item.url}")
            details.SetFocus()
            details.SetInsertionPoint(0)
            self._say(f"Summary ready for #{item.number}.")

        self._background("summarize the discussion", work, show)

    def _do_commit_comments(self, ref: Any, row: object) -> None:
        sha = row.sha if isinstance(row, GitHubCommit) else ""
        if isinstance(row, GitHubTag):
            sha = row.commit_sha
        if not sha:
            self._say("This has no commit to read comments for.")
            return
        from quill.ui.github_commit_comments_dialog import GitHubCommitCommentsDialog

        GitHubCommitCommentsDialog(
            self._parent(), self.items, self._repo_for(ref), sha, announce_cb=self._say
        ).show()

    # -- issues --------------------------------------------------------------------

    def _housekeeping(self) -> Any:
        from quill.core.github.issue_housekeeping import GitHubIssueHousekeeping

        return GitHubIssueHousekeeping(getattr(self.items, "token", None))

    def _do_assign_copilot(self, ref: Any, row: object) -> None:
        assert isinstance(row, GitHubItem)
        repo, number = self._repo_for(ref), row.number

        def checked(assignment: Any) -> None:
            if refusal := assignment.refusal():
                self._say(refusal)
                return
            if not self._confirm("Assign to Copilot", assignment.confirmation()):
                return
            self._background(
                "assign the issue to Copilot",
                lambda: self.items.assign_issue_to_copilot(assignment),
                lambda sentence: (self._say(str(sentence)), self.frame.reload()),
            )

        self._background(
            "ask whether Copilot can take the issue",
            lambda: self.items.check_copilot_assignment(repo, number),
            checked,
        )

    def _do_transfer(self, ref: Any, row: object) -> None:
        assert isinstance(row, GitHubItem)
        repo, number = self._repo_for(ref), row.number
        target = self._ask_text(
            "Transfer Issue",
            f"Move issue #{number} to which repository (owner/name)? It must have the same "
            "owner, and you need write access to both:",
        )
        if not target:
            return
        if not self._confirm(
            "Transfer Issue",
            f"Transfer issue #{number}, {row.title!r}, from {repo} to {target}? Labels and "
            "milestones that do not exist there are dropped, and assignees who cannot be "
            "assigned there are removed.",
        ):
            return
        self._background(
            "transfer the issue",
            lambda: self._housekeeping().transfer(repo, number, target),
            lambda address: (
                self._say(f"Moved #{number} to {target}: {address}"),
                self.frame.reload(),
            ),
        )

    def _do_sub_issues(self, ref: Any, row: object) -> None:
        assert isinstance(row, GitHubItem)
        repo, number = self._repo_for(ref), row.number
        housekeeping = self._housekeeping()

        def open_order(order: Any) -> None:
            if not order or len(order) == 1:
                count = "one sub-issue" if order else "no sub-issues"
                self._say(f"#{number} has {count}; there is nothing to reorder.")
                return
            from quill.ui.github_sub_issue_order_dialog import SubIssueOrderDialog

            SubIssueOrderDialog(
                self._parent(),
                housekeeping,
                repo=repo,
                parent_number=number,
                order=list(order),
                announce_cb=self._say,
            ).show()

        self._background(
            "read the sub-issues", lambda: housekeeping.sub_issues(repo, number), open_order
        )

    def _do_start_worktree(self, ref: Any, row: object) -> None:
        assert isinstance(row, GitHubItem)
        start = self.start_worktree
        if start is not None:
            start(self._parent(), self._repo_for(ref), row.number, row.title, row.is_pr)

    # -- New Issue -------------------------------------------------------------------

    def _do_new_issue(self, _ref: Any, _row: object) -> None:
        repository = str(self._current_repository())  # type: ignore[attr-defined]
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
            if len(usable) < len(templates):
                self._say(
                    "This repository also has an issue form or template QUILL cannot fill; "
                    "it is still on GitHub. Choose another template or a blank issue."
                )
            if not usable:
                self._create_issue_from_template(repository, None)
                return
            labels = ["Blank issue", *[f"{t.name}: {t.about}".rstrip(": ") for t in usable]]
            selected = self._choose("New Issue", f"Choose a template for {repository}:", labels)
            if selected >= 0:
                self._create_issue_from_template(
                    repository, None if selected == 0 else usable[selected - 1]
                )

        self._background("read issue templates", read_templates, choose)

    def _create_issue_from_template(self, repository: str, template: Any | None) -> None:
        """The one issue form both editors use, then a preview that asks first."""
        from quill.core.github.issue_templates import GitHubIssueTemplate
        from quill.core.github.local_drafts import GitHubIssueDraftStore
        from quill.ui.github_issue_draft_dialog import GitHubIssueDraftDialog

        selected = template if isinstance(template, GitHubIssueTemplate) else None
        if selected is not None and selected.form is not None:
            self._create_issue_from_form(repository, selected)
            return
        draft = GitHubIssueDraftDialog(
            self._parent(),
            selected,
            draft_store=GitHubIssueDraftStore.load(getattr(self.items, "token", None)),
            repository=repository,
            announce_cb=self._say,
        ).show()
        if draft is None or not draft.title:
            return
        title, body, labels, assignees = draft.title, draft.body, draft.labels, draft.assignees
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
        self._preview_and_create(repository, title, body, labels, assignees, preview)

    def _create_issue_from_form(self, repository: str, template: Any) -> None:
        """A YAML issue form, filled natively (github_issue_form_dialog.py)."""
        from quill.ui.github_issue_form_dialog import IssueFormDialog

        window = IssueFormDialog(
            self._parent(), template.form, repository=repository, announce=self._say
        )
        if not window.show() or window.result is None:
            return
        title, body = window.result
        labels, assignees = tuple(template.labels), tuple(template.assignees)
        shown_body = body[:2000]
        if len(body) > len(shown_body):
            shown_body += "\n\n[The preview is shortened; the full text will be sent.]"
        preview = (
            f"Create an issue in {repository}?\n\n"
            f"Title: {title}\n"
            f"Form: {template.name}\n"
            f"Labels: {', '.join(labels) or 'none'}\n"
            f"Assignees: {', '.join(assignees) or 'none'}\n\n"
            f"Body:\n{shown_body}"
        )
        self._preview_and_create(repository, title, body, labels, assignees, preview)

    def _preview_and_create(
        self,
        repository: str,
        title: str,
        body: str,
        labels: Any,
        assignees: Any,
        preview: str,
    ) -> None:
        if not self._confirm("Preview New Issue", preview):
            return
        self._background(
            "create the issue",
            lambda: self.items.create_issue(
                repository, title, body, labels=labels, assignees=assignees
            ),
            lambda item: (self._say(f"Created issue #{item.number}."), self.frame.reload()),
        )
