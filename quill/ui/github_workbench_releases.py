"""Release actions, and the repository's own windows, in the GitHub Workbench.

GitHub PRD section 5. On a release: Assets (its files, with Download, Copy
Link and Delete), Edit Release, Draft Release Notes, Upload Asset and Delete
Asset. From Repository > Repository Actions: Milestones, Projects, and Files,
History and Blame -- the windows GitHub Items opened from its view menu. Each
is the same window or provider call GitHub Items used, parented to the
Workbench.

Every write asks first (publishing a draft says who is notified), runs off the
UI thread, and says one outcome.
"""

from __future__ import annotations

import os
import webbrowser
from collections.abc import Callable
from typing import Any

from quill.core.github.items_provider import GitHubRelease

__all__ = ["RELEASE_REASONS", "RELEASE_VERBS", "GitHubWorkbenchReleasesMixin"]

RELEASE_VERBS: dict[str, frozenset[str]] = {
    "assets": frozenset({"release"}),
    "edit_release": frozenset({"release"}),
    "release_notes": frozenset({"release"}),
    "upload_asset": frozenset({"release"}),
    "delete_asset": frozenset({"release"}),
    "milestones_window": frozenset({"view"}),
    "projects_window": frozenset({"view"}),
    "files_window": frozenset({"view"}),
}

RELEASE_REASONS: dict[str, str] = {
    "delete_asset": (
        "Delete an asset from its release: select the release, then Delete Asset, "
        "or Assets and its Delete button."
    ),
    "milestones_window": "Open a repository first. Ctrl+L opens one by name or link.",
    "projects_window": "Sign in to GitHub and open a repository first.",
    "files_window": "Open a repository first. Ctrl+L opens one by name or link.",
}


def _size_words(size: int) -> str:
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):,.1f} MB"
    if size >= 1024:
        return f"{size / 1024:,.1f} KB"
    return f"{size:,} bytes"


