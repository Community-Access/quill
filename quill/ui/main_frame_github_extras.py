"""GitHub Tier 2 commands for ``MainFrame``: Organizations, Releases,
Workflow dispatch, Notifications, and Security alerts
(``docs/planning/github.md`` section 5 -- the rest of the GitHub API
surface, beyond repository administration).

Split out of :mod:`quill.ui.main_frame_github_admin` once that file grew
past a comfortable size; this mixin reuses that module's shared gating
helpers (``_gh_admin_ready``, ``_gh_admin_prompt_repo``,
``_gh_admin_prompt_single``, ``_gh_admin_confirm``, ``_gh_admin_run``) via
``self`` -- both mixins sit in ``MainFrame``'s MRO together, the same
sibling-mixin-sharing-self pattern already used throughout this codebase
(e.g. ``GitHubItemsMixin`` calling ``GitHubRemoteMixin``'s
``_ensure_github_ready``).

Organizations deliberately stop at browsing (Teams are out of scope --
``docs/planning/github.md`` section 1). Discussions and Packages are not
implemented here. Projects v2 is handled by the separate authenticated
GraphQL workbench; it does not shell out to ``gh`` or accept arbitrary queries.
"""

from __future__ import annotations

from typing import Any

from quill.core.github.repo_admin import GitHubRepoAdminProvider
from quill.core.github.token_store import load_github_token


