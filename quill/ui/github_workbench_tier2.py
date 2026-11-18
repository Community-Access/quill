"""Turn a workflow on or off, and answer an invitation to a repository (GitHub PRD 14.1).

* **Turn Workflow On or Off...** on a workflow's row says its state in words
  (on, turned off, turned off by GitHub after 60 days without activity) and
  asks before changing it. The work is :mod:`quill.core.github.workflow_state`.
* **Accept Invitation...** and **Decline Invitation...** on a row of Needs My
  Attention > Invitations answer it, each after asking. The work is
  :mod:`quill.core.github.repo_invitations`.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.github.explore_models import ExploreRow
from quill.core.github.items_provider import GitHubCommit, GitHubTag
from quill.core.github.workflows import GitHubWorkflow

__all__ = ["TIER2_REASONS", "TIER2_VERBS", "GitHubWorkbenchTier2Mixin"]

TIER2_VERBS: dict[str, frozenset[str]] = {
    "workflow_state": frozenset({"workflow"}),
    "accept_invitation": frozenset({"invitation"}),
    "decline_invitation": frozenset({"invitation"}),
    "new_tag": frozenset({"view"}),
    "delete_tag": frozenset({"tag"}),
    "user_status": frozenset({"view"}),
    "commit_status": frozenset({"commit"}),
    "export_sbom": frozenset({"view"}),
}

TIER2_REASONS: dict[str, str] = {
    "workflow_state": "Turning a workflow on or off is for a workflow, while you are signed in.",
    "accept_invitation": "Accept is for an invitation that has not expired.",
    "decline_invitation": "Decline is for an invitation, while you are signed in.",
    "new_tag": "New Tag is for a repository's Tags, while you are signed in.",
    "delete_tag": "Delete Tag is for a tag, while you are signed in.",
    "user_status": "Your status is for the account you are signed in with.",
    "commit_status": "Set Status is for a commit, while you are signed in.",
    "export_sbom": "Export Software Bill of Materials is for a repository.",
}


class GitHubWorkbenchTier2Mixin:
    frame: Any
    signed_in: bool
    _say: Callable[[str], None]
    _background: Callable[[str, Callable[[], Any], Callable[[Any], None]], None]
    _confirm: Callable[[str, str], bool]
    _ask_text: Callable[..., str]
    _choose: Callable[[str, str, list[str]], int]

    def github_api(self) -> Any:
        raise NotImplementedError

    # -- workflows -----------------------------------------------------------------

    def _fits_workflow_state(self, row: object) -> bool:
        return self.signed_in and isinstance(row, GitHubWorkflow) and row.id > 0

    def _do_workflow_state(self, ref: Any, row: object) -> None:
        from quill.core.github.workflow_state import is_enabled, set_enabled, state_words

        assert isinstance(row, GitHubWorkflow)
        on = not is_enabled(row.state)
        now = state_words(row.state)
        question = (
            f"{row.name} is {now}. Turn it on, so it runs on its triggers again?"
            if on
            else f"{row.name} is on. Turn it off? Nothing starts it, not even Run Workflow, "
            "until it is turned on again."
        )
        if not self._confirm("Turn Workflow On or Off", question):
            return
        api, repository = self.github_api(), ref.instance
        self._background(
            "turn the workflow on" if on else "turn the workflow off",
            lambda: set_enabled(api, repository, row.id, row.name, on),
            lambda said: (self._say(str(said)), self.frame.reload()),
        )

    # -- invitations ---------------------------------------------------------------

    @staticmethod
    def _invitation(row: object) -> ExploreRow | None:
        return row if isinstance(row, ExploreRow) and row.kind == "invitation" else None

    def _fits_accept_invitation(self, row: object) -> bool:
        found = self._invitation(row)
        return self.signed_in and found is not None and "expired" not in found.label

    def _fits_decline_invitation(self, row: object) -> bool:
        return self.signed_in and self._invitation(row) is not None

    def _answer(self, row: object, *, accept: bool) -> None:
        from quill.core.github.repo_invitations import accept as accept_it
        from quill.core.github.repo_invitations import decline

        found = self._invitation(row)
        if found is None:
            return
        repository, key = found.repo, found.key
        question = (
            f"Accept the invitation to {repository}? {found.detail.split('.')[0]}."
            if accept
            else f"Decline the invitation to {repository}? To join later, you would need a "
            "new invitation."
        )
        if not self._confirm("Invitation", question):
            return
        api = self.github_api()
        call = accept_it if accept else decline
        self._background(
            "answer the invitation",
            lambda: call(api, key, repository),
            lambda said: (self._say(str(said)), self.frame.reload()),
        )

    def _do_accept_invitation(self, _ref: Any, row: object) -> None:
        self._answer(row, accept=True)

    def _do_decline_invitation(self, _ref: Any, row: object) -> None:
        self._answer(row, accept=False)

    # -- tags ----------------------------------------------------------------------

    def _fits_new_tag(self, _row: object) -> bool:
        current = getattr(self.frame, "current", None)
        return self.signed_in and getattr(current, "key", "") == "tags"

    def _do_new_tag(self, ref: Any, _row: object) -> None:
        from quill.core.github.tags import create_tag, valid_tag_name

        name = self._ask_text("New Tag", "Name of the new tag, such as v1.2.0:")
        if not name:
            return
        why = valid_tag_name(name)
        if why:
            self._say(why)
            return
        at = self._ask_text("New Tag", f"Tag which branch, tag or commit as {name}?", value="main")
        if not at:
            return
        api, repository = self.github_api(), ref.instance
        self._background(
            "make the tag",
            lambda: create_tag(api, repository, name, at),
            lambda said: (self._say(str(said)), self.frame.reload()),
        )

    def _fits_delete_tag(self, row: object) -> bool:
        return self.signed_in and isinstance(row, GitHubTag)

    def _do_delete_tag(self, ref: Any, row: object) -> None:
        from quill.core.github.tags import release_for_tag

        assert isinstance(row, GitHubTag)
        api, repository, name = self.github_api(), ref.instance, row.name
        self._background(
            "look for a release on the tag",
            lambda: release_for_tag(api, repository, name),
            lambda release: self._confirm_delete_tag(repository, name, str(release)),
        )

    def _confirm_delete_tag(self, repository: str, name: str, release: str) -> None:
        from quill.core.github.tags import delete_tag

        warning = (
            f" The release {release} is built on it and will be left without its tag."
            if release
            else ""
        )
        if not self._confirm(
            "Delete Tag",
            f"Delete tag {name} from {repository}?{warning} The commit stays; only the "
            "name goes, and anyone who fetched it keeps their copy.",
        ):
            return
        api = self.github_api()
        self._background(
            "delete the tag",
            lambda: delete_tag(api, repository, name),
            lambda said: (self._say(str(said)), self.frame.reload()),
        )

    # -- your status ---------------------------------------------------------------

    def _fits_user_status(self, _row: object) -> bool:
        return self.signed_in

    def _do_user_status(self, _ref: Any, _row: object) -> None:
        from quill.core.github.user_status import read_status

        api = self.github_api()
        self._background("read your status", lambda: read_status(api), self._status_read)

    def _status_read(self, status: Any) -> None:
        from quill.core.github.user_status import CLEAR_AFTER, clear_status, set_status

        choices = ["Set a New Status...", "Clear Status"]
        picked = self._choose("Your GitHub Status", f"{status.sentence} What now?", choices)
        api = self.github_api()
        if picked == 1:
            self._background("clear your status", lambda: clear_status(api), self._say)
            return
        if picked != 0:
            return
        message = self._ask_text(
            "Your GitHub Status", "Your status, as people will see it:", value=status.message
        )
        if not message:
            return
        emoji = self._ask_text(
            "Your GitHub Status",
            "An emoji by its GitHub name, such as palm_tree or house, or blank for none:",
            value=status.emoji.strip(":"),
        )
        busy = self._confirm(
            "Your GitHub Status",
            "Mark yourself busy? People asking for your review are told you may answer slowly.",
        )
        labels = [label for label, _after in CLEAR_AFTER]
        when = self._choose("Your GitHub Status", "Clear the status:", labels)
        if when < 0:
            return
        after = CLEAR_AFTER[when][1]
        self._background(
            "set your status",
            lambda: set_status(api, message, emoji=emoji, busy=busy, clear_after=after),
            self._say,
        )

    # -- a commit's status ---------------------------------------------------------

    def _fits_commit_status(self, row: object) -> bool:
        return self.signed_in and isinstance(row, GitHubCommit) and bool(row.sha)

    def _do_commit_status(self, ref: Any, row: object) -> None:
        from quill.core.github.commit_status import STATES, set_commit_status

        assert isinstance(row, GitHubCommit)
        title = f"Set Status on {row.short_sha or row.sha[:7]}"
        picked = self._choose(title, "What happened?", [label for label, _code in STATES])
        if picked < 0:
            return
        context = self._ask_text(
            title, "The check's name, as it shows among the commit's checks:", value="manual"
        )
        if not context:
            return
        description = self._ask_text(title, "A few words about it, or blank:")
        link = self._ask_text(title, "A link to the details (https://...), or blank:")
        api, repository, state, sha = self.github_api(), ref.instance, STATES[picked][1], row.sha
        self._background(
            "set the commit status",
            lambda: set_commit_status(api, repository, sha, state, context, description, link),
            self._say,
        )

    # -- the software bill of materials --------------------------------------------

    def _fits_export_sbom(self, _row: object) -> bool:
        current = getattr(self.frame, "current", None)
        return self.signed_in and getattr(current, "template", "") == "repository"

    def _do_export_sbom(self, ref: Any, _row: object) -> None:
        from pathlib import Path

        from quill.core.github.runners_sbom import save_sbom, sbom_name
        from quill.ui.dialog_contract import show_modal_dialog

        repository = ref.instance
        wx = self.frame._wx
        style = wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
        with wx.FileDialog(
            self.frame.frame,
            "Export Software Bill of Materials",
            defaultFile=sbom_name(repository),
            wildcard="SPDX JSON (*.spdx.json)|*.spdx.json",
            style=style,
        ) as box:
            if show_modal_dialog(box, "Export Software Bill of Materials") != wx.ID_OK:
                return
            target = Path(box.GetPath())
        api = self.github_api()
        self._background(
            "export the bill of materials", lambda: save_sbom(api, repository, target), self._say
        )
