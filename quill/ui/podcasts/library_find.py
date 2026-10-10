"""Find in library: one box above the tree, results one arrow apart (qc.md 4.2, P10).

Typing in the box flattens the library tree into matches -- podcasts, episodes,
your own episode notes, show notes and downloaded transcripts -- each row saying
what it is and where it lives:

    Thursday's episode -- an episode of The Daily
    The Daily -- a podcast (3 unheard)
    Note on Thursday's episode: mentioned the bus boycott
    Episode 411 -- an episode of The Daily, mentioned in its show notes
    "...mentioned the Bristol bus boycott..." -- in the transcript of Episode 412, The Daily

Matches are rows of the same tree, tagged exactly as the library tags them, so
Enter plays, Shift+F10 opens the same menu, and the transport button names what
is selected -- nothing about a result needs learning. The count ("14 matches for
bristol") sits on the line under the box and is spoken once, when typing pauses,
never per keystroke. Escape in the box, or emptying it, puts the library back and
the cursor where it was.

**The search is an index, not a scan (F-09).** The work happens in
``quill/core/podcasts/search_index.py`` and ``transcript_index.py``, on the task
manager: the UI thread copies the list of podcasts (one list, not the library),
hands it over, and later draws at most :data:`MAX_ROWS` rows from an immutable
answer. Every search carries a generation number; an answer for a query that
more typing has replaced -- or for a Find that Escape has ended -- is dropped on
arrival, and the job behind it is cancelled so it stops reading. With no task
manager (the tests' host) the same search runs inline, so the behaviour under
test and in the app is one code path.

Kept out of ``quill/apps/podcasts.py``, which is at its GATE-11 budget; the main
panel builds the box and these functions do everything after that.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any

logger = logging.getLogger(__name__)

__all__ = [
    "MAX_ROWS",
    "PAUSE_MS",
    "find_rows",
    "hit_label",
    "match_count_sentence",
    "rows_for_hits",
]

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
    return f"{count:,} {noun} for {query}"


def hit_label(hit: Any, unheard: int = 0) -> str:
    """What a result row says: the thing, then what it is and where it lives."""
    from quill.core.podcasts import search_index as si

    if hit.kind == si.KIND_SHOW:
        extra = f" ({unheard} unheard)" if unheard else ""
        return f"{hit.show_title} -- a podcast{extra}"
    if hit.kind == si.KIND_NOTE:
        return f"Note on {hit.episode_title}: {hit.snippet}"
    if hit.kind == si.KIND_SHOW_NOTES:
        return f"{hit.episode_title} -- an episode of {hit.show_title}, mentioned in its show notes"
    if hit.kind == si.KIND_TRANSCRIPT:
        return (
            f'"...{hit.snippet}..." -- in the transcript of {hit.episode_title}, {hit.show_title}'
        )
    return f"{hit.episode_title} -- an episode of {hit.show_title}"


def rows_for_hits(hits: Sequence[Any], library: Any) -> list[tuple[str, tuple]]:
    """``(label, tree data)`` per hit. The tree data is the library tree's own."""
    from quill.core.podcasts import search_index as si
    from quill.core.podcasts.sorting import unheard_count

    shows = {str(show.id): show for show in getattr(library, "shows", []) or []}
    rows: list[tuple[str, tuple]] = []
    for hit in hits:
        if hit.kind == si.KIND_SHOW:
            show = shows.get(hit.show_id)
            unheard = unheard_count(show) if show is not None else 0
            rows.append((hit_label(hit, unheard), ("show", hit.show_id)))
        else:
            rows.append((hit_label(hit), ("episode", f"{hit.show_id}\x00{hit.episode_guid}")))
    return rows


def find_rows(
    library: Any, query: str, *, notes: list | None = None, transcripts: Any = None
) -> list[tuple[str, tuple]]:
    """Every match as ``(label, tree data)``, in the plan's order, uncapped.

    The synchronous form of what the box does, for callers and tests that want
    the whole answer at once: podcasts, then episode titles newest first, then
    your notes, show notes and transcript text.
    """
    from quill.core.podcasts.search_index import LibrarySearchIndex, find_everything

    shows = list(getattr(library, "shows", []) or [])
    outcome = find_everything(
        LibrarySearchIndex(),
        shows,
        query,
        library=library,
        notes=notes or (),
        transcripts=transcripts,
        cap=10**9,
    )
    return rows_for_hits(outcome.hits, library)


