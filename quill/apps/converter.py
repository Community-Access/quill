"""Quill Converter -- the Universal Converter as a standalone app (#1255).

A small, tray-resident QuillVille window whose whole job is conversion: audio
to audio, video to audio, and (since 1.0.0) video to video, with named effect
recipes, a fifteen-second before-and-after preview, Join into One File, and
Split by Chapters, and chapters carried through every conversion. It reuses the
wx-free engine (:mod:`quill.core.audio.convert` and its neighbours ``formats``,
``dsp``, ``effect_recipes``, ``chapter_plan``, ``assemble``, ``media_probe``)
and the Audio Studio's Chapter Workbench as its chapter editor.

This file is the window: the queue and its choices. The menu bar is
:mod:`quill.apps.converter_menu`; View > Advanced Options is
:mod:`quill.apps.converter_advanced`; the commands are
:mod:`quill.apps.converter_actions` and :mod:`quill.apps.converter_chapters`;
the Custom Effects and report windows are :mod:`quill.ui.converter_dialogs`.

No control on the window takes a letter the menu bar uses: Alt+F must open the
File menu (reported 2026-09-27 as "the converter doesn't let me see the menu
bar", when Alt+F went to the queue and Alt+C pressed Convert).

Bootstrap mirrors Quill Weather / Radio: single-instance via ``core.ipc``, an
:class:`~quill.ui.app_shell.AppShellFrame` host (``_announce`` /
``_set_status`` / ``_show_message_box`` / ``_show_modal_dialog`` / tray).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import wx

from quill.apps.converter_actions import ConverterActionsMixin
from quill.apps.converter_chapters import ConverterChaptersMixin
from quill.apps.converter_url import ConverterUrlMixin
from quill.core import converter_settings
from quill.core.audio.chapter_plan import CHAPTER_SOURCES
from quill.core.audio.convert import available_output_formats
from quill.core.audio.effect_recipes import CUSTOM_RECIPE_ID, recipe_by_id, recipe_choices
from quill.core.audio.formats import INPUT_EXTENSIONS, format_label, is_video_format, open_wildcard
from quill.core.audio.presets import preset_choices
from quill.ui.accessible_names import set_accessible_name
from quill.ui.app_shell import AppShellFrame

_TITLE = "Quill Converter"
_VERSION = "1.0.0"
_BUILD = 1  # this version's build (docs/release/RELEASE.md, "Build numbers")
_REPO = "Community-Access/quill"
_IPC_SLOT = "converter"

#: Shared-store components this app's job depends on: without ffmpeg, available_output_formats() is
#: exactly ["wav"] -- a converter that cannot convert -- and mpv is the Chapter Workbench's player,
#: which needs exact seeking in every format to set a chapter at the playhead (1.0.0). Declared so
#: the family's refcount registry knows an installed Converter still needs the shared copies
#: (app-profiles.json).
REQUIRED_COMPONENTS: tuple[str, ...] = ("ffmpeg", "mpv")


class _QueueDropTarget(wx.FileDropTarget):
    """Files and folders dropped on the queue join it."""

    def __init__(self, owner: QuillConverterFrame) -> None:
        super().__init__()
        self._owner = owner

    def OnDropFiles(self, _x: int, _y: int, filenames: list[str]) -> bool:  # noqa: N802 - wx API
        wx.CallAfter(self._owner.add_paths, [Path(name) for name in filenames])
        return True


class QuillConverterFrame(
    ConverterUrlMixin, ConverterChaptersMixin, ConverterActionsMixin, AppShellFrame
):
    """The Converter window: a queue, four choices, and Convert."""

    def __init__(self, *, safe_mode: bool = False, initial_paths: list[Path] | None = None) -> None:
        self._init_app_shell(_TITLE, safe_mode=safe_mode, size=(620, 560), app_id="converter")
        # Swap in the Converter's own window-purpose resolver so the authored
        # paragraphs lead every F1 answer (GATE-CONVERTER-HELP).
        from quill.core import converter_surface_help
        from quill.ui import app_context_help

        app_context_help.activate(converter_surface_help.purpose_for_title)

        from quill.ui.window_menu import WindowManager

        self._windows = WindowManager(wx)
        self._entries: list[tuple[Path, Path | None]] = []
        self._settings = converter_settings.load()
        self._busy = False
        self._cancel: Any = None
        self._milestone = 0
        self._previewing = False
        self._last_report = ""
        self._last_output: Path | None = None
        self._formats = available_output_formats(_find_ffmpeg())
        self._build_menu_bar()
        self._build_main_panel()
        self._ensure_tray_icon(self._build_tray_menu, tooltip=_TITLE)
        self._start_show_hide_key("converter", converter_settings.settings_path())  # off by default
        # Seed from the command line (the Explorer verb, or `python -m
        # quill.apps.converter <files>`): queue each existing path.
        self.add_paths(initial_paths or [], announce=False)
        self._refresh_statusbar()
        self._start_ipc_poll()

    # -- menu bar --------------------------------------------------------------

    def _build_menu_bar(self) -> None:
        from quill.apps.converter_menu import build_menu_bar

        menu_bar = build_menu_bar(self, wx, title=_TITLE, version=_VERSION, repo=_REPO)
        self._windows.install(self.frame, menu_bar)
        self.frame.SetMenuBar(menu_bar)
        self._windows.register(self.frame, _TITLE)

    def _build_tray_menu(self, menu: wx.Menu) -> None:
        """Nothing of its own: the shared tray menu already has Show and Exit (#1465)."""
        return

    # -- main panel ------------------------------------------------------------

    def _build_main_panel(self) -> None:
        panel = wx.Panel(self.frame, style=wx.TAB_TRAVERSAL)
        root = wx.BoxSizer(wx.VERTICAL)

        root.Add(wx.StaticText(panel, label="Files to convert:"), 0, wx.ALL, 8)
        self._list = wx.ListBox(panel, name="Files to convert")
        set_accessible_name(self._list, "Files to convert")
        self._list.SetHelpText(
            "The queue. Every file here is converted when you press Convert, and "
            "a folder brings the audio and video files inside it, subfolders "
            "included. Delete removes the highlighted row, Alt+Up and Alt+Down "
            "move it, and Alt+Enter describes the file. You can also paste files "
            "copied in File Explorer, or drop them here. Nothing is ever deleted "
            "from disk."
        )
        self._list.SetDropTarget(_QueueDropTarget(self))
        root.Add(self._list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        add_row = wx.BoxSizer(wx.HORIZONTAL)
        self._add_files_btn = wx.Button(panel, label="&Add Files...")
        self._add_files_btn.SetHelpText(
            "Choose audio or video files to add to the queue. You may select "
            "several at once, and adding the same file twice queues it once."
        )
        self._add_folder_btn = wx.Button(panel, label="Add F&older...")
        self._add_folder_btn.SetHelpText(
            "Add a whole folder to the queue. Every audio and video file inside "
            "it is converted, subfolders included, and the folder layout is "
            "reproduced in the output folder."
        )
        self._remove_btn = wx.Button(panel, label="&Remove")
        self._remove_btn.SetHelpText(
            "Take the highlighted row out of the queue. Delete does the same "
            "thing from the list itself. Nothing is removed from disk."
        )
        for btn in (self._add_files_btn, self._add_folder_btn, self._remove_btn):
            add_row.Add(btn, 0, wx.RIGHT, 6)
        root.Add(add_row, 0, wx.ALL, 8)

        root.Add(wx.StaticText(panel, label="Convert &to:"), 0, wx.LEFT | wx.TOP, 8)
        self._format = wx.Choice(panel, choices=[format_label(f) for f in self._formats])
        set_accessible_name(self._format, "Convert to format")
        self._format.SetHelpText(
            "The format every queued file becomes: sound formats first, then video. "
            "A video file converted to a sound format keeps its sound; converted "
            "to a video format it stays a video. Only the formats this computer "
            "can actually write are listed."
        )
        root.Add(self._format, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        root.Add(wx.StaticText(panel, label="&Preset:"), 0, wx.LEFT | wx.TOP, 8)
        self._preset = wx.Choice(panel)
        set_accessible_name(self._preset, "Preset")
        self._preset.SetHelpText(
            "How the result is made. For a sound format: quality settings -- bit "
            "rate, sample rate and channels -- chosen for a purpose, so you do not "
            "have to know any of them. For a video format: how hard to work at "
            "keeping picture detail, and how large the picture may be. The format "
            "above always wins over a preset's own."
        )
        root.Add(self._preset, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        root.Add(wx.StaticText(panel, label="&Effects:"), 0, wx.LEFT | wx.TOP, 8)
        effect_row = wx.BoxSizer(wx.HORIZONTAL)
        choices = recipe_choices()
        self._effect_ids = [rid for rid, _label in choices]
        self._effect = wx.Choice(panel, choices=[label for _rid, label in choices])
        set_accessible_name(self._effect, "Effects")
        self._effect.SetHelpText(
            "What to do to the sound on the way through, named for the problem it "
            "solves: clean up speech, make a podcast or an ACX audiobook, bring "
            "film dialogue forward, remove hum or noise, even out loud and quiet "
            "parts. Custom uses whatever you set in Custom Effects. Effects apply "
            "to the sound of video conversions too. Preview lets you hear them "
            "before you convert."
        )
        self._effects_btn = wx.Button(panel, label="Cu&stom Effects...")
        self._effects_btn.SetHelpText(
            "Every effect on one page, starting from the recipe chosen now: "
            "noise, hum, rumble, de-essing, voice clarity, bass and treble, "
            "dialogue boost, compression, leveling, loudness target, gain, speed, "
            "fades, and keeping only part of each file."
        )
        effect_row.Add(self._effect, 1, wx.RIGHT, 6)
        effect_row.Add(self._effects_btn, 0)
        root.Add(effect_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        root.Add(wx.StaticText(panel, label="Chapter mar&ks:"), 0, wx.LEFT | wx.TOP, 8)
        chapter_row = wx.BoxSizer(wx.HORIZONTAL)
        self._chapter_ids = [key for key, _label in CHAPTER_SOURCES]
        self._chapters = wx.Choice(panel, choices=[label for _key, label in CHAPTER_SOURCES])
        set_accessible_name(self._chapters, "Chapters")
        self._chapters.SetHelpText(
            "Where the converted files' chapter marks come from: each file's own "
            "chapters, a chapter list you wrote beside the file (book.cue, "
            "book.chapters.txt with lines like 0:00 Introduction, Audacity labels, "
            "or chapters.json), chapters found at the pauses, one every few "
            "minutes, or none. Chapters land in every format that can hold them; "
            "for the ones that cannot, such as WAV, a .cue sheet is written beside "
            "the file. Split by Chapters and Join use the same choice."
        )
        self._workbench_btn = wx.Button(panel, label="Chapter Workbench...")
        self._workbench_btn.SetHelpText(
            "Open the highlighted MP3, M4B or M4A in the Chapter Workbench: hear "
            "it, add, rename, move and merge chapters at the playhead, find them "
            "at pauses, import or export chapter lists, and save them into the "
            "file itself."
        )
        chapter_row.Add(self._chapters, 1, wx.RIGHT, 6)
        chapter_row.Add(self._workbench_btn, 0)
        root.Add(chapter_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        root.Add(wx.StaticText(panel, label="Output fol&der:"), 0, wx.LEFT | wx.TOP, 8)
        dest_row = wx.BoxSizer(wx.HORIZONTAL)
        self._dest = wx.TextCtrl(panel, value=self._settings.dest_dir)
        set_accessible_name(self._dest, "Output folder")
        self._dest.SetHelpText(
            "Where the converted files are written. Leave it empty and they go "
            "into a folder named Converted beside the first file in the queue. "
            "An existing file is never overwritten: a converted file that would "
            "collide is numbered instead."
        )
        self._browse_btn = wx.Button(panel, label="&Browse...")
        self._browse_btn.SetHelpText("Pick the output folder with a folder chooser.")
        dest_row.Add(self._dest, 1, wx.RIGHT, 6)
        dest_row.Add(self._browse_btn, 0)
        root.Add(dest_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        # View > Advanced Options: hidden until asked for (converter_advanced).
        from quill.apps import converter_advanced

        self._advanced_box = converter_advanced.build(self, panel)
        root.Add(self._advanced_box, 0, wx.EXPAND)
        self._main_sizer = root

        action_row = wx.BoxSizer(wx.HORIZONTAL)
        self._convert_btn = wx.Button(panel, label="Convert")
        self._convert_btn.SetHelpText(
            "Convert everything in the queue with the choices above. Progress is "
            "announced every quarter, the window can go to the tray while it "
            "works, and while it runs this button is Stop."
        )
        self._preview_btn = wx.Button(panel, label="Pla&y Preview")
        self._preview_btn.SetHelpText(
            "Plays fifteen seconds of the highlighted file -- or the first in the "
            "queue -- exactly as it will sound after converting, effects and all. "
            "Press again to stop. Hear Original plays the same fifteen seconds "
            "untouched, so you can compare."
        )
        self._original_btn = wx.Button(panel, label="Hear Ori&ginal")
        self._original_btn.SetHelpText(
            "Plays the same fifteen seconds Preview does, with nothing changed. "
            "Press again to stop."
        )
        self._url_btn = wx.Button(panel, label="From UR&L...")
        self._url_btn.SetHelpText(
            "Paste a web address and convert its audio: one video, a whole "
            "playlist, or a channel's newest videos. The downloader is included "
            "with Quill Converter; in Safe Mode this is declined."
        )
        for btn in (
            self._convert_btn,
            self._preview_btn,
            self._original_btn,
            self._url_btn,
        ):
            action_row.Add(btn, 0, wx.RIGHT, 6)
        root.Add(action_row, 0, wx.ALL, 8)

        # Not in the Tab order (a progress bar never takes focus); a screen
        # reader finds it by reviewing the window, and NVDA can beep it when
        # background progress bars are on. The status bar says the same in words.
        progress_row = wx.BoxSizer(wx.HORIZONTAL)
        progress_label = wx.StaticText(panel, label="Progress:")
        self._progress = wx.Gauge(panel, range=1000, style=wx.GA_HORIZONTAL | wx.GA_SMOOTH)
        self._progress.SetName("Conversion progress")
        self._progress.SetHelpText(
            "How far the conversion has got, counting inside each file as well "
            "as across the queue. The status bar says the same in words, with "
            "about how long is left. Empty when nothing is converting."
        )
        progress_row.Add(progress_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        progress_row.Add(self._progress, 1, wx.ALIGN_CENTER_VERTICAL)
        root.Add(progress_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        panel.SetSizer(root)
        self._main_panel = panel
        self._restore_choices()
        root.Show(self._advanced_box, self._settings.show_advanced, recursive=True)

        self._add_files_btn.Bind(wx.EVT_BUTTON, self._on_add_files)
        self._add_folder_btn.Bind(wx.EVT_BUTTON, self._on_add_folder)
        self._remove_btn.Bind(wx.EVT_BUTTON, self._on_remove)
        self._browse_btn.Bind(wx.EVT_BUTTON, self._on_browse)
        self._convert_btn.Bind(wx.EVT_BUTTON, lambda _e: self.convert_or_stop())
        self._preview_btn.Bind(wx.EVT_BUTTON, lambda _e: self.preview(original=False))
        self._original_btn.Bind(wx.EVT_BUTTON, lambda _e: self.preview(original=True))
        self._url_btn.Bind(wx.EVT_BUTTON, self._on_convert_url)
        self._effects_btn.Bind(wx.EVT_BUTTON, self._on_custom_effects)
        self._format.Bind(wx.EVT_CHOICE, self._on_format_changed)
        # Remembered as they change, so a closed window or a crash loses nothing.
        self._preset.Bind(wx.EVT_CHOICE, self._on_choice_changed)
        self._effect.Bind(wx.EVT_CHOICE, self._on_choice_changed)
        self._chapters.Bind(wx.EVT_CHOICE, self._on_choice_changed)
        self._workbench_btn.Bind(wx.EVT_BUTTON, lambda _e: self.open_chapter_workbench())
        self._dest.Bind(wx.EVT_KILL_FOCUS, self._on_choice_changed)
        self._list.Bind(wx.EVT_KEY_DOWN, self._on_list_key)

    def _focus_initial_control(self) -> None:
        self._list.SetFocus()

    # -- remembered choices ----------------------------------------------------

    def _restore_choices(self) -> None:
        fmt = self._settings.fmt if self._settings.fmt in self._formats else self._formats[0]
        self._format.SetSelection(self._formats.index(fmt))
        self._fill_presets()
        effect = self._settings.effect if self._settings.effect in self._effect_ids else "none"
        self._effect.SetSelection(self._effect_ids.index(effect))
        chapters = (
            self._settings.chapters if self._settings.chapters in self._chapter_ids else "keep"
        )
        self._chapters.SetSelection(self._chapter_ids.index(chapters))

    def _fill_presets(self) -> None:
        """The preset list for the chosen format's kind, keeping the last choice."""
        kind = "video" if is_video_format(self._chosen_format()) else "audio"
        wanted = self._settings.video_preset if kind == "video" else self._settings.audio_preset
        choices = preset_choices(kind)
        self._preset_ids = [pid for pid, _label in choices]
        self._preset.Set([label for _pid, label in choices])
        self._preset.SetSelection(
            self._preset_ids.index(wanted) if wanted in self._preset_ids else 0
        )

    def _on_format_changed(self, _event: Any) -> None:
        was_video = self._preset_ids[0].startswith("video_")
        self._remember_preset(was_video)
        if was_video != is_video_format(self._chosen_format()):
            self._fill_presets()
        self._remember()

    def _remember_preset(self, video: bool) -> None:
        if video:
            self._settings.video_preset = self._chosen_preset_id()
        else:
            self._settings.audio_preset = self._chosen_preset_id()

    def _remember(self) -> None:
        self._settings.fmt = self._chosen_format()
        self._remember_preset(is_video_format(self._settings.fmt))
        self._settings.effect = self._chosen_effect_id()
        self._settings.chapters = self._chapter_ids[max(0, self._chapters.GetSelection())]
        self._settings.dest_dir = self._dest.GetValue().strip()
        if hasattr(self, "_advanced_choices"):
            from quill.apps import converter_advanced

            converter_advanced.remember(self)
        converter_settings.save(self._settings)

    def set_open_when_done(self, value: bool) -> None:
        self._settings.open_folder_when_done = bool(value)
        self._remember()
        self._announce(
            "The output folder opens when a conversion finishes."
            if value
            else "The output folder no longer opens by itself."
        )

    def _on_choice_changed(self, event: Any) -> None:
        self._remember()
        event.Skip()

    # -- queue -----------------------------------------------------------------

    def _reload(self, *, select: int | None = None) -> None:
        self._list.Clear()
        for entry, _root in self._entries:
            self._list.Append(entry.name if not entry.is_dir() else f"{entry.name} (folder)")
        if self._entries:
            index = select if select is not None else len(self._entries) - 1
            self._list.SetSelection(max(0, min(index, len(self._entries) - 1)))
        self._set_status(f"{len(self._entries)} item(s) queued.")

    def _add_entry(self, path: Path, *, is_folder: bool) -> bool:
        pair = (path, path if is_folder else None)
        if pair in self._entries:
            return False
        self._entries.append(pair)
        return True

    def add_paths(self, paths: list[Path], *, announce: bool = True) -> None:
        """Queue each existing file or folder in *paths* (drop, paste, command line)."""
        added = skipped = 0
        for path in paths:
            if path.is_dir():
                added += self._add_entry(path, is_folder=True)
            elif path.is_file() and path.suffix.lower() in INPUT_EXTENSIONS:
                added += self._add_entry(path, is_folder=False)
            else:
                skipped += 1
        if added or paths:
            self._reload()
        if announce:
            note = f" {skipped} not a media file, left out." if skipped else ""
            self._announce(f"Added {added} to the queue, {len(self._entries)} in all.{note}")

    def paste_files(self) -> None:
        """Ctrl+V: files copied in File Explorer join the queue; in a text box, paste text."""
        focused = wx.Window.FindFocus()
        if isinstance(focused, wx.TextCtrl):
            focused.Paste()
            return
        data = wx.FileDataObject()
        ok = False
        if wx.TheClipboard.Open():
            try:
                ok = wx.TheClipboard.GetData(data)
            finally:
                wx.TheClipboard.Close()
        if not ok or not data.GetFilenames():
            self._announce("The clipboard has no files. Copy them in File Explorer first.")
            return
        self.add_paths([Path(name) for name in data.GetFilenames()])

    def _on_add_files(self, _event: Any) -> None:
        with wx.FileDialog(
            self.frame,
            "Add audio or video files",
            wildcard=open_wildcard(),
            style=wx.FD_OPEN | wx.FD_MULTIPLE | wx.FD_FILE_MUST_EXIST,
        ) as picker:
            if picker.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
                return
            for raw in picker.GetPaths():
                self._add_entry(Path(raw), is_folder=False)
        self._reload()

    def _on_add_folder(self, _event: Any) -> None:
        with wx.DirDialog(
            self.frame, "Add a folder of audio or video files", style=wx.DD_DIR_MUST_EXIST
        ) as picker:
            if picker.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
                return
            self._add_entry(Path(picker.GetPath()), is_folder=True)
        self._reload()

    def _on_remove(self, _event: Any) -> None:
        index = self._list.GetSelection()
        if index != wx.NOT_FOUND and 0 <= index < len(self._entries):
            name = self._entries[index][0].name
            del self._entries[index]
            self._reload(select=index)
            self._announce(f"Removed {name}. {len(self._entries)} left.")

    def clear_queue(self) -> None:
        if self._busy:
            self._announce("Stop the conversion before clearing the queue.")
            return
        self._entries.clear()
        self._reload()
        self._announce("Queue cleared.")

    def move_entry(self, step: int) -> None:
        index = self._list.GetSelection()
        target = index + step
        if index == wx.NOT_FOUND or not 0 <= target < len(self._entries):
            return
        self._entries[index], self._entries[target] = self._entries[target], self._entries[index]
        self._reload(select=target)
        self._announce(f"Moved to position {target + 1} of {len(self._entries)}.")

    def _on_list_key(self, event: Any) -> None:
        code = event.GetKeyCode()
        if code == wx.WXK_DELETE and not event.HasAnyModifiers():
            self._on_remove(event)
            return
        if event.AltDown() and code in (wx.WXK_UP, wx.WXK_DOWN):
            self.move_entry(-1 if code == wx.WXK_UP else 1)
            return
        event.Skip()

    def _on_browse(self, _event: Any) -> None:
        with wx.DirDialog(self.frame, "Choose the output folder") as picker:
            if picker.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
                return
            self._dest.SetValue(picker.GetPath())

    # -- other windows -----------------------------------------------------------

    def _on_custom_effects(self, _event: Any) -> None:
        from quill.ui.converter_dialogs import edit_effects

        current = self._chosen_effect_id()
        recipe = recipe_by_id(current)
        base = recipe.dsp if recipe is not None else self._settings.custom_effects
        edited = edit_effects(
            self, base, start_s=self._settings.start_s, end_s=self._settings.end_s
        )
        if edited is None:
            return
        self._settings.custom_effects, self._settings.start_s, self._settings.end_s = edited
        self._effect.SetSelection(self._effect_ids.index(CUSTOM_RECIPE_ID))
        self._remember()
        self._announce(f"Custom effects set: {self.describe_choices()}.")

    def _on_convert_url(self, _event: Any) -> None:
        self.convert_from_url()

    def set_advanced_visible(self, visible: bool) -> None:
        """View > Advanced Options (Ctrl+Alt+V): show or hide the encoder settings."""
        from quill.apps import converter_advanced

        converter_advanced.show(self, visible)
        self._remember()
        if not visible:
            self._format.SetFocus()


def _find_ffmpeg() -> str | None:
    from quill.core.speech.ffmpeg import find_ffmpeg

    return find_ffmpeg()


def main() -> int:
    from quill.core.data_location import apply_pending_at_launch

    # A queued Data Folder move/import applies before a single data file is
    # read (mirrors quill.__main__.main).
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
        # Hand every file to the running window; with none, just bring it forward.
        for path in initial_paths:
            enqueue_open_request(path.resolve(), slot=_IPC_SLOT)
        if not initial_paths:
            enqueue_open_request(None, slot=_IPC_SLOT)
        return 0

    from quill.core import components

    components.register_running_app("converter", REQUIRED_COMPONENTS)

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
