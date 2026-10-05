"""QUILL Cast's &View menu: the places you go, and how much of Cast you meet.

Jeff, 2026-09-30, after using the app: "the UI is a bit confusing to
understand... Perhaps we should add a View menu and start with basic features and
allow an advanced mode. Users should also be able to turn on and off features for
all quill cast features so that it is magical like other quill apps... Status bar
like in quill/quill lite/radio... We need that also."

Four things arrive together here because they are one idea from four sides.

**The spine.** Earshot's navigation is a flat list of *places* -- Inbox, Queue,
Subscriptions, Library, Downloads, Stats, Settings (its PRD, 5.2). Cast's menu bar
is organised by *machinery*, which is why a newcomer cannot find anything: the
seven places a listener actually moves between were scattered across three menus
and a tree, and two of them had no menu row at all. The top of this menu is that
spine, one key each, in Earshot's order -- so somebody who uses both apps already
knows Cast's shape, and somebody who uses neither can learn seven rows.

**Simple and Advanced** (``core/podcasts/menu_mode.py``). The mode decides which
rows are *built*, not which are greyed out: a disabled row still costs a
screen-reader user a stop and a sentence.

**Customize Features...**, which Radio, Weather and QUILL Lite have all had and
Cast never did -- so Cast was the one app in the family where a listener could not
switch off a part they had no use for. The areas are declared here, next to the
menu that honours them.

**The status bar**, the fourth thing every other app in the family has. Its
visibility is a View-menu check item, exactly as Radio's is.

One rule this menu follows and the rest of the bar should: **a check item's label
states the thing, and its check mark states the answer.** "Hide Caught-Up Podcasts,
checked" is unambiguous read aloud; "Show All Podcasts" with a check mark is a double
negative somebody has to work out while listening.
"""

from __future__ import annotations

import wx

from quill.core.podcasts import cast_features, menu_mode

__all__ = ["CAST_AREAS", "CastViewMenuMixin"]

CAST_AREAS = cast_features.AREAS