def _load_notes() -> list:
    from quill.core.podcasts.episode_notes import load_episode_notes

    try:
        return list(load_episode_notes())
    except Exception:  # noqa: BLE001 - unreadable notes cost the notes, not the search
        return []


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

    def _library_search_indexes(self) -> tuple[Any, Any]:
        """The library and transcript indexes, made on first use and kept."""
        from quill.core.podcasts.search_index import LibrarySearchIndex
        from quill.core.podcasts.transcript_index import TranscriptSearchIndex

        index = getattr(self, "_library_search_index", None)
        if index is None:
            index = self._library_search_index = LibrarySearchIndex()
        transcripts = getattr(self, "_transcript_search_index", None)
        if transcripts is None:
            transcripts = self._transcript_search_index = TranscriptSearchIndex()
        return index, transcripts

    def podcast_search_index_changed(self, show_id: str | None = None) -> None:
        """A podcast's text changed under the index (a feed refresh merged it)."""
        index = getattr(self, "_library_search_index", None)
        if index is not None:
            index.invalidate(show_id)

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
        self._start_library_find(announce=True)

    def _refresh_library_find(self) -> str:
        """Search again for the current query, without speaking.

        What ``_reload_library_tree`` calls while Find is active, so a refresh or
        a save during a search updates the results rather than throwing them
        away. Returns the count sentence when the answer was immediate (no task
        manager), and "" when it will arrive from the worker.
        """
        return self._start_library_find(announce=False)

    def _cancel_library_find(self) -> None:
        """Retire the search in flight: its answer is dropped, its work stopped."""
        self._find_generation = getattr(self, "_find_generation", 0) + 1
        operation = getattr(self, "_find_operation", None)
        self._find_operation = None
        manager = getattr(self, "_task_manager", None)
        if operation and manager is not None:
            try:
                manager.cancel(operation)
            except Exception:  # noqa: BLE001 - a finished task has nothing to cancel
                pass

    def _start_library_find(self, *, announce: bool) -> str:
        query = self._library_find_query()
        if not query:
            return ""
        self._cancel_library_find()
        generation = self._find_generation
        from quill.core.podcasts.search_index import find_everything

        library = self._podcast_library
        # The one piece of work on the UI thread: a copy of the list of podcasts,
        # so the worker never iterates a list this thread may be changing.
        shows = list(getattr(library, "shows", []) or [])
        index, transcripts = self._library_search_indexes()

        def work(cancel: Any) -> Any:
            return find_everything(
                index,
                shows,
                query,
                library=library,
                notes=_load_notes(),
                transcripts=transcripts,
                cap=MAX_ROWS,
                cancel=cancel,
            )

        manager = getattr(self, "_task_manager", None)
        if manager is None:
            return self._apply_library_find(work(None), generation, announce=announce)
        task = manager.submit(
            "cast-library-find",
            lambda cancellation_token, **_kw: work(cancellation_token.is_cancelled),
            on_success=lambda _op, outcome: self._apply_library_find(
                outcome, generation, announce=announce
            ),
            on_failure=lambda _op, exc: self._library_find_failed(exc, generation, announce),
        )
        self._find_operation = getattr(task, "operation_id", None)
        return ""

    def _library_find_current(self, generation: int, query: str) -> bool:
        """Whether an answer is still the one wanted: same search, same words."""
        return generation == getattr(self, "_find_generation", 0) and (
            query == self._library_find_query()
        )

    def _apply_library_find(self, outcome: Any, generation: int, *, announce: bool) -> str:
        """Draw an answer, if it is still current. Returns the count sentence."""
        if not self._library_find_current(generation, outcome.query):
            return ""  # superseded by more typing, or Find has ended
        self._find_operation = None
        rows = rows_for_hits(outcome.hits[:MAX_ROWS], self._podcast_library)
        keep = None
        if not announce:
            # A quiet refresh keeps the cursor on its row when the row survives.
            try:
                keep = self._selected_tree_data()
            except Exception:  # noqa: BLE001
                keep = None
        tree = self._shows_tree
        tree.DeleteAllItems()
        root = tree.AddRoot("Matches")
        first = chosen = None
        for label, data in rows:
            item = tree.AppendItem(root, label)
            tree.SetItemData(item, data)
            first = first or item
            if keep is not None and chosen is None and data == keep:
                chosen = item
        hidden = outcome.total - len(rows)
        if hidden > 0:
            more = tree.AppendItem(root, f"{hidden:,} more -- type more of the name to narrow it")
            tree.SetItemData(more, ("more", ""))
        if chosen or first:
            tree.SelectItem(chosen or first)
        said = match_count_sentence(outcome.total, outcome.query)
        status = getattr(self, "_find_status", None)
        if status is not None:
            try:
                status.SetLabel(said)
            except RuntimeError:
                pass
        if announce:
            self._announce(said)
        return said

    def _library_find_failed(self, exc: BaseException, generation: int, announce: bool) -> None:
        from quill.stability.task_manager import CancelledError

        if isinstance(exc, CancelledError) or generation != getattr(self, "_find_generation", 0):
            return  # superseded: the newer search speaks for itself
        logger.warning("Find in library failed: %s", exc.__class__.__name__)
        if announce:
            self._announce("Find could not search your library. Try again.")

    def _end_library_find(self, *, announce: bool = True) -> None:
        """Back to the library, the cursor on the row it left."""
        timer = getattr(self, "_find_timer", None)
        if timer is not None:
            try:
                timer.Stop()
            except Exception:  # noqa: BLE001
                pass
        self._cancel_library_find()
        key = getattr(self, "_find_return_key", None)
        self._find_return_key = None
        status = getattr(self, "_find_status", None)
        if status is not None:
            try:
                status.SetLabel("")
            except RuntimeError:
                pass
        place = getattr(self, "_find_return_place", "")
        self._find_return_place = ""
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
        event.Skip()

    def focus_library_find(self) -> None:
        """Ctrl+F and View > Find in Library: into the box, its text selected.

        Also warms the indexes in the background, so the first search after a
        launch does not pay for building them while somebody waits to hear a count.
        """
        box = getattr(self, "_find_box", None)
        if box is None:
            return
        box.SetFocus()
        box.SelectAll()
        self._warm_library_search()

    def _warm_library_search(self) -> None:
        manager = getattr(self, "_task_manager", None)
        if manager is None or getattr(self, "_library_search_warmed", False):
            return
        self._library_search_warmed = True
        shows = list(getattr(self._podcast_library, "shows", []) or [])
        index, transcripts = self._library_search_indexes()

        def warm(cancellation_token: Any, **_kw: Any) -> None:
            index.sync(shows, cancel=cancellation_token.is_cancelled)
            transcripts.refresh(cancel=cancellation_token.is_cancelled)

        manager.submit("cast-library-index", warm)
