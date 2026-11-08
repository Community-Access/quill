"""QUILL Lite's GitHub Workbench: the opener, workbench mode and the GitHub menu (2026-11-08).

The Workbench opener (File > GitHub Workbench...) lived in ``lite_window_tools.py``;
it moved here with the rows workbench mode added, so the empty window can share
all of them: :class:`~quill.apps.lite_window.DocumentFrame` and the empty window's
:class:`~quill.apps.lite_shell_menu.ShellMenuMixin` both mix this in.

* **The gates** (Safe Mode, PyGithub, the first-use consent, the no-account
  offer) are in :meth:`GitHubWorkbenchLiteMixin._github_provider`, once, and every
  row goes through it.
* **The view rows** (Inbox, My Work, Notifications, Issues and Pull Requests,
  Actions Runs, Releases, Explore GitHub) are QUILL's, through the one shared
  :class:`quill.ui.github_workbench_commands.GitHubWorkbenchCommands`.
* **Workbench mode** is per window: View > GitHub Workbench Mode (and the GitHub
  menu's Leave row) flips it, says one sentence, and rebuilds this window's bar.
  It is not remembered; a new window starts in normal mode.
* **Clone Repository...** is the shared :mod:`quill.ui.github_clone`; afterwards
  QUILL Lite offers to open a file from the new folder.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import wx

from quill.core.github import workbench_menu
from quill.ui.dialog_contract import show_message_box

__all__ = ["GitHubWorkbenchLiteMixin"]

_TITLE = "GitHub Workbench"


class GitHubWorkbenchLiteMixin:
    """The GitHub rows of a QUILL Lite window, document or empty."""

    app: Any
    path: Any
    _github_workbench_mode: bool = False

    # -- the gates, once ---------------------------------------------------- #

    def _github_provider(self, retry: Any) -> Any:
        """A provider ready to use, or ``None`` after saying why not."""
        from quill.core.github.consent import (
            load_github_consent_complete,
            save_github_consent_complete,
        )
        from quill.core.github.github_provider import GitHubDependencyError, require_pygithub
        from quill.core.github.items_provider import (
            GitHubItemsError,
            GitHubItemsProvider,
            refuse_in_safe_mode,
        )
        from quill.core.github.token_store import load_github_token
        from quill.ui.github_dialogs import GitHubConsentDialog

        try:
            refuse_in_safe_mode(bool(getattr(self.app, "safe_mode", False)))
            require_pygithub()
        except (GitHubItemsError, GitHubDependencyError) as exc:
            show_message_box(str(exc), _TITLE, wx.OK | wx.ICON_INFORMATION, self)
            return None
        if not load_github_consent_complete():
            if not GitHubConsentDialog(self).show():
                return None
            save_github_consent_complete()
        token = load_github_token()
        # No account: say so and offer to add one, rather than opening as a
        # guest without a word. Continue as Guest is still one key away.
        if not token and not self._github_workbench_as_guest(retry):  # type: ignore[attr-defined]
            return None
        try:
            return GitHubItemsProvider(token=token or None)
        except GitHubItemsError as exc:
            show_message_box(str(exc), _TITLE, wx.OK | wx.ICON_INFORMATION, self)
            return None

    def _github_repository(self) -> str:
        from quill.core.github.local_repo import detect_github_repo

        return detect_github_repo(self.path)

    # -- the two windows ---------------------------------------------------- #

    def open_github_items(self, initial_view: str = "", reference: Any = None) -> None:
        """GitHub Items, on a view (the GitHub menu) or a reference (from Explore)."""
        from quill.ui.github_items_dialog import GitHubItemsDialog

        provider = self._github_provider(lambda: self.open_github_items(initial_view, reference))
        if provider is None:
            return
        try:
            GitHubItemsDialog(
                self,
                provider,
                initial_repo=reference.repository if reference else self._github_repository(),
                initial_reference=reference,
                initial_view=initial_view,
                open_file_reference_cb=self._open_github_file_reference,  # type: ignore[attr-defined]
                announce_cb=self._announce,  # type: ignore[attr-defined]
                gist_source_cb=getattr(self, "_github_gist_source", None),
            ).show()
        finally:
            provider.close()

    def open_github_explore(self, initial_view: str | None = None) -> None:
        """Explore GitHub on a view; Enter on an issue or pull request opens it in Items."""
        from quill.ui.github_explore_dialog import GitHubExploreDialog

        provider = self._github_provider(lambda: self.open_github_explore(initial_view))
        if provider is None:
            return
        chosen: list[Any] = []
        try:
            GitHubExploreDialog(
                self,
                provider,
                initial_repo=self._github_repository(),
                initial_view=initial_view,
                announce_cb=self._announce,  # type: ignore[attr-defined]
                on_open_reference=chosen.append,
                gist_source_cb=getattr(self, "_github_gist_source", None),
            ).show()
        finally:
            provider.close()
        if chosen:
            self.open_github_items(reference=chosen[0])

    def _github_views(self) -> Any:
        from quill.ui.github_workbench_commands import GitHubWorkbenchCommands

        return GitHubWorkbenchCommands(self.open_github_items, self.open_github_explore)

    # -- the rows ----------------------------------------------------------- #

    def cmd_github_workbench(self) -> None:
        """File > GitHub Workbench... (Repository Items in the GitHub menu)."""
        self.open_github_items()

    def cmd_github_inbox(self) -> None:
        """GitHub > Inbox...: Explore's attention queue."""
        self._github_views().inbox()

    def cmd_github_my_work(self) -> None:
        """GitHub > My Work..."""
        self._github_views().my_work()

    def cmd_github_notifications(self) -> None:
        """GitHub > Notifications..."""
        self._github_views().notifications()

    def cmd_github_issues(self) -> None:
        """GitHub > Issues and Pull Requests...: GitHub Items on its issues view."""
        self._github_views().issues()

    def cmd_github_actions_runs(self) -> None:
        """GitHub > Actions Runs...: GitHub Items on its runs view."""
        self._github_views().actions_runs()

    def cmd_github_releases(self) -> None:
        """GitHub > Releases...: GitHub Items on its releases view."""
        self._github_views().releases()

    def cmd_github_explore(self) -> None:
        """GitHub > Explore GitHub..."""
        self._github_views().explore()

    def cmd_toggle_github_workbench(self) -> None:
        """View > GitHub Workbench Mode, and GitHub > Leave Workbench Mode."""
        self._github_workbench_mode = not self._github_workbench_mode
        self._announce(  # type: ignore[attr-defined]
            workbench_menu.ANNOUNCE_ON
            if self._github_workbench_mode
            else workbench_menu.ANNOUNCE_OFF
        )
        # The document window's bar, or the empty window's: each host says how.
        self.rebuild_workbench_menus()  # type: ignore[attr-defined]

    def cmd_github_clone(self) -> None:
        """File > Clone Repository..., and GitHub > Clone Repository..."""
        from quill.apps.lite_window_open import app_task_manager
        from quill.ui.github_clone import CloneHost, default_clone_folder, start_clone

        def run_background(name: str, work: Any, on_done: Any, on_failed: Any) -> None:
            app_task_manager(self.app).submit(
                name,
                lambda **_kwargs: work(),
                on_success=lambda _op, folder: on_done(folder),
                on_failure=lambda _op, error: on_failed(error),
            )

        start_clone(
            CloneHost(
                parent=self,
                announce=self._announce,  # type: ignore[attr-defined]
                run_background=run_background,
                after_clone=self._after_github_clone,
                initial_repo=self._github_repository(),
                default_folder=default_clone_folder(),
                safe_mode=bool(getattr(self.app, "safe_mode", False)),
            )
        )

    def _after_github_clone(self, folder: Path) -> None:
        """Offer to open a file from the new folder."""
        answer = show_message_box(
            f"Cloned into {folder}. Open a file from it?",
            "Clone Repository",
            wx.YES_NO | wx.ICON_QUESTION,
            self,
        )
        if answer != wx.YES:
            return
        from quill.core.lite.filetypes import OPEN_WILDCARD
        from quill.ui.dialog_contract import show_modal_dialog

        with wx.FileDialog(
            self,  # type: ignore[arg-type]
            "Open a file from the clone",
            str(folder),
            wildcard=OPEN_WILDCARD,
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as chooser:
            if show_modal_dialog(chooser, "Open a file from the clone") != wx.ID_OK:
                return
            chosen = Path(chooser.GetPath())
        self.app.open_path(chosen)
