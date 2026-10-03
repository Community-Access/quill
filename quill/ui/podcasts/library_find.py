"""Find in library: one box above the tree, results one arrow apart (qc.md 4.2, P10).

The interim of the plan's Find, before Phase 2's one-window host exists. Typing
in the box flattens the library tree into matches -- podcasts, episodes and your
own episode notes -- each row saying what it is and where it lives:

    Thursday's episode -- an episode of The Daily
    The Daily -- a podcast (3 unheard)
    Note on Thursday's episode: mentioned the bus boycott

Matches are rows of the same tree, tagged exactly as the library tags them, so
Enter plays, Shift+F10 opens the same menu, and the transport button names what
is selected -- nothing about a result needs learning. The count ("14 matches for
bristol") sits on the line under the box and is spoken once, when typing pauses,
never per keystroke. Escape in the box, or emptying it, puts the library back and
the cursor where it was.

Two deliberate limits until F-09's incremental index exists, both stated in the
user guide: transcripts are not searched here (reading every cached transcript
on every pause is the scan F-09 exists to replace -- Search Everywhere still
does it on demand), and at most :data:`MAX_ROWS` rows are shown, with a last row
saying how many more there are.

Kept out of ``quill/apps/podcasts.py``, which is at its GATE-11 budget; the main
panel builds the box and these functions do everything after that.
"""

from __future__ import annotations

from typing import Any

__all__ = ["MAX_ROWS", "PAUSE_MS", "find_rows", "match_count_sentence"]

#: How long typing must pause before the tree is rebuilt and the count spoken.
PAUSE_MS = 350

#: Rows shown before a "more" row. The library tree's own cap for an opened view.
MAX_ROWS = 200


def match_count_sentence(count: int, query: str) -> str:
    """ "14 matches for bristol", or the way out when there are none."""
    query = query.strip()
    if count == 0:
        return f"No matches for {query}. Escape returns to your library."
    noun = "match" if count == 1 else "matches"
    return f"{count} {noun} for {query}"


def find_rows(library: Any, query: str, *, notes: list | None = None) -> list[tuple[str, tuple]]:
    """``(label, tree data)`` for every match, podcasts first, then episodes,
    then notes -- the order the plan ranks them, newest first within episodes.

    The tree data is exactly what the library tree uses, so a result row behaves
    like the row it stands for.
    """
    from quill.core.podcasts.filtering import search_everywhere
    from quill.core.podcasts.sorting import unheard_count

    found = search_everywhere(library, query, episode_notes=notes)
    shows = [r for r in found if r.kind == "show"]
    episodes = [r for r in found if r.kind == "episode"]
    episodes.sort(key=lambda r: (r.episode.published or "", r.episode.title or ""), reverse=True)
    noted = [r for r in found if r.kind == "note"]
    rows: list[tuple[str, tuple]] = []
    for result in shows:
        count = unheard_count(result.show)
        extra = f" ({count} unheard)" if count else ""
        rows.append((f"{result.show.title} -- a podcast{extra}", ("show", result.show.id)))
    for result in episodes:
        rows.append((
            f"{result.episode.title} -- an episode of {result.show.title}",
            ("episode", f"{result.show.id}\x00{result.episode.guid}"),
        ))
    for result in noted:
        rows.append((
            f"Note on {result.episode.title}: {result.note_preview}",
            ("episode", f"{result.show.id}\x00{result.episode.guid}"),
        ))
    return rows


