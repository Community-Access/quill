"""The Recently Expired view's actions (QUILL Cast 1.1.0).

Queue Expiration lifts a queued episode that has waited too long out of the
Play Queue and into Recently Expired, where it stays restorable for seven
days. This mixin is that view's context menu and its three handlers.

The wording carries the whole safety story, so it lives here with the code:

* **Restore** is first and never confirmed. Putting something back is not
  destructive, and the entire point of the seven-day hold is that restoring
  is easy.
* **Forget** is confirmed, defaults to No (A-7), and says plainly that it
  leaves the downloaded file alone. Removing a local copy is Remove
  Downloaded Copy's job, on the episode itself, where the wording says so.
* Nothing here deletes an episode. Expiring is a *queue* action; the episode
  keeps its place in its show, unplayed, throughout.

Mixed into ``PodcastManagerDialog`` via ``ManagerPhase4Mixin``.
"""

from __future__ import annotations


class ManagerExpiredMixin:
    """Restore / Restore All / Forget on the Recently Expired node."""

    def _append_recently_expired_items(self, menu: object) -> None:
        """Restore / Restore All / Forget on the Recently Expired node.

        Restore is the point of the whole feature, so it is first and it is
        never confirmed -- putting something back is not destructive. Forget
        is confirmed and defaults to No (A-7), and its wording says plainly
        that it leaves the downloaded file alone: removing a local copy is
        Remove Downloaded Copy's job, on the episode itself.
        """
        from quill.core.podcasts import expiration

        wx = self._wx
        pairs = self._virtual_pairs("recently_expired")
        selected_index = self._episodes.GetFirstSelected()
        selected = pairs[selected_index] if 0 <= selected_index < len(pairs) else None

        restore_item = menu.Append(wx.ID_ANY, "&Restore to the Play Queue")
        restore_item.Enable(selected is not None)
        menu.Bind(wx.EVT_MENU, lambda _e: self._on_restore_expired(selected), restore_item)

        restore_all_item = menu.Append(wx.ID_ANY, "Restore &All")
        restore_all_item.Enable(bool(pairs))
        menu.Bind(wx.EVT_MENU, lambda _e: self._on_restore_all_expired(), restore_all_item)

        forget_item = menu.Append(wx.ID_ANY, "&Forget This One")
        forget_item.SetHelp(
            "Stop offering this episode back. Its downloaded file is left alone; "
            f"it would have been removed automatically after "
            f"{expiration.RECENTLY_EXPIRED_HOLD_DAYS} days anyway."
        )
        forget_item.Enable(selected is not None)
        menu.Bind(wx.EVT_MENU, lambda _e: self._on_forget_expired(selected), forget_item)

    def _on_restore_expired(self, pair: object) -> None:
        from quill.core.podcasts.expiration import restore_expired

        if pair is None:
            return
        show, episode = pair
        if restore_expired(self._library, show.id, episode.guid):
            self._on_library_changed()
            self.refresh_tree()
            self._maybe_fill_virtual_selection()
            self._announce(f"Restored {episode.title} to the end of the Play Queue")

    def _on_restore_all_expired(self) -> None:
        from quill.core.podcasts.expiration import restore_all_expired

        restored = restore_all_expired(self._library)
        if not restored:
            return
        self._on_library_changed()
        self.refresh_tree()
        self._maybe_fill_virtual_selection()
        self._announce(f"Restored {restored} episode(s) to the Play Queue")

    def _on_forget_expired(self, pair: object) -> None:
        from quill.core.podcasts.expiration import forget_expired
        from quill.ui.dialog_contract import show_message_box

        if pair is None:
            return
        wx = self._wx
        show, episode = pair
        answer = show_message_box(
            f'Forget "{episode.title}"? It stops being offered back to you. The episode '
            "stays in your library and its downloaded file is not deleted.",
            "Forget Expired Episode",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
            self.dialog,
            announce=self._announce,
        )
        if answer != wx.YES:
            return
        if forget_expired(self._library, show.id, episode.guid):
            self._on_library_changed()
            self.refresh_tree()
            self._maybe_fill_virtual_selection()
            self._announce(f"Forgot {episode.title}")
