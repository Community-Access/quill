"""Quill Converter -- the Universal Audio Converter as a standalone app (#1255).

A small, tray-resident QuillVille window whose whole job is audio conversion. It
reuses the exact same wx-free engine (:mod:`quill.core.audio.convert` + presets +
dsp) and the exact same orchestration the Audio Studio menu uses
(:mod:`quill.ui.audio_studio.convert_audio_dialog`): the main window is a
build-a-queue converter form, an **Advanced...** button opens the full dialog for
the DSP catalog, and **Convert from URL...** pulls a link's audio (on-demand
yt-dlp, consent-gated). So there is one converter, surfaced two ways.

Bootstrap mirrors Quill Weather / Radio: single-instance via ``core.ipc``, an
:class:`~quill.ui.app_shell.AppShellFrame` host (which supplies ``_announce`` /
``_set_status`` / ``_show_message_box`` / ``_show_modal_dialog`` / tray), plus a
self-contained ``_run_background_task`` so the shared orchestration can run a
batch off the UI thread with tray-aware progress.
"""

from __future__ import annotations

import os
import sys
import threading
from pathlib import Path
from typing import Any

import wx

from quill.core.audio.convert import (
    OnExisting,
    available_output_formats,
    default_destination,
)
from quill.core.audio.presets import DEFAULT_PRESET_ID, preset_choices
from quill.ui.accessible_names import set_accessible_name
from quill.ui.app_shell import AppShellFrame
from quill.ui.audio_studio.convert_audio_dialog import (
    build_request,
    plan_and_run,
    run_audio_conversion,
    run_url_conversion,
)

_TITLE = "Quill Converter"
_VERSION = "1.0.0"
_REPO = "Community-Access/quill"
_IPC_SLOT = "converter"

_ADD_WILDCARD = (
    "Audio and video files|*.mp3;*.wav;*.flac;*.ogg;*.oga;*.opus;*.m4a;*.m4b;*.aac;"
    "*.wma;*.aiff;*.aif;*.alac;*.ape;*.wv;*.mka;*.amr;*.3gp;*.caf;"
    "*.mp4;*.m4v;*.mkv;*.mov;*.webm;*.avi;*.flv;*.wmv|All files (*.*)|*.*"
)


