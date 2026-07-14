"""Local git accessibility commands for ``MainFrame`` (`docs/planning/
github.md` section 4): uncommitted changes, branch switch, stash, blame,
bisect, merge-conflict resolution, and interactive rebase.

Every command here resolves a repository root the same way (the nearest
enclosing ``.git`` above the current document, walking up like
``quill.core.github.local_repo``'s detector; a folder prompt when no
document is open or none is found), requires :mod:`quill.core.git_binaries`
to have located a ``git`` executable (offering Download Optional Components
when it hasn't), and runs the actual git subprocess work on a background
thread via ``_run_background_task`` -- the same shape every other GitHub/
git command in QUILL already uses.

This mixin never talks to GitHub's API and never pushes/pulls a remote --
that split mirrors :mod:`quill.core.local_git` itself.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any


class LocalGitMixin:
    """Adds local git accessibility commands to ``MainFrame``."""

    # ------------------------------------------------------------------
    # Repository root resolution + small shared helpers

    def _local_git_repo_root(self) -> str | None:
        path = getattr(getattr(self, "document", None), "path", None)
        if path:
            found = self._local_git_find_root(Path(path))
            if found:
                return str(found)
        wx = self._wx
        with wx.DirDialog(
            self.frame, "Choose a git repository folder", style=wx.DD_DEFAULT_STYLE
        ) as dialog:
            if self._show_modal_dialog(dialog, "Choose Folder") != wx.ID_OK:
                return None
            chosen = Path(dialog.GetPath())
        found = self._local_git_find_root(chosen)
        if found is None:
            self._set_status(f"'{chosen}' is not a git repository")
            return None
        return str(found)

    @staticmethod
    def _local_git_find_root(start: Path) -> Path | None:
        current = start if start.is_dir() else start.parent
        for folder in (current, *current.parents):
            if (folder / ".git").exists():
                return folder
        return None

    def _local_git_ready(self) -> bool:
        if os.environ.get("QUILL_SAFE_MODE") == "1":
            self._set_status("Local git commands are disabled in Safe Mode")
            return False
        from quill.core.git_binaries import git_available

        if not git_available():
            self._show_message_box(
                "Local git commands need git. Install it from "
                "Help > Download Optional Components, or install git yourself "
                "and make sure it's on your PATH.",
                "Git Not Found",
                self._wx.ICON_INFORMATION | self._wx.OK,
            )
            return False
        return True

    def _local_git_confirm(self, message: str, title: str) -> bool:
        wx = self._wx
        dialog = wx.MessageDialog(
            self.frame, message, title, wx.YES_NO | wx.NO_DEFAULT | wx.ICON_INFORMATION
        )
        try:
            return self._show_modal_dialog(dialog, title) == wx.ID_YES
        finally:
            dialog.Destroy()

    def _local_git_runner(self):
        from quill.stability.safe_subprocess import run_subprocess_safely

        return run_subprocess_safely

    # ------------------------------------------------------------------
    # Uncommitted changes

    def local_git_uncommitted_changes(self) -> None:
        """Tools > Local Git > Uncommitted Changes..."""
        if not self._local_git_ready():
            return
        root = self._local_git_repo_root()
        if root is None:
            return

        from quill.core.local_git import get_status

        def work(_progress: object) -> object:
            return get_status(root, runner=self._local_git_runner())

        self._run_background_task(
            "Checking for changes",
            work,
            lambda status: self._on_local_git_status_for_uncommitted(root, status),
        )

    def _on_local_git_status_for_uncommitted(self, root: str, status: Any) -> None:
        if not status.changes:
            self._set_status("No uncommitted changes")
            return
        from quill.core.local_git import file_content_at_ref
        from quill.ui.local_git_dialogs import UncommittedChangesDialog

        def diff_provider(path: str) -> tuple[str, str]:
            head_text = file_content_at_ref(root, "HEAD", path, runner=self._local_git_runner())
            working_path = Path(root) / path
            try:
                working_text = working_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                working_text = ""
            return head_text, working_text

        UncommittedChangesDialog(
            self.frame,
            list(status.changes),
            diff_provider=diff_provider,
            on_stage=lambda path: self._local_git_stage(root, path),
            on_unstage=lambda path: self._local_git_unstage(root, path),
            on_stage_all=lambda: self._local_git_stage_all(root),
            announce_cb=self._announce,
        ).show()

    def _local_git_stage(self, root: str, path: str) -> None:
        from quill.core.local_git import stage_file

        stage_file(root, path, runner=self._local_git_runner())
        self._set_status(f"Staged {path}")

    def _local_git_unstage(self, root: str, path: str) -> None:
        from quill.core.local_git import unstage_file

        unstage_file(root, path, runner=self._local_git_runner())
        self._set_status(f"Unstaged {path}")

    def _local_git_stage_all(self, root: str) -> None:
        from quill.core.local_git import stage_all

        stage_all(root, runner=self._local_git_runner())
        self._set_status("Staged all changes")

    # ------------------------------------------------------------------
    # Branches

    def local_git_switch_branch(self) -> None:
        """Tools > Local Git > Switch Branch..."""
        if not self._local_git_ready():
            return
        root = self._local_git_repo_root()
        if root is None:
            return

        from quill.core.local_git import list_local_branches

        def work(_progress: object) -> object:
            return list_local_branches(root, runner=self._local_git_runner())

        self._run_background_task(
            "Loading branches", work, lambda branches: self._on_local_git_branches(root, branches)
        )

    def _on_local_git_branches(self, root: str, branches: list[Any]) -> None:
        names = [b.name for b in branches if not b.is_current]
        if not names:
            self._set_status("No other local branches")
            return
        wx = self._wx
        with wx.SingleChoiceDialog(self.frame, "Switch to:", "Switch Branch", names) as dialog:
            if self._show_modal_dialog(dialog, "Switch Branch") != wx.ID_OK:
                self._set_status("Branch switch cancelled")
                return
            target = dialog.GetStringSelection()

        from quill.core.local_git import switch_branch

        def work(_progress: object) -> object:
            return switch_branch(root, target, runner=self._local_git_runner())

        def on_done(result: Any) -> None:
            if not result.ok and "uncommitted" in result.message:
                if self._local_git_confirm(
                    f"{result.message} Switch anyway and carry them over?", "Uncommitted Changes"
                ):
                    self._local_git_force_switch(root, target)
                    return
            self._set_status(result.message)

        self._run_background_task(f"Switching to {target}", work, on_done)

    def _local_git_force_switch(self, root: str, target: str) -> None:
        from quill.core.local_git import switch_branch

        def work(_progress: object) -> object:
            return switch_branch(root, target, runner=self._local_git_runner(), force=True)

        self._run_background_task(
            f"Switching to {target}", work, lambda result: self._set_status(result.message)
        )

    # ------------------------------------------------------------------
    # Stash

    def local_git_stash_changes(self) -> None:
        """Tools > Local Git > Stash Changes..."""
        if not self._local_git_ready():
            return
        root = self._local_git_repo_root()
        if root is None:
            return
        message = self._local_git_prompt_single("Stash Changes", "Stash message (optional):", "")
        if message is None:
            return

        from quill.core.local_git import stash_save

        def work(_progress: object) -> object:
            stash_save(root, message, runner=self._local_git_runner())
            return None

        self._run_background_task(
            "Stashing changes", work, lambda _r: self._set_status("Changes stashed")
        )

    def local_git_manage_stashes(self) -> None:
        """Tools > Local Git > Manage Stashes..."""
        if not self._local_git_ready():
            return
        root = self._local_git_repo_root()
        if root is None:
            return

        from quill.core.local_git import list_stashes

        def work(_progress: object) -> object:
            return list_stashes(root, runner=self._local_git_runner())

        self._run_background_task(
            "Loading stashes", work, lambda stashes: self._on_local_git_stashes(root, stashes)
        )

    def _on_local_git_stashes(self, root: str, stashes: list[Any]) -> None:
        if not stashes:
            self._set_status("No stashes")
            return
        wx = self._wx
        labels = [f"{s.ref}: {s.message}" for s in stashes]
        with wx.SingleChoiceDialog(self.frame, "Stash:", "Manage Stashes", labels) as dialog:
            if self._show_modal_dialog(dialog, "Manage Stashes") != wx.ID_OK:
                return
            index = dialog.GetSelection()
        chosen = stashes[index]
        menu = wx.Menu()
        apply_id, drop_id = wx.NewIdRef(), wx.NewIdRef()
        menu.Append(apply_id, "Apply")
        menu.Append(drop_id, "Drop")

        def on_pick(event: object) -> None:
            picked = int(event.GetId())
            from quill.core.local_git import stash_apply, stash_drop

            if picked == int(apply_id):
                stash_apply(root, chosen.ref, runner=self._local_git_runner())
                self._set_status(f"Applied {chosen.ref}")
            elif picked == int(drop_id):
                stash_drop(root, chosen.ref, runner=self._local_git_runner())
                self._set_status(f"Dropped {chosen.ref}")

        menu.Bind(wx.EVT_MENU, on_pick)
        try:
            self.frame.PopupMenu(menu)
        finally:
            menu.Destroy()

    # ------------------------------------------------------------------
    # Blame

    def local_git_blame_at_cursor(self) -> None:
        """Tools > Local Git > Who Wrote This Line..."""
        if not self._local_git_ready():
            return
        path = getattr(getattr(self, "document", None), "path", None)
        if not path:
            self._set_status("No file to blame")
            return
        root = self._local_git_find_root(Path(path))
        if root is None:
            self._set_status("This file is not inside a git repository")
            return
        try:
            line = self.editor.GetCurrentLine() + 1
        except Exception:  # noqa: BLE001 - defensive, editor state can vary
            line = 1
        rel_path = str(Path(path).resolve().relative_to(Path(root).resolve()))

        from quill.core.local_git import blame_line

        def work(_progress: object) -> object:
            return blame_line(str(root), rel_path, line, runner=self._local_git_runner())

        def on_done(info: Any) -> None:
            self._set_status(f"Line {line}: {info.author}, {info.summary} ({info.commit_sha[:7]})")

        self._run_background_task(f"Checking blame for line {line}", work, on_done)

    # ------------------------------------------------------------------
    # Bisect

    def local_git_bisect_start(self) -> None:
        """Tools > Local Git > Start Bisect..."""
        if not self._local_git_ready():
            return
        root = self._local_git_repo_root()
        if root is None:
            return
        bad = self._local_git_prompt_single("Start Bisect", "Bad commit (default HEAD):", "HEAD")
        if not bad:
            return
        good = self._local_git_prompt_single("Start Bisect", "Known-good commit or tag:", "")
        if not good:
            return

        from quill.core.local_git import bisect_start

        def work(_progress: object) -> object:
            return bisect_start(root, bad, good, runner=self._local_git_runner())

        self._run_background_task(
            "Starting bisect", work, lambda status: self._on_local_git_bisect_status(root, status)
        )

    def _on_local_git_bisect_status(self, root: str, status: Any) -> None:
        if status.done:
            self._set_status(f"Bisect complete: {status.message}")
            return
        if self._local_git_confirm(
            "QUILL checked out the next commit to test. Is this version good or bad?\n\n"
            "Yes = bad, No = good.",
            "Bisect",
        ):
            self._local_git_bisect_mark(root, "bad")
        else:
            self._local_git_bisect_mark(root, "good")

    def _local_git_bisect_mark(self, root: str, verdict: str) -> None:
        from quill.core.local_git import bisect_mark

        def work(_progress: object) -> object:
            return bisect_mark(root, verdict, runner=self._local_git_runner())

        self._run_background_task(
            f"Marking {verdict}",
            work,
            lambda status: self._on_local_git_bisect_status(root, status),
        )

    def local_git_bisect_reset(self) -> None:
        """Tools > Local Git > End Bisect"""
        if not self._local_git_ready():
            return
        root = self._local_git_repo_root()
        if root is None:
            return

        from quill.core.local_git import bisect_reset

        def work(_progress: object) -> object:
            bisect_reset(root, runner=self._local_git_runner())
            return None

        self._run_background_task(
            "Ending bisect", work, lambda _r: self._set_status("Bisect ended")
        )

    # ------------------------------------------------------------------
    # Merge conflicts

    def local_git_resolve_conflicts(self) -> None:
        """Tools > Local Git > Resolve Conflicts..."""
        if not self._local_git_ready():
            return
        root = self._local_git_repo_root()
        if root is None:
            return

        from quill.core.local_git import list_conflicted_files

        def work(_progress: object) -> object:
            return list_conflicted_files(root, runner=self._local_git_runner())

        self._run_background_task(
            "Checking for conflicts",
            work,
            lambda files: self._on_local_git_conflicted_files(root, files),
        )

    def _on_local_git_conflicted_files(self, root: str, files: list[str]) -> None:
        if not files:
            self._set_status("No conflicts to resolve")
            return
        self._local_git_resolve_next_conflict(root, files, 0)

    def _local_git_resolve_next_conflict(self, root: str, files: list[str], index: int) -> None:
        if index >= len(files):
            self._set_status(f"Resolved {len(files)} file(s)")
            return
        path = files[index]
        full_path = Path(root) / path
        try:
            text = full_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            self._set_status(f"Could not read {path}: {exc}")
            return

        from quill.core.local_git import (
            mark_conflict_resolved,
            parse_conflict_hunks,
            resolve_conflict_hunks,
        )
        from quill.ui.local_git_dialogs import MergeConflictDialog

        hunks = parse_conflict_hunks(text)
        if not hunks:
            self._local_git_resolve_next_conflict(root, files, index + 1)
            return
        resolutions = MergeConflictDialog(
            self.frame, path, hunks, announce_cb=self._announce
        ).show()
        if resolutions is None:
            self._set_status(f"Skipped {path}; {len(files) - index} file(s) still conflicted")
            return
        resolved_text = resolve_conflict_hunks(text, resolutions)
        full_path.write_text(resolved_text, encoding="utf-8")
        mark_conflict_resolved(root, path, runner=self._local_git_runner())
        self._local_git_resolve_next_conflict(root, files, index + 1)

    # ------------------------------------------------------------------
    # Interactive rebase

    def local_git_interactive_rebase(self) -> None:
        """Tools > Local Git > Interactive Rebase..."""
        if not self._local_git_ready():
            return
        root = self._local_git_repo_root()
        if root is None:
            return
        base = self._local_git_prompt_single(
            "Interactive Rebase", "Rebase onto (branch, tag, or commit):", ""
        )
        if not base:
            return

        from quill.core.local_git import build_rebase_todo

        def work(_progress: object) -> object:
            return build_rebase_todo(root, base, runner=self._local_git_runner())

        self._run_background_task(
            "Loading commits", work, lambda todo: self._on_local_git_rebase_todo(root, base, todo)
        )

    def _on_local_git_rebase_todo(self, root: str, base: str, todo: list[Any]) -> None:
        if not todo:
            self._set_status(f"No commits between {base} and HEAD")
            return
        from quill.ui.local_git_dialogs import InteractiveRebaseDialog

        chosen = InteractiveRebaseDialog(self.frame, todo, announce_cb=self._announce).show()
        if chosen is None:
            self._set_status("Rebase cancelled")
            return

        from quill.core.local_git import default_sequence_editor_command, execute_rebase

        def work(_progress: object) -> object:
            return execute_rebase(
                root,
                base,
                chosen,
                runner=self._local_git_runner(),
                sequence_editor_command=default_sequence_editor_command,
            )

        self._run_background_task(
            "Rebasing", work, lambda result: self._on_local_git_rebase_result(root, result)
        )

    def _on_local_git_rebase_result(self, root: str, result: Any) -> None:
        if result.ok:
            self._set_status(result.message)
            return
        if result.stopped_for_conflicts:
            if self._local_git_confirm(f"{result.message} Resolve them now?", "Rebase Paused"):
                self._local_git_resolve_rebase_conflicts(root)
                return
        self._set_status(result.message)

    def _local_git_resolve_rebase_conflicts(self, root: str) -> None:
        from quill.core.local_git import list_conflicted_files

        def work(_progress: object) -> object:
            return list_conflicted_files(root, runner=self._local_git_runner())

        def on_files(files: list[str]) -> None:
            self._local_git_resolve_next_rebase_conflict(root, files, 0)

        self._run_background_task("Checking conflicts", work, on_files)

    def _local_git_resolve_next_rebase_conflict(
        self, root: str, files: list[str], index: int
    ) -> None:
        if index >= len(files):
            from quill.core.local_git import rebase_continue

            def work(_progress: object) -> object:
                return rebase_continue(root, runner=self._local_git_runner())

            self._run_background_task(
                "Continuing rebase",
                work,
                lambda result: self._on_local_git_rebase_result(root, result),
            )
            return
        path = files[index]
        full_path = Path(root) / path
        try:
            text = full_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            self._set_status(f"Could not read {path}: {exc}")
            return

        from quill.core.local_git import (
            mark_conflict_resolved,
            parse_conflict_hunks,
            resolve_conflict_hunks,
        )
        from quill.ui.local_git_dialogs import MergeConflictDialog

        hunks = parse_conflict_hunks(text)
        if not hunks:
            self._local_git_resolve_next_rebase_conflict(root, files, index + 1)
            return
        resolutions = MergeConflictDialog(
            self.frame, path, hunks, announce_cb=self._announce
        ).show()
        if resolutions is None:
            self._set_status("Rebase left unresolved; run Interactive Rebase again to continue")
            return
        resolved_text = resolve_conflict_hunks(text, resolutions)
        full_path.write_text(resolved_text, encoding="utf-8")
        mark_conflict_resolved(root, path, runner=self._local_git_runner())
        self._local_git_resolve_next_rebase_conflict(root, files, index + 1)

    def local_git_rebase_abort(self) -> None:
        """Tools > Local Git > Abort Rebase"""
        if not self._local_git_ready():
            return
        root = self._local_git_repo_root()
        if root is None:
            return
        if not self._local_git_confirm(
            "Abort the in-progress rebase and restore the original branch state?", "Abort Rebase"
        ):
            return

        from quill.core.local_git import rebase_abort

        def work(_progress: object) -> object:
            rebase_abort(root, runner=self._local_git_runner())
            return None

        self._run_background_task(
            "Aborting rebase", work, lambda _r: self._set_status("Rebase aborted")
        )

    # ------------------------------------------------------------------
    # Shared prompt helper

    def _local_git_prompt_single(self, title: str, label: str, value: str = "") -> str | None:
        wx = self._wx
        with wx.TextEntryDialog(self.frame, label, title, value) as dialog:
            if self._show_modal_dialog(dialog, title) != wx.ID_OK:
                return None
            return str(dialog.GetValue()).strip()

    # ------------------------------------------------------------------
    # Download Optional Components: the git fallback for a user with neither
    # a system git nor QUILL's bundled copy (quill.core.git_binaries prefers
    # a system install first; this is purely the recovery path).

    def download_git(self, *, on_done: Callable[[bool], None] | None = None) -> None:
        """Fetch QUILL's self-hosted, SHA-256-verified copy of Git (MinGit)
        for Tools > Local Git. QUILL always prefers a system git on PATH
        first; this download exists only for a user who has neither."""
        from quill.core.git_binaries import git_available

        wx = self._wx
        if os.environ.get("QUILL_SAFE_MODE") == "1":
            self._announce("Downloading components is disabled in Safe Mode.")
            return
        if git_available():
            again = self._show_message_box(
                "Git is already installed (either on your system, or QUILL's own "
                "copy). Download QUILL's verified copy again anyway?",
                "Git",
                wx.ICON_QUESTION | wx.YES_NO,
            )
            if again != wx.YES:
                if on_done is not None:
                    on_done(True)
                return
        proceed = self._show_message_box(
            "QUILL will download a portable copy of Git (about 40 MB) and verify "
            "it. It powers Tools > Local Git's interactive rebase, merge conflict "
            "resolution, stash, blame, and bisect commands. Continue?",
            "Download Git",
            wx.ICON_INFORMATION | wx.YES_NO,
        )
        if proceed != wx.YES:
            return

        def _work(progress):
            from quill.core.git_binaries import vendor_dir
            from quill.core.release_assets import fetch_component

            fetch_component(
                "git-windows",
                vendor_dir(),
                progress=lambda fraction, message: progress(message, int(fraction * 100), 100),
                label="Downloading Git...",
            )
            return True

        def _finished(result: object) -> None:
            ok = bool(result)
            if ok:
                self._announce("Git installed. Local Git commands are ready to use.")
            else:
                self._announce("Git could not be installed.")
            if on_done is not None:
                on_done(ok)

        self._run_background_task("Downloading Git", _work, _finished)

    # ------------------------------------------------------------------
    # Command palette registration

    def _register_local_git_commands(self) -> None:
        entries = (
            (
                "localgit.uncommitted_changes",
                "Local Git: Uncommitted Changes...",
                self.local_git_uncommitted_changes,
            ),
            ("localgit.switch_branch", "Local Git: Switch Branch...", self.local_git_switch_branch),
            ("localgit.stash_changes", "Local Git: Stash Changes...", self.local_git_stash_changes),
            (
                "localgit.manage_stashes",
                "Local Git: Manage Stashes...",
                self.local_git_manage_stashes,
            ),
            (
                "localgit.blame_at_cursor",
                "Local Git: Who Wrote This Line...",
                self.local_git_blame_at_cursor,
            ),
            ("localgit.bisect_start", "Local Git: Start Bisect...", self.local_git_bisect_start),
            ("localgit.bisect_reset", "Local Git: End Bisect", self.local_git_bisect_reset),
            (
                "localgit.resolve_conflicts",
                "Local Git: Resolve Conflicts...",
                self.local_git_resolve_conflicts,
            ),
            (
                "localgit.interactive_rebase",
                "Local Git: Interactive Rebase...",
                self.local_git_interactive_rebase,
            ),
            ("localgit.rebase_abort", "Local Git: Abort Rebase", self.local_git_rebase_abort),
        )
        for command_id, title, handler in entries:
            self.commands.try_register(command_id, title, handler, self._binding_for(command_id))
