"""Wave 4 actions in Explore GitHub (QUILL and QUILL Lite share this dialog).

The context menu (Shift+F10 or the Applications key) gains a Repository
Actions submenu for the selected repository row, or for the repository typed
in the Repository box in a repository view: Sync Fork with Upstream, Set
Topics, Watch Level, Archive and Unarchive, Create Repository from This
Template and Delete Repository. A person row offers Follow and Unfollow, and
an Actions caches row offers Delete Cache. GitHub API Rate Limit
(Ctrl+Shift+L, anywhere in the dialog) says how much of the allowance is left
and when it resets.

Every write asks first (Delete Repository asks for the repository's name,
typed, exactly as github.com does), runs off the UI thread, and says only what
GitHub confirmed. A refresh that changed nothing says "No changes since the
last load." instead of reading the same count again.
"""

from __future__ import annotations

import threading
import webbrowser
from typing import TYPE_CHECKING, Any

from quill.core.github.explore import ExploreRow, GitHubExploreError
from quill.core.github.explore_views import REPO_VIEWS
from quill.core.github.items_errors import GitHubItemsError
from quill.core.github.rate_limits import GitHubRateLimitError, fetch_rate_limit_report
from quill.core.github.repo_actions import (
    WATCH_LEVELS,
    GitHubRepoActions,
    watch_level_words,
)
from quill.ui.dialog_contract import dialog_alive

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = ["GitHubExploreRepoActionsMixin"]

_NO_CHANGE_VIEWS_EXCLUDED = frozenset({"attention", "notifications"})