class GitHubWorkbenchReleasesMixin:
    """Releases and the repository windows, for the GitHub provider."""

    items: Any
    frame: Any
    signed_in: bool
    _open_file_url: Callable[[str], None] | None
    _say: Callable[[str], None]
    _background: Callable[[str, Callable[[], Any], Callable[[Any], None]], None]
    _confirm: Callable[[str, str], bool]
    _choose: Callable[[str, str, list[str]], int]
    _repo_for: Callable[[Any], str]
    _parent: Callable[[], Any]
    _current_repository: Callable[[], str]

    # -- can it run? -----------------------------------------------------------------

    def _fits_release_write(self, row: object) -> bool:
        return self.signed_in and isinstance(row, GitHubRelease)

    _fits_edit_release = _fits_release_write
    _fits_upload_asset = _fits_release_write

    def _fits_delete_asset(self, row: object) -> bool:
        return self._fits_release_write(row) and bool(getattr(row, "assets", ()))

    def _fits_milestones_window(self, _row: object) -> bool:
        return bool(self._current_repository())

    _fits_files_window = _fits_milestones_window

    def _fits_projects_window(self, _row: object) -> bool:
        return self.signed_in and bool(self._current_repository())

    def _admin(self) -> Any:
        from quill.core.github.release_admin import GitHubReleaseAdmin

        return GitHubReleaseAdmin(getattr(self.items, "token", None))

    # -- reading ---------------------------------------------------------------------

    def _do_assets(self, ref: Any, row: object) -> None:
        assert isinstance(row, GitHubRelease)
        release = row
        if not release.assets:
            self._say(f"{release.tag} has no files to download.")
            return
        from quill.ui.github_workbench_list_dialog import WorkbenchListDialog

        assets = list(release.assets)
        held: list[Any] = []

        def lines() -> list[str]:
            return [f"{a.name}, {a.download_count:,} downloads, {a.size_display}" for a in assets]

        def download(index: int) -> None:
            link = assets[index].browser_download_url if index >= 0 else ""
            if not link or not webbrowser.open(link, new=2):
                self._say("Could not open this in your browser.")

        def remove(index: int) -> None:
            if index < 0:
                return
            name = assets[index].name

            def gone() -> None:
                del assets[index]
                if held:
                    held[0].set_rows(lines())

            self._delete_named_asset(ref, release, name, gone)

        actions = [
            ("&Download", "Download the file in your browser.", download),
            (
                "Copy &Link",
                "Copy the file's download address.",
                lambda i: self.frame.copy_text(assets[i].browser_download_url if i >= 0 else ""),
            ),
        ]
        if self.signed_in:
            actions.append(("Dele&te...", "Remove the file from the release. Asks first.", remove))
        box = WorkbenchListDialog(
            self._parent(),
            f"Assets of {release.tag}",
            lines(),
            list_name=f"Assets of {release.tag}",
            list_help="The release's files, most downloaded first. Enter downloads one.",
            detail=lambda i: (
                f"{assets[i].name}\n{assets[i].download_count:,} downloads\n"
                f"{assets[i].size_display}\nUpdated {assets[i].updated_at}\n"
                f"{assets[i].browser_download_url}"
            ),
            actions=actions,
            copy_text=self.frame.copy_text,
        )
        held.append(box)
        box.show()

    def _do_release_notes(self, ref: Any, row: object) -> None:
        assert isinstance(row, GitHubRelease)
        from quill.ui.github_release_notes_dialog import GitHubReleaseNotesDialog

        GitHubReleaseNotesDialog(
            self._parent(),
            self.items,
            self._repo_for(ref),
            previous_tag=row.tag,
            announce_cb=self._say,
        ).show()

    # -- writes -----------------------------------------------------------------------

    def _do_edit_release(self, ref: Any, row: object) -> None:
        assert isinstance(row, GitHubRelease)
        repo, admin, tag = self._repo_for(ref), self._admin(), row.tag

        def edit(record: Any) -> None:
            from quill.ui.github_release_edit_dialog import EditReleaseDialog

            values = EditReleaseDialog(self._parent(), record, announce_cb=self._say).show()
            if values is None:
                return
            if (
                record.draft
                and not values.draft
                and not self._confirm(
                    "Publish Release",
                    f"Publish release {record.tag} in {repo}? People watching the repository "
                    "are notified, and the release becomes public.",
                )
            ):
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
                return str(sentence)

            self._background(
                "edit the release",
                work,
                lambda sentence: (self._say(sentence), self.frame.reload()),
            )

        self._background("read the release", lambda: admin.find_release(repo, tag), edit)

    def _do_upload_asset(self, ref: Any, row: object) -> None:
        assert isinstance(row, GitHubRelease)
        wx = self.frame._wx
        from quill.ui.dialog_contract import show_modal_dialog

        title = "Upload Release Asset"
        with wx.FileDialog(
            self._parent(),
            f"Choose a file to attach to release {row.tag}",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dialog:
            if show_modal_dialog(dialog, title) != wx.ID_OK:
                return
            path = str(dialog.GetPath())
        name = os.path.basename(path)
        try:
            size = os.path.getsize(path)
        except OSError:
            size = 0
        repo, admin, tag = self._repo_for(ref), self._admin(), row.tag
        if not self._confirm(
            title, f"Upload {name} ({_size_words(size)}) to release {tag} in {repo}?"
        ):
            return

        def work() -> str:
            record = admin.find_release(repo, tag)
            asset = admin.upload_release_asset(repo, record, path)
            return f"Uploaded {asset.name} ({_size_words(asset.size)}) to release {tag}."

        self._background(
            "upload the file", work, lambda said: (self._say(said), self.frame.reload())
        )

    def _do_delete_asset(self, ref: Any, row: object) -> None:
        assert isinstance(row, GitHubRelease)
        names = [asset.name for asset in row.assets]
        index = self._choose("Delete Release Asset", f"Which file of {row.tag}:", names)
        if index >= 0:
            self._delete_named_asset(ref, row, names[index], lambda: None)

    def _delete_named_asset(
        self, ref: Any, release: GitHubRelease, name: str, then: Callable[[], None]
    ) -> None:
        repo, admin, tag = self._repo_for(ref), self._admin(), release.tag
        if not self._confirm(
            "Delete Release Asset",
            f"Delete {name} from release {tag} in {repo}? Its download count goes with it, "
            "and this cannot be undone.",
        ):
            return

        def work() -> str:
            record = admin.find_release(repo, tag)
            found = record.asset_named(name)
            if found is None:
                return f"{name} is no longer on release {tag}; nothing was deleted."
            admin.delete_asset(repo, found)
            return f"Deleted {name} from release {tag}."

        def done(said: str) -> None:
            self._say(said)
            then()
            self.frame.reload()

        self._background("delete the file", work, done)

    # -- the repository's windows (Repository Actions) ----------------------------------

    def _do_milestones_window(self, _ref: Any, _row: object) -> None:
        from quill.ui.github_milestones_dialog import GitHubMilestonesDialog

        GitHubMilestonesDialog(
            self._parent(), self.items, repo=self._current_repository(), announce_cb=self._say
        ).show()

    def _do_projects_window(self, _ref: Any, _row: object) -> None:
        from quill.ui.github_projects_dialog import GitHubProjectsDialog

        GitHubProjectsDialog(
            self._parent(),
            self.items,
            initial_repo=self._current_repository(),
            announce_cb=self._say,
        ).show()

    def _do_files_window(self, _ref: Any, row: object) -> None:
        from quill.ui.github_repo_files_dialog import GitHubRepoFilesDialog

        GitHubRepoFilesDialog(
            self._parent(),
            self.items,
            repo=self._current_repository(),
            ref=str(getattr(row, "name", "") or "") if _is_branch(row) else "",
            open_in_editor_cb=self._open_file_url,
            announce_cb=self._say,
        ).show()


def _is_branch(row: object) -> bool:
    from quill.core.github.items_provider import GitHubBranch

    return isinstance(row, GitHubBranch)