class GitHubExtrasMixin:
    """Adds Organizations/Releases/Dispatch/Notifications/Security-alerts
    GitHub commands to ``MainFrame``."""

    # ------------------------------------------------------------------
    # Organizations (Teams explicitly out of scope; docs/planning/github.md
    # section 1)

    def github_browse_organization(self) -> None:
        """Tools > GitHub > Browse Organization Repositories..."""
        token = self._gh_admin_ready()
        if token is None:
            return

        def work(_progress: object) -> object:
            provider = GitHubRepoAdminProvider(token)
            try:
                return provider.list_organizations()
            finally:
                provider.close()

        self._gh_admin_run("Loading organizations", work, self._on_github_orgs_loaded)

    def _on_github_orgs_loaded(self, orgs: list[str]) -> None:
        if not orgs:
            self._set_status("This account belongs to no organizations")
            return
        wx = self._wx
        with wx.SingleChoiceDialog(
            self.frame, "Organization:", "Browse Organization Repositories", orgs
        ) as dialog:
            if self._show_modal_dialog(dialog, "Browse Organization Repositories") != wx.ID_OK:
                return
            org = dialog.GetStringSelection()

        token = load_github_token()
        if not token:
            return

        def work(_progress: object) -> object:
            provider = GitHubRepoAdminProvider(token)
            try:
                return provider.list_org_repositories(org)
            finally:
                provider.close()

        self._gh_admin_run(
            f"Loading repositories for {org}",
            work,
            lambda repos: self._on_github_org_repos_loaded(org, repos),
        )

    def _on_github_org_repos_loaded(self, org: str, repos: list[Any]) -> None:
        if not repos:
            self._set_status(f"{org} has no repositories visible to this account")
            return
        wx = self._wx
        names = [r.full_name for r in repos]
        with wx.SingleChoiceDialog(self.frame, "Repository:", org, names) as dialog:
            if self._show_modal_dialog(dialog, org) != wx.ID_OK:
                return
            full_name = dialog.GetStringSelection()
        self.open_github_items_viewer_for(full_name)

    # Releases, authored

    def github_create_release(self) -> None:
        """Tools > GitHub > Create Release..."""
        token = self._gh_admin_ready()
        if token is None:
            return
        full_name = self._gh_admin_prompt_repo("Create Release")
        if full_name is None:
            return
        tag = self._gh_admin_prompt_single("Create Release", "Tag (e.g. v1.0.0):")
        if not tag:
            return
        name = self._gh_admin_prompt_single("Create Release", "Release title (optional):") or ""
        generate_notes = self._gh_admin_confirm(
            "Auto-generate release notes from merged pull requests since the last release?",
            "Create Release",
        )
        body = ""
        if not generate_notes:
            body = self._gh_admin_prompt_single("Create Release", "Release notes (optional):") or ""
        draft = self._gh_admin_confirm("Save as a draft (not published yet)?", "Create Release")

        def work(_progress: object) -> object:
            provider = GitHubRepoAdminProvider(token)
            try:
                return provider.create_release(
                    full_name,
                    tag,
                    name=name,
                    body=body,
                    draft=draft,
                    generate_notes=generate_notes,
                )
            finally:
                provider.close()

        def on_done(info: Any) -> None:
            state = "draft" if info.draft else "published"
            self._set_status(f"Created {state} release {info.tag} ({info.html_url})")

        self._gh_admin_run(f"Creating release {tag}", work, on_done)

    # ------------------------------------------------------------------
    # Workflow dispatch

    def github_dispatch_workflow(self) -> None:
        """Tools > GitHub > Dispatch Workflow..."""
        token = self._gh_admin_ready()
        if token is None:
            return
        full_name = self._gh_admin_prompt_repo("Dispatch Workflow")
        if full_name is None:
            return
        workflow_file = self._gh_admin_prompt_single(
            "Dispatch Workflow", "Workflow file name (e.g. ci.yml):"
        )
        if not workflow_file:
            return
        ref = self._gh_admin_prompt_single("Dispatch Workflow", "Branch or tag:", "main")
        if not ref:
            return
        if not self._gh_admin_confirm(
            f"Dispatch {workflow_file!r} on {ref!r} in {full_name}?", "Confirm Dispatch"
        ):
            self._set_status("Dispatch cancelled")
            return

        def work(_progress: object) -> object:
            from quill.core.github.items_provider import GitHubItemsProvider

            provider = GitHubItemsProvider(token=token)
            try:
                provider.dispatch_workflow(full_name, workflow_file, ref)
                return None
            finally:
                provider.close()

        self._gh_admin_run(
            f"Dispatching {workflow_file}",
            work,
            lambda _r: self._set_status(f"Dispatched {workflow_file} on {ref}"),
        )

    # ------------------------------------------------------------------
    # Notifications

    def github_view_notifications(self) -> None:
        """Tools > GitHub > Notifications...: the shared Explore notifications view.

        The same triage surface QUILL Lite reaches from GitHub Items > Explore:
        Mark Done, Unsubscribe, Mark All Read, Include Read, and Enter opening a
        pull request in Review or an issue in the GitHub Items viewer.
        """
        self.open_github_explore("notifications")

    def open_github_explore(self, initial_view: str | None = None) -> None:
        """Explore GitHub on a view (the GitHub menu's Inbox, My Work, Explore).

        Enter on an issue or pull request opens it in the GitHub Items viewer.
        """
        token = self._gh_admin_ready()
        if token is None:
            return
        from quill.core.github.items_provider import GitHubItemsProvider
        from quill.ui.github_explore_dialog import GitHubExploreDialog

        provider = GitHubItemsProvider(token=token)
        chosen: list[Any] = []
        try:
            GitHubExploreDialog(
                self.frame,
                provider,
                initial_repo=self._github_items_initial_repo(),
                initial_view=initial_view,
                announce_cb=self._announce,
                on_open_reference=chosen.append,
                gist_source_cb=self._github_gist_source,
            ).show()
        finally:
            provider.close()
        if chosen:
            self.open_github_items_viewer_for(chosen[0].repository, initial_reference=chosen[0])

    # ------------------------------------------------------------------
    # Security alerts

    def github_view_security_alerts(self) -> None:
        """Tools > GitHub > Security Alerts..."""
        token = self._gh_admin_ready()
        if token is None:
            return
        full_name = self._gh_admin_prompt_repo("Security Alerts")
        if full_name is None:
            return

        def work(_progress: object) -> object:
            from quill.core.github.items_provider import GitHubItemsProvider

            provider = GitHubItemsProvider(token=token)
            try:
                return provider.fetch_security_alerts(full_name)
            finally:
                provider.close()

        self._gh_admin_run(
            f"Loading security alerts for {full_name}",
            work,
            self._on_github_security_alerts_loaded,
        )

    def _on_github_security_alerts_loaded(self, alerts: list[Any]) -> None:
        if not alerts:
            self._set_status("No open security alerts")
            return
        wx = self._wx
        labels = [f"#{a.number} {a.severity}: {a.package} — {a.summary}" for a in alerts]
        with wx.SingleChoiceDialog(self.frame, "Alert:", "Security Alerts", labels) as dialog:
            if self._show_modal_dialog(dialog, "Security Alerts") != wx.ID_OK:
                return
            index = dialog.GetSelection()
        chosen = alerts[index]
        if chosen.html_url:
            import webbrowser

            webbrowser.open(chosen.html_url)

    # ------------------------------------------------------------------
    # Command palette registration

    def _register_github_extras_commands(self) -> None:
        self.commands.try_register(
            "github.browse_organization",
            "GitHub: Browse Organization Repositories...",
            self.github_browse_organization,
            self._binding_for("github.browse_organization"),
        )
        self.commands.try_register(
            "github.create_release",
            "GitHub: Create Release...",
            self.github_create_release,
            self._binding_for("github.create_release"),
        )
        self.commands.try_register(
            "github.dispatch_workflow",
            "GitHub: Dispatch Workflow...",
            self.github_dispatch_workflow,
            self._binding_for("github.dispatch_workflow"),
        )
        self.commands.try_register(
            "github.view_notifications",
            "GitHub: Notifications...",
            self.github_view_notifications,
            self._binding_for("github.view_notifications"),
        )
        self.commands.try_register(
            "github.view_security_alerts",
            "GitHub: Security Alerts...",
            self.github_view_security_alerts,
            self._binding_for("github.view_security_alerts"),
        )
