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
        total = len(self._episodes_before_search(list(show.episodes))) if show else 0
        matched = len(self._current_episodes)
        self._announce(search_summary(matched, total, self._episode_search_query()))

    def _episodes_before_search(self, episodes: list[PodcastEpisode]) -> list[PodcastEpisode]:
        """The podcast's own Episode Filter, then the state filter.

        Everything the search box then narrows -- and the number the search
        summary reports as "searched", which has to be this list rather than
        the show's whole catalogue or the count contradicts what is on screen.

        **Filtered out** replaces the first step instead of adding to it. It is
        the way back: what this podcast's Episode Filter rejects, and nothing
        else. Without it a hiding scope could put an episode somewhere a person
        could not get to, and a feature that can do that is a feature that
        deletes. Deliberately answered by the *rules* rather than by the library
        scope, so it tells the truth about a podcast that only filters its
        Inbox or its downloads too.
        """
        from quill.core.podcasts.episode_filter_maintenance import visible
        from quill.core.podcasts.models_filters import SCOPE_LIBRARY
        from quill.core.podcasts.show_policy import visible_episodes

        show = self._current_show
        mode = self._selected_episode_filter()
        if show is None:
            return filter_episodes(list(episodes), mode)
        # The catalogue view limit first, because it is about how much of a
        # four-thousand-episode feed this list is *of* -- a view, never a trim:
        # raising it brings every episode back, because none of them went
        # anywhere.
        episodes = visible_episodes(self._library, show, episodes)
        if mode == "filtered_out":
            return [episode for episode in episodes if self._episode_filter_rejects(show, episode)]
        return filter_episodes(visible(self._library, show, episodes, SCOPE_LIBRARY), mode)

    def _apply_episode_filter(self, episodes: list[PodcastEpisode]) -> list[PodcastEpisode]:
        """The podcast's own filter, then the state filter, then the search.

        In this order and in one place, so the three compose rather than
        competing: the Episode Filter decides what this list is *of*, Find
        narrows what the state filter chose, and the sort the caller applies
        afterwards orders whatever survives all three.
        """
        return filter_episodes_by_text(
            self._episodes_before_search(episodes), self._episode_search_query()
        )

    def _episode_filter_rejects(self, show: object, episode: PodcastEpisode) -> bool:
        """Whether this podcast's rules reject *episode*, scopes aside.

        What **Filtered out** lists. Asked of the rules rather than of a scope
        because the question somebody is asking there is "what is this filter
        catching?", and the answer must not depend on which surfaces they
        happened to tick. An exempted episode is never rejected.
        """
        from quill.core.podcasts import episode_filters
        from quill.core.podcasts.episode_filter_maintenance import filter_for, is_exempt

        config = filter_for(self._library, show)
        if config is None or not config.is_active or is_exempt(self._library, show, episode):
            return False
        return not episode_filters.keeps(config, episode)
