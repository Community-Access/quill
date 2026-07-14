"""Workflow run artifact listing + download (community-inspired: a FastGH
PR forwarded as a feature reference).

A small modal dialog opened from :class:`~quill.ui.github_items_dialog.GitHubItemsDialog`'s
Actions... menu on a selected workflow run row ("View Artifacts..."). Lists
the run's build artifacts (name, size, expired) and offers Download
Selected / Download All / Refresh / Open Run in Browser.

Downloads run on a daemon thread behind the existing
:class:`~quill.ui.ai_transcribe_dialog.AIProgressDialog` (Cancel + gauge),
the same pattern already used for the TTS engine downloads -- no new
progress-dialog shape invented here. This dialog has no status-bar handle of
its own (it is opened from a modal viewer, not ``MainFrame``), so the
progress dialog's minimize-to-status-bar affordance is not offered here;
Cancel is always available instead.

Accessibility contract (same as every other GitHub dialog in this package):
every control has a ``SetName``, all navigation is keyboard-completable, and
the dialog goes through ``apply_modal_ids`` + ``show_modal_dialog`` -- never
a raw ``ShowModal()``.
"""

from __future__ import annotations

import threading
import webbrowser
from pathlib import Path
from typing import TYPE_CHECKING

from quill.core.github.items_provider import (
    GitHubArtifact,
    GitHubItemsError,
    GitHubItemsProvider,
)
from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog

if TYPE_CHECKING:
    from collections.abc import Callable


