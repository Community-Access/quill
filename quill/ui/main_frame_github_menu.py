"""GitHub Workbench Mode and the GitHub menu, for ``MainFrame`` (2026-11-08).

View > GitHub Workbench Mode is a check item. While it is on, a GitHub menu sits
on the bar right after Tools, and the GitHub rows of File > Open from Remote and
Tools > Git and GitHub move into it; leaving the mode puts them back. Both
arrangements are built here from one wx-free table,
:mod:`quill.core.github.workbench_menu`, which QUILL Lite builds from too.

Rows keep their command ids wherever they sit, and every label goes through
``_menu_label``, so a key the user bound follows the row (keys belong to command
ids, never to menus). The existing GitHub rows keep their existing menu ids and
bindings; the new ones are bound here to the command registry.

The mode's own entry points (Inbox, My Work, the three Items views, Explore) are
:class:`quill.ui.github_workbench_commands.GitHubWorkbenchCommands`, which QUILL
Lite shares. This mixin is the adapter: it owns no view logic of its own, and
``tests/unit/ui/test_github_workbench_menu_bar.py`` asserts that.

The mode is per window and is not remembered: QUILL starts in normal mode.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quill.core.github import workbench_menu as table
from quill.core.i18n import _

#: The existing GitHub rows' menu ids, by command id (created in
#: ``main_frame_menu.py`` and bound in ``main_frame_menu_bindings.py`` and
#: ``main_frame_github.py``).
_EXISTING_IDS: dict[str, str] = {
    "file.open_github_repository": "_id_github_repository",
    "file.open_github_file_url": "_id_github_file_url",
    "file.github_save_back": "_id_github_save_back",
    "file.github_manage_accounts": "_id_github_manage_accounts",
    "file.open_github_items": "_id_github_items",
    "file.open_github_reference": "_id_github_reference",
    "sync.sync_folder": "_id_git_sync_folder",
    "github.create_repository": "_id_github_create_repo",
    "github.fork_repository": "_id_github_fork_repo",
    "github.rename_repository": "_id_github_rename_repo",
    "github.change_repository_visibility": "_id_github_change_visibility",
    "github.change_default_branch": "_id_github_change_default_branch",
    "github.configure_branch_protection": "_id_github_branch_protection",
    "github.delete_branch": "_id_github_delete_branch",
    "github.commit_multiple_files": "_id_github_commit_multiple",
    "github.browse_organization": "_id_github_browse_org",
    "github.create_release": "_id_github_create_release",
    "github.dispatch_workflow": "_id_github_dispatch_workflow",
    "github.view_notifications": "_id_github_notifications",
    "github.view_security_alerts": "_id_github_security_alerts",
    "github.list_codespaces": "_id_github_list_codespaces",
    "github.create_codespace": "_id_github_create_codespace",
    "localgit.uncommitted_changes": "_id_localgit_uncommitted",
    "localgit.switch_branch": "_id_localgit_switch_branch",
    "localgit.stash_changes": "_id_localgit_stash_changes",
    "localgit.manage_stashes": "_id_localgit_manage_stashes",
    "localgit.blame_at_cursor": "_id_localgit_blame",
    "localgit.bisect_start": "_id_localgit_bisect_start",
    "localgit.bisect_reset": "_id_localgit_bisect_reset",
    "localgit.resolve_conflicts": "_id_localgit_resolve_conflicts",
    "localgit.interactive_rebase": "_id_localgit_interactive_rebase",
    "localgit.rebase_abort": "_id_localgit_rebase_abort",
    "localgit.worktrees": "_id_localgit_worktrees",
    "localgit.new_worktree": "_id_localgit_new_worktree",
    "help.github_guide": "_id_open_github_guide",
}

#: The new commands' titles in the command registry and the palette.
_NEW_TITLES: dict[str, str] = {
    table.TOGGLE_COMMAND_ID: "GitHub Workbench Mode",
    "github.workbench_inbox": "GitHub Inbox...",
    "github.workbench_my_work": "GitHub My Work...",
    "github.workbench_issues": "GitHub Issues and Pull Requests...",
    "github.workbench_actions_runs": "GitHub Actions Runs...",
    "github.workbench_releases": "GitHub Releases...",
    "github.workbench_explore": "Explore GitHub...",
    "github.clone_repository": "Clone GitHub Repository...",
}


class GitHubWorkbenchMenuMixin:
    """The mode switch, the GitHub menu, and the rows' normal homes."""

    _github_workbench_mode: bool = False

    # -- commands ----------------------------------------------------------- #

    def _register_github_workbench_commands(self) -> None:
        """Register the switch, the view rows and Clone (main_frame_commands)."""
        handlers = {
            table.TOGGLE_COMMAND_ID: self.toggle_github_workbench_mode,
            "github.clone_repository": self.clone_github_repository,
        }
        for command_id, title in _NEW_TITLES.items():
            handler = handlers.get(command_id) or (
                lambda cid=command_id: self._github_workbench_commands().run(cid)
            )
            self.commands.register(command_id, title, handler, self._binding_for(command_id))

    def _github_workbench_commands(self) -> Any:
        from quill.ui.github_workbench_commands import GitHubWorkbenchCommands

        return GitHubWorkbenchCommands(
            open_items=lambda view: self.open_github_items_viewer(initial_view=view),
            open_explore=self.open_github_explore,
        )

    def _github_workbench_available(self) -> bool:
        return bool(self._feature_enabled("core.github_remote"))

    def toggle_github_workbench_mode(self) -> None:
        """View > GitHub Workbench Mode, and the GitHub menu's Leave row."""
        if not self._github_workbench_mode and not self._github_workbench_available():
            self._announce("GitHub is turned off in this profile.")
            return
        self._github_workbench_mode = not self._github_workbench_mode
        # Said first, then rebuilt: the sentence is queued before the work of
        # rebuilding the largest bar in the family, so it is never late.
        self._announce(table.ANNOUNCE_ON if self._github_workbench_mode else table.ANNOUNCE_OFF)
        self._build_menu()
        # The Workbench status cell comes or goes with the mode, unannounced
        # (main_frame_github_status): the sentence above already said so.
        refresh = getattr(self, "_refresh_github_status_cell", None)
        if callable(refresh):
            refresh()

    def clone_github_repository(self) -> None:
        """GitHub > Clone Repository..., and File > Open from Remote > Clone Repository..."""
        from quill.ui.github_clone import CloneHost, default_clone_folder, start_clone

        def run_background(name: str, work: Any, on_done: Any, on_failed: Any) -> None:
            self._task_manager.submit(
                name,
                lambda **_kwargs: work(),
                on_success=lambda _op, folder: on_done(folder),
                on_failure=lambda _op, error: on_failed(error),
            )

        start_clone(
            CloneHost(
                parent=self.frame,
                announce=self._announce,
                run_background=run_background,
                after_clone=self._after_github_clone,
                initial_repo=self._github_items_initial_repo(),
                default_folder=default_clone_folder(),
                safe_mode=bool(getattr(self, "_safe_mode", False)),
            )
        )

    def _after_github_clone(self, folder: Path) -> None:
        """Offer the new folder: as a project (Developer profile), or a file from it."""
        wx = self._wx
        developer = bool(self._feature_enabled("core.developer"))
        style = (wx.YES_NO | wx.CANCEL if developer else wx.YES_NO) | wx.ICON_QUESTION
        dialog = wx.MessageDialog(
            self.frame, f"Cloned into {folder}. Open it now?", "Clone Repository", style
        )
        if developer:
            dialog.SetYesNoCancelLabels("Open a &File...", "Open as &Project", "Not Now")
        else:
            dialog.SetYesNoLabels("Open a &File...", "Not Now")
        try:
            answer = self._show_modal_dialog(dialog, "Clone Repository")
        finally:
            dialog.Destroy()
        if answer == wx.ID_YES:
            with wx.FileDialog(
                self.frame, "Open a file from the clone", str(folder), style=wx.FD_OPEN
            ) as chooser:
                if self._show_modal_dialog(chooser, "Open a file from the clone") == wx.ID_OK:
                    self.open_file(Path(chooser.GetPath()))
        elif answer == wx.ID_NO and developer:
            self.open_project_at(folder)

    # -- building the rows -------------------------------------------------- #

    def _github_row_id(self, command_id: str) -> Any:
        """The row's menu id: the existing one, or a new one bound to the registry."""
        attribute = _EXISTING_IDS.get(command_id)
        if attribute is not None:
            existing = getattr(self, attribute, None)
            if existing is None:
                existing = self._wx.NewIdRef()
                setattr(self, attribute, existing)
            return existing
        ids: dict[str, Any] = self.__dict__.setdefault("_github_new_ids", {})
        if command_id not in ids:
            new_id = self._wx.NewIdRef()
            ids[command_id] = new_id
            self.frame.Bind(
                self._wx.EVT_MENU, lambda _e, cid=command_id: self.commands.run(cid), id=new_id
            )
        return ids[command_id]

    def _github_append_row(self, menu: Any, row: table.Row) -> None:
        menu.Append(
            self._github_row_id(row.command_id), self._menu_label(_(row.label), row.command_id)
        )

    def _github_fill(self, menu: Any, entries: Any) -> int:
        return table.fill(menu, entries, self._github_append_row, self._wx.Menu)

    def _append_github_remote_rows(self, remote_menu: Any) -> None:
        """File > Open from Remote's GitHub rows, while the mode is off."""
        # Built first of all the GitHub rows, so this is where a fresh bar gets
        # fresh ids. Open GitHub Reference's id is bound by main_frame_github.py
        # whichever mode is on, so it must exist either way.
        self.__dict__["_github_new_ids"] = {}
        self._id_github_reference = self._wx.NewIdRef()
        if self._github_workbench_mode:
            return
        remote_menu.AppendSeparator()
        self._github_fill(remote_menu, table.NORMAL_REMOTE_ROWS)

    def _append_git_family_menu(self, tools_menu: Any) -> None:
        """Tools > Git and GitHub (GitHub, Local Git), while the mode is off."""
        if self._github_workbench_mode:
            return
        wx = self._wx
        git_family = wx.Menu()
        repository = wx.Menu()
        self._github_fill(repository, table.REPOSITORY_ROWS)
        git_family.AppendSubMenu(repository, _("Git&Hub"))
        local_git = wx.Menu()
        self._github_fill(local_git, table.LOCAL_GIT_ROWS)
        git_family.AppendSubMenu(local_git, _("&Local Git"))
        tools_menu.AppendSubMenu(git_family, _("&Git and GitHub"))

    def _append_github_workbench_toggle(self, view_menu: Any) -> None:
        """View > GitHub Workbench Mode, where GitHub is on."""
        if not self._github_workbench_available():
            # GitHub switched off while the mode was on: the mode ends quietly
            # with the rebuild, because there is nothing left to arrange.
            self._github_workbench_mode = False
            return
        self._id_github_workbench_mode = self._github_row_id(table.TOGGLE_COMMAND_ID)
        view_menu.AppendCheckItem(
            self._id_github_workbench_mode,
            self._menu_label(_(table.TOGGLE_VIEW_LABEL), table.TOGGLE_COMMAND_ID),
        )
        view_menu.Check(self._id_github_workbench_mode, self._github_workbench_mode)

    def _append_github_workbench_menu(self, menu_bar: Any) -> None:
        """The GitHub menu, right after Tools, while the mode is on."""
        if not self._github_workbench_mode:
            self._github_readout_id = None
            return
        wx = self._wx
        menu = wx.Menu()
        self._github_readout_id = wx.NewIdRef()
        label = table.readout_label(self._github_items_initial_repo())
        if label:
            menu.Append(self._github_readout_id, label)
            menu.Enable(self._github_readout_id, False)  # a status readout, not a command
        # The Leave row: the switch's second label, on its own id so the View
        # check item stays the only checkable item for the command.
        leave_id = wx.NewIdRef()
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.toggle_github_workbench_mode(), id=leave_id)
        first, *rest = table.WORKBENCH_ROWS
        assert isinstance(first, table.Row) and first.command_id == table.TOGGLE_COMMAND_ID
        menu.Append(leave_id, self._menu_label(_(first.label), table.TOGGLE_COMMAND_ID))
        self._github_fill(menu, rest)
        # A literal, so the bar gates read it (test_menu_bar_access_keys, the menu
        # shape gate); a test holds it equal to table.GITHUB_MENU_TITLE.
        menu_bar.Append(menu, _("&GitHub"))

    def _refresh_github_readout(self, menu_bar: Any) -> None:
        """Keep the repository readout current as the document changes."""
        readout = getattr(self, "_github_readout_id", None)
        if readout is None or menu_bar is None:
            return
        item = menu_bar.FindItemById(readout)
        label = table.readout_label(self._github_items_initial_repo())
        if item is not None and label:
            item.SetItemLabel(label)

    # -- the accelerator map ------------------------------------------------ #

    def _command_to_menu_id_map(self) -> dict[str, int]:
        """Add the GitHub rows, so a key bound to one fires in either mode."""
        mapping: dict[str, int] = super()._command_to_menu_id_map()  # type: ignore[misc]
        for command_id in (*table.command_ids(), *table.command_ids(table.NORMAL_REMOTE_ROWS)):
            if command_id in mapping:
                continue
            attribute = _EXISTING_IDS.get(command_id)
            menu_id = (
                getattr(self, attribute, None)
                if attribute is not None
                else self.__dict__.get("_github_new_ids", {}).get(command_id)
            )
            if menu_id is not None:
                mapping[command_id] = menu_id
        return mapping
