"""Search Everywhere, and the searches it remembers (list.md 5.5).

Extracted from ``manager_phase4`` under GATE-11, along a real seam: everything
here is the one verb that crosses the whole library, from opening the dialog to
landing the selection on what it found.

**The memory is the new part.** Cast's search started from nothing every time.
That costs more than it sounds, because of what a podcast search is: "the
episode about the harbour" gets looked for several times across a week, from a
different place in the library each time, and the query is the part somebody
has to reconstruct from memory on every attempt. Quill Radio has remembered
its searches for a while; the pure half here is
:mod:`quill.core.podcasts.search_history`.

The list rides the app's own history file -- the one that already holds the
recently-played episodes -- so clearing that clears this too, rather than
leaving a second record of what somebody has been searching for that they did
not know existed.
"""

from __future__ import annotations

from quill.core.podcasts.filtering import search_everywhere


class SearchEverywhereMixin:
    """Podcasts > Search Everywhere, for the Podcast Manager."""

    def _on_search_everywhere(self) -> None:
        from quill.core.podcasts.episode_notes import load_episode_notes
        from quill.core.podcasts.transcripts import iter_cached_transcripts
        from quill.ui.podcasts.search_everywhere_dialog import SearchEverywhereDialog

        try:
            transcripts = list(iter_cached_transcripts())
        except Exception:  # noqa: BLE001 - a broken cache must not block search
            transcripts = []
        dialog = SearchEverywhereDialog(
            self.dialog,
            on_search=lambda query: search_everywhere(
                self._library,
                query,
                episode_notes=load_episode_notes(),
                transcripts=transcripts,
            ),
            announce_cb=self._announce,
            # The searches already run, on the box's down arrow (list.md 5.5).
            # Read from and written back to the app's history, which is where
            # the recently-played list lives too -- one file, so clearing it
            # clears both.
            recent_searches=self._remembered_searches(),
            on_recent_searches_changed=self._store_remembered_searches,
        )
        result = dialog.show()
        if result is None:
            return
        self._select_search_result(result)

    def _remembered_searches(self) -> tuple[str, ...]:
        """What has been searched for before, or nothing when there is no host.

        The Podcast Manager can be opened from full QUILL as well as from the
        standalone app, and only one of those carries a podcast history. An
        absent history costs the dropdown, not the search.
        """
        history = getattr(self._transport_host, "_podcast_history", None)
        return tuple(getattr(history, "recent_searches", ()) or ())

    def _store_remembered_searches(self, entries: tuple[str, ...]) -> None:
        """Persist the updated list through the host's own saver.

        Never a direct write: the history file is one the app is also holding,
        and two writers is how a setting disappears.
        """
        history = getattr(self._transport_host, "_podcast_history", None)
        if history is None:
            return
        history.recent_searches = tuple(entries)
        saver = getattr(self._transport_host, "_save_podcast_history", None)
        if callable(saver):
            saver()

    def _select_search_result(self, result: object) -> None:
        """Land the tree/list selection on a Search Everywhere hit."""
        show = self._library.find_show(getattr(result, "show_id", "") or "")
        if show is None:
            return
        self.refresh_tree()
        self._restore_tree_anchor(("show", show.id))
        guid = getattr(result, "episode_guid", "") or ""
        if guid:
            for row, episode in enumerate(self._current_episodes):
                if episode.guid == guid:
                    self._episodes.Select(row)
                    self._episodes.Focus(row)
                    break
        self._announce(f"Selected {show.title}")
