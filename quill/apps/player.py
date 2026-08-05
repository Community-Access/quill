"""Quill Media Player -- the accessible media/audiobook player as a standalone app.

A tray-resident QuillVille window that plays audiobooks and audio files with
chapter navigation, resume, bookmarks, and a precise "Go to Position (H:M:S)"
command. It reuses the exact same building blocks QUILL hosts: the accessible
transport panel (:class:`quill.ui.audio_studio.player_panel.PlayerPanel`), the
pure bookmark store (:class:`quill.core.media.bookmarks.BookmarkStore`), the
resume-position store, and the Go-to-Position dialog -- so there is one player,
surfaced both inside QUILL and here.

Bootstrap mirrors the sibling apps (Converter / Radio / Weather): single-instance
via ``core.ipc`` and an :class:`~quill.ui.app_shell.AppShellFrame` host that
supplies ``_announce`` / ``_show_modal_dialog`` / tray / updates.

See ``player.md`` (Section 9.11) for the design.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import wx

from quill.core.media import DspSettings, build_audio_filters, format_spoken
from quill.core.media.bookmarks import BookmarkStore, MediaBookmark
from quill.core.speech.chapter_io import format_timestamp
from quill.ui.accessible_names import set_accessible_name
from quill.ui.app_shell import AppShellFrame
from quill.ui.dialog_contract import apply_listbox_activation
from quill.ui.media.go_to_position_dialog import GoToPositionDialog
from quill.ui.media.listen_mixin import MediaListenMixin

_TITLE = "Quill Media Player"
_VERSION = "1.0.0"
_REPO = "Community-Access/quill"
_IPC_SLOT = "player"

_OPEN_WILDCARD = (
    "Audio and audiobook files|*.mp3;*.m4b;*.m4a;*.aac;*.ogg;*.oga;*.opus;*.flac;"
    "*.wav;*.wma;*.aiff;*.aif|All files (*.*)|*.*"
)


class QuillMediaPlayerFrame(MediaListenMixin, AppShellFrame):
    """A standalone, tray-resident media player window."""

    _STATUS_LABELS = ("State", "Position", "Chapter", "Sleep", "Backend")

    def __init__(self, *, safe_mode: bool = False, initial_paths: list[Path] | None = None) -> None:
        self._init_app_shell(_TITLE, safe_mode=safe_mode, size=(620, 520))
        from quill.ui.window_menu import WindowManager

        self._windows = WindowManager(wx)
        self._book_path: Path | None = None
        self._book_key = ""
        self._chapters: list = []
        # (title, payload, depth) per heading; payload is ("seek", ms) for an
        # in-file position or ("load", url) for a separate track. depth drives the tree.
        self._chapter_nodes: list[tuple[str, tuple[str, object], int]] = []
        self._mini_player: wx.Frame | None = None
        # Ordered separate-file tracks for continuous play (auto-advance).
        self._playlist: list[tuple[str, tuple[str, object]]] = []
        self._playlist_index = -1
        self._sleep_eoc = False  # armed "stop at end of chapter"
        self._sleep_eoc_from = -1
        self._bookmarks = BookmarkStore()
        self._magical = False
        self._compact = False
        # Hands-free voice capture (offline; reuses #617's mic + Whisper stack).
        self._voice_services: Any = None
        self._listening = False
        self._listen_timer: wx.Timer | None = None
        self._listen_menu_item: Any = None
        self._listen_last_toggle = 0.0
        self._build_menu_bar()
        self._build_main_panel()
        self._ensure_tray_icon(self._build_tray_menu, tooltip=_TITLE)
        self._register_tray_hotkey("Ctrl+Alt+Shift+P")
        # Persist the listening position periodically so resume works next launch.
        self._resume_timer = wx.Timer(self.frame)
        self.frame.Bind(wx.EVT_TIMER, lambda _e: self._save_resume(), self._resume_timer)
        self._resume_timer.Start(15_000)
        self._sleep_timer = wx.Timer(self.frame)
        self.frame.Bind(wx.EVT_TIMER, lambda _e: self._on_sleep_fired(), self._sleep_timer)
        for raw in initial_paths or []:
            if raw.exists() and raw.is_file():
                self._load_book(raw)
                break

    # -- menu bar --------------------------------------------------------------

    def _build_menu_bar(self) -> None:
        menu_bar = wx.MenuBar()

        file_menu = wx.Menu()
        open_id, folder_id, goto_id = (wx.NewIdRef() for _ in range(3))
        tray_id, exit_id = wx.NewIdRef(), wx.NewIdRef()
        daisy_id, library_id = wx.NewIdRef(), wx.NewIdRef()
        file_menu.Append(open_id, "&Open File...\tCtrl+O")
        file_menu.Append(folder_id, "Open F&older as Book...")
        file_menu.Append(daisy_id, "Open &DAISY Book...")
        file_menu.Append(library_id, "Book &Library...")
        file_menu.Append(goto_id, "&Go to Position...\tCtrl+G")
        bookmarks_menu = wx.Menu()
        export_bm_id, export_sync_id, import_sync_id = (wx.NewIdRef() for _ in range(3))
        bookmarks_menu.Append(export_bm_id, "Export &Bookmarks...")
        bookmarks_menu.Append(export_sync_id, "Export &Sync Bundle...")
        bookmarks_menu.Append(import_sync_id, "&Import Sync Bundle...")
        file_menu.AppendSubMenu(bookmarks_menu, "Book&marks && Sync")
        file_menu.AppendSeparator()
        file_menu.Append(tray_id, "Minimize to &Tray\tCtrl+W")
        file_menu.Append(exit_id, "E&xit")
        menu_bar.Append(file_menu, "&File")
        self.frame.Bind(wx.EVT_MENU, self._on_open_daisy, id=daisy_id)
        self.frame.Bind(wx.EVT_MENU, self._on_open_library, id=library_id)
        self.frame.Bind(wx.EVT_MENU, self._on_export_bookmarks, id=export_bm_id)
        self.frame.Bind(wx.EVT_MENU, self._on_export_sync, id=export_sync_id)
        self.frame.Bind(wx.EVT_MENU, self._on_import_sync, id=import_sync_id)
        self._keep_menu_ids(daisy_id, library_id, export_bm_id, export_sync_id, import_sync_id)

        nav_menu = wx.Menu()
        (
            add_bm_id,
            note_bm_id,
            edit_bm_id,
            copy_bm_id,
            focus_bm_id,
            focus_player_id,
            read_status_id,
            review_field_id,
        ) = (wx.NewIdRef() for _ in range(8))
        nav_menu.Append(add_bm_id, "Add &Bookmark\tCtrl+B")
        nav_menu.Append(note_bm_id, "Add Bookmark with &Note...\tCtrl+Shift+B")
        nav_menu.Append(edit_bm_id, "&Edit Bookmark Note...")
        nav_menu.Append(copy_bm_id, "&Copy Bookmark to Clipboard\tCtrl+Shift+C")
        nav_menu.Append(focus_bm_id, "Go to Book&marks List")
        nav_menu.Append(focus_player_id, "Go to &Player Controls")
        nav_menu.Append(review_field_id, "Review Status &Field\tF6")
        nav_menu.Append(read_status_id, "Read Status &Bar\tShift+F6")
        menu_bar.Append(nav_menu, "&Navigation")

        playback_menu = wx.Menu()
        sleep_menu = wx.Menu()
        sleep_refs = []
        self._sleep_minutes_by_id: dict[int, int] = {}
        for minutes, label in (
            (0, "&Off"),
            (15, "&15 minutes"),
            (30, "&30 minutes"),
            (60, "6&0 minutes"),
            (-1, "End of &Chapter"),
        ):
            sid = wx.NewIdRef()
            sleep_refs.append(sid)
            item = sleep_menu.AppendRadioItem(sid, label)
            if minutes == 0:
                item.Check(True)
            self._sleep_minutes_by_id[int(sid)] = minutes
            self.frame.Bind(wx.EVT_MENU, self._on_set_sleep, id=sid)
        playback_menu.AppendSubMenu(sleep_menu, "&Sleep Timer")
        summarize_id, recap_id, voice_id, listen_id = (wx.NewIdRef() for _ in range(4))
        playback_menu.Append(summarize_id, "Summarize This &Chapter (AI)")
        playback_menu.Append(recap_id, "AI &Recap of Where I Am")
        playback_menu.AppendSeparator()
        self._listen_menu_item = playback_menu.AppendCheckItem(
            listen_id, "&Listen for a Command\tCtrl+Shift+L"
        )
        playback_menu.Append(voice_id, "Type a &Voice Command...\tCtrl+Shift+V")
        self.frame.Bind(wx.EVT_MENU, self._on_summarize_chapter, id=summarize_id)
        self.frame.Bind(wx.EVT_MENU, self._on_welcome_back_recap, id=recap_id)
        self.frame.Bind(wx.EVT_MENU, self._on_listen_command, id=listen_id)
        self.frame.Bind(wx.EVT_MENU, self._on_voice_command, id=voice_id)
        self._keep_menu_ids(summarize_id, recap_id, voice_id, listen_id)
        menu_bar.Append(playback_menu, "&Playback")

        view_menu = wx.Menu()
        compact_id, magical_id, ontop_id, mini_id = (wx.NewIdRef() for _ in range(4))
        view_menu.Append(mini_id, "Mini &Player")
        view_menu.AppendCheckItem(compact_id, "&Compact Mode")
        view_menu.AppendCheckItem(magical_id, "&Magical Mode")
        view_menu.AppendCheckItem(ontop_id, "Always on &Top")
        self.frame.Bind(wx.EVT_MENU, self._on_open_mini_player, id=mini_id)
        self.frame.Bind(wx.EVT_MENU, self._on_toggle_compact, id=compact_id)
        self.frame.Bind(wx.EVT_MENU, self._on_toggle_magical, id=magical_id)
        self.frame.Bind(wx.EVT_MENU, self._on_toggle_ontop, id=ontop_id)
        menu_bar.Append(view_menu, "&View")
        self._keep_menu_ids(
            *sleep_refs,
            compact_id,
            magical_id,
            ontop_id,
            mini_id,
            read_status_id,
            review_field_id,
            note_bm_id,
            edit_bm_id,
            copy_bm_id,
        )

        for item_id, handler in (
            (open_id, self._on_open_file),
            (folder_id, self._on_open_folder),
            (goto_id, self._on_go_to_position),
            (tray_id, lambda _e: self.toggle_window_to_tray()),
            (exit_id, lambda _e: self._exit_application()),
            (add_bm_id, self._on_add_bookmark),
            (note_bm_id, self._on_add_bookmark_note),
            (edit_bm_id, self._on_edit_bookmark),
            (copy_bm_id, self._on_copy_bookmark),
            (focus_bm_id, lambda _e: self._bookmarks_list.SetFocus()),
            (focus_player_id, lambda _e: self._player.SetFocus()),
            (review_field_id, lambda _e: self._review_next_field()),
            (read_status_id, lambda _e: self._read_status_bar()),
        ):
            self.frame.Bind(wx.EVT_MENU, handler, id=item_id)

        from quill.ui.quillville_menu import build_quillville_menu

        menu_bar.Append(
            build_quillville_menu(
                wx, self.frame, self._launch_sibling, exclude="player", retain=self._keep_menu_ids
            ),
            "&QuillVille",
        )

        help_menu = wx.Menu()
        updates_id, about_id = wx.NewIdRef(), wx.NewIdRef()
        help_menu.Append(updates_id, "Check for &Updates...")
        help_menu.Append(about_id, "&About Quill Media Player")
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.check_for_app_updates(
                repo_slug=_REPO, current_version=_VERSION, app_key="player"
            ),
            id=updates_id,
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._show_about(), id=about_id)
        menu_bar.Append(help_menu, "&Help")

        self._windows.install(self.frame, menu_bar)
        self.frame.SetMenuBar(menu_bar)
        self._windows.register(self.frame, _TITLE)
        self._keep_menu_ids(
            open_id,
            folder_id,
            goto_id,
            tray_id,
            exit_id,
            add_bm_id,
            focus_bm_id,
            focus_player_id,
            updates_id,
            about_id,
        )

    def _build_tray_menu(self, menu: wx.Menu) -> None:
        show_id = wx.NewIdRef()
        menu.Append(show_id, "Open Quill Media Player")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._restore_from_tray(), id=show_id)

    # -- main panel ------------------------------------------------------------

    def _build_main_panel(self) -> None:
        from quill.ui.audio_studio.player_panel import PlayerPanel

        panel = wx.Panel(self.frame, style=wx.TAB_TRAVERSAL)
        root = wx.BoxSizer(wx.VERTICAL)

        self._now_playing = wx.TextCtrl(
            panel, style=wx.TE_READONLY | wx.TE_MULTILINE, size=(-1, 44)
        )
        set_accessible_name(self._now_playing, "Now playing")
        self._now_playing.SetValue("Open a file or a folder to begin.")
        root.Add(self._now_playing, 0, wx.EXPAND | wx.ALL, 8)

        self._player = PlayerPanel(panel, announce=self._announce, on_finished=self._on_finished)
        root.Add(self._player, 0, wx.EXPAND | wx.ALL, 8)

        notebook = wx.Notebook(panel)

        # Chapters page -- a tree so multi-level (DAISY) headings keep their
        # hierarchy; flat MP3/M4B chapters render as a single level.
        ch_page = wx.Panel(notebook)
        ch_page.SetName("Chapters")
        ch_sizer = wx.BoxSizer(wx.VERTICAL)
        self._chapter_tree = wx.TreeCtrl(
            ch_page,
            name="Chapters",
            style=wx.TR_HIDE_ROOT | wx.TR_HAS_BUTTONS | wx.TR_LINES_AT_ROOT | wx.TR_SINGLE,
        )
        set_accessible_name(self._chapter_tree, "Chapters")
        self._chapter_root = self._chapter_tree.AddRoot("Chapters")
        self._chapter_tree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self._on_chapter_activate)
        ch_sizer.Add(self._chapter_tree, 1, wx.EXPAND | wx.ALL, 6)
        ch_page.SetSizer(ch_sizer)
        notebook.AddPage(ch_page, "Chapters")

        # Bookmarks page.
        bm_page = wx.Panel(notebook)
        bm_page.SetName("Bookmarks")
        bm_sizer = wx.BoxSizer(wx.VERTICAL)
        self._bookmarks_list = wx.ListBox(bm_page, name="Bookmarks")
        set_accessible_name(self._bookmarks_list, "Bookmarks")
        apply_listbox_activation(self._bookmarks_list, self._on_bookmark_activate)
        bm_sizer.Add(self._bookmarks_list, 1, wx.EXPAND | wx.ALL, 6)
        bm_row = wx.BoxSizer(wx.HORIZONTAL)
        self._add_bm_btn = wx.Button(bm_page, label="&Add Bookmark")
        self._remove_bm_btn = wx.Button(bm_page, label="&Remove Bookmark")
        self._add_bm_btn.Bind(wx.EVT_BUTTON, self._on_add_bookmark)
        self._remove_bm_btn.Bind(wx.EVT_BUTTON, self._on_remove_bookmark)
        bm_row.Add(self._add_bm_btn, 0, wx.RIGHT, 6)
        bm_row.Add(self._remove_bm_btn, 0)
        bm_sizer.Add(bm_row, 0, wx.ALL, 6)
        bm_page.SetSizer(bm_sizer)
        notebook.AddPage(bm_page, "Bookmarks")

        # Audio (equalizer & effects) page -- a reusable, under-cap panel.
        from quill.ui.media.audio_dsp_panel import AudioDspPanel

        self._dsp_panel = AudioDspPanel(notebook, on_change=self._apply_dsp)
        notebook.AddPage(self._dsp_panel, "Audio")

        notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self._on_page_changed)
        self._notebook = notebook
        root.Add(notebook, 1, wx.EXPAND | wx.ALL, 8)

        panel.SetSizer(root)
        self._main_panel = panel

        # A rich multi-field status bar (State / Position / Chapter / Sleep / Backend),
        # reviewable field-by-field with F6 (the QUILL status-bar pattern).
        status = self.frame.GetStatusBar() or self.frame.CreateStatusBar()
        status.SetFieldsCount(len(self._STATUS_LABELS))
        self._status_field_index = 0
        self._status_timer = wx.Timer(self.frame)
        self.frame.Bind(wx.EVT_TIMER, lambda _e: self._update_status_line(), self._status_timer)
        self._status_timer.Start(1_000)

    def _focus_initial_control(self) -> None:
        # Focus opens on the transport (Play/Pause is inside PlayerPanel).
        self._player.SetFocus()

    def _on_chapter_activate(self, event: Any) -> None:
        item = event.GetItem()
        if not (item and item.IsOk()):
            return
        payload = self._chapter_tree.GetItemData(item)
        if not payload:
            return
        kind = payload[0]
        if kind == "seek":
            self._player.seek_to(int(payload[1]))
        elif kind in ("load", "track"):
            self._play_track_node(payload, self._chapter_tree.GetItemText(item))

    def _on_page_changed(self, event: Any) -> None:
        page = event.GetSelection()
        name = self._notebook.GetPageText(page) if page != wx.NOT_FOUND else ""
        if name == "Chapters":
            self._announce(f"Chapters, {len(self._chapter_nodes)} headings")
        elif name == "Bookmarks":
            self._announce(f"Bookmarks, {self._bookmarks_list.GetCount()} items")
        else:
            self._announce(name)
        event.Skip()

    def _apply_dsp(self, settings: DspSettings) -> None:
        if self._player.apply_audio_filters(build_audio_filters(settings)):
            self._announce("Audio effects applied.")
        else:
            self._announce("Audio effects need the libmpv engine.")

    def _refresh_chapters(self) -> None:
        tree = self._chapter_tree
        tree.DeleteChildren(self._chapter_root)
        # Map depth -> the most recent item at that depth, to nest children.
        parents: dict[int, Any] = {0: self._chapter_root}
        for title, payload, depth in self._chapter_nodes:
            parent = parents.get(depth - 1, self._chapter_root)
            if payload[0] == "seek":
                label = f"{title} - {format_timestamp(int(payload[1]))}"  # type: ignore[arg-type]
            else:
                label = title
            item = tree.AppendItem(parent, label)
            tree.SetItemData(item, payload)
            parents[depth] = item
            for deeper in [d for d in parents if d > depth]:
                del parents[deeper]
        tree.ExpandAll()

    def _status_values(self) -> list[tuple[str, str]]:
        """The (label, value) pair for each status field, in order."""
        if self._book_path is None:
            return [(label, "-") for label in self._STATUS_LABELS]
        try:
            playing = self._player.is_playing()
        except Exception:  # noqa: BLE001
            playing = False
        position = self._player.playhead_ms()
        length = self._player.length_ms()
        pos_text = format_timestamp(position)
        if length > 0:
            pos_text += f" / {format_timestamp(length)}"
        chapter_index = self._player.current_chapter_index()
        if self._chapters and chapter_index >= 0:
            chapter = f"{chapter_index + 1} of {len(self._chapters)}"
        else:
            chapter = "-"
        values = [
            "Playing" if playing else "Paused",
            pos_text,
            chapter,
            "On" if self._sleep_timer.IsRunning() else "Off",
            "libmpv" if self._player.supports_dsp() else "wx.media",
        ]
        return list(zip(self._STATUS_LABELS, values, strict=False))

    def _update_status_line(self) -> None:
        try:
            status = self.frame.GetStatusBar()
            if status is not None:
                for index, (_label, value) in enumerate(self._status_values()):
                    status.SetStatusText(value, index)
            # End-of-chapter sleep: pause when we cross into the next chapter.
            if self._sleep_eoc and self._chapters:
                current = self._player.current_chapter_index()
                if current > self._sleep_eoc_from:
                    self._sleep_eoc = False
                    self._player.pause()
                    self._save_resume()
                    self._announce("End of chapter. Paused. Goodnight.")
        except Exception:  # noqa: BLE001 - a status update must never break playback
            pass

    def _read_status_bar(self) -> None:
        parts = [f"{label}: {value}" for label, value in self._status_values()]
        self._announce(". ".join(parts))

    def _review_next_field(self) -> None:
        values = self._status_values()
        self._status_field_index = (self._status_field_index + 1) % len(values)
        label, value = values[self._status_field_index]
        self._announce(f"{label}: {value}")

    # -- book loading ----------------------------------------------------------

    def _on_open_file(self, _event: Any) -> None:
        with wx.FileDialog(
            self.frame,
            "Open an audio file or audiobook",
            wildcard=_OPEN_WILDCARD,
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as picker:
            if picker.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
                return
            self._load_book(Path(picker.GetPath()))

    def _on_open_folder(self, _event: Any) -> None:
        with wx.DirDialog(self.frame, "Open a folder as a book") as picker:
            if picker.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
                return
            folder = Path(picker.GetPath())
        audio = sorted(
            p for p in folder.iterdir() if p.suffix.lower() in {".mp3", ".m4a", ".m4b", ".flac"}
        )
        if audio:
            self._load_book(audio[0])
        else:
            self._show_message_box("No audio files were found in that folder.", _TITLE)

    def _on_open_daisy(self, _event: Any) -> None:
        with wx.FileDialog(
            self.frame,
            "Open a DAISY book (choose its .ncx)",
            wildcard="DAISY navigation (*.ncx)|*.ncx|All files (*.*)|*.*",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as picker:
            if picker.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
                return
            self._load_daisy(Path(picker.GetPath()))

    def _load_daisy(self, ncx: Path) -> None:
        from quill.core.media import parse_ncx, resolve_heading_times

        try:
            headings = parse_ncx(ncx.read_text(encoding="utf-8", errors="replace"))
        except Exception as error:  # noqa: BLE001 - surfaced to the user
            self._show_message_box(f"Could not read the DAISY navigation.\n\n{error}", _TITLE)
            return
        root_dir = ncx.parent

        def load_smil(name: str) -> str | None:
            candidate = root_dir / name
            return (
                candidate.read_text(encoding="utf-8", errors="replace")
                if candidate.is_file()
                else None
            )

        resolved = resolve_heading_times(headings, load_smil)
        chapters, nodes, audio_path = self._daisy_build(resolved, root_dir)
        if audio_path is None or not audio_path.is_file():
            self._show_message_box("No playable audio was found for this DAISY book.", _TITLE)
            return
        if not self._player.load(str(audio_path), chapters):
            self._show_message_box(f"Could not play {audio_path.name}.", _TITLE)
            return
        self._book_path = audio_path
        self._book_key = str(ncx)
        self._chapters = chapters
        self._chapter_nodes = nodes
        self._set_playlist_from_nodes()
        self._now_playing.SetValue(ncx.stem)
        self._refresh_chapters()
        self._refresh_bookmarks()
        self._set_status(f"DAISY book: {ncx.stem}")
        self._announce(f"DAISY book opened. {len(resolved)} headings.")

    @staticmethod
    def _daisy_build(
        resolved: list, root_dir: Path
    ) -> tuple[list, list[tuple[str, tuple[str, object], int]], Path | None]:
        """Build chapter markers, tree nodes, and the first audio file for a DAISY book.

        Single-audio books get ``("seek", ms)`` nodes; a book split across several
        audio files gets ``("track", (path, ms))`` nodes that load the right file
        and park at the offset. ``depth`` drives the tree so a multi-level table of
        contents keeps its hierarchy.
        """
        from quill.core.speech.chapters import Chapter

        timed = [h for h in resolved if h.time_ms is not None and h.audio_src]
        if not timed:
            return [], [], None
        multi = len({h.audio_src for h in timed}) > 1
        first_file = timed[0].audio_src
        first_headings = sorted(
            (h for h in timed if h.audio_src == first_file), key=lambda h: h.time_ms or 0
        )
        chapters = []
        for index, heading in enumerate(first_headings):
            start = int(heading.time_ms or 0)
            if index + 1 < len(first_headings):
                end = int(first_headings[index + 1].time_ms or start)
            else:
                end = start + 3_600_000
            title = heading.title or f"Heading {index + 1}"
            chapters.append(
                Chapter(index=index, title=title, start_ms=start, end_ms=max(end, start + 1_000))
            )
        nodes: list[tuple[str, tuple[str, object], int]] = []
        for heading in timed:
            title = heading.title or "Heading"
            offset = int(heading.time_ms or 0)
            if multi:
                payload: tuple[str, object] = ("track", (str(root_dir / heading.audio_src), offset))
            else:
                payload = ("seek", offset)
            nodes.append((title, payload, heading.depth))
        return chapters, nodes, root_dir / first_file

    def _load_book(self, path: Path) -> None:
        from quill.core.paths import app_data_dir
        from quill.core.speech.listening_positions import load_position_ms

        resume = load_position_ms(app_data_dir(), path)
        chapters = self._read_chapters(path)
        if not self._player.load(str(path), chapters, resume_ms=resume):
            self._show_message_box(f"Could not open {path.name}.", _TITLE)
            return
        self._book_path = path
        self._book_key = str(path)
        self._chapters = chapters
        self._chapter_nodes = [(c.title, ("seek", int(c.start_ms)), 1) for c in chapters]
        self._set_playlist_from_nodes()
        self._now_playing.SetValue(path.stem)
        self._refresh_chapters()
        self._refresh_bookmarks()
        self._set_status(f"Loaded {path.name}")
        if self._magical and resume > 0:
            self._announce(self._welcome_back(resume))

    def _welcome_back(self, resume_ms: int) -> str:
        """A spoken welcome-back recap: chapter (if known) + where you left off."""
        where = format_spoken(resume_ms)
        chapter = self._chapter_title_at(resume_ms)
        if chapter:
            return f"Welcome back. {chapter}, resuming at {where}."
        return f"Welcome back. Resuming at {where}."

    def _chapter_title_at(self, ms: int) -> str:
        """The title of the chapter containing ``ms``, or '' when unknown."""
        best = ""
        for chapter in self._chapters:
            if getattr(chapter, "start_ms", 0) <= ms:
                best = getattr(chapter, "title", "") or best
            else:
                break
        return best

    @staticmethod
    def _read_chapters(path: Path) -> list:
        """Best-effort chapter extraction (ID3 / M4B); empty on any failure."""
        try:
            from quill.core.speech.audiobook import read_chapters

            return read_chapters(path)
        except Exception:  # noqa: BLE001 - a book without readable chapters still plays
            return []

    def _save_resume(self) -> None:
        if self._book_path is None:
            return
        try:
            from quill.core.paths import app_data_dir
            from quill.core.speech.listening_positions import save_position_ms

            save_position_ms(app_data_dir(), self._book_path, self._player.playhead_ms())
        except Exception:  # noqa: BLE001 - resume is best-effort, never fatal
            pass

    def _on_finished(self) -> None:
        # Continuous play: auto-advance to the next track of a multi-file book.
        if self._playlist and self._playlist_index + 1 < len(self._playlist):
            self._playlist_index += 1
            title, payload = self._playlist[self._playlist_index]
            self._play_payload(payload, title, autoplay=True)
            self._announce(f"Next: {title}.")
        else:
            self._announce("End of book.")

    def _play_payload(self, payload: tuple, title: str, *, autoplay: bool) -> None:
        kind = payload[0]
        if kind == "load":
            self._player.load(str(payload[1]), [], resume_ms=0, autoplay=autoplay)
        elif kind == "track":
            path, offset = payload[1]
            self._player.load(str(path), [], resume_ms=int(offset), autoplay=autoplay)
        self._set_status(("Playing " if autoplay else "Loaded ") + title)

    def _play_track_node(self, payload: tuple, title: str) -> None:
        for index, (_title, node_payload) in enumerate(self._playlist):
            if node_payload == payload:
                self._playlist_index = index
                break
        self._play_payload(payload, title, autoplay=True)

    # -- sleep timer & view toggles -------------------------------------------

    def _on_set_sleep(self, event: Any) -> None:
        minutes = self._sleep_minutes_by_id.get(event.GetId(), 0)
        self._sleep_timer.Stop()
        self._sleep_eoc = False
        if minutes == -1:
            self._sleep_eoc = True
            self._sleep_eoc_from = self._player.current_chapter_index()
            self._announce("Sleep at the end of this chapter.")
        elif minutes > 0:
            self._sleep_timer.StartOnce(minutes * 60 * 1_000)
            self._announce(f"Sleep timer set for {minutes} minutes.")
        else:
            self._announce("Sleep timer off.")

    def _on_sleep_fired(self) -> None:
        self._player.pause()
        self._save_resume()
        self._announce("Sleep timer: paused. Goodnight.")

    # -- voice commands --------------------------------------------------------

    def _on_voice_command(self, _event: Any) -> None:
        """Say-or-type a natural command; parse it and carry it out.

        The command grammar (``core.media.voice``) and its dispatch
        (``ui.media.voice_control``) are engine-free and unit-tested. This entry
        is keyboard- and OS-dictation-friendly today; a hands-free push-to-talk
        recogniser is the documented next step (PRD Section 18, awaits #617).
        """
        from quill.core.media.voice import parse_voice_command
        from quill.ui.media.voice_control import apply_voice_intent

        prompt = (
            "Say or type a command\n"
            "(e.g. 'skip back thirty', 'next chapter', 'go to 1:20:00', "
            "'bookmark this', 'sleep in twenty'):"
        )
        dialog = wx.TextEntryDialog(self.frame, prompt, "Voice Command")
        try:
            if self._show_modal_dialog(dialog, "Voice Command") != wx.ID_OK:
                return
            phrase = dialog.GetValue()
        finally:
            dialog.Destroy()
        result = apply_voice_intent(self, parse_voice_command(phrase))
        if result:
            self._announce(result)

    def _voice_step_chapter(self, delta: int) -> None:
        """Move one chapter (single-file seek markers) or one track (playlist)."""
        if self._chapters:
            index = self._player.current_chapter_index()
            target = max(0, min(len(self._chapters) - 1, index + delta))
            self._player.play_chapter(target)
        elif self._playlist:
            target = max(0, min(len(self._playlist) - 1, self._playlist_index + delta))
            if target != self._playlist_index:
                self._playlist_index = target
                title, payload = self._playlist[target]
                self._play_payload(payload, title, autoplay=True)

    # Thin hooks the voice dispatcher calls (see ui.media.voice_control).
    def voice_next_chapter(self) -> None:
        self._voice_step_chapter(1)

    def voice_prev_chapter(self) -> None:
        self._voice_step_chapter(-1)

    def voice_add_bookmark(self) -> None:
        self._on_add_bookmark(None)

    def voice_where_am_i(self) -> None:
        self._read_status_bar()

    def voice_summarize(self) -> None:
        self._on_summarize_chapter(None)

    def voice_recap(self) -> None:
        self._on_welcome_back_recap(None)

    def voice_set_sleep(self, minutes: int) -> None:
        self._sleep_timer.Stop()
        self._sleep_eoc = False
        if minutes > 0:
            self._sleep_timer.StartOnce(minutes * 60 * 1_000)

    def voice_sleep_eoc(self) -> None:
        self._sleep_timer.Stop()
        self._sleep_eoc = True
        self._sleep_eoc_from = self._player.current_chapter_index()

    def _on_toggle_compact(self, event: Any) -> None:
        self._compact = event.IsChecked()
        for widget in (self._now_playing, self._notebook):
            widget.Show(not self._compact)
        self._main_panel.Layout()
        self._announce("Compact mode on." if self._compact else "Compact mode off.")

    def _on_toggle_magical(self, event: Any) -> None:
        self._magical = event.IsChecked()
        self._announce("Magical mode on." if self._magical else "Magical mode off.")

    def _on_toggle_ontop(self, event: Any) -> None:
        style = self.frame.GetWindowStyleFlag()
        if event.IsChecked():
            style |= wx.STAY_ON_TOP
        else:
            style &= ~wx.STAY_ON_TOP
        self.frame.SetWindowStyleFlag(style)
        self._announce("Always on top on." if event.IsChecked() else "Always on top off.")

    # -- library & mini-player -------------------------------------------------

    def _on_open_library(self, _event: Any) -> None:
        from quill.core.media import librivox
        from quill.ui.media.library_dialog import LibraryDialog

        dialog = LibraryDialog(self.frame, search_fn=lambda q: librivox.search(q))
        try:
            if self._show_modal_dialog(dialog, "Book Library") == wx.ID_OK:
                book = dialog.selected_book()
                if book is not None:
                    self._open_librivox_book(book)
        finally:
            dialog.Destroy()

    def _open_librivox_book(self, book: Any) -> None:
        if not book.has_audio:
            self._show_message_box("That book has no playable audio.", _TITLE)
            return
        self._book_path = None
        self._book_key = f"librivox:{book.book_id}"
        self._chapters = []
        self._chapter_nodes = [(s.title, ("load", s.url), 1) for s in book.sections]
        self._set_playlist_from_nodes()
        title = f"{book.title} - {book.authors}" if book.authors else book.title
        self._now_playing.SetValue(title)
        self._refresh_chapters()
        self._refresh_bookmarks()
        first = book.sections[0]
        self._playlist_index = 0
        self._play_payload(("load", first.url), first.title, autoplay=False)
        self._announce(f"{book.title}. {len(book.sections)} sections. Press Play.")

    def _set_playlist_from_nodes(self) -> None:
        """Derive the continuous-play track list from the chapter nodes."""
        self._playlist = [
            (title, payload)
            for title, payload, _depth in self._chapter_nodes
            if payload[0] in ("load", "track")
        ]
        self._playlist_index = -1

    def _on_open_mini_player(self, _event: Any) -> None:
        from quill.ui.media.mini_player import MiniPlayerFrame

        if self._mini_player:
            self._mini_player.Raise()
            return
        self._mini_player = MiniPlayerFrame(self.frame, self._player, announce=self._announce)
        self._mini_player.Bind(wx.EVT_CLOSE, self._on_mini_close)
        self._mini_player.Show()

    def _on_mini_close(self, event: Any) -> None:
        self._mini_player = None
        event.Skip()

    def _on_summarize_chapter(self, _event: Any) -> None:
        if not self._book_key and self._book_path is None:
            self._show_message_box("Open a book first.", _TITLE)
            return
        from quill.ui.media.recap_actions import summarize_current_chapter

        index = self._player.current_chapter_index()
        title, start, duration = "", 0, 0
        if 0 <= index < len(self._chapters):
            chapter = self._chapters[index]
            title = getattr(chapter, "title", "")
            start = int(getattr(chapter, "start_ms", 0))
            duration = int(getattr(chapter, "duration_ms", 0))
        summarize_current_chapter(
            self,
            book_key=self._book_key or "book",
            chapter_index=index,
            title=title,
            audio_path=str(self._book_path) if self._book_path else "",
            start_ms=start,
            duration_ms=duration,
        )

    def _on_welcome_back_recap(self, _event: Any) -> None:
        if not self._book_key and self._book_path is None:
            self._show_message_box("Open a book first.", _TITLE)
            return
        from quill.ui.media.recap_actions import welcome_back_recap

        index = self._player.current_chapter_index()
        playhead = self._player.playhead_ms()
        title, start = "", 0
        if 0 <= index < len(self._chapters):
            title = getattr(self._chapters[index], "title", "")
            start = int(getattr(self._chapters[index], "start_ms", 0))
        # Recap the passage from the chapter start up to the current point.
        welcome_back_recap(
            self,
            book_key=self._book_key or "book",
            chapter_index=index,
            title=title,
            audio_path=str(self._book_path) if self._book_path else "",
            start_ms=start,
            duration_ms=max(1_000, playhead - start),
        )

    # -- go to position --------------------------------------------------------

    def _on_go_to_position(self, _event: Any) -> None:
        if self._book_path is None:
            self._show_message_box("Open a file first.", _TITLE)
            return
        dialog = GoToPositionDialog(
            self.frame,
            duration_ms=self._player.length_ms(),
            current_ms=self._player.playhead_ms(),
            announce=self._announce,
        )
        try:
            if self._show_modal_dialog(dialog, "Go to Position") == wx.ID_OK:
                target = dialog.get_target_ms()
                self._player.seek_to(target)
                clamped = dialog.clamped_message()
                if clamped:
                    self._announce(clamped)
                else:
                    self._announce(f"Jumped to {format_spoken(target)}.")
        finally:
            dialog.Destroy()

    # -- bookmarks -------------------------------------------------------------

    def _on_add_bookmark(self, _event: Any) -> None:
        if not self._book_key:
            self._show_message_box("Open a file first.", _TITLE)
            return
        position = self._player.playhead_ms()
        self._bookmarks.add(self._book_key, position)
        self._refresh_bookmarks()
        self._announce(f"Bookmark added at {format_spoken(position)}.")

    def _on_add_bookmark_note(self, _event: Any) -> None:
        if not self._book_key:
            self._show_message_box("Open a file first.", _TITLE)
            return
        note = self._prompt_text("Add Bookmark", "Note for this bookmark:", "")
        if note is None:
            return
        position = self._player.playhead_ms()
        self._bookmarks.add(self._book_key, position, note=note)
        self._refresh_bookmarks()
        self._announce(f"Bookmark added at {format_spoken(position)}.")

    def _on_edit_bookmark(self, _event: Any) -> None:
        mark = self._selected_bookmark()
        if mark is None:
            return
        note = self._prompt_text("Edit Bookmark", "Note:", mark.note)
        if note is None:
            return
        self._bookmarks.add(self._book_key, mark.position_ms, label=mark.label, note=note)
        self._refresh_bookmarks()
        self._announce("Bookmark note updated.")

    def _prompt_text(self, title: str, prompt: str, default: str) -> str | None:
        with wx.TextEntryDialog(self.frame, prompt, title, default) as dialog:
            if dialog.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
                return None
            return dialog.GetValue().strip()

    def _on_copy_bookmark(self, _event: Any) -> None:
        mark = self._selected_bookmark()
        if mark is None:
            return
        from quill.ui.media.bookmark_actions import copy_bookmark_to_clipboard

        copy_bookmark_to_clipboard(self, mark, self._now_playing.GetValue())

    def _on_export_bookmarks(self, _event: Any) -> None:
        if not self._book_key:
            self._show_message_box("Open a book first.", _TITLE)
            return
        from quill.ui.media.bookmark_actions import export_bookmarks_markdown

        export_bookmarks_markdown(
            self, self._now_playing.GetValue(), self._bookmarks.list(self._book_key)
        )

    def _on_export_sync(self, _event: Any) -> None:
        from quill.ui.media.bookmark_actions import export_sync_bundle

        export_sync_bundle(self, self._bookmarks)

    def _on_import_sync(self, _event: Any) -> None:
        from quill.ui.media.bookmark_actions import import_sync_bundle

        import_sync_bundle(self, self._bookmarks, self._refresh_bookmarks)

    def _on_remove_bookmark(self, _event: Any) -> None:
        mark = self._selected_bookmark()
        if mark is None:
            return
        self._bookmarks.remove(self._book_key, mark.position_ms)
        self._refresh_bookmarks()
        self._announce("Bookmark removed.")

    def _on_bookmark_activate(self, _control: object) -> None:
        mark = self._selected_bookmark()
        if mark is not None:
            self._player.seek_to(mark.position_ms)

    def _selected_bookmark(self) -> MediaBookmark | None:
        index = self._bookmarks_list.GetSelection()
        marks = self._bookmarks.list(self._book_key) if self._book_key else []
        if index == wx.NOT_FOUND or not (0 <= index < len(marks)):
            return None
        return marks[index]

    def _refresh_bookmarks(self) -> None:
        self._bookmarks_list.Clear()
        for mark in self._bookmarks.list(self._book_key) if self._book_key else []:
            when = format_spoken(mark.position_ms)
            note = mark.note or mark.label
            self._bookmarks_list.Append(f"{note} ({when})" if note else when)

    # -- misc ------------------------------------------------------------------

    def _show_about(self) -> None:
        self._show_message_box(
            f"{_TITLE} {_VERSION}\n\n"
            "The accessible QUILL media player: audiobooks and audio with chapter "
            "navigation, resume, bookmarks, and precise Go to Position -- offline, "
            "keyboard- and screen-reader-first.",
            f"About {_TITLE}",
        )


def main() -> int:
    safe_mode = bool(os.environ.get("QUILL_SAFE_MODE"))
    start_in_tray = "--tray" in sys.argv
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
    frame = QuillMediaPlayerFrame(safe_mode=safe_mode, initial_paths=initial_paths)
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
