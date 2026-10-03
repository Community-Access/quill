"""The Watched Folders window (qc.md 5d, C2-02): a peer, like Notifications.

Each row is a sentence -- name, state, how many files, when something last
arrived, then the path last because it is the longest and least often needed.
Enter goes to the folder's files in Personal Audio. The buttons are the verbs;
the Applications key offers them again with Open Folder in File Explorer and
Copy Path.

Made once and hidden on close, so its number in the Window menu does not move.
The work -- watching, scanning, announcing -- is the host's
(:mod:`quill.ui.podcasts.folder_watch`); this window only asks for it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import wx

from quill.core.podcasts.watched_folder_words import row_text
from quill.core.podcasts.watched_folders import WatchedFolder

__all__ = ["TITLE", "WatchedFoldersWindow", "open_watched_folders_window"]

TITLE = "Watched Folders"
_EMPTY = "No folders yet. Press Add Folder to choose one."


class WatchedFoldersWindow:
    """The frame, its list, and the verbs."""

    def __init__(self, host: Any) -> None:
        self._host = host
        self._folders: list[WatchedFolder] = []
        self.frame = wx.Frame(host.frame, title=TITLE, size=(720, 440))
        panel = wx.Panel(self.frame, style=wx.TAB_TRAVERSAL)
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(wx.StaticText(panel, label="&List of folders:"), 0, wx.LEFT | wx.TOP, 8)
        self._list = wx.ListBox(panel, choices=[], style=wx.LB_SINGLE)
        self._list.SetHelpText(
            "Every folder Cast watches. Anything that lands in one arrives in "
            "Personal Audio by itself. Enter goes to the folder's files; the "
            "Applications key offers the buttons, Open Folder in File Explorer and "
            "Copy Path. Escape closes the window."
        )
        root.Add(self._list, 1, wx.EXPAND | wx.ALL, 8)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        for label, help_text, handler in (
            (
                "&Add Folder...",
                "Choose a folder for Cast to watch, then how its files should arrive.",
                self._add,
            ),
            (
                "Folder &Settings...",
                "Change the name, what happens to the original, what you hear, and "
                "which files this folder brings in.",
                self._settings,
            ),
            (
                "Scan &Now",
                "Looks at this folder straight away. Useful for a folder on a network "
                "drive, which Cast otherwise checks every ten minutes.",
                self._scan,
            ),
            (
                "Pa&use or Resume",
                "Stops watching this folder for now, or starts again. Nothing already "
                "brought in changes.",
                self._toggle_pause,
            ),
            (
                "Re&move...",
                "Stops watching this folder. The files already brought in stay in "
                "Personal Audio and nothing on disk is touched.",
                self._remove,
            ),
        ):
            button = wx.Button(panel, label=label)
            button.SetHelpText(help_text)
            button.Bind(wx.EVT_BUTTON, lambda _e, h=handler: h())
            buttons.Add(button, 0, wx.RIGHT, 6)
        buttons.AddStretchSpacer(1)
        close = wx.Button(panel, label="Close")
        close.SetHelpText("Closes this window and returns to where you were.")
        from quill.ui.dialog_contract import bind_close_button

        bind_close_button(self.frame, close, modeless=True)
        buttons.Add(close, 0)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        panel.SetSizer(root)
        from quill.ui.dialog_contract import apply_listbox_activation

        apply_listbox_activation(self._list, lambda _e: self._go_to())
        for context_event in (wx.EVT_CONTEXT_MENU, wx.EVT_RIGHT_UP):
            self._list.Bind(context_event, self._on_context)
        self._list.Bind(wx.EVT_KEY_DOWN, self._on_key)
        self.frame.Bind(wx.EVT_CLOSE, self._on_close)
        self.frame.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)

    # -- showing --------------------------------------------------------------------- #

    def show(self, *, focus: bool = True) -> None:
        self.refresh()
        from quill.ui.dialog_contract import show_modeless_surface

        show_modeless_surface(self.frame, TITLE, announce=self._host._announce)
        self.frame.Raise()
        if focus:
            self._list.SetFocus()

    def refresh(self, *, keep: int = -1) -> None:
        library = self._host._podcast_library
        self._folders = list(library.watched_folders)
        rows = [row_text(library, folder) for folder in self._folders]
        self._list.Set(rows or [_EMPTY])
        if self._list.GetCount():
            wanted = keep if 0 <= keep < self._list.GetCount() else 0
            self._list.SetSelection(wanted)

    def _on_close(self, event: Any) -> None:
        if event.CanVeto():
            event.Veto()
            self.frame.Hide()
            from quill.ui.dialog_contract import announce_surface_exit

            announce_surface_exit(TITLE, self._host._announce)
            focus = getattr(self._host, "_focus_cast_initial_control", None)
            if callable(focus):
                focus()
            return
        event.Skip()

    def _on_char_hook(self, event: Any) -> None:
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.frame.Close()
            return
        event.Skip()

    # -- the verbs ---------------------------------------------------------------------- #

    def _current(self, *, say: bool = True) -> WatchedFolder | None:
        index = self._list.GetSelection()
        if not self._folders or not (0 <= index < len(self._folders)):
            if say:
                self._host._announce("Choose a folder first, or press Add Folder.")
            return None
        return self._folders[index]

    def _add(self) -> None:
        folder = self._host.add_watched_folder(parent=self.frame)
        if folder is not None:
            self.refresh(keep=len(self._folders))
            self._list.SetFocus()

    def _settings(self) -> None:
        folder = self._current()
        if folder is not None and self._host.change_watched_folder_settings(
            folder, parent=self.frame
        ):
            self.refresh(keep=self._list.GetSelection())

    def _scan(self) -> None:
        folder = self._current()
        if folder is not None:
            self._host.scan_watched_folder_now(folder.id)

    def _toggle_pause(self) -> None:
        folder = self._current()
        if folder is not None:
            self._host.pause_watched_folder(folder.id, not folder.paused)
            self.refresh(keep=self._list.GetSelection())

    def _remove(self) -> None:
        folder = self._current()
        if folder is not None and self._host.remove_watched_folder(folder.id, parent=self.frame):
            self.refresh(keep=self._list.GetSelection())

    def _go_to(self) -> None:
        folder = self._current()
        if folder is None:
            return
        self.frame.Hide()
        wx.CallAfter(self._host.show_place, "personal_audio")

    def _open_in_explorer(self) -> None:
        folder = self._current()
        if folder is None:
            return
        if not Path(folder.path).is_dir():
            self._host._announce(f"{folder.display_name()} is not there to open.")
            return
        wx.LaunchDefaultApplication(folder.path)

    def _copy_path(self) -> None:
        folder = self._current()
        if folder is None:
            return
        if self._host._copy_to_clipboard(folder.path):
            self._host._announce("Path copied.")
        else:
            self._host._announce("The clipboard is busy; the path was not copied.")

    def _on_key(self, event: Any) -> None:
        if event.GetKeyCode() in (wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE):
            self._remove()
            return
        event.Skip()

    def _on_context(self, event: Any) -> None:
        folder = self._current(say=False)
        if folder is None:
            return
        menu = wx.Menu()
        rows: list[tuple[str, Any]] = [
            ("&Go to Its Files\tEnter", self._go_to),
            ("Folder &Settings...", self._settings),
            ("Scan &Now", self._scan),
            ("&Resume Watching" if folder.paused else "&Pause Watching", self._toggle_pause),
            ("Open Folder in File &Explorer", self._open_in_explorer),
            ("&Copy Path", self._copy_path),
            ("Re&move...\tDelete", self._remove),
        ]
        for label, handler in rows:
            item = menu.Append(wx.ID_ANY, label)
            menu.Bind(wx.EVT_MENU, lambda _e, h=handler: h(), item)
        try:
            self._list.PopupMenu(menu)
        finally:
            menu.Destroy()
        if hasattr(event, "Skip"):
            event.Skip(False)


def open_watched_folders_window(host: Any, *, focus: bool = True) -> WatchedFoldersWindow:
    """Open, or raise, the host's Watched Folders window (made once, hidden on close)."""
    window = getattr(host, "_watched_folders_window", None)
    if window is None:
        window = WatchedFoldersWindow(host)
        host._watched_folders_window = window
        _install_peer(host, window)
    window.show(focus=focus)
    return window


def _install_peer(host: Any, window: WatchedFoldersWindow) -> None:
    windows = getattr(host, "_windows", None)
    frame = window.frame
    menu_bar = wx.MenuBar()
    own = wx.Menu()
    close_id = wx.NewIdRef()
    own.Append(close_id, "&Close\tCtrl+W")
    frame.Bind(wx.EVT_MENU, lambda _e: frame.Close(), id=close_id)
    menu_bar.Append(own, "Watched &Folders")
    if windows is not None:
        windows.install(frame, menu_bar)
    frame.SetMenuBar(menu_bar)
    keep = getattr(host, "_keep_menu_ids", None)
    if callable(keep):
        keep(close_id)
    if windows is not None:
        windows.register(frame, TITLE, focus=lambda: window._list.SetFocus())
