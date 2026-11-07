"""Release actions for the shared GitHub Items viewer (QUILL and QUILL Lite).

Draft Release Notes, and in Wave 4: Edit Release (name, notes, draft,
prerelease, and publishing a draft), Upload Asset (a file chooser, then
progress said at 25, 50 and 75 percent and the result GitHub confirmed) and
Delete Asset (from a release's asset list, after a confirmation). Reached
from the Actions button and the row's context menu in the Releases view.
"""

from __future__ import annotations

import os
from typing import Any

from quill.core.github.items_provider import GitHubRelease, GitHubReleaseAsset
from quill.core.github.release_admin import GitHubReleaseAdmin
from quill.ui.dialog_contract import dialog_alive


def _size_words(size: int) -> str:
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):,.1f} MB"
    if size >= 1024:
        return f"{size / 1024:,.1f} KB"
    return f"{size:,} bytes"


class GitHubItemsReleaseMixin:
    """Create a local, editable release-notes preview, and manage a release and its files."""

    def _draft_release_notes(self) -> None:
        from quill.ui.github_release_notes_dialog import GitHubReleaseNotesDialog

        selected = self._selected_indices()
        previous_tag = ""
        if len(selected) == 1 and 0 <= selected[0] < len(self._rows):
            selected_release = self._rows[selected[0]]
            if isinstance(selected_release, GitHubRelease):
                previous_tag = selected_release.tag
        GitHubReleaseNotesDialog(
            self.dialog,
            self._provider,
            self._repo,
            previous_tag=previous_tag,
            announce_cb=self._announce,
        ).show()

    # -- Wave 4 ------------------------------------------------------------------

    def _add_release_actions(self, add: Any) -> None:
        """The Releases view's rows for the Actions menu or the context menu."""
        add("Draft Release Notes...", self._draft_release_notes)
        if not self._provider.is_authenticated:
            return
        add("Edit Release...", self._edit_selected_release)
        add("Upload Asset...", self._upload_release_asset)
        asset = self._selected_release_asset()
        if asset is not None:
            add(f"Delete Asset {asset.name}...", self._delete_selected_asset)

    def _release_admin(self) -> GitHubReleaseAdmin:
        return GitHubReleaseAdmin(getattr(self._provider, "token", None))

    def _selected_release(self) -> GitHubRelease | None:
        drilled = getattr(self, "_drill_release", None)
        if isinstance(drilled, GitHubRelease):
            return drilled
        selected = self._selected_indices()
        if len(selected) == 1 and 0 <= selected[0] < len(self._rows):
            model = self._rows[selected[0]]
            if isinstance(model, GitHubRelease):
                return model
        self._announce("Select one release first.")
        return None

    def _selected_release_asset(self) -> GitHubReleaseAsset | None:
        if getattr(self, "_drill_release", None) is None:
            return None
        selected = self._selected_indices()
        if len(selected) == 1 and 0 <= selected[0] < len(self._rows):
            model = self._rows[selected[0]]
            if isinstance(model, GitHubReleaseAsset):
                return model
        return None

    def _edit_selected_release(self) -> None:
        release = self._selected_release()
        if release is None:
            return
        repo, admin = self._repo, self._release_admin()

        def edit(record: Any) -> None:
            from quill.ui.github_release_edit_dialog import EditReleaseDialog

            values = EditReleaseDialog(self.dialog, record, announce_cb=self._announce).show()
            if values is None:
                return
            if (
                record.draft
                and not values.draft
                and not self._confirm_action(
                    f"Publish release {record.tag} in {repo}? People watching the repository "
                    "are notified, and the release becomes public.",
                    "Publish Release",
                )
            ):
                self._announce("Cancelled; the release was not changed.")
                return

            def work() -> str:
                _after, sentence = admin.edit_release(
                    repo,
                    record,
                    name=values.name,
                    body=values.body,
                    draft=values.draft,
                    prerelease=values.prerelease,
                )
                return sentence

            self._housekeeping_write(work, then_reload=True)

        self._housekeeping_run(
            lambda: admin.find_release(repo, release.tag),
            edit,
            latest_only=True,
            busy=f"Reading release {release.tag}...",
        )

    def _upload_release_asset(self) -> None:
        release = self._selected_release()
        if release is None:
            return
        wx = self._wx
        with wx.FileDialog(
            self.dialog,
            f"Choose a file to attach to release {release.tag}",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dialog:
            if self._show_modal(dialog, "Upload Release Asset") != wx.ID_OK:
                return
            path = dialog.GetPath()
        name = os.path.basename(path)
        try:
            size = os.path.getsize(path)
        except OSError:
            size = 0
        if not self._confirm_action(
            f"Upload {name} ({_size_words(size)}) to release {release.tag} in {self._repo}?",
            "Upload Release Asset",
        ):
            self._announce("Cancelled; nothing was uploaded.")
            return
        repo, admin = self._repo, self._release_admin()

        def say_step(text: str) -> None:
            if dialog_alive(self.dialog):
                self._set_status(text)

        def said(percent: int) -> None:
            self._wx.CallAfter(say_step, f"Uploading {name}: {percent} percent.")

        def work() -> str:
            record = admin.find_release(repo, release.tag)
            asset = admin.upload_release_asset(repo, record, path, progress=said)
            return f"Uploaded {asset.name} ({_size_words(asset.size)}) to release {release.tag}."

        self._housekeeping_write(work, then_reload=True)

    def _delete_selected_asset(self) -> None:
        asset = self._selected_release_asset()
        release = getattr(self, "_drill_release", None)
        if asset is None or not isinstance(release, GitHubRelease):
            self._announce("Open a release's files and select one first.")
            return
        if not self._confirm_action(
            f"Delete {asset.name} from release {release.tag} in {self._repo}? Its download "
            "count goes with it, and this cannot be undone.",
            "Delete Release Asset",
        ):
            self._announce("Cancelled; the file was not deleted.")
            return
        repo, admin, tag = self._repo, self._release_admin(), release.tag

        def work() -> str:
            record = admin.find_release(repo, tag)
            found = record.asset_named(asset.name)
            if found is None:
                return f"{asset.name} is no longer on release {tag}; nothing was deleted."
            admin.delete_asset(repo, found)
            return f"Deleted {asset.name} from release {tag}."

        self._housekeeping_write(work, then_reload=True)


__all__ = ["GitHubItemsReleaseMixin"]
