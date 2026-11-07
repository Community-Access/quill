"""Repository Files: browse a repository at any branch, tag or commit (QUILL and QUILL Lite).

A tree of folders and files, loaded a folder at a time as you expand it (Right
arrow or Enter opens a folder, Left closes it). Enter on a file shows its text
in the read-only Contents box; Open in Editor opens it in the editor through the
same path as File, Open Remote, GitHub File URL; README shows the README of the
selected folder (or of the repository); History and Blame open
:class:`~quill.ui.github_file_runs_dialog.GitHubFileRunsDialog`.

Every read runs off the UI thread. The tree carries a load token, so a folder
that finishes loading after the tree was reloaded at another ref is dropped
rather than grafted onto the wrong tree.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import TYPE_CHECKING

from quill.core.github.items_errors import GitHubItemsError
from quill.core.github.repo_files import RepoEntry, blob_url
from quill.ui.dialog_contract import (
    apply_modal_ids,
    bind_close_button,
    dialog_alive,
    show_modal_dialog,
)
from quill.ui.dpi import dip_size
from quill.ui.github_file_runs_dialog import FileRun, GitHubFileRunsDialog

if TYPE_CHECKING:
    from quill.core.github.items_provider import GitHubItemsProvider

__all__ = ["GitHubRepoFilesDialog"]


def _message(exc: BaseException) -> str:
    """The error's sentence, without the support code a screen reader would read out."""
    return str(exc.args[0]) if exc.args else str(exc)


_PLACEHOLDER = "Loading..."