class CastViewMenuMixin:
    """Builds the &View menu and the four toggles behind it.

    A mixin on ``PodcastsAppFrame``, and a separate module because
    ``podcasts_menu.py`` is a 500-line method already at the edge of GATE-11's
    default cap -- and because this menu is the one part of the bar that is about
    *the app's shape* rather than about podcasts.
    """

    def _build_view_menu(self, menu_bar: wx.MenuBar) -> None:
        """Append &View. Called by ``_build_menu_bar`` after &Downloads."""
        view_menu = wx.Menu()
        self._append_places(view_menu)
        view_menu.AppendSeparator()
        self._append_library_view_items(view_menu)
        view_menu.AppendSeparator()
        self._append_appearance_items(view_menu)
        menu_bar.Append(view_menu, "&View")

    # -- the &Window menu --------------------------------------------------- #

    def install_cast_window_menu(self, menu_bar: wx.MenuBar) -> None:
        """Append &Window and register the main window in it.

        The one keyboard route between Cast's windows that does not involve
        Alt+Tab and guessing which of several identically-titled windows is
        which. Rebuilt just-in-time each time the menu opens, because windows
        come and go and a stale list is worse than none.

        Called near the end of ``_build_menu_bar``, after &Quillins and before
        &Help, so the bar's tail matches Radio's and Weather's.
        """
        windows = getattr(self, "_windows", None)
        if windows is None:
            return
        windows.install(self.frame, menu_bar)
        # The main window is a peer like any other, and it is the one Ctrl+1
        # should reach. focus= is what a return-to-this-window lands on: the
        # library tree, which is where Cast puts focus at launch, because landing
        # somewhere arbitrary would be worse than landing somewhere familiar.
        windows.register(self.frame, "QUILL Cast", focus=lambda: self._focus_cast_initial_control())

    def _focus_cast_initial_control(self) -> None:
        """Where focus lands when Cast's own window is returned to.

        Also what the status bar falls back to on Escape, which is why it exists
        as a named method rather than a lambda over the tree: every other app in
        the family has a ``_focus_initial_control`` and shared code looks for one.
        """
        tree = getattr(self, "_shows_tree", None)
        if tree is None:
            return
        try:
            tree.SetFocus()
        except Exception:  # noqa: BLE001 - a window mid-teardown is not a crash
            pass

    def _focus_initial_control(self) -> None:
        """The family-standard name for the above, for shared code to call."""
        self._focus_cast_initial_control()

    # -- building a row only when the mode shows it ------------------------ #

    def _advanced_row(self, menu: wx.Menu, row: str, item_id: object, label: str) -> bool:
        """Append *label* only when the mode in force shows *row*.

        A one-line call at each site rather than an ``if`` around each one, because
        the menu bar is already the longest method in the app and seventeen extra
        branches would make it unreadable for a feature whose whole purpose is
        legibility.

        The caller's ``Bind`` is deliberately left in place at every site. Binding
        an id whose menu item was never created is harmless in wx, and leaving it is
        what keeps the promise menu_mode.py makes: in Simple mode the command still
        answers from the Command Palette and from Go To, so a hidden row is a
        shorter menu and never a removed feature.
        """
        if not self._cast_shows_row(row):
            return False
        menu.Append(item_id, label)
        return True

    # -- the spine -------------------------------------------------------- #

    #: Each place's View row: label, chord, opener (qc.md 4.7). Built from the
    #: places model so a place whose feature is off is absent here too.
    _PLACE_ROWS: tuple[tuple[str, str, str, str], ...] = (
        ("inbox", "&Inbox", "Ctrl+Shift+I", "open_cast_inbox"),
        ("new_episodes", "Ne&w Episodes", "Ctrl+Shift+W", "open_cast_new_episodes"),
        ("continue_listening", "Con&tinue Listening", "Ctrl+Shift+L", "open_continue_listening"),
        ("favorites", "Fa&vorites", "Ctrl+Shift+V", "open_cast_favorites"),
        ("playlists", "Pla&ylists", "Ctrl+Shift+Y", "open_cast_playlists"),
        ("personal_audio", "Personal &Audio", "Ctrl+Shift+U", "open_cast_personal_audio"),
        ("queue", "Play &Queue", "Ctrl+Shift+Q", "_open_play_queue"),
        ("recently_expired", "Recently E&xpired", "Ctrl+Shift+X", "open_cast_recently_expired"),
        ("downloads", "&Downloads", "Ctrl+D", "open_podcast_downloads"),
        ("notifications", "N&otifications", "Ctrl+Shift+N", "open_cast_notifications"),
        ("podcasts", "&Podcasts", "Ctrl+Shift+S", "open_cast_subscriptions"),
    )

    def _append_places(self, view_menu: wx.Menu) -> None:
        """Find, then the places in the listener's order, one key each (qc.md 4.3)."""
        from quill.core.podcasts import places as places_model

        find_id = wx.NewIdRef()
        view_menu.Append(find_id, "Fi&nd\tCtrl+F")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.focus_library_find(), id=find_id)
        self._keep_menu_ids(find_id)
        rows = {
            place_id: (label, accel, opener) for place_id, label, accel, opener in self._PLACE_ROWS
        }
        layout = places_model.decode(self._podcast_library.settings.places_layout)
        for place in places_model.visible(
            layout, enabled=self._cast_area_enabled, include_hidden=True
        ):
            label, accelerator, opener = rows[place.id]
            item_id = wx.NewIdRef()
            view_menu.Append(item_id, f"{label}\t{accelerator}")
            handler = getattr(self, opener)
            self.frame.Bind(wx.EVT_MENU, lambda _e, h=handler: h(), id=item_id)
            self._keep_menu_ids(item_id)
        places_id = wx.NewIdRef()
        view_menu.Append(places_id, "P&laces...\tCtrl+Shift+G")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_places_chooser(), id=places_id)
        self._keep_menu_ids(places_id)

    # -- what the library tree shows -------------------------------------- #
    # The chords were chosen against both halves of what Cast already claims:
    # APP_KEYMAPS["cast"] *and* the accelerator literals in podcasts_menu.py, since
    # a collision with a menu literal is exactly as silent as one with a binding --
    # wx binds one of the pair and the label keeps advertising the key for the other.
    # The first four chosen here all collided (Ctrl+Alt+Shift+B was app.backup, +Z
    # app.quiet_hours, +P app.recent_problems, +X app.export_setup). Cast has two
    # free letters left in the Ctrl+Alt+Shift space and nineteen in Ctrl+Shift, so
    # the everyday toggles live there and can be mnemonic -- H for Hide, O for
    # fOlder, B for Bar. Only the mode switch keeps a long chord, which is rule 9:
    # a once-a-year command gets *a* key, not a short one.

    #: View > Show: the one episode filter, applied to every list (qc.md 4.2).
    _SHOW_FILTERS: tuple[tuple[str, str], ...] = (
        ("all", "&All Episodes"),
        ("unplayed", "&Unheard Only"),
        ("in_progress", "&Started Only"),
        ("downloaded", "&Downloaded Only"),
        ("played", "&Played Only"),
    )
    #: View > Sort Episodes, the library's own sort modes in the listener's words.
    _EPISODE_SORTS: tuple[tuple[str, str], ...] = (
        ("date_newest", "&Newest First"),
        ("date_oldest", "&Oldest First"),
        ("title_az", "By &Title"),
        ("duration_shortest", "Shortest &First"),
        ("duration_longest", "&Longest First"),
    )

    def _append_show_and_sort(self, view_menu: wx.Menu) -> None:
        """Show > (the one filter) and Sort Episodes > (the one order)."""
        show_menu = wx.Menu()
        current = str(getattr(self._podcast_history, "episode_filter", "all") or "all")
        for mode, label in self._SHOW_FILTERS:
            mode_id = wx.NewIdRef()
            show_menu.AppendRadioItem(mode_id, label)
            if mode == current:
                show_menu.Check(mode_id, True)
            self.frame.Bind(wx.EVT_MENU, lambda _e, m=mode: self._set_episode_filter(m), id=mode_id)
            self._keep_menu_ids(mode_id)
        view_menu.AppendSubMenu(show_menu, "S&how")
        sort_menu = wx.Menu()
        current_sort = str(self._podcast_library.settings.episode_sort_mode)
        for mode, label in self._EPISODE_SORTS:
            mode_id = wx.NewIdRef()
            sort_menu.AppendRadioItem(mode_id, label)
            if mode == current_sort:
                sort_menu.Check(mode_id, True)
            self.frame.Bind(wx.EVT_MENU, lambda _e, m=mode: self._set_episode_sort(m), id=mode_id)
            self._keep_menu_ids(mode_id)
        view_menu.AppendSubMenu(sort_menu, "Sort &Episodes")

    def _set_episode_filter(self, mode: str) -> None:
        self._podcast_history.episode_filter = mode
        self._save_podcast_history()
        self._refresh_place(keep=True)
        label = dict(self._SHOW_FILTERS).get(mode, mode).replace("&", "")
        self._announce(f"Showing {label.lower()}.")

    def _set_episode_sort(self, mode: str) -> None:
        self._podcast_library.settings.episode_sort_mode = mode
        self._save_podcast_library()
        self._refresh_place(keep=True)
        label = dict(self._EPISODE_SORTS).get(mode, mode).replace("&", "")
        self._announce(f"Episodes sorted {label.lower()}.")

    def _append_library_view_items(self, view_menu: wx.Menu) -> None:
        """Show, Sort Episodes, Hide Caught-Up Podcasts (R1) and the Inbox's folder scope (R4)."""
        self._append_show_and_sort(view_menu)
        self._hide_caught_up_item_id = wx.NewIdRef()
        view_menu.AppendCheckItem(
            self._hide_caught_up_item_id, "Hide Caught-&Up Podcasts\tCtrl+Shift+H"
        )
        view_menu.Check(self._hide_caught_up_item_id, self._podcast_history.hide_caught_up)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self._toggle_hide_caught_up(), id=self._hide_caught_up_item_id
        )
        scope_id = wx.NewIdRef()
        self._area_row(view_menu, "inbox", scope_id, "Inbox &Folder...\tCtrl+Shift+O")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.choose_inbox_folder_scope(), id=scope_id)
        # Every layout and order for the library and the Inbox in one window
        # whose choices take effect as they are made (Jeff, 2026-10-03).
        arrange_id = wx.NewIdRef()
        view_menu.Append(arrange_id, "&Rearrange Library and Inbox...\tCtrl+Shift+R")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_library_view(), id=arrange_id)
        self._keep_menu_ids(self._hide_caught_up_item_id, scope_id, arrange_id)

    def open_library_view(self) -> None:
        """View > Rearrange Library and Inbox... (Ctrl+Shift+R)."""
        from quill.ui.podcasts.library_view_dialog import open_library_view

        open_library_view(self)

    # -- how much of Cast, and what it looks like ------------------------- #

    def _append_appearance_items(self, view_menu: wx.Menu) -> None:
        self._status_bar_item_id = wx.NewIdRef()
        view_menu.AppendCheckItem(self._status_bar_item_id, "Show Status &Bar\tCtrl+Shift+B")
        view_menu.Check(self._status_bar_item_id, self._podcast_history.show_status_bar)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self._toggle_cast_status_bar(), id=self._status_bar_item_id
        )
        # Present in both modes, always, and it says which mode is in force: the
        # one row a mode must never hide is the row that changes the mode.
        self._advanced_item_id = wx.NewIdRef()
        view_menu.AppendCheckItem(self._advanced_item_id, "Advanced Feature&s\tCtrl+Alt+Shift+G")
        view_menu.Check(
            self._advanced_item_id,
            menu_mode.normalize_mode(self._podcast_history.menu_mode) == menu_mode.ADVANCED,
        )
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self._toggle_advanced_menus(), id=self._advanced_item_id
        )
        features_id = wx.NewIdRef()
        # Radio's chord for the same command (family rule 2), and the menu-bar
        # gate's rule that every row shows a keyboard route.
        view_menu.Append(features_id, "&Customize Features...	Ctrl+Alt+C")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._open_cast_app_features(), id=features_id)
        self._keep_menu_ids(self._status_bar_item_id, self._advanced_item_id, features_id)

    # -- the toggles ------------------------------------------------------- #

    def _cast_menu_mode(self) -> str:
        """The mode in force. One reader, so the menu and the builder agree."""
        return menu_mode.normalize_mode(getattr(self._podcast_history, "menu_mode", ""))

    def _cast_shows_row(self, row: str) -> bool:
        """Whether an advanced row is built. What ``_build_menu_bar`` asks."""
        return menu_mode.shows(self._cast_menu_mode(), row)

    def _toggle_advanced_menus(self) -> None:
        """Switch the mode, save it, and rebuild the bar so it takes effect now.

        Now rather than at the next launch, which is what Customize Features has
        to say: a mode is a thing somebody is trying, and "restart to see it"
        turns an experiment into a decision.
        """
        current = self._cast_menu_mode()
        wanted = menu_mode.SIMPLE if current == menu_mode.ADVANCED else menu_mode.ADVANCED
        self._podcast_history.menu_mode = wanted
        self._save_podcast_history()
        self._build_menu_bar()
        self._announce(menu_mode.switch_announcement(wanted))

    def _toggle_hide_caught_up(self) -> None:
        """Hide or show podcasts with nothing unheard (R1).

        Announced with the count, because the whole effect of this switch is rows
        that are no longer there -- and a listener who cannot see the tree has no
        way to tell "hidden" from "I have no podcasts".
        """
        history = self._podcast_history
        history.hide_caught_up = not history.hide_caught_up
        self._save_podcast_history()
        self._reload_library_tree()
        if history.hide_caught_up:
            hidden = sum(
                1
                for show in self._podcast_library.shows
                if not any(not episode.played for episode in show.episodes)
            )
            self._announce(
                f"Caught-up podcasts hidden. {hidden} hidden; turn them back on in the View menu."
            )
        else:
            self._announce("All podcasts shown.")

    def _toggle_cast_status_bar(self) -> None:
        """Show or hide the status bar, and say where the keyboard route is.

        F6 is named in the announcement rather than only in the user guide: a bar
        that is now visible and cannot be reached is worse than no bar, and a
        listener who just switched it on is exactly the person who needs the key.
        """
        history = self._podcast_history
        history.show_status_bar = not history.show_status_bar
        self._save_podcast_history()
        bar = getattr(self, "_cast_status_bar", None)
        if bar is not None:
            bar.set_visible(history.show_status_bar)
        if history.show_status_bar:
            self._announce("Status bar shown. Press F6 to move into it.")
        else:
            self._announce("Status bar hidden.")

    def _open_cast_app_features(self) -> None:
        """View > Customize Features...: switch whole areas of Cast on or off.

        The shared dialog every other app in the family uses, so the surface a
        listener already knows from Radio behaves identically here.
        """
        from quill.core.app_features import save_app_features
        from quill.core.paths import app_data_dir
        from quill.ui.app_features_dialog import AppFeaturesDialog

        dialog = AppFeaturesDialog(
            self.frame,
            app_title="QUILL Cast",
            areas=CAST_AREAS,
            settings=self._cast_app_features(),
            profiles=cast_features.PROFILES,
            announce_cb=self._announce,
        )
        if dialog.show():
            save_app_features(app_data_dir(), self._cast_app_features())
            # Now, not at the next launch: the menus, the places and Go To follow
            # the switches at once; the status bar's cells follow at the next
            # launch, and the sentence says so.
            self._build_menu_bar()
            self._rebuild_places()
            shown = [place.id for place in self._visible_places()]
            if self._current_place not in shown and shown:
                self.show_place(shown[0], focus=False)
            self._announce(
                "Feature settings saved. The menus and places follow them now; the "
                "status bar follows the next time you open QUILL Cast."
            )

    def _cast_app_features(self):  # noqa: ANN201 - AppFeatureSettings
        """Cast's area switches, loaded once and kept on the frame."""
        settings = getattr(self, "_app_features", None)
        if settings is None:
            from quill.core.app_features import load_app_features
            from quill.core.paths import app_data_dir

            settings = load_app_features(app_data_dir(), "cast")
            self._app_features = settings
        return settings

    def _cast_area_enabled(self, area_id: str) -> bool:
        """Whether an area survives the listener's switches. Menus ask this."""
        return area_id not in self._cast_app_features().disabled
