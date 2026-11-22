"""Scribe for Documents in QUILL Cast: an episode's linked documents (PRD 8.6).

**Episode > Convert Linked Document with Scribe for Documents...** looks in
the selected episode's show notes for links that point straight at a file
Scribe takes (PDF, Word, EPUB and the rest of the 23 types), and sends the
one the person chooses by its address (URL input, direct file links only):

* none: one sentence, "This episode's show notes link no documents Scribe
  for Documents can convert.";
* one: straight to the shared Convert dialog, which names the link;
* several: "Choose a Linked Document" first (:mod:`quill.ui.scribe_link_choice`).

The result opens in QUILL, or QUILL Lite when only Lite is installed, from
Open Result or Next Steps -- never by itself, so the result sentence is not
cut off by the editor coming to the front. The Podcasts menu's Scribe for
Documents submenu holds the family's shared rows.

The Episode and Podcasts menus have spent their access letters (as the
WordPress row says), so the row has its key and no letter.
"""

from __future__ import annotations

from typing import Any

from quill.ui.scribe_app_host import ENTRY_KEY, AppScribeMixin, append_scribe_submenu

__all__ = ["CastScribeMixin"]

_TITLE = "QUILL Cast"
ROW_LABEL = "Convert Linked Document with Scribe for Documents..."


def _before_tray(menu: Any) -> int | None:
    """The Podcasts menu: above the separator before Send to Tray and Exit."""
    items = list(menu.GetMenuItems())
    for index, item in enumerate(items):
        if item.GetItemLabelText().startswith("Send to Tra"):
            return index - 1 if index and items[index - 1].IsSeparator() else index
    return None


class CastScribeMixin(AppScribeMixin):
    """The Episode row and the Podcasts menu's Scribe for Documents submenu."""

    scribe_app_name = _TITLE

    def _append_scribe_rows(self, episode_menu: Any, podcasts_menu: Any) -> None:
        import wx

        row_id = wx.NewIdRef()
        episode_menu.Append(row_id, f"{ROW_LABEL}\t{ENTRY_KEY}")
        self.frame.Bind(  # type: ignore[attr-defined]
            wx.EVT_MENU, lambda _e: self.scribe_convert_linked_episode(), id=row_id
        )
        ids = append_scribe_submenu(
            self,
            podcasts_menu,
            wx,
            title="Scribe for Documents",
            position=_before_tray(podcasts_menu),
        )
        self._keep_menu_ids(row_id, *ids)  # type: ignore[attr-defined]

    def scribe_convert_linked_episode(self) -> None:
        from quill.core.scribe.links import documents_in_html
        from quill.ui.scribe_link_choice import convert_linked

        selected = self._selected_episode()  # type: ignore[attr-defined]
        if selected is None:
            self._announce("Choose an episode first.")  # type: ignore[attr-defined]
            return
        _show, episode = selected
        documents = documents_in_html(str(getattr(episode, "description", "") or ""))
        convert_linked(
            self._scribe(),
            documents,
            parent=self._scribe_frame(),
            where="this episode's show notes",
            subject="this episode's show notes",
            verb="link",
            say=self._announce,  # type: ignore[attr-defined]
            modal=self._scribe_modal,
        )