class ArtifactsDialog:
    """Modal list of one workflow run's build artifacts, with download."""

    def __init__(
        self,
        parent: object,
        provider: GitHubItemsProvider,
        *,
        repo: str,
        run_id: int,
        run_label: str,
        run_url: str = "",
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._provider = provider
        self._repo = repo
        self._run_id = run_id
        self._run_url = run_url
        self._announce = announce_cb or (lambda _m: None)
        self._artifacts: list[GitHubArtifact] = []

        self.dialog = wx.Dialog(
            parent,
            title=f"Artifacts - {run_label}",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize((520, 380))
        self.dialog.SetSize((600, 420))
        panel = wx.Panel(self.dialog)
        root = wx.BoxSizer(wx.VERTICAL)

        intro = wx.StaticText(panel, label=f"Build artifacts for {run_label} in {repo}:")
        intro.Wrap(560)
        root.Add(intro, 0, wx.ALL, 10)

        self._list = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL, size=(-1, 220))
        self._list.SetName("Artifacts")
        self._list.InsertColumn(0, "Name", width=280)
        self._list.InsertColumn(1, "Size", width=90)
        self._list.InsertColumn(2, "Status", width=90)
        root.Add(self._list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._download_selected_btn = wx.Button(panel, label="Download &Selected...")
        self._download_selected_btn.SetName("Download selected artifact")
        self._download_all_btn = wx.Button(panel, label="Download &All...")
        self._download_all_btn.SetName("Download all artifacts")
        self._refresh_btn = wx.Button(panel, label="&Refresh")
        self._refresh_btn.SetName("Refresh artifact list")
        self._browser_btn = wx.Button(panel, label="Open Run in &Browser")
        self._browser_btn.SetName("Open this workflow run in the default web browser")
        self._browser_btn.Enable(bool(run_url))
        btn_row.Add(self._download_selected_btn, 0, wx.RIGHT, 6)
        btn_row.Add(self._download_all_btn, 0, wx.RIGHT, 6)
        btn_row.Add(self._refresh_btn, 0, wx.RIGHT, 6)
        btn_row.Add(self._browser_btn)
        root.Add(btn_row, 0, wx.ALL, 10)

        self._status = wx.StaticText(panel, label="Loading artifacts...")
        self._status.Wrap(560)
        root.Add(self._status, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        close_row = wx.StdDialogButtonSizer()
        close_row.AddButton(wx.Button(panel, id=wx.ID_CANCEL, label="&Close"))
        close_row.Realize()
        root.Add(close_row, 0, wx.EXPAND | wx.ALL, 8)

        panel.SetSizer(root)
        self.dialog.Fit()
        apply_modal_ids(self.dialog, escape_id=wx.ID_CANCEL)

        self._download_selected_btn.Bind(wx.EVT_BUTTON, self._on_download_selected)
        self._download_all_btn.Bind(wx.EVT_BUTTON, self._on_download_all)
        self._refresh_btn.Bind(wx.EVT_BUTTON, self._on_refresh)
        self._browser_btn.Bind(wx.EVT_BUTTON, self._on_open_browser)

    def show(self) -> None:
        self._reload()
        show_modal_dialog(self.dialog, "Artifacts", announce=self._announce)

    # ------------------------------------------------------------------
    # Loading

    def _reload(self) -> None:
        self._set_status("Loading artifacts...")
        self._set_buttons_enabled(False)

        def worker() -> None:
            wx = self._wx
            try:
                artifacts = self._provider.fetch_workflow_run_artifacts(self._repo, self._run_id)
            except GitHubItemsError as exc:
                wx.CallAfter(self._on_load_error, str(exc))
                return
            wx.CallAfter(self._on_loaded, artifacts)

        threading.Thread(  # GATE-40-OK: single run's artifact list, bounded.
            target=worker, daemon=True
        ).start()

    def _on_loaded(self, artifacts: list[GitHubArtifact]) -> None:
        self._artifacts = artifacts
        self._list.DeleteAllItems()
        for artifact in artifacts:
            idx = self._list.InsertItem(self._list.GetItemCount(), artifact.name)
            self._list.SetItem(idx, 1, artifact.size_display)
            self._list.SetItem(idx, 2, "Expired" if artifact.expired else "Available")
        self._set_buttons_enabled(True)
        self._set_status(
            "This run has no artifacts." if not artifacts else f"{len(artifacts)} artifact(s)."
        )

    def _on_load_error(self, message: str) -> None:
        self._set_status(f"Error: {message}")
        self._set_buttons_enabled(True)

    def _on_refresh(self, _event: object) -> None:
        self._reload()

    def _on_open_browser(self, _event: object) -> None:
        if self._run_url:
            webbrowser.open(self._run_url)
            self._announce("Opened in browser.")

    # ------------------------------------------------------------------
    # Download

    def _selected_artifact(self) -> GitHubArtifact | None:
        idx = self._list.GetFirstSelected()
        if 0 <= idx < len(self._artifacts):
            return self._artifacts[idx]
        return None

    def _on_download_selected(self, _event: object) -> None:
        artifact = self._selected_artifact()
        if artifact is None:
            self._announce("Select an artifact first.")
            return
        self._download([artifact])

    def _on_download_all(self, _event: object) -> None:
        if not self._artifacts:
            self._announce("No artifacts to download.")
            return
        self._download(list(self._artifacts))

    def _choose_download_folder(self) -> Path | None:
        wx = self._wx
        with wx.DirDialog(
            self.dialog,
            "Choose a folder to save the artifact zip file(s)",
            style=wx.DD_DEFAULT_STYLE,
        ) as dir_dialog:
            if (
                show_modal_dialog(dir_dialog, "Choose Download Folder", announce=self._announce)
                != wx.ID_OK
            ):
                return None
            return Path(dir_dialog.GetPath())

    def _confirm_overwrite(self, names: str) -> bool:
        wx = self._wx
        confirm = wx.MessageDialog(
            self.dialog,
            f"{names} already exist(s) in this folder. Overwrite?",
            "Confirm Overwrite",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
        )
        try:
            return (
                show_modal_dialog(confirm, "Confirm Overwrite", announce=self._announce)
                == wx.ID_YES
            )
        finally:
            confirm.Destroy()

    def _download(self, artifacts: list[GitHubArtifact]) -> None:
        live = [a for a in artifacts if not a.expired]
        if not live:
            self._announce("The selected artifact(s) have expired and cannot be downloaded.")
            return

        dest_dir = self._choose_download_folder()
        if dest_dir is None:
            return

        existing = [a for a in live if (dest_dir / f"{a.name}.zip").exists()]
        if existing and not self._confirm_overwrite(", ".join(a.name for a in existing)):
            self._announce("Download cancelled.")
            return

        from quill.ui.ai_transcribe_dialog import AIProgressDialog

        cancel = threading.Event()
        progress = AIProgressDialog(
            self.dialog,
            "Downloading Artifacts",
            f"Preparing to download {len(live)} artifact(s)...",
            on_cancel=cancel.set,
        )
        progress.show()

        def worker() -> None:
            done = 0
            failed: list[str] = []
            for artifact in live:
                if cancel.is_set():
                    break
                dest = dest_dir / f"{artifact.name}.zip"

                def _on_progress(downloaded: int, total: int, _name: str = artifact.name) -> None:
                    pct = int(downloaded * 100 / total) if total else -1
                    progress.set_progress(pct, f"{_name}: {downloaded // 1024} KB")

                try:
                    self._provider.download_artifact_to_file(
                        artifact,
                        dest,
                        progress=_on_progress,
                        should_cancel=cancel.is_set,
                    )
                    done += 1
                except GitHubItemsError as exc:
                    failed.append(f"{artifact.name} ({exc})")
            self._wx.CallAfter(self._on_download_finished, progress, done, failed, cancel.is_set())

        threading.Thread(  # GATE-40-OK: consented, user-initiated artifact download.
            target=worker, daemon=True
        ).start()

    def _on_download_finished(
        self,
        progress: object,
        done: int,
        failed: list[str],
        cancelled: bool,
    ) -> None:
        if cancelled:
            progress.close()
            self._set_status("Download cancelled.")
            return
        message = (
            f"Downloaded {done}. Failed: {'; '.join(failed)}"
            if failed
            else f"Downloaded {done} artifact(s)."
        )
        progress.switch_to_ok(message)
        self._set_status(message)

    # ------------------------------------------------------------------
    # Helpers

    def _set_buttons_enabled(self, enabled: bool) -> None:
        self._download_selected_btn.Enable(enabled and bool(self._artifacts))
        self._download_all_btn.Enable(enabled and bool(self._artifacts))
        self._refresh_btn.Enable(enabled)

    def _set_status(self, message: str) -> None:
        self._status.SetLabel(message)
        parent = self._status.GetParent()
        if parent is not None:
            parent.Layout()
        if message:
            self._announce(message)


__all__ = ["ArtifactsDialog"]