class GitHubRepoFilesDialog:
    """Browse folders and files; view, open, README, history and blame."""

    def __init__(
        self,
        parent: object,
        provider: GitHubItemsProvider,
        *,
        repo: str,
        ref: str = "",
        open_in_editor_cb: Callable[[str], None] | None = None,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._provider = provider
        self._repo = repo
        self._ref = ref
        self._open_in_editor = open_in_editor_cb
        self._announce = announce_cb or (lambda _message: None)
        self._token = 0
        self._content_token = 0
        self.dialog = wx.Dialog(
            parent,
            title=f"Repository Files: {repo}",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize(dip_size(self.dialog, 680, 500))
        self.dialog.SetSize(dip_size(self.dialog, 860, 640))
        panel = wx.Panel(self.dialog)
        root = wx.BoxSizer(wx.VERTICAL)
        ref_row = wx.BoxSizer(wx.HORIZONTAL)
        ref_label = wx.StaticText(panel, label="&Branch, tag or commit:")
        ref_label.SetHelpText("Which version of the repository to browse.")
        ref_row.Add(ref_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self._ref_ctrl = wx.ComboBox(panel, value=ref, style=wx.CB_DROPDOWN | wx.TE_PROCESS_ENTER)
        self._ref_ctrl.SetName("Branch, tag or commit to browse")
        self._ref_ctrl.SetHelpText(
            "Type a branch, a tag or a commit SHA, or pick a branch or tag from the list, "
            "then press Enter or Go."
        )
        ref_row.Add(self._ref_ctrl, 1, wx.RIGHT, 6)
        self._go_btn = wx.Button(panel, label="&Go")
        self._go_btn.SetName("Browse the repository at this branch, tag or commit")
        self._go_btn.SetHelpText("Loads the top folder of the repository at the version above.")
        ref_row.Add(self._go_btn, 0)
        root.Add(ref_row, 0, wx.EXPAND | wx.ALL, 8)
        tree_label = wx.StaticText(panel, label="&Files")
        tree_label.SetHelpText("The repository's folders and files.")
        root.Add(tree_label, 0, wx.LEFT, 8)
        self._tree = wx.TreeCtrl(
            panel, style=wx.TR_HAS_BUTTONS | wx.TR_LINES_AT_ROOT | wx.TR_HIDE_ROOT | wx.TR_SINGLE
        )
        self._tree.SetName("Repository folders and files")
        self._tree.SetHelpText(
            "Right arrow or Enter opens a folder and Left closes it. Enter on a file shows "
            "its text in Contents. Each file says its size."
        )
        root.Add(self._tree, 2, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        contents_label = wx.StaticText(panel, label="&Contents")
        contents_label.SetHelpText("The text of the file or README you opened.")
        root.Add(contents_label, 0, wx.LEFT | wx.TOP, 8)
        self._contents = wx.TextCtrl(
            panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2 | wx.HSCROLL
        )
        self._contents.SetName("File contents, read-only")
        self._contents.SetHelpText(
            "Read-only. Arrow through it like a document; Ctrl+A then Ctrl+C copies. "
            "Open in Editor opens the file for editing."
        )
        root.Add(self._contents, 2, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        self._status = wx.StaticText(panel, label="")
        self._status.SetName("Repository files status")
        self._status.SetHelpText("Says what is loading, what loaded, or why it failed.")
        root.Add(self._status, 0, wx.EXPAND | wx.ALL, 8)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self._view_btn = wx.Button(panel, label="&View File")
        self._view_btn.SetName("Show the selected file's text in Contents")
        self._view_btn.SetHelpText("Shows the selected file's text, read-only, in Contents.")
        self._edit_btn = wx.Button(panel, label="Open in &Editor")
        self._edit_btn.SetName("Open the selected file in the editor")
        self._edit_btn.SetHelpText(
            "Opens the selected file in the editor, the same way as opening a GitHub file "
            "link, so you can edit it."
        )
        self._readme_btn = wx.Button(panel, label="&README")
        self._readme_btn.SetName("Show the README of the selected folder or the repository")
        self._readme_btn.SetHelpText(
            "Shows the README GitHub shows for the selected folder, or for the whole "
            "repository when nothing is selected."
        )
        self._history_btn = wx.Button(panel, label="&History...")
        self._history_btn.SetName("Commits that changed the selected file or folder")
        self._history_btn.SetHelpText(
            "Lists the commits that changed the selected file or folder, newest first."
        )
        self._blame_btn = wx.Button(panel, label="B&lame...")
        self._blame_btn.SetName("Who last changed each run of lines in the selected file")
        self._blame_btn.SetHelpText(
            "Lists the file in runs of lines, each with the author, date, short SHA and "
            "commit title. Needs a signed-in account."
        )
        close_btn = wx.Button(panel, wx.ID_CANCEL, "Close")
        close_btn.SetName("Close repository files")
        close_btn.SetHelpText("Close this window.")
        for button in (
            self._view_btn,
            self._edit_btn,
            self._readme_btn,
            self._history_btn,
            self._blame_btn,
        ):
            buttons.Add(button, 0, wx.RIGHT, 6)
        buttons.AddStretchSpacer()
        buttons.Add(close_btn)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        panel.SetSizer(root)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.dialog.SetSizer(outer)
        self._go_btn.Bind(wx.EVT_BUTTON, lambda _event: self._load_root())
        self._ref_ctrl.Bind(wx.EVT_TEXT_ENTER, lambda _event: self._load_root())
        self._ref_ctrl.Bind(wx.EVT_COMBOBOX, lambda _event: self._load_root())
        self._tree.Bind(wx.EVT_TREE_ITEM_EXPANDING, self._on_expanding)
        self._tree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self._on_activate)
        self._tree.Bind(wx.EVT_TREE_SEL_CHANGED, lambda _event: self._update_buttons())
        self._view_btn.Bind(wx.EVT_BUTTON, lambda _event: self._view_file())
        self._edit_btn.Bind(wx.EVT_BUTTON, lambda _event: self._open_file_in_editor())
        self._readme_btn.Bind(wx.EVT_BUTTON, lambda _event: self._show_readme())
        self._history_btn.Bind(wx.EVT_BUTTON, lambda _event: self._show_history())
        self._blame_btn.Bind(wx.EVT_BUTTON, lambda _event: self._show_blame())
        bind_close_button(self.dialog, close_btn, modeless=False)
        self._update_buttons()

    # -- lifecycle ------------------------------------------------------------

    def show(self) -> None:
        wx = self._wx
        self._start()
        self.dialog.CentreOnParent()
        apply_modal_ids(
            self.dialog,
            affirmative_id=wx.ID_CANCEL,
            affirmative_label="Close",
            cancel_id=wx.ID_CANCEL,
            cancel_label="Close",
            escape_id=wx.ID_CANCEL,
        )
        try:
            show_modal_dialog(self.dialog, "Repository Files", announce=self._announce)
        finally:
            self.dialog.Destroy()

    def _background(self, work: Callable[[], object], done: Callable[[object, str], None]) -> None:
        def worker() -> None:
            try:
                result = work()
            except GitHubItemsError as exc:
                self._wx.CallAfter(done, None, _message(exc))
                return
            except Exception as exc:  # noqa: BLE001 - shown and spoken, never swallowed
                self._wx.CallAfter(done, None, f"Unexpected error: {_message(exc)}")
                return
            self._wx.CallAfter(done, result, "")

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: repository read.

    def _say(self, message: str) -> None:
        self._status.SetLabel(message)
        self._announce(message)

    def _start(self) -> None:
        """Find the default branch when no ref was given, and fill the ref list."""
        repo = self._repo
        self._status.SetLabel("Loading branches and tags...")

        def work() -> object:
            ref = self._ref or self._provider.fetch_default_branch(repo)
            try:
                names = self._provider.fetch_ref_names(repo)
            except GitHubItemsError:
                names = [ref]
            return ref, names

        def done(result: object, error: str) -> None:
            if not dialog_alive(self.dialog):
                return
            if error or not isinstance(result, tuple):
                self._say(f"Could not open {repo}: {error}")
                return
            ref, names = result
            self._ref_ctrl.Set(list(names))
            self._ref_ctrl.ChangeValue(str(ref))
            self._load_root()

        self._background(work, done)

    # -- the tree -------------------------------------------------------------

    def _current_ref(self) -> str:
        return self._ref_ctrl.GetValue().strip()

    def _load_root(self) -> None:
        ref = self._current_ref()
        if not ref:
            self._say("Type a branch, tag or commit first.")
            return
        self._ref = ref
        self._token += 1
        token = self._token
        self._tree.DeleteAllItems()
        root = self._tree.AddRoot(self._repo)
        self._status.SetLabel(f"Loading {self._repo} at {ref}...")
        self._load_folder(root, "", token, announce=True)

    def _load_folder(self, item: object, path: str, token: int, *, announce: bool = False) -> None:
        repo, ref = self._repo, self._ref

        def done(result: object, error: str) -> None:
            if token != self._token or not dialog_alive(self.dialog) or not item.IsOk():
                return
            self._tree.DeleteChildren(item)
            if error:
                self._say(f"Could not open {path or 'the top folder'}: {error}")
                return
            entries = result if isinstance(result, list) else []
            for entry in entries:
                child = self._tree.AppendItem(item, entry.label)
                self._tree.SetItemData(child, entry)
                if entry.is_folder:
                    self._tree.AppendItem(child, _PLACEHOLDER)
            if not path:
                first, _cookie = self._tree.GetFirstChild(item)
                if first.IsOk():
                    self._tree.SelectItem(first)
                    self._tree.SetFocus()
            message = f"{len(entries)} items in {path or ref}."
            if announce or self._wx.Window.FindFocus() is not self._tree:
                self._say(message)
            else:
                self._status.SetLabel(message)
            self._update_buttons()

        self._background(lambda: self._provider.fetch_repo_folder(repo, ref, path), done)

    def _entry(self, item: object = None) -> RepoEntry | None:
        target = item if item is not None else self._tree.GetSelection()
        if target is None or not target.IsOk():
            return None
        data = self._tree.GetItemData(target)
        return data if isinstance(data, RepoEntry) else None

    def _on_expanding(self, event: object) -> None:
        item = event.GetItem()
        entry = self._entry(item)
        if entry is None or not entry.is_folder:
            return
        child, _cookie = self._tree.GetFirstChild(item)
        if child.IsOk() and self._tree.GetItemText(child) == _PLACEHOLDER:
            self._load_folder(item, entry.path, self._token)

    def _on_activate(self, event: object) -> None:
        item = event.GetItem()
        entry = self._entry(item)
        if entry is None:
            return
        if entry.is_folder:
            self._tree.Toggle(item)
        else:
            self._view_file()

    def _update_buttons(self) -> None:
        entry = self._entry()
        is_file = entry is not None and entry.kind == "file"
        self._view_btn.Enable(is_file)
        self._edit_btn.Enable(is_file and self._open_in_editor is not None)
        self._blame_btn.Enable(is_file and self._provider.is_authenticated)
        self._history_btn.Enable(entry is not None)

    # -- actions --------------------------------------------------------------

    def _show_text(self, text: str, what: str) -> None:
        self._contents.SetValue(text)
        self._contents.SetInsertionPoint(0)
        lines = text.count("\n") + (1 if text and not text.endswith("\n") else 0)
        self._say(f"{what}: {lines} lines in Contents.")

    def _view_file(self) -> None:
        entry = self._entry()
        if entry is None or entry.kind != "file":
            self._announce("Choose a file first.")
            return
        self._content_token += 1
        token, repo, ref = self._content_token, self._repo, self._ref
        self._status.SetLabel(f"Loading {entry.path}...")

        def done(result: object, error: str) -> None:
            if token != self._content_token or not dialog_alive(self.dialog):
                return
            if error:
                self._say(error)
                return
            self._show_text(str(result), entry.name)

        self._background(lambda: self._provider.fetch_repo_file_text(repo, entry.path, ref), done)

    def _open_file_in_editor(self) -> None:
        entry = self._entry()
        if entry is None or entry.kind != "file" or self._open_in_editor is None:
            self._announce("Choose a file first.")
            return
        url = blob_url(self._repo, self._ref, entry.path)
        if self.dialog.IsModal():
            self.dialog.EndModal(self._wx.ID_OK)
        self._open_in_editor(url)

    def _show_readme(self) -> None:
        entry = self._entry()
        folder = ""
        if entry is not None:
            folder = entry.path if entry.is_folder else entry.path.rpartition("/")[0]
        self._content_token += 1
        token, repo, ref = self._content_token, self._repo, self._ref
        self._status.SetLabel("Loading the README...")

        def done(result: object, error: str) -> None:
            if token != self._content_token or not dialog_alive(self.dialog):
                return
            if error or not isinstance(result, tuple):
                self._say(error or "Could not read the README.")
                return
            path, text = result
            self._show_text(str(text), str(path))

        self._background(lambda: self._provider.fetch_readme(repo, ref, folder), done)

    def _show_history(self) -> None:
        entry = self._entry()
        if entry is None:
            self._announce("Choose a file or folder first.")
            return
        repo, ref, path = self._repo, self._ref, entry.path

        def load() -> list[FileRun]:
            return [
                FileRun(
                    commit.label(),
                    f"{commit.title}\n{commit.author}, {commit.date}\nCommit {commit.sha}\n"
                    f"{commit.url}",
                    commit.url,
                )
                for commit in self._provider.fetch_file_history(repo, path, ref)
            ]

        GitHubFileRunsDialog(
            self.dialog,
            title=f"History of {entry.name}",
            noun="commits",
            load=load,
            announce_cb=self._announce,
        ).show()

    def _show_blame(self) -> None:
        entry = self._entry()
        if entry is None or entry.kind != "file":
            self._announce("Choose a file first.")
            return
        repo, ref, path = self._repo, self._ref, entry.path

        def load() -> list[FileRun]:
            return [
                FileRun(
                    run.label(),
                    f"{run.label()}\nCommit {run.sha}\n{run.url}",
                    run.url or f"https://github.com/{repo}/commit/{run.sha}",
                )
                for run in self._provider.fetch_blame(repo, ref, path)
            ]

        GitHubFileRunsDialog(
            self.dialog,
            title=f"Blame for {entry.name}",
            noun="runs",
            load=load,
            announce_cb=self._announce,
        ).show()
