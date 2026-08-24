"""Find in this show: the episode search that sits between the two others.

QUILL Cast has had a state filter ("unplayed", "downloaded") and a
cross-library Search Everywhere for a while, and nothing in between -- so
"which episode of *this* show was the one about the harbour" had no answer
except arrowing two hundred rows (list.md section 5).

Three rules, all of them the reason this is a mixin rather than four lines
in the filter row:

* **Titles and descriptions.** A show that numbers its episodes and puts the
  subject in the notes -- most interview podcasts -- is precisely the case a
  title-only search fails.
* **It composes, it does not replace.** The query is applied *inside*
  ``_apply_episode_filter``, after the state filter and before the sort, so
  Find narrows what the filter chose and the sort orders what survives both.
* **Typing is silent; Enter counts.** A per-keystroke announcement talks over
  the typing. Enter says how many matched out of how many were searched, and
  a search that found nothing says the filter above may be why.

Extracted from ``manager_phase4.py`` under GATE-11.
"""

from __future__ import annotations

from quill.core.podcasts.filtering import filter_episodes, filter_episodes_by_text
from quill.core.podcasts.models import PodcastEpisode


class EpisodeSearchMixin:
    """The episode list's own search box, mixed into the Podcast Manager."""

    def _episode_search_query(self) -> str:
        ctrl = getattr(self, "_episode_search_ctrl", None)
        return str(ctrl.GetValue()) if ctrl is not None else ""

    def _on_episode_search_typed(self, _event: object) -> None:
        """Narrow the list as the query is typed, silently."""
        self._fill_episodes(self._current_show)

    def _on_episode_search_submit(self, _event: object) -> None:
        """Enter: say how many matched, out of how many were searched (5.3)."""
        from quill.core.podcasts.filtering import search_summary

        show = self._current_show
        total = (
            len(filter_episodes(list(show.episodes), self._selected_episode_filter()))
            if show
            else 0
        )
        matched = len(self._current_episodes)
        self._announce(search_summary(matched, total, self._episode_search_query()))

    def _apply_episode_filter(self, episodes: list[PodcastEpisode]) -> list[PodcastEpisode]:
        """The state filter, then the in-show search (section 5.2).

        In this order and in one place, so the two compose rather than
        competing: Find narrows what the filter already chose, and the sort
        the caller applies afterwards orders whatever survives both.
        """

        chosen = filter_episodes(episodes, self._selected_episode_filter())
        return filter_episodes_by_text(chosen, self._episode_search_query())