class CastLibraryFindMixin:
    """The box's behaviour. On ``PodcastsAppFrame`` through the main panel."""

    def _library_find_query(self) -> str:
        box = getattr(self, "_find_box", None)
        if box is None:
            return ""
        try:
            return str(box.GetValue() or "").strip()
        except RuntimeError:
            return ""

    def _library_find_active(self) -> bool:
        return bool(self._library_find_query())

    def _on_find_text(self, _event: Any = None) -> None:
        """Typing restarts the pause; the tree is rebuilt when it ends."""
        import wx

        timer = getattr(self, "_find_timer", None)
        if timer is not None:
            try:
                timer.Stop()
            except Exception:  # noqa: BLE001
                pass
        if not self._library_find_query():
            self._end_library_find(announce=False)
            return
        self._find_timer = wx.CallLater(PAUSE_MS, self._run_library_find)

    def _run_library_find(self) -> None:
        """Flatten the tree into matches and say the count, once."""
        query = self._library_find_query()
        if not query:
            return
        if getattr(self, "_find_return_key", None) is None:
            # Where to put the cursor back when Find ends: the row it was on.
            selected = None
            try:
                selected = self._selected_tree_data()
            except Exception:  # noqa: BLE001
                pass
            self._find_return_key = selected or ("", "")
            self._find_return_place = getattr(self, "_current_place", "")
        pane = getattr(self, "_content", None)
        if pane is not None:
            pane.show(pane.TREE)
            pane.set_heading("Matches")
        said = self._refresh_library_find()
        self._announce(said)

    def _refresh_library_find(self) -> str:
        """Rebuild the matches for the current query. Returns the count sentence.

        Also what ``_reload_library_tree`` calls while Find is active, so a
        refresh or a save during a search updates the results rather than
        throwing them away.
        """
        from quill.core.podcasts.episode_notes import load_episode_notes

        query = self._library_find_query()
        try:
            notes = load_episode_notes()
        except Exception:  # noqa: BLE001 - unreadable notes cost the notes, not the search
            notes = []
        rows = find_rows(self._podcast_library, query, notes=notes)
        tree = self._shows_tree
        tree.DeleteAllItems()
        root = tree.AddRoot("Matches")
        first = None
        for label, data in rows[:MAX_ROWS]:
            item = tree.AppendItem(root, label)
            tree.SetItemData(item, data)
            first = first or item
        hidden = len(rows) - MAX_ROWS
        if hidden > 0:
            more = tree.AppendItem(root, f"{hidden} more -- type more of the name to narrow it")
            tree.SetItemData(more, ("more", ""))
        if first is not None:
            tree.SelectItem(first)
        said = match_count_sentence(len(rows), query)
        status = getattr(self, "_find_status", None)
        if status is not None:
            try:
                status.SetLabel(said)
            except RuntimeError:
                pass
        return said

    def _end_library_find(self, *, announce: bool = True) -> None:
        """Back to the library, the cursor on the row it left."""
        timer = getattr(self, "_find_timer", None)
        if timer is not None:
            try:
                timer.Stop()
            except Exception:  # noqa: BLE001
                pass
        key = getattr(self, "_find_return_key", None)
        self._find_return_key = None
        status = getattr(self, "_find_status", None)
        if status is not None:
            try:
                status.SetLabel("")
            except RuntimeError:
                pass
        place = getattr(self, "_find_return_place", "")
        if place and callable(getattr(self, "show_place", None)):
            self.show_place(place, focus=False, keep=key if key and key[0] else None)
        else:
            self._reload_library_tree(keep_key=key if key and key[0] else None)
        if announce:
            self._announce("Back to your library.")

    def _on_find_key(self, event: Any) -> None:
        """Escape clears the box and returns; Down moves into the matches."""
        import wx

        code = event.GetKeyCode()
        if code == wx.WXK_ESCAPE and self._library_find_query():
            self._find_box.ChangeValue("")
            self._end_library_find()
            self._shows_tree.SetFocus()
            return
        if code == wx.WXK_DOWN and self._library_find_active():
            self._shows_tree.SetFocus()
            return
        if code == wx.WXK_ESCAPE and not self._library_find_query():
            pane = getattr(self, "_content", None)
            if pane is not None:
                pane.focus()
                return
        event.Skip()

    def focus_library_find(self) -> None:
        """Ctrl+F and View > Find in Library: into the box, its text selected."""
        box = getattr(self, "_find_box", None)
        if box is None:
            return
        box.SetFocus()
        box.SelectAll()
