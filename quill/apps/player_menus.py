"""Quill Media Player's menu bar, built in one place.

Extracted from :mod:`quill.apps.player` under GATE-11 (extract, never
rebaseline) when the family's output-device row arrived and pushed that
module past its ceiling. The menu bar is the obvious seam: one question --
what is on the bar, and what does each row do -- and nothing else in the app
reads any of it.

A mixin rather than a function, for the same reason ``MediaListenMixin`` and
``NoteCuesMixin`` are: every row binds to the frame's own handlers, and a
mixin keeps ``self`` meaning the app it has always meant.
"""

from __future__ import annotations

import wx

from quill.apps.player_preferences import open_preferences

__all__ = ["MediaPlayerMenuMixin"]


class MediaPlayerMenuMixin:
    """The menu bar for :class:`quill.apps.player.QuillMediaPlayerFrame`."""

    def _build_menu_bar(self) -> None:
        # The app's identity constants stay in quill.apps.player, which
        # imports THIS module -- so they are read at call time; a top-level
        # import back into it would be a cycle.
        from quill.apps.player import _BUILD, _REPO, _TITLE, _VERSION
        from quill.core.app_version import installed_version

        menu_bar = wx.MenuBar()

        file_menu = wx.Menu()
        open_id, folder_id, goto_id = (wx.NewIdRef() for _ in range(3))
        tray_id, exit_id = wx.NewIdRef(), wx.NewIdRef()
        daisy_id, library_id = wx.NewIdRef(), wx.NewIdRef()
        file_menu.Append(open_id, "&Open File...\tCtrl+O")
        file_menu.Append(folder_id, "O&pen Folder as Book...\tCtrl+Shift+O")
        file_menu.Append(daisy_id, "Open &DAISY Book...\tCtrl+Alt+D")
        file_menu.Append(library_id, "Book &Library...\tCtrl+L")
        file_menu.Append(goto_id, "&Go to Position...\tCtrl+G")
        bookmarks_menu = wx.Menu()
        export_bm_id, export_sync_id, import_sync_id = (wx.NewIdRef() for _ in range(3))
        bookmarks_menu.Append(export_bm_id, "Export &Bookmarks...\tCtrl+Alt+E")
        bookmarks_menu.Append(export_sync_id, "Export &Sync Bundle...\tCtrl+Alt+S")
        bookmarks_menu.Append(import_sync_id, "&Import Sync Bundle...\tCtrl+Alt+I")
        file_menu.AppendSubMenu(bookmarks_menu, "Book&marks && Sync")
        file_menu.AppendSeparator()
        # Ctrl+, is Preferences in every app in the family (qc.md X-01); P is
        # Open Folder's access key here, so this one is E.
        prefs_id = wx.NewIdRef()
        file_menu.Append(prefs_id, "Pr&eferences...\tCtrl+,")
        self.frame.Bind(wx.EVT_MENU, lambda _e: open_preferences(self), id=prefs_id)
        self._keep_menu_ids(prefs_id)
        file_menu.Append(tray_id, "Minimize to &Tray\tCtrl+W")
        self._append_show_hide_key_item(file_menu, "player")
        file_menu.Append(exit_id, "E&xit\tCtrl+Q")
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
        nav_menu.Append(edit_bm_id, "&Edit Bookmark Note...\tCtrl+Alt+N")
        nav_menu.Append(copy_bm_id, "&Copy Bookmark to Clipboard\tCtrl+Shift+C")
        nav_menu.Append(focus_bm_id, "Go to Book&marks List\tCtrl+Alt+M")
        nav_menu.Append(focus_player_id, "Go to &Player Controls\tCtrl+Alt+P")
        nav_menu.Append(review_field_id, "Review Status &Field\tF6")
        nav_menu.Append(read_status_id, "&Read Status Bar\tShift+F6")
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
        self._keep_menu_ids(self._add_note_cue_menu_item(playback_menu, wx))
        summarize_id, recap_id, voice_id, listen_id = (wx.NewIdRef() for _ in range(4))
        playback_menu.Append(summarize_id, "Summarize This &Chapter (AI)\tCtrl+Alt+C")
        playback_menu.Append(recap_id, "AI &Recap of Where I Am\tCtrl+Alt+R")
        playback_menu.AppendSeparator()
        self._listen_menu_item = playback_menu.AppendCheckItem(
            listen_id, "&Listen for a Command\tCtrl+Shift+L"
        )
        playback_menu.Append(voice_id, "Type a &Voice Command...\tCtrl+Shift+V")
        playback_menu.AppendSeparator()
        device_id = wx.NewIdRef()
        # Which sound card the book plays out of. &D and Ctrl+Shift+K are
        # both free in this bar, and Ctrl+Shift+K is the chord QUILL Cast
        # already uses for the same command -- the family agrees wherever it
        # can (Quill Radio's Ctrl+Shift+D is taken here by Open Folder).
        playback_menu.Append(device_id, "Audio Output &Device...\tCtrl+Shift+K")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._choose_output_device(), id=device_id)
        self._keep_menu_ids(device_id)
        self.frame.Bind(wx.EVT_MENU, self._on_summarize_chapter, id=summarize_id)
        self.frame.Bind(wx.EVT_MENU, self._on_welcome_back_recap, id=recap_id)
        self.frame.Bind(wx.EVT_MENU, self._on_listen_command, id=listen_id)
        self.frame.Bind(wx.EVT_MENU, self._on_voice_command, id=voice_id)
        self._keep_menu_ids(summarize_id, recap_id, voice_id, listen_id)
        menu_bar.Append(playback_menu, "&Playback")

        view_menu = wx.Menu()
        compact_id, magical_id, ontop_id, mini_id = (wx.NewIdRef() for _ in range(4))
        view_menu.Append(mini_id, "Mini &Player\tCtrl+Shift+M")
        view_menu.AppendCheckItem(compact_id, "&Compact Mode\tCtrl+Alt+K")
        view_menu.AppendCheckItem(magical_id, "&Magical Mode\tCtrl+Shift+G")
        view_menu.AppendCheckItem(ontop_id, "Always on &Top\tCtrl+Shift+T")
        self.frame.Bind(wx.EVT_MENU, self._on_open_mini_player, id=mini_id)
        self.frame.Bind(wx.EVT_MENU, self._on_toggle_compact, id=compact_id)
        self.frame.Bind(wx.EVT_MENU, self._on_toggle_magical, id=magical_id)
        self.frame.Bind(wx.EVT_MENU, self._on_toggle_ontop, id=ontop_id)
        menu_bar.Append(view_menu, "&View")
        # Preferences drives the same three rows and keeps their check marks true.
        self._view_toggle_ids = {"compact": compact_id, "magical": magical_id, "on_top": ontop_id}
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
        help_menu.Append(updates_id, "Check for &Updates...\tCtrl+Alt+U")
        from quill.ui.menu_palette import append_palette_row

        append_palette_row(self, help_menu)  # qc.md X-01
        # Every app in the family answers the same question the same way:
        # one item, one key, one form that reaches a person who can reply.
        from quill.ui.support_menu import append_get_help_item

        append_get_help_item(self, help_menu, wx, source_app=_TITLE, app_version=_VERSION)
        help_menu.Append(about_id, "&About Quill Media Player\tCtrl+Alt+A")
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.check_for_app_updates(
                repo_slug=_REPO,
                current_version=installed_version(_VERSION, build=_BUILD),
                app_key="player",
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

    # -- About ------------------------------------------------------------
    #
    # Moved here with the bar it hangs off, under GATE-11: the Help menu's
    # own row, and nothing else in the app reads it.

    def _show_about(self) -> None:
        from quill.apps.player import _BUILD, _TITLE, _VERSION
        from quill.core.app_version import describe_version

        self._show_message_box(
            f"{_TITLE} {describe_version(_VERSION, build=_BUILD)}\n\n"
            "The accessible QUILL media player: audiobooks and audio with chapter "
            "navigation, resume, bookmarks, and precise Go to Position -- offline, "
            "keyboard- and screen-reader-first.\n\nSupport: support@community-access.org",
            f"About {_TITLE}",
        )
