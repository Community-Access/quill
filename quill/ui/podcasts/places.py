"""The places a listener moves between, each reachable by one key.

Earshot's navigation is a flat list of places -- Inbox, Queue, Subscriptions,
Library, Downloads, Stats, Settings (its PRD, 5.2). Cast had every one of those and
no list of them: they were scattered across three menus and a tree, and two of them
(the Inbox and Personal Audio) had no menu row at all, so the only way in was to
know where to arrow. That is a fine arrangement for somebody who built the app and
a maze for everybody else, and it is the specific thing behind "the UI is a bit
confusing to understand" (Jeff, 2026-09-30).

So the &View menu carries the spine, and these are its handlers.

**Going to a place means landing on it, with focus.** A menu row that redraws a
tree and leaves focus on the menu bar has not taken anybody anywhere -- worse, it
looks like nothing happened, which is the report that started this. Each of these
selects the node *and* moves focus into the tree, so the screen reader reads the
place you asked for as the thing that just got focus. That is also why none of them
announces the place by name: the focus move says it, and saying it too is GATE-13's
textbook duplication.

**A place that is empty says how to fill it**, and says it once, on arrival. An
empty Inbox and a missing Personal Audio are the two most likely first encounters
for a new listener, and "empty" on its own leaves them nowhere.

Kept out of ``quill/apps/podcasts.py``, which is exactly on its GATE-11 budget, and
out of ``podcasts_view_menu.py``, which builds the menu rather than answering them.
"""

from __future__ import annotations

from typing import Any

__all__ = ["CastPlacesMixin"]


