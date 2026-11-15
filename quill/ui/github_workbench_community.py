"""Actions on Explore's rows in the GitHub Workbench: people, labels, alerts and the rest.

GitHub PRD section 5. Explore GitHub did these before the Workbench had them:
Open Discussion Thread, Dismiss or Reopen Alert, Show Details and Delete Cache
on an Actions cache, Edit and Delete Label, Follow or Unfollow, Clone, and
Snooze or Unsnooze a notification on this device. Each calls the same client
or window Explore used, parented to the Workbench.

Every write to GitHub asks first, runs off the UI thread, and says one
outcome; snoozing changes only this device and says so.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from quill.core.github.explore_models import ExploreRow

__all__ = ["COMMUNITY_REASONS", "COMMUNITY_VERBS", "GitHubWorkbenchCommunityMixin"]

COMMUNITY_VERBS: dict[str, frozenset[str]] = {
    "discussion_thread": frozenset({"discussion"}),
    "dismiss_alert": frozenset({"security"}),
    "show_details": frozenset({"cache"}),
    "delete_cache": frozenset({"cache"}),
    "edit_label": frozenset({"label"}),
    "delete_label": frozenset({"label"}),
    "follow": frozenset({"person"}),
    "clone": frozenset({"repo"}),
    "snooze": frozenset({"notification"}),
    "unsnooze": frozenset({"notification"}),
}

COMMUNITY_REASONS: dict[str, str] = {
    "discussion_thread": "This row is not a discussion GitHub can open by number.",
    "dismiss_alert": "Sign in to GitHub first, on an alert GitHub can triage.",
}


def _row(row: object) -> ExploreRow:
    assert isinstance(row, ExploreRow)
    return row


def _queue_key(row: ExploreRow) -> str:
    """The attention queue's key for *row* (as Explore keyed its snoozes)."""
    return row.url or f"{row.repo}/{row.kind}/{row.key}"