class QuillConverterFrame(AppShellFrame):
    """A standalone converter window (queue + convert), tray-resident."""

    def __init__(self, *, safe_mode: bool = False, initial_paths: list[Path] | None = None) -> None:
        self._init_app_shell(_TITLE, safe_mode=safe_mode, size=(560, 460))
        from quill.ui.window_menu import WindowManager

        self._windows = WindowManager(wx)
        self._entries: list[tuple[Path, Path | None]] = []
        self._formats = available_output_formats(_find_ffmpeg())
        self._build_menu_bar()
        self._build_main_panel()
        self._ensure_tray_icon(self._build_tray_menu, tooltip=_TITLE)
        self._register_tray_hotkey("Ctrl+Alt+Shift+C")  # show/hide to the tray
        # Seed from the command line (the Explorer "Convert with Quill" verb, or
        # `python -m quill.apps.converter <files>`): queue each existing path.
        for raw in initial_paths or []:
            if raw.exists():
                self._add_entry(raw, is_folder=raw.is_dir())
        if self._entries:
            self._reload()
        else:
            self._refresh_statusbar()

    # -- menu bar --------------------------------------------------------------

    def _build_menu_bar(self) -> None:
        menu_bar = wx.MenuBar()

        file_menu = wx.Menu()
        add_files_id, add_folder_id, url_id, advanced_id = (wx.NewIdRef() for _ in range(4))
        tray_id, exit_id = wx.NewIdRef(), wx.NewIdRef()
        file_menu.Append(add_files_id, "&Add Files...\tCtrl+O")
        file_menu.Append(add_folder_id, "Add F&older...\tCtrl+Shift+O")
        file_menu.Append(url_id, "Convert from &URL...\tCtrl+U")
        file_menu.Append(advanced_id, "Ad&vanced Options...\tCtrl+Alt+V")
        file_menu.AppendSeparator()
        file_menu.Append(tray_id, "Minimize to &Tray\tCtrl+W")
        file_menu.Append(exit_id, "E&xit\tCtrl+Q")
        menu_bar.Append(file_menu, "&File")
        for item_id, handler in (
            (add_files_id, self._on_add_files),
            (add_folder_id, self._on_add_folder),
            (url_id, self._on_convert_url),
            (advanced_id, self._on_advanced),
            (tray_id, lambda _e: self.toggle_window_to_tray()),
            (exit_id, lambda _e: self._exit_application()),
        ):
            self.frame.Bind(wx.EVT_MENU, handler, id=item_id)

        from quill.ui.quillville_menu import build_quillville_menu

        menu_bar.Append(
            build_quillville_menu(
                wx,
                self.frame,
                self._launch_sibling,
                exclude="converter",
                retain=self._keep_menu_ids,
            ),
            "&QuillVille",
        )

        help_menu = wx.Menu()
        updates_id, about_id = wx.NewIdRef(), wx.NewIdRef()
        help_menu.Append(updates_id, "Check for &Updates...\tCtrl+Alt+U")
        help_menu.Append(about_id, "&About Quill Converter\tCtrl+Alt+A")
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.check_for_app_updates(
                repo_slug=_REPO, current_version=_VERSION, app_key="converter"
            ),
            id=updates_id,
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._show_about(), id=about_id)
        menu_bar.Append(help_menu, "&Help")

        self._windows.install(self.frame, menu_bar)
        self.frame.SetMenuBar(menu_bar)
        self._windows.register(self.frame, _TITLE)
        self._keep_menu_ids(
            add_files_id, add_folder_id, url_id, advanced_id, tray_id, exit_id, updates_id, about_id
        )

    def _build_tray_menu(self, menu: wx.Menu) -> None:
        show_id = wx.NewIdRef()
        menu.Append(show_id, "Open Quill Converter")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._restore_from_tray(), id=show_id)

    # -- main panel ------------------------------------------------------------

    def _build_main_panel(self) -> None:
        panel = wx.Panel(self.frame, style=wx.TAB_TRAVERSAL)
        root = wx.BoxSizer(wx.VERTICAL)

        root.Add(wx.StaticText(panel, label="&Files to convert:"), 0, wx.ALL, 8)
        self._list = wx.ListBox(panel, name="Files to convert")
        set_accessible_name(self._list, "Files to convert")
        root.Add(self._list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        add_row = wx.BoxSizer(wx.HORIZONTAL)
        self._add_files_btn = wx.Button(panel, label="&Add Files...")
        self._add_folder_btn = wx.Button(panel, label="Add F&older...")
        self._remove_btn = wx.Button(panel, label="&Remove")
        for btn in (self._add_files_btn, self._add_folder_btn, self._remove_btn):
            add_row.Add(btn, 0, wx.RIGHT, 6)
        root.Add(add_row, 0, wx.ALL, 8)

        root.Add(wx.StaticText(panel, label="Con&vert to:"), 0, wx.LEFT | wx.TOP, 8)
        self._format = wx.Choice(panel, choices=[f.upper() for f in self._formats])
        self._format.SetSelection(0)
        set_accessible_name(self._format, "Convert to format")
        root.Add(self._format, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        root.Add(wx.StaticText(panel, label="&Preset:"), 0, wx.LEFT | wx.TOP, 8)
        self._preset_ids = [pid for pid, _label in preset_choices()]
        self._preset = wx.Choice(panel, choices=[label for _pid, label in preset_choices()])
        self._preset.SetSelection(max(0, self._preset_ids.index(DEFAULT_PRESET_ID)))
        set_accessible_name(self._preset, "Preset")
        root.Add(self._preset, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        root.Add(wx.StaticText(panel, label="Output f&older:"), 0, wx.LEFT | wx.TOP, 8)
        dest_row = wx.BoxSizer(wx.HORIZONTAL)
        self._dest = wx.TextCtrl(panel)
        set_accessible_name(self._dest, "Output folder")
        self._browse_btn = wx.Button(panel, label="&Browse...")
        dest_row.Add(self._dest, 1, wx.RIGHT, 6)
        dest_row.Add(self._browse_btn, 0)
        root.Add(dest_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        action_row = wx.BoxSizer(wx.HORIZONTAL)
        self._convert_btn = wx.Button(panel, label="&Convert")
        self._url_btn = wx.Button(panel, label="Convert from &URL...")
        self._advanced_btn = wx.Button(panel, label="Ad&vanced...")
        for btn in (self._convert_btn, self._url_btn, self._advanced_btn):
            action_row.Add(btn, 0, wx.RIGHT, 6)
        root.Add(action_row, 0, wx.ALL, 8)

        panel.SetSizer(root)
        self._main_panel = panel

        self._add_files_btn.Bind(wx.EVT_BUTTON, self._on_add_files)
        self._add_folder_btn.Bind(wx.EVT_BUTTON, self._on_add_folder)
        self._remove_btn.Bind(wx.EVT_BUTTON, self._on_remove)
        self._browse_btn.Bind(wx.EVT_BUTTON, self._on_browse)
        self._convert_btn.Bind(wx.EVT_BUTTON, self._on_convert)
        self._url_btn.Bind(wx.EVT_BUTTON, self._on_convert_url)
        self._advanced_btn.Bind(wx.EVT_BUTTON, self._on_advanced)
        self._list.Bind(wx.EVT_KEY_DOWN, self._on_list_key)

    def _focus_initial_control(self) -> None:
        self._list.SetFocus()

    # -- queue helpers ---------------------------------------------------------

    def _reload(self) -> None:
        self._list.Clear()
        for entry, _root in self._entries:
            self._list.Append(entry.name if entry.is_file() else f"{entry.name} (folder)")
        self._set_status(f"{len(self._entries)} item(s) queued.")

    def _add_entry(self, path: Path, *, is_folder: bool) -> None:
        pair = (path, path if is_folder else None)
        if pair not in self._entries:
            self._entries.append(pair)

    def _on_add_files(self, _event: Any) -> None:
        with wx.FileDialog(
            self.frame,
            "Add audio or video files",
            wildcard=_ADD_WILDCARD,
            style=wx.FD_OPEN | wx.FD_MULTIPLE | wx.FD_FILE_MUST_EXIST,
        ) as picker:
            if picker.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
                return
            for raw in picker.GetPaths():
                self._add_entry(Path(raw), is_folder=False)
        self._reload()

    def _on_add_folder(self, _event: Any) -> None:
        with wx.DirDialog(
            self.frame, "Add a folder of audio files", style=wx.DD_DIR_MUST_EXIST
        ) as picker:
            if picker.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
                return
            self._add_entry(Path(picker.GetPath()), is_folder=True)
        self._reload()

    def _on_remove(self, _event: Any) -> None:
        index = self._list.GetSelection()
        if index != wx.NOT_FOUND and 0 <= index < len(self._entries):
            del self._entries[index]
            self._reload()

    def _on_list_key(self, event: Any) -> None:
        if event.GetKeyCode() == wx.WXK_DELETE:
            self._on_remove(event)
            return
        event.Skip()

    def _on_browse(self, _event: Any) -> None:
        with wx.DirDialog(self.frame, "Choose the output folder") as picker:
            if picker.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
                return
            self._dest.SetValue(picker.GetPath())

    # -- actions ---------------------------------------------------------------

    def _on_convert(self, _event: Any) -> None:
        if not self._entries:
            self._show_message_box("Add some files or a folder first.", _TITLE)
            return
        dest = self._dest.GetValue().strip()
        if not dest:
            dest = str(default_destination(self._entries[0][0]))
        request = build_request(
            self._entries,
            fmt=self._formats[max(0, self._format.GetSelection())],
            preset_id=self._preset_ids[max(0, self._preset.GetSelection())],
            dest_dir=Path(dest),
            recurse=True,
            on_existing=OnExisting.RENAME,
        )
        if request is None:
            self._show_message_box("Nothing to convert.", _TITLE)
            return
        plan_and_run(self, request)

    def _on_convert_url(self, _event: Any) -> None:
        run_url_conversion(self)

    def _on_advanced(self, _event: Any) -> None:
        # Hand the current queue to the full dialog (Advanced DSP, per-run options).
        run_audio_conversion(self, initial_entries=list(self._entries))

    def _show_about(self) -> None:
        self._show_message_box(
            f"{_TITLE} {_VERSION}\n\n"
            "The Universal Audio Converter: convert audio and video-audio between "
            "formats, with presets, an Advanced DSP catalog, and URL import -- "
            "offline, on your machine.\n\nSupport: support@community-access.org",
            f"About {_TITLE}",
        )

    # -- background task (self-contained; tray-aware progress) ------------------

    def _run_background_task(
        self,
        label: str,
        work: Any,
        on_success: Any,
        *,
        notify_on_success: bool = False,
        notify_on_error: bool = True,
        notification_category: str = "",
        protect_on_close: bool = False,
    ) -> None:
        """Run ``work(progress)`` off the UI thread; deliver on the UI thread.

        Honours the shared contract: ``progress(message, current, total)`` drives
        the status bar and the tray tooltip; errors surface as a message box.
        """
        del notify_on_success, notify_on_error, notification_category, protect_on_close
        self._set_status(f"{label} started")

        def progress(message: str, current: int, total: int) -> None:
            wx.CallAfter(self._note_progress, label, message, current, total)

        def worker() -> None:
            try:
                result = work(progress)
            except Exception as error:  # noqa: BLE001 - surfaced on the UI thread
                wx.CallAfter(self._finish_task, label, error, None, on_success)
                return
            wx.CallAfter(self._finish_task, label, None, result, on_success)

        threading.Thread(target=worker, daemon=True).start()

    def _note_progress(self, label: str, message: str, current: int, total: int) -> None:
        pct = int(current * 100 / total) if total else 0
        text = message or f"{label}: {pct}%"
        self._set_status(text)
        if self._tray_icon is not None:
            icon = self._app_icon or wx.ArtProvider.GetIcon(
                wx.ART_INFORMATION, wx.ART_OTHER, (16, 16)
            )
            try:
                self._tray_icon.SetIcon(icon, f"{_TITLE} -- {text}")
            except Exception:  # noqa: BLE001 - a tooltip update must never break a run
                pass

    def _finish_task(self, label: str, error: Any, result: Any, on_success: Any) -> None:
        if error is not None:
            self._set_status(f"{label} failed")
            self._show_message_box(f"{label} failed.\n\n{error}", label, wx.ICON_ERROR | wx.OK)
            self._refresh_statusbar()
            return
        self._set_status(f"{label} finished")
        try:
            on_success(result)
        finally:
            self._refresh_statusbar()


def _find_ffmpeg() -> str | None:
    from quill.core.speech.ffmpeg import find_ffmpeg

    return find_ffmpeg()


def main() -> int:
    from quill.core.data_location import apply_pending_at_launch

    # A queued Data Folder move/import applies before a single data file is
    # read (mirrors quill.__main__.main -- the family shares one profile, so
    # whichever app launches next must be the one to apply it).
    apply_pending_at_launch()
    safe_mode = bool(os.environ.get("QUILL_SAFE_MODE"))
    start_in_tray = "--tray" in sys.argv
    # Positional args are files to queue (the Explorer verb passes the selection).
    initial_paths = [Path(arg) for arg in sys.argv[1:] if not arg.startswith("-")]
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
    frame = QuillConverterFrame(safe_mode=safe_mode, initial_paths=initial_paths)
    frame._log_listener = log_listener
    if start_in_tray:
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