class CastPlacesMixin:
    """The View menu's place handlers. Mixed into ``PodcastsAppFrame``."""

    # -- the tree, and landing in it --------------------------------------- #

    def _go_to_tree_node(self, key: tuple[str, str]) -> bool:
        """Select the tree node tagged *key* and put focus on the tree.

        ``_reload_library_tree`` already knows how to land on a node -- it takes a
        ``keep_key`` so a redraw does not lose the listener's place -- so going
        somewhere is the same operation as staying somewhere, which is why there is
        no second selection path here to disagree with it.

        Returns whether the tree exists to be focused; a caller that gets ``False``
        is running without the main window and should say so rather than pretend.
        """
        tree = getattr(self, "_shows_tree", None)
        if tree is None:
            return False
        self._reload_library_tree(keep_key=key)
        try:
            tree.SetFocus()
        except Exception:  # noqa: BLE001 - a window mid-teardown is not a crash
            return False
        return True

    # -- Inbox ------------------------------------------------------------- #

    def open_cast_inbox(self) -> None:
        """Go to the Inbox, and say what to do about it when it is empty.

        The empty sentence comes from ``inbox_scope`` rather than being written
        here, because it is the same sentence the Manager's Inbox shows and there
        must not be two versions of it -- and because only that module knows
        whether the Inbox is empty or merely *filtered* empty, which want
        different answers.
        """
        if not self._go_to_tree_node(("view", "inbox")):
            self._announce("The Inbox is in the main window, which is not open.")
            return
        from quill.core.podcasts.inbox_scope import empty_state

        said = empty_state(
            self._podcast_library,
            getattr(self._podcast_library.settings, "inbox_folder_scope", None),
        )
        if said:
            self._announce(said)

    def choose_inbox_folder_scope(self) -> None:
        """Narrow the Inbox to one library folder, or widen it again (R4).

        A chooser rather than a submenu of every folder: a library with forty
        folders would put forty rows in the View menu, and only the handful that
        have anything in the Inbox are worth offering -- which is what
        ``folder_ids_with_inbox`` answers.

        The current scope is the pre-selected row, so the dialog opens saying what
        is in force. Somebody who opens it to find out, and presses Escape, has
        their answer and has changed nothing.
        """
        import wx

        from quill.core.podcasts import inbox_scope

        library = self._podcast_library
        current = getattr(library.settings, "inbox_folder_scope", inbox_scope.ALL)
        scopes: list[tuple[str, str]] = [
            (inbox_scope.ALL, "All podcasts"),
            (inbox_scope.UNFILED, "Not in a folder"),
        ]
        for folder_id in inbox_scope.folder_ids_with_inbox(library):
            scopes.append((folder_id, inbox_scope.scope_label(library, folder_id)))
        labels = [
            f"{label} ({len(inbox_scope.inbox_pairs_in_library_folder(library, scope))})"
            for scope, label in scopes
        ]
        selected = next((i for i, (scope, _l) in enumerate(scopes) if scope == current), 0)

        dialog = wx.SingleChoiceDialog(
            self.frame,
            "Show the Inbox for which podcasts?\n\n"
            "This only changes what the Inbox lists. Nothing is removed from it, "
            "and the count beside each choice is how many episodes it would show.",
            "Inbox Folder",
            labels,
        )
        try:
            dialog.SetSelection(selected)
            from quill.ui.dialog_contract import show_modal_dialog

            if show_modal_dialog(dialog, "Inbox Folder", announce=self._announce) != wx.ID_OK:
                return
            chosen = scopes[dialog.GetSelection()][0]
        finally:
            dialog.Destroy()
        library.settings.inbox_folder_scope = chosen
        self._save_podcast_library()
        self._reload_library_tree(keep_key=("view", "inbox"))
        count = len(inbox_scope.inbox_pairs_in_library_folder(library, chosen))
        self._announce(
            f"Inbox showing {inbox_scope.scope_label(library, chosen)}: "
            f"{count} episode{'' if count == 1 else 's'}."
        )

    # -- Podcasts, and Personal Audio ------------------------------------- #

    def open_cast_subscriptions(self) -> None:
        """Go to the library tree itself -- the list of everything you follow."""
        if not self._go_to_tree_node(("view", "favorites")):
            self._announce("Your podcasts are in the main window, which is not open.")
            return
        if not self._podcast_library.shows:
            self._announce(
                "You do not follow any podcasts yet. Add Podcast, in the Podcasts "
                "menu, searches the directories by name."
            )

    def open_cast_personal_audio(self) -> None:
        """Go to your own recordings and audiobooks (R8).

        Personal Audio is a local show rather than a pinned view, so there is
        nothing to land on until something has been imported -- which is exactly
        when the empty sentence matters, since a menu row that silently does
        nothing is indistinguishable from a broken one.
        """
        from quill.core.podcasts import personal_audio

        local = next((show for show in self._podcast_library.shows if show.is_local), None)
        if local is None:
            self._announce(personal_audio.empty_state(self._podcast_library))
            return
        if not self._go_to_tree_node(("show", local.id)):
            self._announce("Personal Audio is in the main window, which is not open.")

    # -- what the tree leaves out ----------------------------------------- #

    def _visible_library_shows(self) -> list[Any]:
        """The shows the tree should draw, honouring Hide Caught-Up Podcasts (R1).

        A show with nothing unheard is hidden; a show with **no episodes at all**
        is not, and that exception is the whole of the care this needs. A podcast
        you have just started following has no episodes until the first refresh
        finishes, and hiding it would make following something look like it had
        failed.
        """
        shows = list(self._podcast_library.shows)
        if not getattr(self._podcast_history, "hide_caught_up", False):
            return shows
        kept = []
        for show in shows:
            if not show.episodes:
                kept.append(show)
                continue
            if any(not episode.played for episode in show.episodes):
                kept.append(show)
        return kept

    def _caught_up_empty_state(self) -> str:
        """What the tree says when the filter has hidden everything (R1).

        Names the switch and where it lives, because a tree that is empty and says
        only "no podcasts" is how somebody concludes their library is gone -- and
        the listener who turned this on last week is not the listener who remembers
        turning it on.
        """
        if not getattr(self._podcast_history, "hide_caught_up", False):
            return ""
        if self._visible_library_shows() or not self._podcast_library.shows:
            return ""
        return "All caught up -- turn off Hide Caught-Up Podcasts in the View menu"

    # -- where a launch lands ---------------------------------------------- #

    def _select_default_launch_view(self) -> None:
        """Land on the place the listener chose, not always the tree top.

        Somebody whose routine is "open it and see what is new" should not have to
        arrow there every single time. Moved here from ``podcasts.py`` under
        GATE-11, and it belongs here anyway: it is the same question the View
        menu's rows answer, asked once at startup.
        """
        view_id = self._podcast_library.settings.default_launch_view
        if not view_id:
            # No stated preference: land on what is new. The Inbox if anything
            # is waiting, else Continue Listening if anything is half-heard, else
            # leave the cursor where the tree puts it. Earshot's answer, and the
            # one a listener would give if asked why they opened the app.
            from quill.core.podcasts.virtual_views import virtual_view_pairs

            for candidate in ("inbox", "continue_listening"):
                if virtual_view_pairs(self._podcast_library, candidate):
                    view_id = candidate
                    break
            else:
                return
        self._reload_library_tree(keep_key=("view", view_id))

    # -- what the transport button would do -------------------------------- #

    def _transport_button_face(self, intent: str):  # noqa: ANN202 - ButtonFace
        """The Play/Pause/Resume button's label and sentence, as one reading.

        "Play what?" was the report (Jeff, 2026-09-30): the button announced the
        bare verb, so somebody hearing it had been told nothing about what pressing
        it would start, whether it would resume a place, or -- in the one state
        where it does nothing at all -- that it would do nothing. The object goes
        in the *label* -- an accessible name on a wxMSW button is never read.

        Lives here rather than in ``podcasts.py`` because answering it needs the
        library cursor, which is this mixin's subject, and because that module is
        exactly on its GATE-11 budget. The words themselves are built in
        ``core/podcasts/transport_intent.py``, wx-free, so every phrase it can
        produce is under test.
        """
        from quill.core.podcasts import transport_intent

        state = self._podcast_controller.state
        show = self._podcast_library.find_show(state.show_id) if state.show_id else None
        episode = (
            show.find_episode(state.episode_guid)
            if show is not None and state.episode_guid
            else None
        )
        selection, playable = self._selected_playable()
        return transport_intent.button_face(
            intent,
            show_title=str(getattr(show, "title", "") or ""),
            episode_title=str(getattr(episode, "title", "") or ""),
            selection=selection,
            can_play_selection=playable,
        )

    def _selected_playable(self) -> tuple[str, bool]:
        """``(what the cursor is on, whether pressing Play would start it)``.

        A folder, a pinned view and a show with no episodes are all selections that
        cannot be played, and a button announcing that it would play "News" when
        News is a folder has lied about the one thing it was asked. So the flag is
        computed rather than assumed from the fact that something is selected.
        """
        selected = self._selected_tree_data()
        if selected is None:
            return ("", False)
        kind, value = selected
        if kind == "show":
            show = self._podcast_library.find_show(value)
            if show is None:
                return ("", False)
            return (show.title, bool(show.episodes))
        if kind == "episode":
            show_id, _, guid = value.partition("\x00")
            show = self._podcast_library.find_show(show_id)
            episode = show.find_episode(guid) if show is not None else None
            if episode is None:
                return ("", False)
            return (f"{episode.title}, from {show.title}", True)
        # A pinned view or a folder: named, so the listener hears where they are,
        # and not playable, so the sentence says what to do instead.
        if kind == "folder":
            folder = self._podcast_library.find_folder(value)
            return ((folder.name if folder is not None else ""), False)
        return ("", False)

    # -- Feed Check --------------------------------------------------------- #

    def open_cast_feed_check(self) -> None:
        """Podcasts > Feed Check...: which feeds are healthy (ear.md R2).

        Here with the other places because that is what it is -- somewhere you go
        to find something out, rather than something you do to a row. Opening it
        checks nothing; the report is bookkeeping Cast already keeps.
        """
        from quill.ui.podcasts.feed_check_dialog import open_feed_check

        open_feed_check(self)

    # -- the button row follows the selection ------------------------------ #

    def _refresh_selection_buttons(self) -> None:
        """Re-describe the buttons that act on the library cursor.

        Called on every selection change, because a button that names its object
        is only honest while the object is current. Cheap: two labels and one
        enable, no I/O. The object goes in the *label*: an accessible name on a
        wxMSW button is never read (qc.md 6b, item 1).
        """
        try:
            self._refresh_transport_controls()
        except Exception:  # noqa: BLE001 - a redraw must never take the tree down
            pass
        button = getattr(self, "_unfollow_btn", None)
        if button is None:
            return
        from quill.core.transport_button import object_label

        show = self._unfollow_target()
        label = object_label("&Unfollow", str(getattr(show, "title", "") or ""))
        if button.GetLabel() != label:
            button.SetLabel(label)
        button.Enable(show is not None)

    def _unfollow_target(self):  # noqa: ANN202 - PodcastShow | None
        """The podcast Unfollow would act on: the selected show, or the selected
        episode's show (qc.md 4.5). A folder or a view is nothing to unfollow."""
        show = self._selected_show()
        if show is not None:
            return show
        pair = self._selected_episode()
        return pair[0] if pair is not None else None

    def _on_unfollow_button(self) -> None:
        """Stop following the selected podcast, through the shared undoable prompt."""
        show = self._unfollow_target()
        if show is None:
            self._announce("Select a podcast in the library first.")
            return
        from quill.ui.podcasts.show_actions import unsubscribe_show_prompt

        def changed() -> None:
            self._save_podcast_library()
            self._reload_library_tree()
            self._refresh_selection_buttons()

        unsubscribe_show_prompt(
            self.frame, self._podcast_library, show, announce=self._announce, on_change=changed
        )

    # -- what Play means on the cursor --------------------------------------- #

    def _play_selection_or_say_why(self) -> None:
        """Play whatever the library cursor is on, or say what would work.

        A podcast plays its next episode; an episode plays itself; a view plays
        its newest unstarted episode (Continue Listening: its most recent). And
        when nothing under the cursor can play, the sentence is the long form of
        the button's own label, so the refusal and the description never differ.
        """
        from quill.core.podcasts import transport_intent
        from quill.ui.podcasts import library_tree

        selected = self._selected_tree_data()
        kind, value = selected if selected is not None else ("", "")
        if kind == "show":
            self._play_show_next_episode(value)
            return
        if kind == "episode":
            show_id, _, guid = value.partition("\x00")
            self._play_specific_episode(show_id, guid)
            return
        if kind == "view":
            pair = library_tree.first_playable_in_view(self._podcast_library, value)
            if pair is not None:
                self._play_episode_object(*pair)
                return
        self._announce(self._transport_button_face(transport_intent.STOPPED).spoken)