class GitHubWorkbenchCommunityMixin:
    """Explore's row actions, for the GitHub provider."""

    items: Any
    frame: Any
    signed_in: bool
    _say: Callable[[str], None]
    _background: Callable[[str, Callable[[], Any], Callable[[Any], None]], None]
    _confirm: Callable[[str, str], bool]
    _choose: Callable[[str, str, list[str]], int]
    _ask_text: Callable[..., str]
    _parent: Callable[[], Any]
    _explore_client: Callable[[], Any]

    # -- can it run? -----------------------------------------------------------------

    def _fits_discussion_thread(self, row: object) -> bool:
        return isinstance(row, ExploreRow) and row.kind == "discussion" and row.key.isdecimal()

    def _fits_dismiss_alert(self, row: object) -> bool:
        from quill.core.github.alert_triage import parse_alert_key

        return self.signed_in and isinstance(row, ExploreRow) and bool(parse_alert_key(row.key))

    def _fits_signed_in_key(self, row: object) -> bool:
        return self.signed_in and isinstance(row, ExploreRow) and bool(row.key)

    _fits_delete_cache = _fits_signed_in_key
    _fits_edit_label = _fits_signed_in_key
    _fits_delete_label = _fits_signed_in_key
    _fits_follow = _fits_signed_in_key

    def _actions(self) -> Any:
        from quill.core.github.repo_actions import GitHubRepoActions

        return GitHubRepoActions(getattr(self.items, "token", None))

    # -- discussions and alerts ----------------------------------------------------------

    def _do_discussion_thread(self, _ref: Any, row: object) -> None:
        found = _row(row)
        from quill.ui.github_discussion_dialog import GitHubDiscussionDialog

        GitHubDiscussionDialog(
            self._parent(),
            self.items,
            repo=found.repo,
            number=int(found.key),
            announce_cb=self._say,
        ).show()
        self.frame.reload()

    def _do_dismiss_alert(self, _ref: Any, row: object) -> None:
        from quill.core.github.alert_triage import DISMISS_REASONS, parse_alert_key

        found = _row(row)
        parsed = parse_alert_key(found.key)
        if parsed is None:
            return
        kind, number = parsed
        title = "Dismiss or Reopen Alert"
        choice = self._choose(title, f"{kind.label} alert #{number}:", ["Dismiss...", "Reopen"])
        if choice < 0:
            return
        if choice == 1:
            if not self._confirm(title, f"Reopen {kind.label} alert #{number} in {found.repo}?"):
                return
            self._alert_write(found.repo, kind, number, f"Reopened {kind.label} alert #{number}.")
            return
        reasons = DISMISS_REASONS[kind.key]
        index = self._choose(
            title,
            f"Why are you dismissing {kind.label} alert #{number}?",
            [words for _value, words in reasons],
        )
        if index < 0:
            return
        reason, words = reasons[index]
        comment = self._ask_text(title, "Comment for the dismissal (optional):")
        if not self._confirm(
            title,
            f"Dismiss {kind.label} alert #{number} in {found.repo} as {words.lower()}? "
            "Everyone with access sees it as dismissed.",
        ):
            return
        self._alert_write(
            found.repo,
            kind,
            number,
            f"Dismissed {kind.label} alert #{number}.",
            dismiss=True,
            reason=reason,
            comment=comment,
        )

    def _alert_write(
        self, repo: str, kind: Any, number: int, said: str, *, dismiss: bool = False, **extra: str
    ) -> None:
        self._background(
            "change the alert",
            lambda: self.items.set_security_alert_state(
                repo, kind.key, number, dismiss=dismiss, **extra
            ),
            lambda _r: (self._say(said), self.frame.reload()),
        )

    # -- caches ------------------------------------------------------------------------

    def _do_show_details(self, _ref: Any, _row: object) -> None:
        self.frame.details.SetFocus()

    def _do_delete_cache(self, _ref: Any, row: object) -> None:
        found = _row(row)
        name = found.label.split(",", 1)[0]
        if not self._confirm(
            "Delete Cache",
            f"Delete the Actions cache {name} from {found.repo}? Workflows build it again "
            "the next time they need it.",
        ):
            return
        self._background(
            "delete the cache",
            lambda: self._actions().delete_cache(found.repo, found.key),
            lambda _r: (self._say(f"Deleted the cache {name}."), self.frame.reload()),
        )

    # -- labels ------------------------------------------------------------------------

    def _do_edit_label(self, ref: Any, row: object) -> None:
        found = _row(row)
        repo = found.repo or str(getattr(ref, "instance", ""))
        lines = found.detail.splitlines()
        color = lines[1].removeprefix("Color: #") if len(lines) > 1 else "ededed"
        about = lines[2] if len(lines) > 2 else ""
        title = "Edit Label"
        name = self._ask_text(title, "Label name:", value=found.key)
        if not name:
            return
        color = self._ask_text(title, "Six-digit color without #:", value=color) or color
        about = self._ask_text(title, "Description (optional):", value=about)
        old = found.key
        self._background(
            "edit the label",
            lambda: self._explore_client().edit_label(repo, old, name, color, about),
            lambda _r: (self._say(f"Updated label {name}."), self.frame.reload()),
        )

    def _do_delete_label(self, ref: Any, row: object) -> None:
        found = _row(row)
        repo = found.repo or str(getattr(ref, "instance", ""))
        if not self._confirm(
            "Delete Label",
            f"Delete label {found.key} from {repo}? It comes off every issue and pull "
            "request that has it, and this cannot be undone.",
        ):
            return
        name = found.key
        self._background(
            "delete the label",
            lambda: self._explore_client().delete_label(repo, name),
            lambda _r: (self._say(f"Deleted label {name}."), self.frame.reload()),
        )

    # -- people and repositories ------------------------------------------------------------

    def _do_follow(self, _ref: Any, row: object) -> None:
        login = _row(row).key.lstrip("@")
        choice = self._choose("Follow or Unfollow", f"@{login}:", ["Follow", "Unfollow"])
        if choice < 0:
            return
        follow = choice == 0
        said = f"You now follow @{login}." if follow else f"You no longer follow @{login}."
        self._background(
            "change who you follow",
            lambda: self._actions().set_following(login, follow),
            lambda _r: self._say(said),
        )

    def _do_clone(self, _ref: Any, row: object) -> None:
        import os
        import sys

        from quill.stability.safe_mode import should_enable_safe_mode
        from quill.ui.github_clone import CloneHost, default_clone_folder, start_clone

        found = _row(row)

        def run(name: str, work: Any, done: Any, failed: Any) -> None:
            self.frame._run_background(name, work, done, failed)

        start_clone(
            CloneHost(
                parent=self._parent(),
                announce=self._say,
                run_background=run,
                after_clone=lambda _folder: None,
                initial_repo=found.repo or found.key,
                default_folder=default_clone_folder(),
                safe_mode=should_enable_safe_mode(sys.argv, os.environ),
            ),
            token_loader=lambda: str(getattr(self.items, "token", None) or ""),
        )

    # -- snoozing, on this device ------------------------------------------------------------

    def _queue(self) -> Any:
        from quill.core.github.attention_queue import GitHubAttentionQueue

        return GitHubAttentionQueue.load(self._explore_client().account_login())

    def _do_snooze(self, _ref: Any, row: object) -> None:
        key = _queue_key(_row(row))
        self._background(
            "snooze it",
            lambda: self._queue().snooze(key, datetime.now(UTC) + timedelta(days=1)),
            lambda _r: (
                self._say("Snoozed here for one day. GitHub was not changed."),
                self.frame.reload(),
            ),
        )

    def _do_unsnooze(self, _ref: Any, row: object) -> None:
        key = _queue_key(_row(row))
        self._background(
            "unsnooze it",
            lambda: self._queue().unsnooze(key),
            lambda changed: self._say(
                "Unsnoozed here. GitHub was not changed." if changed else "It was not snoozed."
            ),
        )
