"""Cast's main window: Now Playing, Find, Places, the content pane, notes, buttons, status bar.

One window (qc.md section 4). Top to bottom, in the order a screen reader
meets them: the Now Playing line (a reviewable field, never announced on its
own); Find (Ctrl+F from anywhere; typing flattens the content pane into
matches); the **Places** list and, beside it, the **content pane** whose kind
follows the place -- the episode list, the podcast list, the notices, or the
folder tree -- under a heading that names the place and its count; the show
notes of the selected episode; the button row, each button naming its object
in its label; and the status bar, F6 away.

Two things in here are worth knowing before changing them.

**Every control gets a real label, created before it.** On wxMSW the accessible
name of a plain control comes from the ``wx.StaticText`` constructed immediately
before it in z-order; ``SetName`` sets wxWindow's own name and the screen reader
never sees it. ``quill/tools/check_control_labels.py`` is the gate that catches it.

**One EVT_CHAR_HOOK, not several.** Alt+F4-to-tray, the scan hold, F6 into the
status bar, Alt+Shift+Up/Down on a place (Windows routes Alt+arrow to the menu
system before a list sees it) and the Winamp transport letters are all
dispatched from one handler, in that order, and the order is the priority.
"""

from __future__ import annotations

import wx

from quill.ui.dialog_contract import set_accessible_name
from quill.ui.podcasts.library_find import CastLibraryFindMixin

__all__ = ["CastMainPanelMixin"]