class GitHubExploreRepoActionsMixin:
    """Repository, person, cache and rate-limit actions for ``GitHubExploreDialog``."""

    # -- Menu ----------------------------------------------------------------

    def _wave4_target_repo(self, row: ExploreRow | None) -> str:
        if row is not None and row.kind == "repo" and "/" in row.repo:
            return row.repo
        typed = self._repo.GetValue().strip()
        return typed if self._view_key() in REPO_VIEWS and "/" in typed else ""

    def _add_wave4_actions(self, menu: Any, add: Callable[..., None], row: Any) -> None:
        """Add the Wave 4 rows to the context menu being built."""
        wx = self._wx
        signed_in = self._client._provider.is_authenticated
        repo = self._wave4_target_repo(row)
        if signed_in and repo:
            sub = wx.Menu()
            for label, action in (
                ("Sync Fork with Upstream...", lambda: self._sync_fork(repo)),
                ("Set Topics...", lambda: self._set_topics(repo)),
                ("Watch Level...", lambda: self._choose_watch_level(repo)),
                ("Archive Repository...", lambda: self._set_archived(repo, True)),
                ("Unarchive Repository...", lambda: self._set_archived(repo, False)),
                ("Create Repository from This Template...", lambda: self._from_template(repo)),
                ("Delete Repository...", lambda: self._delete_repository(repo)),
            ):
                item_id = wx.NewIdRef()
                sub.Append(item_id, label)
                sub.Bind(wx.EVT_MENU, lambda _event, callback=action: callback(), id=item_id)
            menu.AppendSubMenu(sub, f"Repository Actions for {repo}")
        if signed_in and row is not None and row.kind == "person" and row.key:
            add(f"Follow @{row.key}", lambda: self._set_following(row.key, True))
            add(f"Unfollow @{row.key}", lambda: self._set_following(row.key, False))
        if signed_in and row is not None and row.kind == "cache" and row.key:
            add("Delete Cache...", lambda: self._delete_cache(row))
        add("GitHub API Rate Limit\tCtrl+Shift+L", self._show_rate_limit)

    def _on_explore_char_hook(self, event: Any) -> None:
        wx = self._wx
        if event.GetKeyCode() == ord("L") and event.GetModifiers() == (
            wx.MOD_CONTROL | wx.MOD_SHIFT
        ):
            self._show_rate_limit()
            return
        event.Skip()

    # -- Background plumbing -------------------------------------------------

    def _actions(self) -> GitHubRepoActions:
        return GitHubRepoActions(getattr(self._client._provider, "token", None))

    def _run_wave4(self, work: Callable[[], str], *, reload_view: bool = False) -> None:
        """Run one write off the UI thread; say GitHub's answer, or why it refused."""
        if self._write_in_flight:
            self._announce("Wait for the current GitHub action to finish before starting another.")
            return
        self._write_in_flight = True
        self._write_token += 1
        token = self._write_token
        self._status.SetLabel("Sending action to GitHub...")

        def worker() -> None:
            wx = self._wx
            try:
                message = work()
            except (GitHubItemsError, GitHubExploreError) as exc:
                wx.CallAfter(self._write_done, token, _words(exc), False)
                return
            except Exception as exc:  # noqa: BLE001 - say any provider failure
                wx.CallAfter(self._write_done, token, f"Action failed: {exc}", False)
                return
            wx.CallAfter(self._write_done, token, message, reload_view)

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: GitHub write.

    def _read_then(self, work: Callable[[], Any], then: Callable[[Any], None]) -> None:
        """Read off the UI thread, then continue on it (a prompt that needs the answer)."""
        token = getattr(self, "_wave4_read_token", 0) + 1
        self._wave4_read_token = token
        self._status.SetLabel("Reading from GitHub...")

        def finish(result: Any) -> None:
            if token != self._wave4_read_token or not dialog_alive(self.dialog):
                return
            if isinstance(result, Exception):
                message = _words(result)
                self._status.SetLabel(message)
                self._announce(message)
                return
            self._status.SetLabel("")
            then(result)

        def worker() -> None:
            try:
                result: Any = work()
            except Exception as exc:  # noqa: BLE001 - shown on the UI thread
                result = exc
            self._wx.CallAfter(finish, result)

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: GitHub read.

    # -- Repository actions --------------------------------------------------

    def _sync_fork(self, repo: str) -> None:
        if not self._confirm(
            f"Sync {repo} with its upstream? GitHub merges the upstream's new commits "
            "into the fork's default branch.",
            "Sync Fork",
        ):
            return
        self._run_wave4(lambda: self._actions().sync_fork(repo))

    def _set_topics(self, repo: str) -> None:
        def ask(current: tuple[str, ...]) -> None:
            text = self._prompt(
                f"Topics for {repo}, separated by spaces or commas (blank removes them all):",
                "Set Topics",
                " ".join(current),
            )
            if text is None:
                return

            def work() -> str:
                topics = self._actions().set_topics(repo, text)
                if not topics:
                    return f"{repo} now has no topics."
                return f"Topics for {repo} are now: {', '.join(topics)}."

            self._run_wave4(work)

        self._read_then(lambda: self._actions().get_topics(repo), ask)

    def _choose_watch_level(self, repo: str) -> None:
        def ask(current: str) -> None:
            wx = self._wx
            labels = [label for _key, label in WATCH_LEVELS]
            with wx.SingleChoiceDialog(
                self.dialog,
                f"How to watch {repo}. GitHub reports it now as: {watch_level_words(current)}.",
                "Watch Level",
                labels,
            ) as dialog:
                keys = [key for key, _label in WATCH_LEVELS]
                dialog.SetSelection(keys.index(current) if current in keys else 0)
                if self._show_choice(dialog, "Watch Level") != wx.ID_OK:
                    return
                level = keys[dialog.GetSelection()]
            if level == "releases":
                opened = webbrowser.open(f"https://github.com/{repo}")
                self._announce(
                    "GitHub's API cannot set Releases only. "
                    + (
                        "Opened the repository page; use its Watch button."
                        if opened
                        else "Use the Watch button on the repository's page."
                    )
                )
                return

            def work() -> str:
                self._actions().set_watch_level(repo, level)
                return f"{repo}: {watch_level_words(level)}."

            self._run_wave4(work)

        self._read_then(lambda: self._actions().get_watch_level(repo), ask)

    def _set_archived(self, repo: str, archived: bool) -> None:
        question = (
            f"Archive {repo}? It becomes read-only: no pushes, issues or pull requests "
            "until it is unarchived."
            if archived
            else f"Unarchive {repo}? It takes pushes, issues and pull requests again."
        )
        title = "Archive Repository" if archived else "Unarchive Repository"
        if not self._confirm(question, title):
            return

        def work() -> str:
            self._actions().set_archived(repo, archived)
            return f"{repo} is {'archived' if archived else 'no longer archived'}."

        self._run_wave4(work, reload_view=True)

    def _from_template(self, template: str) -> None:
        from quill.ui.github_repo_admin_dialogs import CreateRepositoryDialog

        result = CreateRepositoryDialog(self.dialog).show()
        if result is None:
            return

        def work() -> str:
            full_name, url = self._actions().create_from_template(
                template,
                result.name,
                owner=result.org,
                description=result.description,
                private=result.private,
            )
            return f"Created {full_name} from the template {template}: {url}"

        self._run_wave4(work)

    def _delete_repository(self, repo: str) -> None:
        from quill.ui.github_repo_admin_dialogs import TypedConfirmDialog

        if not TypedConfirmDialog(
            self.dialog,
            title="Delete Repository",
            message=(
                f"Delete {repo} and everything in it: code, issues, pull requests, wiki and "
                "releases. This cannot be undone. Type the repository's full name to confirm."
            ),
            expected=repo,
            confirm_label="Delete",
        ).show():
            self._announce("Cancelled; the repository was not deleted.")
            return

        def work() -> str:
            self._actions().delete_repository(repo)
            return f"Deleted {repo}."

        self._run_wave4(work, reload_view=True)

    # -- People and caches ---------------------------------------------------

    def _set_following(self, login: str, follow: bool) -> None:
        def work() -> str:
            self._actions().set_following(login, follow)
            return f"You now follow @{login}." if follow else f"You no longer follow @{login}."

        self._run_wave4(work)

    def _delete_cache(self, row: ExploreRow) -> None:
        name = row.label.split(",", 1)[0]
        if not self._confirm(
            f"Delete the Actions cache {name} from {row.repo}? Workflows build it again "
            "the next time they need it.",
            "Delete Cache",
        ):
            return

        def work() -> str:
            self._actions().delete_cache(row.repo, row.key)
            return f"Deleted the cache {name}."

        self._run_wave4(work, reload_view=True)

    # -- Rate limit ----------------------------------------------------------

    def _show_rate_limit(self) -> None:
        token = getattr(self._client._provider, "token", None)

        def say(report: Any) -> None:
            sentence = report.sentence()
            self._status.SetLabel(sentence)
            self._announce(sentence)

        def work() -> Any:
            try:
                return fetch_rate_limit_report(token)
            except GitHubRateLimitError as exc:
                raise GitHubExploreError(_words(exc)) from exc

        self._read_then(work, say)

    # -- Quiet refresh -------------------------------------------------------

    def _note_if_unchanged(self, view: str, message: str) -> str:
        """Say "No changes" when a reload of the same view found the same rows."""
        if view in _NO_CHANGE_VIEWS_EXCLUDED:
            return message
        key = (
            view,
            self._repo.GetValue().strip().casefold(),
            self._query.GetValue().strip(),
            self._person.GetValue().strip().casefold(),
        )
        signature = tuple((row.label, row.detail) for row in self._rows)
        seen: dict[tuple[str, ...], tuple[tuple[str, str], ...]] = getattr(
            self, "_wave4_signatures", {}
        )
        self._wave4_signatures = seen
        previous = seen.get(key)
        seen[key] = signature
        if previous is not None and previous == signature:
            return f"No changes since the last load; {len(self._rows)} results."
        return message

    def _show_choice(self, dialog: Any, title: str) -> int:
        from quill.ui.dialog_contract import show_modal_dialog

        return int(show_modal_dialog(dialog, title, announce=self._announce))


def _words(exc: BaseException) -> str:
    text = str(exc.args[0]) if exc.args else str(exc)
    return text
