"""Choose a repository issue template before starting the issue composer."""

from __future__ import annotations

import threading
import webbrowser

from quill.core.github.issue_templates import GitHubIssueTemplate
from quill.core.github.items_provider import GitHubItem, GitHubItemsError


class GitHubIssueTemplatesMixin:
    """Offer readable Markdown templates and explain link-only issue forms."""

    def _new_issue(self) -> None:
        self._choose_issue_template()

    def _new_pull_request(self) -> None:
        self._prompt_and_create(kind="pr")

    def _prompt_and_create(self, *, kind: str, template: GitHubIssueTemplate | None = None) -> None:
        if kind == "issue":
            from quill.core.github.local_drafts import GitHubIssueDraftStore
            from quill.ui.github_issue_draft_dialog import GitHubIssueDraftDialog

            draft_store = GitHubIssueDraftStore.load(getattr(self._provider, "token", None))
            self._issue_draft_store = draft_store
            draft = GitHubIssueDraftDialog(
                self.dialog,
                template,
                draft_store=draft_store,
                repository=self._repo,
                announce_cb=self._announce,
            ).show()
            if draft is not None:
                self._check_issue_duplicates(
                    draft.title,
                    draft.body,
                    draft.labels,
                    draft.assignees,
                )
            return
        wx = self._wx
        title_prompt = "New Pull Request"
        with wx.TextEntryDialog(self.dialog, "Title:", title_prompt) as dlg:
            if self._show_modal(dlg, title_prompt) != wx.ID_OK:
                return
            title = dlg.GetValue().strip()
        if not title:
            return
        with wx.TextEntryDialog(
            self.dialog,
            "Body (optional):",
            title_prompt,
            style=wx.OK | wx.CANCEL | wx.CENTRE | wx.TE_MULTILINE,
        ) as dlg:
            if self._show_modal(dlg, title_prompt) != wx.ID_OK:
                return
            body = dlg.GetValue().strip()
        head = ""
        base = ""
        if kind == "pr":
            with wx.TextEntryDialog(
                self.dialog, "Head branch (your changes):", title_prompt
            ) as dlg:
                if self._show_modal(dlg, title_prompt) != wx.ID_OK:
                    return
                head = dlg.GetValue().strip()
            with wx.TextEntryDialog(
                self.dialog, "Base branch (merge into):", title_prompt, value="main"
            ) as dlg:
                if self._show_modal(dlg, title_prompt) != wx.ID_OK:
                    return
                base = dlg.GetValue().strip()
            if not head or not base:
                self._announce("Head and base branches are required for a pull request.")
                return
        self._set_status("Creating pull request...")

        def worker() -> None:
            try:
                item = self._provider.create_pull_request(self._repo, title, body, head, base)
            except GitHubItemsError as exc:
                wx.CallAfter(self._set_status, f"Error: {exc}")
                return
            wx.CallAfter(self._on_item_created, item)

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: consented create.

    def _on_item_created(self, item: GitHubItem, draft_clear_failed: bool = False) -> None:
        message = f"Created {item.kind} #{item.number}: {item.title}"
        if draft_clear_failed:
            message += " The local draft could not be cleared; review it before creating again."
        self._set_status(message)
        self._reload()

    def _choose_issue_template(self) -> None:
        wx = self._wx
        if not self._repo:
            self._announce("Load a repository before creating an issue.")
            return
        try:
            templates = self._provider.fetch_issue_templates(self._repo)
        except GitHubItemsError as exc:
            self._set_status(str(exc))
            dialog = wx.MessageDialog(
                self.dialog,
                f"Could not read the repository's issue templates.\n\n{exc}\n\n"
                "Create a blank issue instead?",
                "Issue Templates Unavailable",
                wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
            )
            try:
                if self._show_modal(dialog, "Issue Templates Unavailable") == wx.ID_YES:
                    self._prompt_and_create(kind="issue")
            finally:
                dialog.Destroy()
            return
        if not templates:
            self._prompt_and_create(kind="issue")
            return

        choices = ["Blank issue"]
        choices.extend(
            f"{template.name} — {template.about}" if template.about else template.name
            for template in templates
        )
        dialog = wx.SingleChoiceDialog(
            self.dialog,
            "Choose a repository issue template:",
            "New Issue",
            choices,
        )
        dialog.SetName("Issue template")
        try:
            if self._show_modal(dialog, "Choose Issue Template") != wx.ID_OK:
                return
            index = dialog.GetSelection()
        finally:
            dialog.Destroy()
        if index == 0:
            self._prompt_and_create(kind="issue")
            return
        template = templates[index - 1] if 0 < index <= len(templates) else None
        if template is None:
            self._announce("No issue template was selected.")
            return
        if not template.supported or template.body_truncated:
            reason = (
                "This structured issue form is completed on GitHub."
                if not template.supported
                else "This issue template is too large to load fully in QUILL."
            )
            self._open_template_in_browser(template, reason)
            return
        self._prompt_and_create(kind="issue", template=template)

    def _open_template_in_browser(self, template: GitHubIssueTemplate, reason: str) -> None:
        if not template.url:
            self._announce(f"{reason} The template has no browser link.")
            return
        wx = self._wx
        dialog = wx.MessageDialog(
            self.dialog,
            f"{reason}\n\nOpen the template in your browser? QUILL will not attach "
            "your GitHub token to that browser request.",
            "Open Issue Template in Browser",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_INFORMATION,
        )
        try:
            if self._show_modal(dialog, "Open Issue Template in Browser") != wx.ID_YES:
                return
        finally:
            dialog.Destroy()
        self._announce(
            "Opened issue template in browser."
            if webbrowser.open(template.url, new=2)
            else "Could not open the issue template in browser."
        )

    def _check_issue_duplicates(
        self,
        title: str,
        body: str,
        labels: tuple[str, ...],
        assignees: tuple[str, ...],
    ) -> None:
        wx = self._wx
        escaped = title.replace("\\", "\\\\").replace('"', '\\"')
        query = f'is:issue in:title "{escaped}"'
        repository = self._repo
        self._set_status("Checking for similar issues...")

        def worker() -> None:
            try:
                matches = self._provider.search_items(repository, query, limit=5)
            except GitHubItemsError as exc:
                wx.CallAfter(
                    self._duplicate_check_failed,
                    title,
                    body,
                    labels,
                    assignees,
                    str(exc),
                )
                return
            wx.CallAfter(
                self._duplicate_check_ready,
                title,
                body,
                labels,
                assignees,
                [item for item in matches if isinstance(item, GitHubItem) and not item.is_pr],
            )

        threading.Thread(
            target=worker, daemon=True
        ).start()  # GATE-40-OK: explicit duplicate preflight.

    def _duplicate_check_ready(
        self,
        title: str,
        body: str,
        labels: tuple[str, ...],
        assignees: tuple[str, ...],
        matches: list[GitHubItem],
    ) -> None:
        if matches:
            rows = "\n".join(f"#{item.number}: {item.title}" for item in matches)
            wx = self._wx
            dialog = wx.MessageDialog(
                self.dialog,
                f"Similar open issues were found:\n\n{rows}\n\nCreate a new issue anyway?",
                "Possible Duplicate Issues",
                wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
            )
            try:
                if self._show_modal(dialog, "Possible Duplicate Issues") != wx.ID_YES:
                    self._announce("Issue creation cancelled after duplicate suggestions.")
                    return
            finally:
                dialog.Destroy()
        self._create_issue(title, body, labels, assignees)

    def _duplicate_check_failed(
        self,
        title: str,
        body: str,
        labels: tuple[str, ...],
        assignees: tuple[str, ...],
        error: str,
    ) -> None:
        wx = self._wx
        dialog = wx.MessageDialog(
            self.dialog,
            "QUILL could not check for similar issues:\n\n"
            f"{error}\n\nCreate the issue without a duplicate check?",
            "Duplicate Check Unavailable",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
        )
        try:
            if self._show_modal(dialog, "Duplicate Check Unavailable") != wx.ID_YES:
                self._announce("Issue creation cancelled because the duplicate check failed.")
                return
        finally:
            dialog.Destroy()
        self._create_issue(title, body, labels, assignees)

    def _create_issue(
        self,
        title: str,
        body: str,
        labels: tuple[str, ...],
        assignees: tuple[str, ...],
    ) -> None:
        wx = self._wx
        repository = self._repo
        self._set_status(f"Creating issue in {repository}...")

        def worker() -> None:
            try:
                if labels or assignees:
                    item = self._provider.create_issue(
                        repository,
                        title,
                        body,
                        labels=labels,
                        assignees=assignees,
                    )
                else:
                    item = self._provider.create_issue(repository, title, body)
            except GitHubItemsError as exc:
                wx.CallAfter(self._set_status, f"Error: {exc}")
                return
            draft_store = getattr(self, "_issue_draft_store", None)
            draft_clear_failed = (
                not draft_store.delete_issue(repository) if draft_store is not None else False
            )
            wx.CallAfter(self._on_item_created, item, draft_clear_failed)

        threading.Thread(
            target=worker, daemon=True
        ).start()  # GATE-40-OK: confirmed issue creation.


__all__ = ["GitHubIssueTemplatesMixin"]
