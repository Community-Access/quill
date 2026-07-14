"""GitHub Codespaces and Copilot CLI commands for ``MainFrame``
(`docs/planning/github.md` section 1's Tier 3 -- the narrow `gh`-CLI bridge).

**Needs live-device verification**, same caveat as :mod:`quill.core.github.gh_bridge`
itself: every command here is wired and unit-tested with a fake `gh` runner,
but has not been exercised against a real `gh` installation, a real
Codespaces-enabled repository, or real Copilot CLI access. Ship behind the
same gates as everything else in this file family (Safe Mode, `gh`
availability), but treat it as needing a real-device pass before it is
fully promoted.

Codespaces cost real money/quota on GitHub's side, unlike everything else
in QUILL's GitHub integration -- the create-codespace confirmation says so
explicitly, not just "this changes something on GitHub."
"""

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from typing import Any


class GhBridgeMixin:
    """Adds GitHub Codespaces and Copilot CLI commands to ``MainFrame``."""

    # ------------------------------------------------------------------
    # Shared gating

    def _gh_bridge_ready(self) -> str | None:
        """Return the resolved ``gh`` executable path, or None after
        reporting why it's unavailable."""
        if os.environ.get("QUILL_SAFE_MODE") == "1":
            self._set_status("GitHub CLI commands are disabled in Safe Mode")
            return None
        from quill.core.git_binaries import resolve_gh

        gh_path = resolve_gh()
        if gh_path is None:
            self._show_message_box(
                "This action needs the GitHub CLI (gh), which QUILL did not find "
                "on your system. Install it from cli.github.com and make sure "
                "it's on your PATH.",
                "GitHub CLI Not Found",
                self._wx.ICON_INFORMATION | self._wx.OK,
            )
            return None
        return str(gh_path)

    def _gh_bridge_runner(self):
        from quill.stability.safe_subprocess import run_subprocess_safely

        return run_subprocess_safely

    def _gh_bridge_confirm(self, message: str, title: str) -> bool:
        wx = self._wx
        dialog = wx.MessageDialog(
            self.frame, message, title, wx.YES_NO | wx.NO_DEFAULT | wx.ICON_INFORMATION
        )
        try:
            return self._show_modal_dialog(dialog, title) == wx.ID_YES
        finally:
            dialog.Destroy()

    def _gh_bridge_prompt_single(self, title: str, label: str, value: str = "") -> str | None:
        wx = self._wx
        with wx.TextEntryDialog(self.frame, label, title, value) as dialog:
            if self._show_modal_dialog(dialog, title) != wx.ID_OK:
                return None
            text = str(dialog.GetValue()).strip()
            return text or None

    # ------------------------------------------------------------------
    # Codespaces

    def github_list_codespaces(self) -> None:
        """Tools > GitHub > Codespaces..."""
        gh_path = self._gh_bridge_ready()
        if gh_path is None:
            return

        def work(_progress: object) -> object:
            from quill.core.github.gh_bridge import list_codespaces

            return list_codespaces(gh_path=gh_path, runner=self._gh_bridge_runner())

        self._run_background_task("Loading codespaces", work, self._on_gh_bridge_codespaces_loaded)

    def _on_gh_bridge_codespaces_loaded(self, codespaces: list[Any]) -> None:
        if not codespaces:
            self._set_status("No codespaces. Use GitHub: Create Codespace... to start one.")
            return
        wx = self._wx
        labels = [f"{c.display_name} ({c.repository}) — {c.state}" for c in codespaces]
        with wx.SingleChoiceDialog(self.frame, "Codespace:", "Codespaces", labels) as dialog:
            if self._show_modal_dialog(dialog, "Codespaces") != wx.ID_OK:
                return
            index = dialog.GetSelection()
        chosen = codespaces[index]

        menu = wx.Menu()
        stop_id, delete_id = wx.NewIdRef(), wx.NewIdRef()
        menu.Append(stop_id, "Stop")
        menu.Append(delete_id, "Delete")

        def on_pick(event: object) -> None:
            picked = int(event.GetId())
            if picked == int(stop_id):
                self._gh_bridge_stop_codespace(chosen.name)
            elif picked == int(delete_id):
                self._gh_bridge_delete_codespace(chosen.name)

        menu.Bind(wx.EVT_MENU, on_pick)
        try:
            self.frame.PopupMenu(menu)
        finally:
            menu.Destroy()

    def _gh_bridge_stop_codespace(self, name: str) -> None:
        gh_path = self._gh_bridge_ready()
        if gh_path is None:
            return

        def work(_progress: object) -> object:
            from quill.core.github.gh_bridge import stop_codespace

            stop_codespace(name, gh_path=gh_path, runner=self._gh_bridge_runner())
            return None

        self._run_background_task(
            f"Stopping {name}", work, lambda _r: self._set_status(f"Stopped {name}")
        )

    def _gh_bridge_delete_codespace(self, name: str) -> None:
        if not self._gh_bridge_confirm(
            f"Delete codespace {name!r}? This cannot be undone.", "Confirm Delete"
        ):
            self._set_status("Delete cancelled")
            return
        gh_path = self._gh_bridge_ready()
        if gh_path is None:
            return

        def work(_progress: object) -> object:
            from quill.core.github.gh_bridge import delete_codespace

            delete_codespace(name, gh_path=gh_path, runner=self._gh_bridge_runner())
            return None

        self._run_background_task(
            f"Deleting {name}", work, lambda _r: self._set_status(f"Deleted {name}")
        )

    def github_create_codespace(self) -> None:
        """Tools > GitHub > Create Codespace..."""
        gh_path = self._gh_bridge_ready()
        if gh_path is None:
            return
        full_name = self._gh_admin_prompt_repo("Create Codespace")
        if full_name is None:
            return
        branch = self._gh_bridge_prompt_single(
            "Create Codespace", "Branch (optional, blank = default branch):"
        )
        branch = branch or ""
        if not self._gh_bridge_confirm(
            f"Create a new codespace for {full_name}"
            + (f" on {branch!r}" if branch else "")
            + "?\n\nCodespaces use GitHub compute and storage minutes and may cost "
            "money depending on your account's plan and usage — this is not a free "
            "action the way most QUILL commands are.",
            "Confirm Create Codespace (uses paid GitHub compute)",
        ):
            self._set_status("Codespace creation cancelled")
            return

        def work(_progress: object) -> object:
            from quill.core.github.gh_bridge import create_codespace

            return create_codespace(
                full_name, branch=branch, gh_path=gh_path, runner=self._gh_bridge_runner()
            )

        def on_done(info: Any) -> None:
            self._set_status(f"Created codespace {info.display_name} ({info.state})")

        self._run_background_task(f"Creating codespace for {full_name}", work, on_done)

    # ------------------------------------------------------------------
    # Copilot CLI: suggest / explain

    def github_copilot_suggest(self) -> None:
        """Tools > GitHub > Ask Copilot for a Command..."""
        gh_path = self._gh_bridge_ready()
        if gh_path is None:
            return
        query = self._gh_bridge_prompt_single(
            "Ask Copilot for a Command",
            'Describe what you want to do (e.g. "undo my last commit but keep the changes"):',
        )
        if not query:
            return

        def work(_progress: object) -> object:
            from quill.core.github.gh_bridge import copilot_suggest

            return copilot_suggest(query, gh_path=gh_path, runner=self._gh_bridge_runner())

        def on_done(result: str) -> None:
            self._show_message_box(
                result.strip() or "Copilot did not suggest anything.",
                "Copilot Suggestion",
                self._wx.ICON_INFORMATION | self._wx.OK,
            )

        self._run_background_task("Asking Copilot", work, on_done)

    def github_copilot_explain(self) -> None:
        """Tools > GitHub > Explain a Command..."""
        gh_path = self._gh_bridge_ready()
        if gh_path is None:
            return
        command = self._gh_bridge_prompt_single(
            "Explain a Command", "Paste a git or gh command to have explained:"
        )
        if not command:
            return

        def work(_progress: object) -> object:
            from quill.core.github.gh_bridge import copilot_explain

            return copilot_explain(command, gh_path=gh_path, runner=self._gh_bridge_runner())

        def on_done(result: str) -> None:
            self._show_message_box(
                result.strip() or "Copilot did not explain that command.",
                "Copilot Explanation",
                self._wx.ICON_INFORMATION | self._wx.OK,
            )

        self._run_background_task("Asking Copilot", work, on_done)

    # ------------------------------------------------------------------
    # Download Optional Components: the gh fallback for a user with neither
    # a system gh nor QUILL's bundled copy (quill.core.git_binaries prefers
    # a system install first; this is purely the recovery path).

    def download_gh(self, *, on_done: Callable[[bool], None] | None = None) -> None:
        """Fetch QUILL's self-hosted, SHA-256-verified copy of the GitHub CLI
        for Codespaces and Copilot commands. QUILL always prefers a system
        gh on PATH first; this download exists only for a user who has
        neither. Windows and macOS only -- there is no self-hosted Linux
        asset (a Linux user typically already has gh via their distro)."""
        from quill.core.git_binaries import gh_available

        wx = self._wx
        if os.environ.get("QUILL_SAFE_MODE") == "1":
            self._announce("Downloading components is disabled in Safe Mode.")
            return
        if gh_available():
            again = self._show_message_box(
                "The GitHub CLI is already installed (either on your system, or "
                "QUILL's own copy). Download QUILL's verified copy again anyway?",
                "GitHub CLI",
                wx.ICON_QUESTION | wx.YES_NO,
            )
            if again != wx.YES:
                if on_done is not None:
                    on_done(True)
                return
        proceed = self._show_message_box(
            "QUILL will download a portable copy of the GitHub CLI (about 14 MB) "
            "and verify it. It powers Tools > GitHub's Codespaces and Copilot "
            "suggest/explain commands. Continue?",
            "Download GitHub CLI",
            wx.ICON_INFORMATION | wx.YES_NO,
        )
        if proceed != wx.YES:
            return

        def _work(progress):
            from quill.core.git_binaries import vendor_dir
            from quill.core.release_assets import fetch_component

            component = "gh-macos" if sys.platform == "darwin" else "gh-windows"
            fetch_component(
                component,
                vendor_dir(),
                progress=lambda fraction, message: progress(message, int(fraction * 100), 100),
                label="Downloading the GitHub CLI...",
            )
            return True

        def _finished(result: object) -> None:
            ok = bool(result)
            if ok:
                self._announce("GitHub CLI installed. Codespaces and Copilot commands are ready.")
            else:
                self._announce("The GitHub CLI could not be installed.")
            if on_done is not None:
                on_done(ok)

        self._run_background_task("Downloading GitHub CLI", _work, _finished)

    # ------------------------------------------------------------------
    # Command palette registration

    def _register_gh_bridge_commands(self) -> None:
        entries = (
            ("github.list_codespaces", "GitHub: Codespaces...", self.github_list_codespaces),
            (
                "github.create_codespace",
                "GitHub: Create Codespace...",
                self.github_create_codespace,
            ),
            (
                "github.copilot_suggest",
                "GitHub: Ask Copilot for a Command...",
                self.github_copilot_suggest,
            ),
            (
                "github.copilot_explain",
                "GitHub: Explain a Command...",
                self.github_copilot_explain,
            ),
        )
        for command_id, title, handler in entries:
            self.commands.try_register(command_id, title, handler, self._binding_for(command_id))
