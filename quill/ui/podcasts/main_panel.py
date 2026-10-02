"""Cast's main window: the tree, the transport row, the status bar, the keys.

Extracted from ``quill/apps/podcasts.py`` under GATE-11 (extract, never
rebaseline) when the status bar arrived: that module sat exactly on its budget
with one line spare. It is the right seam regardless -- building the panel and
deciding which keystrokes the window claims are one subject, and neither touches
anything else in the frame.

Two things in here are worth knowing before changing them.

**Every control gets a real label, created before it.** On wxMSW the accessible
name of a plain control comes from the ``wx.StaticText`` constructed immediately
before it in z-order; ``SetName`` sets wxWindow's own name and the screen reader
never sees it. Two edit fields in Add Podcast shipped announcing as bare "edit"
for exactly that reason. ``quill/tools/check_control_labels.py`` is the gate that
now catches it.

**One EVT_CHAR_HOOK, not several.** Two hooks on the same window means only one
of them decides whether a key travels on, and which one wins is an implementation
detail nobody should depend on. So Alt+F4-to-tray, the scan hold, F6 into the
status bar and the Winamp transport letters are all dispatched from one handler,
in that order, and the order is the priority.
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

        self._now_playing_text = wx.StaticText(panel, label="Podcasts: stopped")
        set_accessible_name(self._now_playing_text, "Now playing")
        root.Add(self._now_playing_text, 0, wx.EXPAND | wx.ALL, 8)

        # Find in library (qc.md 4.2, the interim of P10): typing flattens the
        # tree below into matches; Escape puts the library back. Its label is
        # created first, which is what names it on wxMSW.
        root.Add(wx.StaticText(panel, label="Fi&nd in library:"), 0, wx.LEFT | wx.RIGHT, 8)
        self._find_box = wx.TextCtrl(panel)
        set_accessible_name(self._find_box, "Find in library")  # VoiceOver (#1012)
        self._find_box.SetHelpText(
            "Type part of a podcast name, an episode title or one of your notes. "
            "The library below becomes the matches; Down Arrow moves into them, "
            "Enter plays one, and Escape brings your library back. Ctrl+F comes "
            "here from anywhere in the window."
        )
        self._find_box.Bind(wx.EVT_TEXT, self._on_find_text)
        self._find_box.Bind(wx.EVT_KEY_DOWN, self._on_find_key)
        root.Add(self._find_box, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        self._find_status = wx.StaticText(panel, label="")
        root.Add(self._find_status, 0, wx.LEFT | wx.RIGHT, 8)
        library_label = wx.StaticText(panel, label="&Library:")
        root.Add(library_label, 0, wx.LEFT | wx.RIGHT, 8)
        self._shows_tree = wx.TreeCtrl(
            panel, style=wx.TR_HAS_BUTTONS | wx.TR_LINES_AT_ROOT | wx.TR_HIDE_ROOT
        )
        self._shows_tree.SetHelpText(
            "Your podcasts, folders, and pinned views. Arrow through the library; "
            "Enter on a podcast plays its next episode and Enter on a view opens "
            "its episode list. Shift F10 offers the selected row's actions."
        )
        set_accessible_name(
            self._shows_tree,
            "Your podcast library: pinned views and folders; Enter on a show "
            "plays its next episode, Shift+F10 opens all actions",
        )
        root.Add(self._shows_tree, 1, wx.EXPAND | wx.ALL, 8)
        self._shows_tree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self._on_library_activated)
        # Right-click arrives as the item event; Shift+F10 and the Applications
        # key can arrive as a bare EVT_CONTEXT_MENU, which only the item event
        # was bound for -- so the key this tree's own help teaches opened
        # nothing (qc.md 6b item 3; Radio fixed the same in aaed65f). The
        # handler reads the selection, never the event, so both reach one menu.
        for context_event in (wx.EVT_TREE_ITEM_MENU, wx.EVT_CONTEXT_MENU):
            self._shows_tree.Bind(context_event, self._on_library_context_menu)
        self._shows_tree.Bind(wx.EVT_KEY_DOWN, self._on_library_key)
        self._shows_tree.Bind(wx.EVT_TREE_ITEM_EXPANDING, self._on_library_expanding)
        # The button row describes the selection, so it follows the selection.
        self._shows_tree.Bind(
            wx.EVT_TREE_SEL_CHANGED, lambda e: (self._refresh_selection_buttons(), e.Skip())
        )

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        # Every button in this row names its object IN ITS LABEL, never in an
        # accessible name: on wxMSW a button is self-labelled and
        # set_accessible_name is inert on it (qc.md 6b, item 1), so "Play what?"
        # can only be answered by the label. The labels are built by
        # core/transport_button.py, elided at forty characters, and each button
        # gets an equal share of the row (proportion 1), so nothing reflows as
        # the selection changes. tests/unit/ui/podcasts/test_button_object_in_label.py
        # is the gate that no set_accessible_name targets a wx.Button here.
        #
        # Mnemonics are chosen against the menu bar's top-level letters, not
        # only against each other. Alt+S opened Stop instead of the
        # Subscriptions menu, and Alt+V the favourites toggle instead of View,
        # because wxMSW hands an ambiguous Alt+letter to the control (Jeff,
        # 2026-09-30). The menu bar wins -- its letters are how a listener
        # navigates -- so the buttons yield: Y (Play), S (Pause and Resume), T,
        # F, U, A, I. GATE-15 (quill/tools/check_menubar_mnemonics.py) reads the
        # computed transport labels as well as the literals here.
        from quill.core.podcasts import transport_intent

        # One transport button, not two static ones: it tracks Play, Pause,
        # and Resume so it is never dead in a given state.
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
        # Favorite toggle for whatever show is playing right now, same
        # pattern as Quill Radio's main-page toggle.
        self._favorite_toggle_btn = wx.Button(panel, label="Add to &Favorites")
        self._favorite_toggle_btn.SetHelpText(
            "Adds the playing podcast to Favorites, or removes it if already there. "
            "Disabled when there is no playing podcast."
        )
        self._favorite_toggle_btn.Enable(False)
        self._favorite_toggle_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_favorite_toggle())
        buttons.Add(self._favorite_toggle_btn, 1, wx.EXPAND | wx.RIGHT, 6)
        # Unfollow beside Add, because a row of buttons that can add a podcast
        # and cannot remove one is half a row (Jeff: "shouldn't that also show
        # remove podcast if a podcast is highlighted?"). Labelled with the
        # selected podcast and disabled with nothing selected; the shared prompt
        # asks first and makes it one undoable step.
        self._unfollow_btn = wx.Button(panel, label="&Unfollow")
        self._unfollow_btn.SetHelpText(
            "Stops following the podcast named on the button, the one selected in "
            "the library. Asks first, says what happens to anything downloaded, "
            "and Ctrl+Z puts it back."
        )
        self._unfollow_btn.Enable(False)
        self._unfollow_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_unfollow_button())
        buttons.Add(self._unfollow_btn, 1, wx.EXPAND | wx.RIGHT, 6)
        # "Open Manager" named a window, not a thing you wanted. Until Phase 2
        # folds that window into this one, the button says what is in it.
        for label, handler in (
            ("Episode L&ist...", lambda _e: self.open_podcast_manager()),
            ("&Add Podcast...", lambda _e: self._podcast_open_add_dialog()),
        ):
            button = wx.Button(panel, label=label)
            button.SetHelpText(
                "Opens the episode list and podcast actions, or opens Add Podcast "
                "to find and follow another show, as named by this button."
            )
            button.Bind(wx.EVT_BUTTON, handler)
            buttons.Add(button, 1, wx.EXPAND | wx.RIGHT, 6)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)

        # The status bar, last in the panel and last in the tab order -- and it
        # refuses Tab focus entirely, so it costs a listener nothing until they
        # press F6. Built even when hidden, because building it lazily would mean
        # the first F6 after switching it on had nothing to focus.
        from quill.ui.podcasts.status_bar import CastStatusBar

        self._cast_status_bar = CastStatusBar(self)
        root.Add(self._cast_status_bar.build(panel), 0, wx.EXPAND | wx.ALL, 4)
        self._cast_status_bar.set_visible(
            bool(getattr(self._podcast_history, "show_status_bar", True))
        )

        panel.SetSizer(root)
        self._main_panel = panel
        self._reload_library_tree()
        self._refresh_transport_controls()
        # Winamp classic transport letters on the main page, sharing Quill
        # Radio's key map (quill/ui/radio/winamp_keys.py) so the letters mean
        # the same thing in both apps.
        self.frame.Bind(wx.EVT_CHAR_HOOK, self._on_main_char_hook)
        self.frame.Bind(wx.EVT_KEY_UP, self._on_main_key_up)
        # Losing the window must end a scan: a listener left at four times
        # speed because they alt-tabbed mid-hold has no way to know why.
        self.frame.Bind(wx.EVT_ACTIVATE, self._on_main_activate)
        from quill.ui.podcasts.scan_hold_control import ScanHoldController

        self._scan_hold = ScanHoldController(self, parent=self.frame)
        self._select_default_launch_view()
        self._shows_tree.SetFocus()

    def open_notification_target(self, target: str) -> None:
        """Enter on a notification: select the podcast it was about.

        The other half of the pair Quill Radio implements: one notification
        file, two apps, and each lands the cursor its own way.
        """
        from quill.ui import notification_open

        notification_open.open_in_cast(self, target)

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
        bar.focus_bar(return_focus=getattr(self, "_shows_tree", None))
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
