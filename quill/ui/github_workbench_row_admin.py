"""Single commands on rows the Workbench already lists; the work is in ``row_admin``.

Releases, milestones and deployments gain Delete; webhooks gain Send Test Push
and Turn On or Off; branches gain Merge Into...; branches and tags gain
Download Source...; repository rows gain Send Repository Dispatch....
Everything that cannot be undone asks first, naming what will go.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core.github.explore_models import ExploreRow
from quill.core.github.items_provider import GitHubBranch, GitHubRelease, GitHubTag

__all__ = ["ROW_ADMIN_REASONS", "ROW_ADMIN_VERBS", "GitHubWorkbenchRowAdminMixin"]

ROW_ADMIN_VERBS: dict[str, frozenset[str]] = {
    "delete_release": frozenset({"release"}),
    "delete_milestone": frozenset({"milestone"}),
    "delete_deployment": frozenset({"deployment"}),
    "webhook_test_push": frozenset({"webhook"}),
    "webhook_on_off": frozenset({"webhook"}),
    "merge_into": frozenset({"branch"}),
    "download_source": frozenset({"branch", "tag"}),
    "repository_dispatch": frozenset({"repo"}),
}

ROW_ADMIN_REASONS: dict[str, str] = {
    "delete_release": "Delete Release is for a release, while you are signed in.",
    "delete_milestone": "Delete Milestone is for a milestone, while you are signed in.",
    "delete_deployment": "Delete Deployment is for a deployment, while you are signed in.",
    "webhook_test_push": "Send Test Push is for a repository's webhook, while signed in.",
    "webhook_on_off": "Turn On or Off is for a webhook, while you are signed in.",
    "merge_into": "Merge Into is for a branch, while you are signed in.",
    "download_source": "Download Source is for a branch or a tag.",
    "repository_dispatch": "Repository Dispatch is for a repository, while you are signed in.",
}


class GitHubWorkbenchRowAdminMixin:
    frame: Any
    items: Any
    signed_in: bool
    _say: Callable[[str], None]
    _background: Callable[[str, Callable[[], Any], Callable[[Any], None]], None]
    _choose: Callable[[str, str, list[str]], int]
    _confirm: Callable[[str, str], bool]
    _ask_text: Callable[..., str]
    _repo_for: Callable[[Any], str]

    def github_api(self) -> Any:
        raise NotImplementedError

    @staticmethod
    def _explore(row: object, kind: str) -> ExploreRow | None:
        found = isinstance(row, ExploreRow) and row.kind == kind and bool(row.key)
        return row if found else None  # type: ignore[return-value]

    def _done_reload(self, said: object) -> None:
        self._say(str(said))
        self.frame.reload()

    # -- what each fits ----------------------------------------------------------------------

    def _fits_delete_release(self, row: object) -> bool:
        return self.signed_in and isinstance(row, GitHubRelease)

    def _fits_delete_milestone(self, row: object) -> bool:
        return self.signed_in and self._explore(row, "milestone") is not None

    def _fits_delete_deployment(self, row: object) -> bool:
        return self.signed_in and self._explore(row, "deployment") is not None

    def _fits_webhook_test_push(self, row: object) -> bool:
        found = self._explore(row, "webhook")
        return self.signed_in and found is not None and "/" in (found.repo or "")

    def _fits_webhook_on_off(self, row: object) -> bool:
        return self.signed_in and self._explore(row, "webhook") is not None

    def _fits_merge_into(self, row: object) -> bool:
        return self.signed_in and isinstance(row, GitHubBranch)

    def _fits_download_source(self, row: object) -> bool:
        return isinstance(row, (GitHubBranch, GitHubTag))

    def _fits_repository_dispatch(self, row: object) -> bool:
        return self.signed_in and self._explore(row, "repo") is not None

    # -- deletes -------------------------------------------------------------------------------

    def _do_delete_release(self, ref: Any, row: object) -> None:
        from quill.core.github.row_admin import delete_release

        assert isinstance(row, GitHubRelease)
        repo, tag = self._repo_for(ref), row.tag
        downloads = f", and its {row.asset_count} files" if row.asset_count else ""
        which = self._choose(
            "Delete Release",
            f"Delete the release {row.name or tag}{downloads}? This cannot be undone.",
            ["Delete the release, keep the tag", "Delete the release and its tag"],
        )
        if which < 0:
            return
        api = self.github_api()
        self._background(
            f"delete the release {tag}",
            lambda: delete_release(api, repo, tag, delete_tag=which == 1),
            self._done_reload,
        )

    def _do_delete_milestone(self, ref: Any, row: object) -> None:
        from quill.core.github.row_admin import delete_milestone

        found = self._explore(row, "milestone")
        if found is None:
            return
        repo, title = found.repo or self._repo_for(ref), found.key
        if not self._confirm(
            "Delete Milestone",
            f"Delete the milestone {title}? Its issues and pull requests stay, with no "
            "milestone. This cannot be undone; closing it keeps it.",
        ):
            return
        api = self.github_api()
        self._background(
            f"delete the milestone {title}",
            lambda: delete_milestone(api, repo, title),
            self._done_reload,
        )

    def _do_delete_deployment(self, ref: Any, row: object) -> None:
        from quill.core.github.row_admin import delete_deployment

        found = self._explore(row, "deployment")
        if found is None:
            return
        repo, number = found.repo or self._repo_for(ref), found.key
        if not self._confirm(
            "Delete Deployment",
            f"Delete deployment {number} ({found.label}) from its history? This cannot be undone.",
        ):
            return
        api = self.github_api()
        self._background(
            "delete the deployment",
            lambda: delete_deployment(api, repo, number),
            self._done_reload,
        )

    # -- webhooks ------------------------------------------------------------------------------

    def _do_webhook_test_push(self, ref: Any, row: object) -> None:
        from quill.core.github.row_admin import test_push

        found = self._explore(row, "webhook")
        if found is None:
            return
        owner, api = found.repo or ref.instance, self.github_api()
        self._background("send a test push", lambda: test_push(api, owner, found.key), self._say)

    def _do_webhook_on_off(self, ref: Any, row: object) -> None:
        from quill.core.github.row_admin import set_webhook_active

        found = self._explore(row, "webhook")
        if found is None:
            return
        which = self._choose(
            "Turn Webhook On or Off",
            f"{found.label}:",
            ["Turn it on", "Turn it off: GitHub sends it nothing"],
        )
        if which < 0:
            return
        owner, api = found.repo or ref.instance, self.github_api()
        self._background(
            "change the webhook",
            lambda: set_webhook_active(api, owner, found.key, which == 0),
            self._done_reload,
        )

    # -- branches, tags and repositories -------------------------------------------------------

    def _do_merge_into(self, ref: Any, row: object) -> None:
        from quill.core.github.row_admin import merge_branch

        assert isinstance(row, GitHubBranch)
        repo, head = self._repo_for(ref), row.name
        base = self._ask_text(
            "Merge Into", f"Merge {head} into which branch?", value=row.default_branch or ""
        )
        if not base or base == head:
            return
        if not self._confirm(
            "Merge Into",
            f"Merge {head} into {base} on GitHub now, as a merge commit, with no pull "
            f"request or review? Branch protection on {base} still applies.",
        ):
            return
        api = self.github_api()
        self._background(
            f"merge {head} into {base}",
            lambda: merge_branch(api, repo, base, head),
            self._done_reload,
        )

    def _do_download_source(self, ref: Any, row: object) -> None:
        from quill.core.github.row_admin import source_download
        from quill.ui.dialog_contract import show_modal_dialog

        assert isinstance(row, (GitHubBranch, GitHubTag))
        repo, name = self._repo_for(ref), row.name
        which = self._choose(
            "Download Source", f"{repo} at {name}, as:", ["A zip file", "A tar.gz file"]
        )
        if which < 0:
            return
        archive = "zip" if which == 0 else "tar.gz"
        download = source_download(repo, name, "zip" if which == 0 else "tar")
        wx = self.frame._wx
        title = "Download Source"
        with wx.FileDialog(
            self.frame.frame,
            title,
            defaultFile=f"{download.name}.{archive}",
            wildcard=f"{archive} files (*.{archive})|*.{archive}",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as box:
            if show_modal_dialog(box, title) != wx.ID_OK:
                return
            where = Path(box.GetPath())
        self._background(
            "download the source",
            lambda: self.items.download_artifact_to_file(download, where),
            lambda _done: self._say(f"Saved {repo} at {name} to {where.name}."),
        )

    def _do_repository_dispatch(self, ref: Any, row: object) -> None:
        from quill.core.github.row_admin import repository_dispatch

        found = self._explore(row, "repo")
        if found is None:
            return
        repo = found.key
        event = self._ask_text(
            "Repository Dispatch",
            "The event's name, as the workflow's repository_dispatch types say, such as deploy:",
        )
        if not event:
            return
        payload = self._ask_text(
            "Repository Dispatch",
            'Extra values for the workflow as JSON, such as {"env": "test"}, or leave it empty:',
        )
        api = self.github_api()
        self._background(
            "send the event", lambda: repository_dispatch(api, repo, event, payload), self._say
        )
