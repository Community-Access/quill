"""Clone Repository, shared by QUILL and QUILL Lite (2026-11-08).

One window and one flow, reached from GitHub > Clone Repository... in workbench
mode, from File > Open from Remote > Clone Repository... in QUILL and from File >
Clone Repository... in QUILL Lite. The work itself is
:mod:`quill.core.github.clone`; this module asks the two questions (which
repository, which folder), runs the clone in the background, and says how it
went once.

Each editor hands in a :class:`CloneHost`: its parent window, its voice, its
background runner, and what to do with the new folder (QUILL offers to open it
as a project or open a file from it; QUILL Lite offers a file). Nothing here
knows which editor it is in.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from quill.core.github.clone import (
    GIT_DOWNLOAD_URL,
    CloneError,
    CloneSource,
    clone_repository,
    parse_clone_source,
    target_folder,
)
from quill.ui.dialog_contract import apply_modal_ids, show_message_box, show_modal_dialog
from quill.ui.dpi import dip

__all__ = [
    "CloneHost",
    "CloneRepositoryDialog",
    "CloneRequest",
    "default_clone_folder",
    "start_clone",
]

TITLE = "Clone Repository"
NO_GIT = (
    "Cloning needs Git for Windows, which is not installed on this computer. "
    "Open its download page?"
)


def default_clone_folder() -> str:
    """The GitHub folder in Documents when it exists (GitHub Desktop's habit), else Documents."""
    home = Path.home()
    for candidate in (home / "Documents" / "GitHub", home / "Documents"):
        if candidate.is_dir():
            return str(candidate)
    return str(home)


@dataclass(frozen=True, slots=True)
class CloneRequest:
    """What the window collected."""

    source: CloneSource
    parent_folder: Path


@dataclass(slots=True)
class CloneHost:
    """What an editor gives the clone flow.

    *run_background* is ``(name, work, on_done, on_failed)``: run ``work()`` off
    the UI thread and call one of the two back on it.
    """

    parent: Any
    announce: Callable[[str], None]
    run_background: Callable[
        [str, Callable[[], Path], Callable[[Path], None], Callable[[BaseException], None]], None
    ]
    after_clone: Callable[[Path], None]
    initial_repo: str = ""
    default_folder: str = ""
    safe_mode: bool = False


class CloneRepositoryDialog:
    """Repository and destination folder, with Browse; OK clones."""

    def __init__(self, parent: Any, *, initial_repo: str = "", default_folder: str = "") -> None:
        import wx

        self._wx = wx
        self.dialog = wx.Dialog(parent, title=TITLE, style=wx.DEFAULT_DIALOG_STYLE)
        panel = wx.Panel(self.dialog)
        sizer = wx.BoxSizer(wx.VERTICAL)

        sizer.Add(
            wx.StaticText(panel, label="&Repository (owner/name or address)"),
            flag=wx.LEFT | wx.RIGHT | wx.TOP,
            border=12,
        )
        self._repo = wx.TextCtrl(panel, value=initial_repo, size=(dip(parent, 420), -1))
        self._repo.SetName("Repository, owner/name or address")
        self._repo.SetHelpText(
            "The repository to copy to this computer: owner/name, such as "
            "octocat/hello-world, or its address from GitHub's Code button."
        )
        sizer.Add(self._repo, flag=wx.EXPAND | wx.LEFT | wx.RIGHT, border=12)

        sizer.Add(
            wx.StaticText(panel, label="&Into this folder"),
            flag=wx.LEFT | wx.RIGHT | wx.TOP,
            border=12,
        )
        row = wx.BoxSizer(wx.HORIZONTAL)
        self._folder = wx.TextCtrl(panel, value=default_folder)
        self._folder.SetName("Into this folder")
        self._folder.SetHelpText(
            "The folder the copy goes in. QUILL makes a new folder inside it named "
            "after the repository."
        )
        row.Add(self._folder, 1, wx.EXPAND | wx.RIGHT, 8)
        browse = wx.Button(panel, label="&Browse...")
        browse.SetHelpText("Choose the folder the copy goes in.")
        browse.Bind(wx.EVT_BUTTON, self._on_browse)
        row.Add(browse, 0)
        sizer.Add(row, flag=wx.EXPAND | wx.LEFT | wx.RIGHT, border=12)

        buttons = wx.StdDialogButtonSizer()
        ok = wx.Button(panel, wx.ID_OK, label="Clone")
        ok.SetDefault()
        ok.SetHelpText("Copy the repository into the folder.")
        cancel = wx.Button(panel, wx.ID_CANCEL, label="Cancel")
        cancel.SetHelpText("Close without cloning.")
        buttons.AddButton(ok)
        buttons.AddButton(cancel)
        buttons.Realize()
        sizer.Add(buttons, flag=wx.EXPAND | wx.ALL, border=8)

        panel.SetSizer(sizer)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.dialog.SetSizer(outer)
        self.dialog.Fit()
        self._repo.SetFocus()
        if initial_repo:
            self._repo.SelectAll()

    def _on_browse(self, _event: object) -> None:
        wx = self._wx
        with wx.DirDialog(
            self.dialog, "Clone into this folder", self._folder.GetValue().strip()
        ) as chooser:
            if show_modal_dialog(chooser, "Clone into this folder") == wx.ID_OK:
                self._folder.SetValue(chooser.GetPath())

    def show(self) -> tuple[str, str] | None:
        """``(repository, folder)`` as typed, or ``None`` on Cancel."""
        wx = self._wx
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        try:
            if show_modal_dialog(self.dialog, TITLE) != wx.ID_OK:
                return None
            return self._repo.GetValue().strip(), self._folder.GetValue().strip()
        finally:
            self.dialog.Destroy()


def _ask(host: CloneHost) -> CloneRequest | None:
    """Ask until the answers make sense or the person cancels."""
    import wx

    repo, folder = host.initial_repo, host.default_folder
    while True:
        answer = CloneRepositoryDialog(host.parent, initial_repo=repo, default_folder=folder).show()
        if answer is None:
            return None
        repo, folder = answer
        try:
            source = parse_clone_source(repo)
            if not folder:
                raise CloneError("Choose the folder the copy goes in.")
            target_folder(folder, source)
        except CloneError as error:
            show_message_box(str(error), TITLE, wx.OK | wx.ICON_INFORMATION, host.parent)
            continue
        return CloneRequest(source=source, parent_folder=Path(folder))


def _offer_git_download(host: CloneHost) -> None:
    import webbrowser

    import wx

    if show_message_box(NO_GIT, TITLE, wx.YES_NO | wx.ICON_INFORMATION, host.parent) == wx.YES:
        webbrowser.open(GIT_DOWNLOAD_URL, new=2)


def start_clone(host: CloneHost, *, token_loader: Callable[[], str] | None = None) -> None:
    """The whole flow: refuse in Safe Mode, find git, ask, clone, say, offer."""
    import wx

    from quill.core.git_binaries import GitBinaryError, find_git

    if host.safe_mode:
        show_message_box(
            "Cloning is off in Safe Mode, which turns off everything that reaches the network.",
            TITLE,
            wx.OK | wx.ICON_INFORMATION,
            host.parent,
        )
        return
    try:
        git = find_git()
    except GitBinaryError:
        git = None
    if git is None:
        _offer_git_download(host)
        return
    request = _ask(host)
    if request is None:
        return
    if token_loader is None:
        from quill.core.github.token_store import load_github_token

        token_loader = load_github_token
    token = (token_loader() or "") if request.source.on_github else ""
    source = request.source
    target = target_folder(request.parent_folder, source)

    def work() -> Path:
        from quill.stability.safe_subprocess import run_subprocess_safely

        return clone_repository(git, source, target, token=token, runner=run_subprocess_safely)

    def done(folder: Path) -> None:
        host.announce(f"Cloned {source.full_name or source.name}.")
        host.after_clone(folder)

    def failed(error: BaseException) -> None:
        message = (
            str(error).split("] ", 1)[-1]
            if isinstance(error, CloneError)
            else f"Could not clone {source.name}."
        )
        host.announce(message)

    host.announce(f"Cloning {source.full_name or source.name}.")
    host.run_background(f"Cloning {source.name}", work, done, failed)
