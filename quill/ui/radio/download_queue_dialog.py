"""**Downloads...** -- the queue, and everything you can do to it.

The window behind *View > Downloads*. A queue you cannot see is a progress bar
with extra steps: the questions people actually have are *"is it still going?"*,
*"did that one work?"* and *"where did it go?"*, and all three are answered here.

Four decisions:

* **Finished rows stay.** A queue that tidies itself away as it succeeds cannot
  answer "did that actually download?", which is the question asked most. They
  are cleared when *you* say so.
* **Every row is a whole sentence, with its state last.** "Chapter 4,
  Middlemarch, downloading now". State last because when you are arrowing a
  queue you already know what the items are -- what you are looking for is where
  each one has got to.
* **Open Containing Folder is the point of finishing.** A download you cannot
  find is a download that did not really happen, so a saved row keeps its path
  and can hand you to it.
* **Buttons say what they will do to the row you are on**, and are unavailable
  when they would do nothing -- Cancel on something already saved, Open on
  something that never arrived.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core.radio.download_queue import DONE, RUNNING, WAITING, DownloadQueue, QueueItem
from quill.ui.dialog_contract import (
    announce_surface_exit,
    apply_listbox_activation,
    apply_modal_ids,
)

TITLE = "Downloads"

#: Shown when there is nothing queued. A finished queue is a good state, and
#: saying so beats an empty list that reads like a failure.
NOTHING = "Nothing has been queued for download yet."


class DownloadQueueDialog:
    """Watch the queue, and cancel, remove, clear or open anything in it."""

    def __init__(
        self,
        parent: Any,
        *,
        queue: DownloadQueue,
        cancel: Callable[[QueueItem], bool] | None = None,
        clear_all: Callable[[], int] | None = None,
        announce: Callable[[str], None] | None = None,
        show_modal_dialog: Callable[[Any, str], int] | None = None,
        open_folder: Callable[[str], bool] | None = None,
        open_preferences: Callable[[], None] | None = None,
        transport_host: object | None = None,
        windows: object | None = None,
        on_closed: Callable[[], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._transport_host = transport_host
        self._queue = queue
        self._cancel = cancel
        self._clear_all = clear_all
        self._announce = announce or (lambda _m: None)
        self._show_modal_dialog = show_modal_dialog
        self._open_folder = open_folder
        self._open_preferences = open_preferences
        self._rows: list[QueueItem] = []
        self._menu_id_refs: list[object] = []
        #: Runs when the modeless window closes, so the opener can stop
        #: pointing background refreshes at a dead window.
        self._on_closed = on_closed or (lambda: None)

        # Modeless parentless wx.Frame (a peer window in the taskbar, the
        # &Window menu and Ctrl+Tab) when standalone Radio supplies a
        # WindowManager; an unchanged modal wx.Dialog for embedded QUILL.
        self._windows = windows
        self._modeless = windows is not None
        if self._modeless:
            self._dialog = wx.Frame(None, title=TITLE, style=wx.DEFAULT_FRAME_STYLE)
            self._surface = wx.Panel(self._dialog, style=wx.TAB_TRAVERSAL)
            self._build_surface_menu_bar()
            self._dialog.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)
            self._dialog.Bind(wx.EVT_CLOSE, self._on_close)
        else:
            self._dialog = wx.Dialog(
                parent, title=TITLE, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
            )
            self._surface = self._dialog
        root = wx.BoxSizer(wx.VERTICAL)

        self._heading = wx.StaticText(self._surface, label="")
        root.Add(self._heading, 0, wx.ALL, 10)

        root.Add(wx.StaticText(self._surface, label="Dow&nloads:"), 0, wx.LEFT | wx.RIGHT, 10)
        self._list = wx.ListBox(self._surface, style=wx.LB_SINGLE)
        self._list.SetName("Everything queued for download, and where each one has got to")
        root.Add(self._list, 1, wx.EXPAND | wx.ALL, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self._open_btn = wx.Button(self._surface, label="&Open Containing Folder")
        self._open_btn.SetHelpText(
            "Shows the highlighted download's saved file in Explorer. Only a "
            "finished download has a folder to show."
        )
        self._cancel_btn = wx.Button(self._surface, label="&Cancel This One")
        self._cancel_btn.SetHelpText(
            "Stops the highlighted download. Anything already saved is kept."
        )
        self._remove_btn = wx.Button(self._surface, label="&Remove From List")
        self._remove_btn.SetHelpText(
            "Takes the highlighted row off the list without touching any saved file."
        )
        self._clear_btn = wx.Button(self._surface, label="Clear &Finished")
        self._clear_btn.SetHelpText("Removes every finished row; the saved files stay on disk.")
        self._clear_all_btn = wx.Button(self._surface, label="Clear &All")
        self._clear_all_btn.SetHelpText(
            "Empties the whole list, stopping anything still going. Saved files are kept."
        )
        for button in (
            self._open_btn,
            self._cancel_btn,
            self._remove_btn,
            self._clear_btn,
            self._clear_all_btn,
        ):
            buttons.Add(button, 0, wx.RIGHT, 6)
        if open_preferences is not None:
            # Where things land and whether closing keeps the queue going are
            # decided in Download Preferences; the queue window is where the
            # question occurs to people, so the door is here too.
            prefs_btn = wx.Button(self._surface, label="&Preferences...")
            prefs_btn.SetName("Download Preferences: folders, filing, and background downloads")
            prefs_btn.Bind(wx.EVT_BUTTON, lambda _e: open_preferences())
            buttons.Add(prefs_btn, 0, wx.RIGHT, 6)
        if not self._modeless:
            # Only the modal dialog carries a Close button: a real window
            # closes with Alt+F4/Ctrl+F4, Ctrl+W, or Escape (2026-08-23).
            from quill.ui.dialog_contract import bind_close_button

            close_btn = wx.Button(self._surface, wx.ID_CANCEL, "Close")
            close_btn.SetHelpText(
                "Closes the queue window. Whether downloads keep going is the "
                "background-downloads preference."
            )
            bind_close_button(self._dialog, close_btn, modeless=False)
            buttons.Add(close_btn, 0)
        root.Add(buttons, 0, wx.ALL, 10)

        self._surface.SetSizer(root)
        if self._modeless:
            outer = wx.BoxSizer(wx.VERTICAL)
            outer.Add(self._surface, 1, wx.EXPAND)
            self._dialog.SetSizer(outer)
        self._dialog.SetMinSize((680, 420))
        self._dialog.Fit()
        if not self._modeless:
            apply_modal_ids(self._dialog, cancel_id=wx.ID_CANCEL, cancel_label="Close")

        # The transport keyboard, when the surface that opened this one knows
        # about the player. It was installed in the browse tree and nowhere
        # else, so every other Radio dialog was a window where the keys that
        # work everywhere stopped working. The WindowManager's Ctrl+Tab /
        # Ctrl+1..9 rows ride in the same table when this is a peer window.
        if self._transport_host is not None:
            from quill.ui.radio import transport_keys

            transport_keys.install(
                self._dialog,
                self._transport_host,
                wx=wx,
                extra_entries=self._windows.accelerator_entries() if self._modeless else (),
            )

        self._open_btn.Bind(wx.EVT_BUTTON, lambda _e: self.open_selected())
        self._cancel_btn.Bind(wx.EVT_BUTTON, lambda _e: self.cancel_selected())
        self._remove_btn.Bind(wx.EVT_BUTTON, lambda _e: self.remove_selected())
        self._clear_btn.Bind(wx.EVT_BUTTON, lambda _e: self.clear_finished())
        self._clear_all_btn.Bind(wx.EVT_BUTTON, lambda _e: self.clear_everything())
        self._list.Bind(wx.EVT_LISTBOX, lambda _e: self._sync_buttons())
        # Enter on a saved row opens where it went -- the one thing you want
        # from a finished download (GATE-13: a ListBox emits no activate event).
        apply_listbox_activation(self._list, lambda _e: self.open_selected())

        self.refresh()
        self._list.SetFocus()

    @property
    def dialog(self) -> Any:
        return self._dialog

    def _build_surface_menu_bar(self) -> None:
        """Menu bar for the modeless frame: &Close + the shared &Window menu."""
        wx = self._wx
        menu_bar = wx.MenuBar()
        surface_menu = wx.Menu()
        close_id = wx.NewIdRef()
        surface_menu.Append(close_id, "&Close\tCtrl+W")
        self._dialog.Bind(wx.EVT_MENU, lambda _e: self._dialog.Close(), id=close_id)
        menu_bar.Append(surface_menu, "&Downloads")
        # The app's own Station commands, so Alt+S opens the same menu here it
        # opens in the main window -- see surface_app_menu for the report.
        from quill.ui.radio import surface_app_menu

        self._menu_id_refs.extend(
            surface_app_menu.install(
                win=self._dialog,
                host=surface_app_menu.host_of(self),
                menu_bar=menu_bar,
                wx=wx,
                skip=(),
            )
        )
        self._windows.install(self._dialog, menu_bar)
        self._dialog.SetMenuBar(menu_bar)
        self._menu_id_refs.append(close_id)

    def _on_char_hook(self, event: Any) -> None:
        # A frame has no automatic Escape->Cancel; wire it (and Ctrl+F4, the
        # document-window close key) to close, like every peer window.
        wx = self._wx
        if event.GetKeyCode() == wx.WXK_ESCAPE or (
            event.GetKeyCode() == wx.WXK_F4 and event.ControlDown()
        ):
            self._dialog.Close()
            return
        event.Skip()

    def _on_close(self, event: Any) -> None:
        # First thing: stop the runner pointing background refreshes here.
        self._on_closed()
        previous = self._windows.previous_key(self._dialog)
        self._windows.unregister(self._dialog)
        announce_surface_exit(TITLE, self._announce)
        event.Skip()
        self._dialog.Destroy()
        if previous:
            self._windows.activate(previous)

    def refresh(self) -> None:
        """Redraw from the queue, keeping the cursor on the same row.

        By identity rather than index: rows are removed and the list is
        rebuilt while somebody is reading it, and an index would silently move
        them onto a different download.
        """
        selected = self.selected()
        self._rows = list(self._queue.items)
        self._list.Set([item.row_label() for item in self._rows])
        self._heading.SetLabel(self._queue.summary() if self._rows else NOTHING)
        if self._rows:
            index = next(
                (i for i, item in enumerate(self._rows) if selected and item.id == selected.id),
                0,
            )
            self._list.SetSelection(min(index, len(self._rows) - 1))
        self._sync_buttons()
        self._surface.Layout()
        self._dialog.Layout()

    def selected(self) -> QueueItem | None:
        index = self._list.GetSelection()
        if index < 0 or index >= len(self._rows):
            return None
        return self._rows[index]

    def _sync_buttons(self) -> None:
        """Enable only what would actually do something to this row."""
        item = self.selected()
        self._open_btn.Enable(bool(item and item.state == DONE and item.path))
        self._cancel_btn.Enable(bool(item and item.state in (WAITING, RUNNING)))
        self._remove_btn.Enable(bool(item and item.state != RUNNING))
        finished = any(i.is_finished for i in self._rows)
        self._clear_btn.Enable(finished)
        self._clear_all_btn.Enable(bool(self._rows))

    def open_selected(self) -> bool:
        """Show where a finished download went."""
        item = self.selected()
        if item is None or item.state != DONE or not item.path:
            self._announce("That one has not been saved yet.")
            return False
        folder = str(Path(item.path).parent)
        if self._open_folder is not None:
            opened = bool(self._open_folder(folder))
        else:
            # The shared, tested argv -- the split "/select," form Explorer
            # ignores, opening Documents instead, is a bug this repo already hit
            # once and does not need to hit twice.
            import subprocess

            from quill.core.file_manager import reveal_command

            try:
                subprocess.Popen(reveal_command(item.path))  # noqa: S603
                opened = True
            except OSError:
                opened = False
        self._announce(
            f"Showing {item.name} in {folder}." if opened else "That folder could not be opened."
        )
        return opened

    def cancel_selected(self) -> bool:
        item = self.selected()
        if item is None or self._cancel is None:
            return False
        if not self._cancel(item):
            return False
        self._announce(f"Cancelled {item.name}. Anything already saved is kept.")
        self.refresh()
        return True

    def remove_selected(self) -> bool:
        """Take a row off the list without touching what is on disk."""
        item = self.selected()
        if item is None:
            return False
        if not self._queue.remove(item):
            self._announce("That one is downloading now. Cancel it first.")
            return False
        self._announce(f"Removed {item.name} from the list. Any saved file is untouched.")
        self.refresh()
        return True

    def clear_finished(self) -> int:
        removed = self._queue.clear_finished()
        self._announce(f"Cleared {removed} finished." if removed else "Nothing finished to clear.")
        self.refresh()
        return removed

    def clear_everything(self) -> int:
        """Empty the list, stopping anything still going."""
        removed = self._clear_all() if self._clear_all is not None else self._queue.clear_all()
        self._announce(
            f"Cleared the download list. {removed} removed. Anything already saved is kept."
        )
        self.refresh()
        return removed

    def show(self) -> int:
        """Show the window; the modal shape is destroyed afterwards (A11Y-4),
        the modeless one when its own close handler runs."""
        if self._modeless:
            from quill.ui.dialog_contract import show_modeless_surface

            self._windows.register(self._dialog, TITLE)
            show_modeless_surface(self._dialog, TITLE, announce=self._announce)
            return 0
        try:
            if self._show_modal_dialog is not None:
                return int(self._show_modal_dialog(self._dialog, TITLE))
            return int(self._dialog.ShowModal())  # dialog_button_contract: exempt
        finally:
            self._dialog.Destroy()
