"""Quill Inkwell -- abbreviation expansion everywhere, not just in QUILL.

QUILL has always expanded abbreviations inside its own editor. Inkwell is the
same feature, in every other application: type "addr" and a space in a browser,
a mail client, or a form, and the address you saved appears.

The point of it being part of the family rather than a separate product is that
there is exactly **one** library. Inkwell and QUILL read and write the same
``abbreviations.json`` in the same data directory -- add an abbreviation in
either and it works in both immediately, with no import, export, or sync.

The window is small on purpose: expansion is a background service, so Inkwell
lives in the system tray and its window is only where you manage the list.
Clipboard handling stays deliberately minimal -- a snapshot for ``${clipboard}``
and nothing more.

Bootstrap mirrors the other family apps: single-instance via ``core.ipc``, an
:class:`~quill.ui.app_shell.AppShellFrame` host for announcements, tray, and
the shared dialog contract.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import wx

from quill.core.abbreviations import (
    AbbreviationLibrary,
    load_abbreviation_library,
    record_use,
    resolve_expansion,
    save_abbreviation_library,
)
from quill.core.expansion.settings import (
    InkwellSettings,
    load_settings,
    save_settings,
)
from quill.ui.app_shell import AppShellFrame
from quill.ui.inkwell_expansion import InkwellExpansionMixin

_TITLE = "Quill Inkwell"
_VERSION = "1.0.0"
_REPO = "Community-Access/quill"
_IPC_SLOT = "inkwell"

#: Hotkey ids for the two system-wide chords this app registers of its own
#: (the tray toggle's id belongs to AppShellFrame).
_QUICK_INSERT_HOTKEY_ID = 0x51A1
_EXPAND_NOW_HOTKEY_ID = 0x51A2


class QuillInkwellFrame(AppShellFrame, InkwellExpansionMixin):
    """The manager window for a system-wide expander that runs in the tray."""

    def __init__(self, *, safe_mode: bool = False) -> None:
        self._init_app_shell(_TITLE, safe_mode=safe_mode, size=(560, 420))
        from quill.core.paths import app_data_dir
        from quill.ui.window_menu import WindowManager

        self._data_dir: Path = app_data_dir()
        self._settings: InkwellSettings = load_settings(self._data_dir)
        self._library: AbbreviationLibrary = load_abbreviation_library(self._data_dir)
        self._hook: Any = None
        self._windows = WindowManager(wx)
        self._build_menu_bar()
        self._build_main_panel()
        self._ensure_tray_icon(self._build_tray_menu, tooltip=_TITLE)
        self._register_tray_hotkey(self._settings.tray_hotkey)
        # Two more system-wide chords, so the expander is reachable from
        # whatever application you are typing in -- which is the whole point.
        self._register_global_hotkey(
            _QUICK_INSERT_HOTKEY_ID, self._settings.quick_insert_hotkey, self.open_quick_insert
        )
        self._register_global_hotkey(
            _EXPAND_NOW_HOTKEY_ID, self._settings.expand_now_hotkey, self.expand_now
        )
        self.frame.Bind(wx.EVT_CLOSE, self._on_close)
        # Safe Mode means "do the minimum and touch nothing": a global keyboard
        # hook is exactly the kind of thing it exists to keep switched off.
        if safe_mode:
            self._announce("Safe Mode: system-wide expansion is off.")
        elif self._settings.expansion_enabled:
            wx.CallAfter(self._start_expansion)
        self._start_ipc_poll()
        self._refresh_status()

    # -- menus -------------------------------------------------------------------

    def _build_menu_bar(self) -> None:
        menu_bar = wx.MenuBar()

        file_menu = wx.Menu()
        tray_id, exit_id = wx.NewIdRef(), wx.NewIdRef()
        file_menu.Append(tray_id, "Minimize to &Tray\tCtrl+W")
        file_menu.Append(exit_id, "E&xit")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.toggle_window_to_tray(), id=tray_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._exit_application(), id=exit_id)
        menu_bar.Append(file_menu, "&File")

        abbr_menu = wx.Menu()
        manage_id, quick_id, clip_id = wx.NewIdRef(), wx.NewIdRef(), wx.NewIdRef()
        abbr_menu.Append(manage_id, "&Manage Abbreviations...\tCtrl+M")
        abbr_menu.Append(quick_id, "&Quick Insert...\tCtrl+K")
        abbr_menu.Append(clip_id, "New from &Clipboard...\tCtrl+Shift+N")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_manager(), id=manage_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_quick_insert(), id=quick_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.new_from_clipboard(), id=clip_id)
        expand_now_id = wx.NewIdRef()
        abbr_menu.Append(expand_now_id, "&Expand the Word I Just Typed")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.expand_now(), id=expand_now_id)
        abbr_menu.AppendSeparator()
        self._pause_item_id = wx.NewIdRef()
        abbr_menu.AppendCheckItem(
            self._pause_item_id, "&Expand in other applications\tCtrl+Shift+E"
        )
        abbr_menu.Check(self._pause_item_id, self._settings.expansion_enabled)
        self.frame.Bind(
            wx.EVT_MENU, lambda e: self.set_expansion_enabled(e.IsChecked()), id=self._pause_item_id
        )
        menu_bar.Append(abbr_menu, "&Abbreviations")

        options_menu = wx.Menu()
        self._startup_item_id = wx.NewIdRef()
        options_menu.AppendCheckItem(self._startup_item_id, "Start Quill Inkwell with &Windows")
        options_menu.Check(self._startup_item_id, self._launch_at_startup_enabled())
        self.frame.Bind(
            wx.EVT_MENU,
            lambda e: self._set_launch_at_startup(e.IsChecked()),
            id=self._startup_item_id,
        )
        self._start_tray_item_id = wx.NewIdRef()
        options_menu.AppendCheckItem(self._start_tray_item_id, "Start &minimized to the tray")
        options_menu.Check(self._start_tray_item_id, self._settings.start_in_tray)
        self.frame.Bind(
            wx.EVT_MENU,
            lambda e: self._set_pref("start_in_tray", e.IsChecked()),
            id=self._start_tray_item_id,
        )
        self._close_tray_item_id = wx.NewIdRef()
        options_menu.AppendCheckItem(self._close_tray_item_id, "&Close button keeps expanding")
        options_menu.Check(self._close_tray_item_id, self._settings.close_to_tray)
        self.frame.Bind(
            wx.EVT_MENU,
            lambda e: self._set_pref("close_to_tray", e.IsChecked()),
            id=self._close_tray_item_id,
        )
        options_menu.AppendSeparator()
        self._paste_item_id = wx.NewIdRef()
        options_menu.AppendCheckItem(
            self._paste_item_id, "Insert by &pasting (for apps that drop typed text)"
        )
        options_menu.Check(self._paste_item_id, self._settings.injection_mode == "paste")
        self.frame.Bind(
            wx.EVT_MENU,
            lambda e: self._set_injection_mode(e.IsChecked()),
            id=self._paste_item_id,
        )
        self._announce_item_id = wx.NewIdRef()
        options_menu.AppendCheckItem(self._announce_item_id, "&Announce every expansion")
        options_menu.Check(self._announce_item_id, self._settings.announce_expansions)
        self.frame.Bind(
            wx.EVT_MENU,
            lambda e: self._set_pref("announce_expansions", e.IsChecked()),
            id=self._announce_item_id,
        )
        excluded_id = wx.NewIdRef()
        options_menu.Append(excluded_id, "E&xcluded Applications...")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.edit_exclusions(), id=excluded_id)
        menu_bar.Append(options_menu, "&Options")

        from quill.ui.quillville_menu import build_quillville_menu

        menu_bar.Append(
            build_quillville_menu(
                wx,
                self.frame,
                self._launch_sibling,
                exclude="inkwell",
                retain=self._keep_menu_ids,
            ),
            "&QuillVille",
        )

        help_menu = wx.Menu()
        updates_id, about_id = wx.NewIdRef(), wx.NewIdRef()
        help_menu.Append(updates_id, "Check for &Updates...")
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.check_for_app_updates(
                repo_slug=_REPO, current_version=_VERSION, app_key="inkwell"
            ),
            id=updates_id,
        )
        help_menu.Append(about_id, "&About Quill Inkwell")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._show_about(), id=about_id)
        menu_bar.Append(help_menu, "&Help")

        self._windows.install(self.frame, menu_bar)
        self.frame.SetMenuBar(menu_bar)
        self._windows.register(self.frame, _TITLE)
        self._keep_menu_ids(
            tray_id,
            exit_id,
            manage_id,
            quick_id,
            clip_id,
            expand_now_id,
            self._pause_item_id,
            self._startup_item_id,
            self._start_tray_item_id,
            self._close_tray_item_id,
            self._paste_item_id,
            self._announce_item_id,
            excluded_id,
            updates_id,
            about_id,
        )

    def _build_tray_menu(self, menu: wx.Menu) -> None:
        show_id, quick_id, toggle_id, exit_id = (
            wx.NewIdRef(),
            wx.NewIdRef(),
            wx.NewIdRef(),
            wx.NewIdRef(),
        )
        menu.Append(show_id, "Open Quill Inkwell")
        menu.Append(quick_id, "Quick Insert...")
        menu.AppendCheckItem(toggle_id, "Expand in other applications")
        menu.Check(toggle_id, self._settings.expansion_enabled)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._restore_from_tray(), id=show_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_quick_insert(), id=quick_id)
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.set_expansion_enabled(not self._settings.expansion_enabled),
            id=toggle_id,
        )
        self._append_sibling_app_tray_items(menu, exclude="inkwell")
        menu.AppendSeparator()
        menu.Append(exit_id, "Exit")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._exit_application(), id=exit_id)
        self._keep_menu_ids(show_id, quick_id, toggle_id, exit_id)

    # -- main panel --------------------------------------------------------------

    def _build_main_panel(self) -> None:
        panel = wx.Panel(self.frame)
        root = wx.BoxSizer(wx.VERTICAL)

        self._status_text = wx.StaticText(panel, label="")
        root.Add(self._status_text, 0, wx.ALL, 10)

        self._list = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_SUNKEN)
        self._list.SetName("Abbreviations")
        self._list.InsertColumn(0, "Abbreviation", width=120)
        self._list.InsertColumn(1, "Expands to", width=290)
        self._list.InsertColumn(2, "Category", width=100)
        root.Add(self._list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        manage_btn = wx.Button(panel, label="&Manage Abbreviations...")
        quick_btn = wx.Button(panel, label="&Quick Insert...")
        manage_btn.Bind(wx.EVT_BUTTON, lambda _e: self.open_manager())
        quick_btn.Bind(wx.EVT_BUTTON, lambda _e: self.open_quick_insert())
        buttons.Add(manage_btn, 0, wx.RIGHT, 6)
        buttons.Add(quick_btn, 0)
        root.Add(buttons, 0, wx.ALL, 10)

        panel.SetSizer(root)
        self._panel = panel
        self._reload_list()

    def _focus_initial_control(self) -> None:
        self._list.SetFocus()

    def _reload_list(self) -> None:
        self._list.DeleteAllItems()
        for i, entry in enumerate(self._library.abbreviations):
            label = entry.abbreviation if entry.enabled else f"{entry.abbreviation} (disabled)"
            self._list.InsertItem(i, label)
            self._list.SetItem(i, 1, entry.expansion.replace("\n", " ")[:60])
            self._list.SetItem(i, 2, entry.category)

    def _refresh_status(self) -> None:
        count = len(self._library.abbreviations)
        if self._safe_mode:
            state = "off (Safe Mode)"
        elif not self._settings.expansion_enabled:
            state = "paused"
        elif self._hook is not None and getattr(self._hook, "installed", False):
            state = "on"
        else:
            state = "starting"
        text = f"{count} abbreviations. Expansion in other applications: {state}."
        self._status_text.SetLabel(text)
        self._set_status(text)

    # -- commands ----------------------------------------------------------------

    def set_expansion_enabled(self, enabled: bool) -> None:
        self._settings.expansion_enabled = enabled
        save_settings(self._data_dir, self._settings)
        if enabled:
            self._start_expansion()
            if self._hook is not None:
                self._hook.resume()
        elif self._hook is not None:
            self._hook.pause()
        self._announce("Expanding in other applications." if enabled else "Expansion paused.")
        self._refresh_status()

    def open_manager(self) -> None:
        from quill.ui.abbreviation_manager_dialog import AbbreviationManagerDialog

        dlg = AbbreviationManagerDialog(self.frame, self._library)
        self._show_modal_dialog(dlg.dialog, "Manage Abbreviations")
        dlg.close()
        self._library = load_abbreviation_library(self._data_dir)
        self._library_stamp = None
        self._reload_list()
        self._refresh_status()

    def open_quick_insert(self) -> None:
        """Pick an abbreviation and type its expansion into the previous window.

        Inkwell's window is in front while the picker is open, so the expansion
        is typed after focus returns to wherever the user was working.
        """
        from quill.ui.quick_insert_dialog import QuickInsertDialog

        previous_hwnd = self._foreground_before_dialog()
        dlg = QuickInsertDialog(self.frame, self._library)
        result = self._show_modal_dialog(dlg.dialog, "Quick Insert")
        chosen = dlg.chosen
        dlg.close()
        if result != wx.ID_OK or chosen is None:
            return
        from quill.ui.fill_in_dialog import prompt_for_fields

        filled = prompt_for_fields(
            self.frame, chosen.expansion, self._show_modal_dialog, title=chosen.abbreviation
        )
        if filled is None:
            return
        text, cursor_offset, has_cursor = resolve_expansion(filled, self._clipboard_text())
        record_use(self._library, chosen.id)
        save_abbreviation_library(self._library, self._data_dir)
        self._library_stamp = None
        self._insert_into_previous_window(
            text, len(text) - cursor_offset if has_cursor else 0, previous_hwnd
        )

    def _foreground_before_dialog(self) -> int:
        try:
            from quill.platform.windows.foreground import foreground_window_info

            window = foreground_window_info()
            return 0 if window.hwnd == self.frame.GetHandle() else window.hwnd
        except Exception:  # noqa: BLE001
            return 0

    def _insert_into_previous_window(self, text: str, caret_from_end: int, hwnd: int) -> None:
        if not hwnd:
            self._announce("Nothing to insert into; copied to the clipboard instead.")
            self._copy_to_clipboard(text)
            return
        try:
            from quill.platform.windows import text_injector
            from quill.platform.windows.foreground import force_foreground_window

            force_foreground_window(hwnd)
            wx.CallLater(
                150,
                lambda: text_injector.inject_expansion(
                    text, backspace_count=0, caret_from_end=caret_from_end
                ),
            )
        except Exception:  # noqa: BLE001
            self._copy_to_clipboard(text)
            self._announce("Could not type there; copied to the clipboard instead.")

    def new_from_clipboard(self) -> None:
        """Turn whatever is on the clipboard into a new abbreviation."""
        import uuid

        from quill.core.abbreviations import Abbreviation
        from quill.ui.abbreviation_manager_dialog import _AbbreviationEditDialog

        text = self._clipboard_text()
        if not text.strip():
            self._announce("The clipboard has no text to save.")
            return
        entry = Abbreviation(id=str(uuid.uuid4()), abbreviation="", expansion=text)
        dlg = _AbbreviationEditDialog(
            self.frame,
            entry,
            categories=sorted({a.category for a in self._library.abbreviations if a.category}),
        )
        result = self._show_modal_dialog(dlg.dialog, "New Abbreviation")
        if result == wx.ID_OK and dlg.trigger_text:
            dlg.apply_to(entry)
            self._library.abbreviations.append(entry)
            self._library.abbreviations.sort(key=lambda a: a.abbreviation.lower())
            save_abbreviation_library(self._library, self._data_dir)
            self._library_stamp = None
            self._reload_list()
            self._announce(f"Saved {entry.abbreviation}.")
        dlg.close()

    def edit_exclusions(self) -> None:
        """Applications where expansion must never run, on top of the built-in list."""
        current = "\n".join(self._settings.excluded_processes)
        dialog = wx.TextEntryDialog(
            self.frame,
            "One program file name per line, for example notepad.exe.\n"
            "Password managers and Windows sign-in prompts are always excluded.",
            "Excluded Applications",
            current,
            style=wx.TE_MULTILINE | wx.OK | wx.CANCEL,
        )
        if self._show_modal_dialog(dialog, "Excluded Applications") == wx.ID_OK:
            names = [line.strip().lower() for line in dialog.GetValue().splitlines()]
            self._settings.excluded_processes = [n for n in names if n]
            save_settings(self._data_dir, self._settings)
            self._announce(f"{len(self._settings.excluded_processes)} applications excluded.")
        dialog.Destroy()

    def _register_global_hotkey(self, hotkey_id: int, chord: str, handler: object) -> None:
        """Claim one system-wide chord, best effort.

        A chord another program already owns stays theirs -- Inkwell says so
        rather than appearing to work. Failing to register must never stop the
        app from starting.
        """
        if not sys.platform.startswith("win") or not chord:
            return
        from quill.ui.tray_hotkey import parse_hotkey

        parsed = parse_hotkey(wx, chord)
        if parsed is None:
            return
        flags, key_code = parsed
        try:
            if not self.frame.RegisterHotKey(hotkey_id, flags, key_code):
                self._set_status(f"{chord} is already in use by another program.")
                return
        except Exception:  # noqa: BLE001
            return
        self.frame.Bind(wx.EVT_HOTKEY, lambda _e: handler(), id=hotkey_id)

    # -- preferences -------------------------------------------------------------

    def _set_pref(self, name: str, value: bool) -> None:
        setattr(self._settings, name, value)
        save_settings(self._data_dir, self._settings)

    def _set_injection_mode(self, paste: bool) -> None:
        self._settings.injection_mode = "paste" if paste else "type"
        save_settings(self._data_dir, self._settings)
        self._announce(
            "Expansions are pasted; the clipboard is restored afterwards."
            if paste
            else "Expansions are typed; the clipboard is never touched."
        )

    def _launch_at_startup_enabled(self) -> bool:
        try:
            from quill.platform.windows import inkwell_startup

            return bool(inkwell_startup.is_launch_at_startup_enabled())
        except Exception:  # noqa: BLE001
            return False

    def _set_launch_at_startup(self, enabled: bool) -> None:
        try:
            from quill.platform.windows import inkwell_startup

            inkwell_startup.set_launch_at_startup(enabled)
        except Exception:  # noqa: BLE001
            self._announce("Could not change the Windows startup setting.")
            return
        self._announce(
            "Quill Inkwell will start with Windows."
            if enabled
            else "Quill Inkwell will not start with Windows."
        )

    # -- lifecycle ---------------------------------------------------------------

    def _show_about(self) -> None:
        self._show_message_box(
            f"{_TITLE} {_VERSION}\n\n"
            "Abbreviation expansion in every application, sharing one library "
            "with QUILL.\n\nFree, and part of the QuillVille family.",
            f"About {_TITLE}",
            wx.ICON_INFORMATION | wx.OK,
        )

    def _start_ipc_poll(self) -> None:
        """Poll the IPC queue: a second launch asks this one to come forward."""
        timer = wx.Timer(self.frame)
        self.frame.Bind(wx.EVT_TIMER, self._on_ipc_timer, timer)
        timer.Start(800)
        self._ipc_timer = timer

    def _on_ipc_timer(self, _event: object) -> None:
        from quill.core.ipc import drain_open_requests

        if drain_open_requests(slot=_IPC_SLOT):
            self._restore_from_tray()

    def _on_close(self, event: wx.CloseEvent) -> None:
        # Closing the window must not stop expansion: the service is the point,
        # the window is only its manager.
        if self._settings.close_to_tray and event.CanVeto():
            event.Veto()
            self.toggle_window_to_tray()
            self._announce("Quill Inkwell is still expanding, in the tray.")
            return
        self._stop_expansion()
        event.Skip()

    def _exit_application(self) -> None:
        self._stop_expansion()
        super()._exit_application()


def main() -> int:
    safe_mode = bool(os.environ.get("QUILL_SAFE_MODE"))
    start_in_tray = "--tray" in sys.argv
    from quill.core.ipc import (
        enqueue_open_request,
        release_primary_instance,
        try_claim_primary_instance,
    )

    if not try_claim_primary_instance(slot=_IPC_SLOT):
        enqueue_open_request(None, slot=_IPC_SLOT)
        return 0

    from quill.core.paths import app_data_dir
    from quill.stability.logging_config import configure_logging

    log_listener = configure_logging(app_data_dir() / "logs")
    app = wx.App()
    frame = QuillInkwellFrame(safe_mode=safe_mode)
    frame._log_listener = log_listener
    if start_in_tray or frame._settings.start_in_tray:
        frame.toggle_window_to_tray()
    else:
        frame.frame.Show()
        frame.frame.Raise()
        wx.CallAfter(frame._focus_initial_control)
    try:
        app.MainLoop()
    finally:
        release_primary_instance(slot=_IPC_SLOT)
        log_listener.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