class CastMainPanelMixin(CastLibraryFindMixin):
    """The main panel and the window's key handling. On ``PodcastsAppFrame``."""

    def _build_main_panel(self) -> None:
        panel = wx.Panel(self.frame, style=wx.TAB_TRAVERSAL)
        root = wx.BoxSizer(wx.VERTICAL)

        # 4.1: the Now Playing line, a reviewable read-only field in a larger
        # weight, so a listener can arrow through the exact spelling of a title.
        root.Add(wx.StaticText(panel, label="Now playin&g:"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        self._now_playing_text = wx.TextCtrl(
            panel, value="Podcasts: stopped", style=wx.TE_READONLY | wx.BORDER_NONE
        )
        self._now_playing_text.SetHelpText(
            "What is playing, how far in, and the speed when it is not normal. Read "
            "only; arrow through it to check a title. Ctrl+T says it from anywhere."
        )
        font = self._now_playing_text.GetFont()
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        self._now_playing_text.SetFont(font)
        root.Add(self._now_playing_text, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        # 4.2: Find. Typing flattens the content pane into matches across the
        # whole library; Escape puts the place back.
        root.Add(wx.StaticText(panel, label="Fi&nd:"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        self._find_box = wx.TextCtrl(panel)
        set_accessible_name(self._find_box, "Find")  # VoiceOver (#1012)
        self._find_box.SetHelpText(
            "Type part of a podcast name, an episode title or one of your notes. "
            "The content pane becomes the matches, each row saying what it is and "
            "where it lives; Down Arrow moves into them, Enter goes to one, and "
            "Escape brings the place back. Ctrl+F comes here from anywhere."
        )
        self._find_box.Bind(wx.EVT_TEXT, self._on_find_text)
        self._find_box.Bind(wx.EVT_KEY_DOWN, self._on_find_key)
        root.Add(self._find_box, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        self._find_status = wx.StaticText(panel, label="")
        root.Add(self._find_status, 0, wx.LEFT | wx.RIGHT, 8)

        # 4.3 and 4.4: Places beside the content pane.
        from quill.ui.podcasts.content_pane import ContentPane
        from quill.ui.podcasts.places_list import PlacesList

        middle = wx.BoxSizer(wx.HORIZONTAL)
        places_column = wx.BoxSizer(wx.VERTICAL)
        self._places = PlacesList(
            panel,
            wx=wx,
            on_enter=self._on_place_entered,
            on_change=self._on_place_changed,
            on_hide=self._on_place_hide,
            on_rename=self._on_place_rename,
            on_menu=self._on_place_menu,
        )
        places_column.Add(self._places.label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        places_column.Add(self._places.box, 1, wx.EXPAND | wx.LEFT | wx.BOTTOM, 8)
        middle.Add(places_column, 0, wx.EXPAND)

        # The pane's two pages each hold a heading created before their control,
        # which is what names the list and the tree on wxMSW (content_pane.py).
        self._content = ContentPane(panel, wx=wx)
        episode_list = self._build_episode_list(self._content.list_page)
        self._shows_tree = wx.TreeCtrl(
            self._content.tree_page,
            style=wx.TR_HAS_BUTTONS | wx.TR_LINES_AT_ROOT | wx.TR_HIDE_ROOT,
        )
        self._shows_tree.SetHelpText(
            "Your podcasts and folders. Arrow through them; Enter on a podcast "
            "plays its next episode; expand a podcast to reach its episodes; Left "
            "Arrow at the top returns to Places. Shift F10 offers the row's actions."
        )
        set_accessible_name(
            self._shows_tree,
            "Your podcasts: folders and podcasts; Enter on a podcast plays its next "
            "episode, Shift+F10 opens all actions",
        )
        self._content.attach(episode_list, self._shows_tree, list_heading=self._list_heading)
        content_column = wx.BoxSizer(wx.VERTICAL)
        content_column.Add(self._content.book, 1, wx.EXPAND | wx.ALL, 4)
        middle.Add(content_column, 1, wx.EXPAND)
        root.Add(middle, 1, wx.EXPAND)

        self._shows_tree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self._on_library_activated)
        # Right-click arrives as the item event; Shift+F10 and the Applications
        # key can arrive as a bare EVT_CONTEXT_MENU (qc.md 6b item 3), so both
        # reach one menu that reads the selection, never the event.
        for context_event in (wx.EVT_TREE_ITEM_MENU, wx.EVT_CONTEXT_MENU):
            self._shows_tree.Bind(context_event, self._on_library_context_menu)
        self._shows_tree.Bind(wx.EVT_KEY_DOWN, self._on_library_key)
        self._shows_tree.Bind(wx.EVT_TREE_ITEM_EXPANDING, self._on_library_expanding)
        self._shows_tree.Bind(
            wx.EVT_TREE_SEL_CHANGED,
            lambda e: (self._refresh_selection_buttons(), self._refresh_notes_pane(), e.Skip()),
        )
        self._episodes.Bind(
            wx.EVT_LIST_ITEM_ACTIVATED,
            lambda _e: self._activate_content_row(self._list_selected_data()),
        )
        self._episodes.Bind(wx.EVT_KEY_DOWN, self._on_content_list_key)
        for context_event in (wx.EVT_LIST_ITEM_RIGHT_CLICK, wx.EVT_CONTEXT_MENU):
            self._episodes.Bind(context_event, self._on_content_context_menu)
        self._episodes.Bind(
            wx.EVT_LIST_ITEM_SELECTED,
            lambda e: (self._refresh_selection_buttons(), self._refresh_notes_pane(), e.Skip()),
        )

        # The show notes of the selected episode, one Tab from the list (Jeff,
        # 2026-10-02). The same Notes reader Now Playing has.
        from quill.ui.notes_reader import NotesReader

        self._notes_pane = NotesReader(
            panel,
            root,
            label="Sh&ow notes:",
            announce=self._announce,
            on_seek=self._seek_selected_episode,
            show_modal=getattr(self, "_show_modal_dialog", None),
            copy_format=lambda: str(
                getattr(self._podcast_history, "notes_copy_format", "plain") or "plain"
            ),
            set_copy_format=self._remember_notes_copy_format,
            min_height=90,
            labels={"copy": "&Copy Notes", "links": "Lin&ks", "browser": "View in B&rowser"},
        )
        self._notes_pane.set_placeholder("Select an episode to read its show notes here.")

        # 4.5: the button row. Every button names its object IN ITS LABEL, never
        # in an accessible name (qc.md 6b, item 1); mnemonics are chosen against
        # the menu bar's letters (GATE-15): Y, S, T, F, U, A.
        from quill.core.podcasts import transport_intent

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self._play_pause_btn = wx.Button(
            panel, label=transport_intent.button_label(transport_intent.STOPPED)
        )
        self._play_pause_btn.SetHelpText(
            "Starts the selected podcast or episode when stopped, pauses current "
            "playback, or resumes it from the saved position when paused. The label "
            "names what it would play, pause or resume."
        )
        self._play_pause_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_transport_button())
        buttons.Add(self._play_pause_btn, 1, wx.EXPAND | wx.RIGHT, 6)
        self._stop_btn = wx.Button(panel, label="S&top")
        self._stop_btn.SetHelpText(
            "Stops the current episode. Enabled only while something is playing or "
            "paused; Play starts playback again."
        )
        self._stop_btn.Bind(wx.EVT_BUTTON, lambda _e: self.podcast_stop())
        buttons.Add(self._stop_btn, 1, wx.EXPAND | wx.RIGHT, 6)
        self._favorite_toggle_btn = wx.Button(panel, label="Add to &Favorites")
        self._favorite_toggle_btn.SetHelpText(
            "Adds the playing podcast to Favorites, or removes it if already there. "
            "Disabled when there is no playing podcast."
        )
        self._favorite_toggle_btn.Enable(False)
        self._favorite_toggle_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_favorite_toggle())
        buttons.Add(self._favorite_toggle_btn, 1, wx.EXPAND | wx.RIGHT, 6)
        self._unfollow_btn = wx.Button(panel, label="&Unfollow")
        self._unfollow_btn.SetHelpText(
            "Stops following the podcast named on the button, the one selected in "
            "the library. Asks first, says what happens to anything downloaded, "
            "and Ctrl+Z puts it back."
        )
        self._unfollow_btn.Enable(False)
        self._unfollow_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_unfollow_button())
        buttons.Add(self._unfollow_btn, 1, wx.EXPAND | wx.RIGHT, 6)
        add_button = wx.Button(panel, label="&Add Podcast...")
        add_button.SetHelpText(
            "Opens Add Podcast, to find a podcast by name in a directory or follow "
            "one by its feed address."
        )
        add_button.Bind(wx.EVT_BUTTON, lambda _e: self._podcast_open_add_dialog())
        buttons.Add(add_button, 1, wx.EXPAND | wx.RIGHT, 6)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)

        # 4.6: the status bar, last in the panel and last in the tab order, and
        # it refuses Tab focus until F6.
        from quill.ui.podcasts.status_bar import CastStatusBar

        self._cast_status_bar = CastStatusBar(self)
        root.Add(self._cast_status_bar.build(panel), 0, wx.EXPAND | wx.ALL, 4)
        self._cast_status_bar.set_visible(
            bool(getattr(self._podcast_history, "show_status_bar", True))
            and self._cast_area_enabled("status_bar")
        )

        panel.SetSizer(root)
        self._main_panel = panel
        self._rebuild_places()
        self._reload_library_tree()
        self._refresh_transport_controls()
        self.frame.Bind(wx.EVT_CHAR_HOOK, self._on_main_char_hook)
        self.frame.Bind(wx.EVT_KEY_UP, self._on_main_key_up)
        # Losing the window must end a scan: a listener left at four times
        # speed because they alt-tabbed mid-hold has no way to know why.
        self.frame.Bind(wx.EVT_ACTIVATE, self._on_main_activate)
        from quill.ui.podcasts.scan_hold_control import ScanHoldController

        self._scan_hold = ScanHoldController(self, parent=self.frame)
        self._select_default_launch_view()

    # -- the notes pane follows the cursor ------------------------------------ #

    def _refresh_notes_pane(self) -> None:
        """The pane follows the library cursor: an episode's notes, a podcast's
        description, or a sentence saying what to select."""
        pane = getattr(self, "_notes_pane", None)
        if pane is None:
            return
        pair = self._selected_episode()
        if pair is not None:
            show, episode = pair
            pane.set_notes(
                str(getattr(episode, "description", "") or ""),
                title=str(getattr(episode, "title", "")),
                podcast=str(getattr(show, "title", "")),
            )
            return
        show = self._selected_show()
        if show is not None and str(getattr(show, "description", "") or "").strip():
            pane.set_notes(str(show.description), title=str(show.title), podcast=str(show.title))
            return
        pane.set_placeholder("Select an episode to read its show notes here.")

    def _seek_selected_episode(self, ms: int) -> None:
        """Enter on a timestamp in the pane: seek the playing episode, or start
        the selected one from there."""
        from quill.core.media.timecode import format_spoken

        pair = self._selected_episode()
        if pair is None:
            self._announce("Select an episode first.")
            return
        show, episode = pair
        controller = self._podcast_controller
        state = controller.state
        if state.show_id and state.episode_guid == episode.guid:
            controller.seek(int(ms))
            self._announce(f"At {format_spoken(int(ms))}.")
            return
        from quill.ui.podcasts.show_actions import start_episode_playback

        if start_episode_playback(
            controller,
            self._podcast_library,
            show,
            episode,
            resume_ms=int(ms),
            announce=self._announce,
        ):
            self._announce(f"Playing {episode.title} from {format_spoken(int(ms))}.")

    def _remember_notes_copy_format(self, fmt: str) -> None:
        history = getattr(self, "_podcast_history", None)
        if history is None:
            return
        history.notes_copy_format = fmt
        saver = getattr(self, "_save_podcast_history", None)
        if callable(saver):
            saver()

    def open_notification_target(self, target: str) -> None:
        """Enter on a notification: select the podcast it was about.

        The other half of the pair Quill Radio implements: one notification
        file, two apps, and each lands the cursor its own way.
        """
        from quill.ui import notification_open

        self.show_place("podcasts", focus=False)
        notification_open.open_in_cast(self, target)
        self._content.focus()

    def _on_content_context_menu(self, event: object) -> None:
        from quill.ui.podcasts.context_menus import episode_row_menu, podcast_row_menu

        selected = self._list_selected_data()
        if selected is None:
            return
        kind = selected[0]
        if kind == "episode":
            episode_row_menu(self)
        elif kind == "show":
            podcast_row_menu(self)
        elif kind == "notice":
            self._on_notice_context_menu(selected[1])
        elif kind == "playlist":
            from quill.ui.podcasts.context_menus import playlist_row_menu

            playlist_row_menu(self, selected[1])
        if hasattr(event, "Skip"):
            event.Skip(False)

    def _on_notice_context_menu(self, notice_id: str) -> None:
        menu = wx.Menu()
        for label, handler in (
            ("&Open\tEnter", lambda: self._open_notice(notice_id)),
            ("Mark &Read", lambda: self._mark_notice_read(notice_id)),
            ("Mark All as R&ead", self.mark_all_notices_read),
            ("&Remove\tDelete", lambda: self._dismiss_notice(notice_id)),
            ("&Clear List", self.clear_all_notices),
        ):
            item = menu.Append(wx.ID_ANY, label)
            menu.Bind(wx.EVT_MENU, lambda _e, h=handler: h(), item)
        try:
            self._episodes.PopupMenu(menu)
        finally:
            menu.Destroy()

    def _on_main_char_hook(self, event: wx.KeyEvent) -> None:
        """Alt+F4-to-tray first, then the Winamp transport letters.

        One hook rather than two: two EVT_CHAR_HOOK bindings on the same
        window means only one of them decides whether the key travels on, and
        which one wins is an implementation detail nobody should depend on.
        """
        if (
            event.GetKeyCode() == wx.WXK_F4
            and event.AltDown()
            and getattr(self._podcast_history, "alt_f4_to_tray", False)
            and self._cast_area_enabled("tray")
        ):
            self._send_to_tray()
            return
        # F6 moves into the status bar and a second F6 hands focus back, the same
        # region key the QUILL editor and Quill Radio use. Before the scan hold and
        # the transport letters because it is a navigation key, and a navigation key
        # a transport swallows is a region a keyboard listener cannot reach -- the
        # same mistake bare Left and Right were making in the library tree.
        if (
            event.GetKeyCode() == wx.WXK_F6
            and not event.AltDown()
            and not event.ControlDown()
            and self._cast_focus_status_bar()
        ):
            return
        if (
            event.GetKeyCode() in (wx.WXK_UP, wx.WXK_DOWN)
            and event.AltDown()
            and event.ShiftDown()
            and wx.Window.FindFocus() is getattr(getattr(self, "_places", None), "box", None)
        ):
            # Alt+Shift+Up/Down moves a place (qc.md 4.3): Radio's chord, caught
            # here because Windows routes Alt+arrow to the menu system first.
            place_id = self._places.selected
            if place_id:
                self._move_place(place_id, -1 if event.GetKeyCode() == wx.WXK_UP else 1)
            return
        scan = getattr(self, "_scan_hold", None)
        if scan is not None and scan.handles(
            key_code=event.GetKeyCode(),
            shift=bool(event.ShiftDown()),
            ctrl=bool(event.ControlDown()),
            alt=bool(event.AltDown()),
        ):
            # Every auto-repeat comes through here, which is how the hold is
            # measured; press() is idempotent for exactly that reason.
            scan.press()
            return
        self._on_winamp_char_hook(event)

    def _on_main_key_up(self, event: wx.KeyEvent) -> None:
        """End a scan the moment the key actually comes up.

        The watchdog timer would end it anyway; this only makes the drop back
        immediate rather than up to the grace window late.
        """
        scan = getattr(self, "_scan_hold", None)
        if scan is not None and scan.is_scanning and event.GetKeyCode() == wx.WXK_RIGHT:
            scan.stop()
        event.Skip()

    def _on_main_activate(self, event: wx.ActivateEvent) -> None:
        if not event.GetActive():
            scan = getattr(self, "_scan_hold", None)
            if scan is not None:
                scan.stop()
        event.Skip()

    def _cast_focus_status_bar(self) -> bool:
        """F6: into the bar, or back out of it. True when the key was used.

        Returns a bool rather than swallowing unconditionally, so F6 still travels
        on when the bar is hidden -- a key that silently does nothing is worse than
        one that does what it always did.
        """
        bar = getattr(self, "_cast_status_bar", None)
        if bar is None or not bar.is_shown():
            return False
        if bar.has_focus():
            bar._leave_bar()  # noqa: SLF001 - the bar owns its own exit path
            return True
        bar.focus_bar(return_focus=self._content.control)
        return True

    def _refresh_cast_status_bar(self) -> None:
        """Redraw the bar's readouts. Called wherever the transport refreshes.

        Never raises: a readout that cannot be computed must not take down the
        thing that changed, and the bar is the least important surface in the
        window by definition.
        """
        bar = getattr(self, "_cast_status_bar", None)
        if bar is None:
            return
        try:
            bar.refresh()
        except Exception:  # noqa: BLE001 - a stale readout is not worth a crash
            pass
