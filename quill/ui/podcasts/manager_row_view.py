"""How an episode row is built and what it says.

Split out of ``manager_dialog`` under GATE-11, along the seam Radio's
``results_view`` and ``recordings_row_view`` already follow: *choosing* episodes
on one side, *presenting* them on the other. Everything here answers "what does
this row say?" -- which columns exist, in what order, and what goes in each.

That seam is where the configurable columns landed. Once a listener can reorder
and hide columns, ``SetItem(row, 2, ...)`` is a promise about a position nobody
can keep, so every cell is produced by id and written through the shared column
view.
"""

from __future__ import annotations

from quill.core.media.list_columns import ColumnDef
from quill.core.podcasts.episode_availability import downloaded_words, status_words
from quill.core.podcasts.list_columns import EPISODES as _EPISODE_COLUMNS
from quill.core.podcasts.models import PodcastEpisode, PodcastShow
from quill.ui.media.list_columns_view import build_columns, columns_for

#: This list's id in Cast's column catalogue -- taken from the catalogue itself
#: rather than retyped, so the fill site and the preference cannot end up naming
#: two different lists.
SURFACE = _EPISODE_COLUMNS.id


class ManagerRowViewMixin:
    """Episode-row presentation for :class:`PodcastManagerDialog`."""

    def _build_episode_columns(self) -> None:
        """Give the episode list the columns the listener chose, in their order.

        Subscriptions > Choose Columns... owns which columns exist; a report row
        is read out column by column, so that choice is the sentence every
        episode row speaks.
        """
        self._episode_columns: list[ColumnDef] = columns_for("cast", SURFACE)
        build_columns(self._episodes, self._episode_columns)

    def _queue_reason(self, episode: PodcastEpisode, show: PodcastShow | None) -> str:
        """In the Play Queue place, why an episode is waiting (qc.md X-04)."""
        if getattr(self, "_current_place", "") != "queue" or show is None:
            return ""
        for item in self._library.queue:
            if item.show_id == show.id and item.episode_guid == episode.guid:
                return f"; queued by {item.reason}" if item.reason else ""
        return ""

    def _played_elsewhere(self, episode: PodcastEpisode) -> str:
        """In Continue Listening, the device a place came from (ear.md B1)."""
        device = str(getattr(episode, "last_played_on", "") or "")
        if not device or getattr(self, "_current_place", "") != "continue_listening":
            return ""
        return f"; last played on {device}"

    def _episode_row_values(
        self, episode: PodcastEpisode, show: PodcastShow | None
    ) -> dict[str, str]:
        """Every cell an episode row could show, keyed by column id.

        Built whole rather than per shown column: the values are cheap, and a
        function that only computes what is currently visible is one that has to
        be revisited every time the catalogue grows.
        """
        minutes, seconds = divmod(episode.duration_seconds, 60)
        duration_text = f"{minutes}:{seconds:02d}" if episode.duration_seconds else ""
        remaining_seconds = episode.duration_seconds - int(episode.position_ms / 1000)
        # Only worth saying while there is something left and something was
        # started: "58 min left" on an untouched episode is the duration said
        # twice, and a negative answer on an overrun position is nonsense.
        remaining = ""
        if episode.position_ms and 0 < remaining_seconds < episode.duration_seconds:
            remaining = f"{remaining_seconds // 60} min left"
        return {
            # The podcast's own title-tidying rules, applied here rather than
            # to the stored episode: the feed's title is the publisher's and is
            # never rewritten, and this is the reading of it (title_cleanup.py).
            "title": self._display_title(episode, show),
            "published": episode.published[:16],
            "duration": duration_text,
            "status": self._episode_status_text(episode)
            + self._queue_reason(episode, show)
            + self._played_elsewhere(episode),
            "podcast": show.title if show is not None else "",
            "remaining": remaining,
            # FUX-13: a file deleted outside Cast plays only by streaming, so it
            # is not called "Downloaded" (episode_availability.py).
            "downloaded": downloaded_words(str(episode.downloaded_path or "")),
            # R25: the Row Description setting, finally read by something. It
            # decides how much of the show notes a row carries -- nothing, the
            # first sentence, or all of it -- and the column decides whether the
            # row carries them at all.
            "description": self._episode_description(episode),
        }

    def _episode_description(self, episode: PodcastEpisode) -> str:
        """As much of the show notes as Row Description asks for.

        The setting lived for a release with nothing reading it. It is asked here,
        per row, rather than stamped onto the episode, so changing it takes effect
        on the next redraw instead of on the next refresh.
        """
        from quill.core.podcasts.row_speech import RowSpeech, format_description

        speech = RowSpeech.from_values(self._row_speech_values())
        return format_description(episode.description, speech.description)

    #: The stored names ``RowSpeech.from_values`` reads. Listed rather than
    #: derived, because the dataclass field names and the setting names are
    #: deliberately different (``description`` is stored as ``row_description``).
    _ROW_SPEECH_SETTINGS = (
        "row_order",
        "row_say_podcast",
        "row_say_date",
        "row_duration",
        "row_say_download",
        "row_say_extras",
        "row_description",
        "row_episode_numbers",
    )

    def _row_speech_values(self) -> dict[str, object]:
        """The stored row-reading preferences, from wherever this host keeps them.

        Cast holds them on the library settings; a host that has none answers with
        an empty mapping, and ``RowSpeech.from_values`` then gives its defaults --
        the same defaults the settings page shows.
        """
        settings = getattr(self._library, "settings", None)
        if settings is None:
            return {}
        return {
            name: getattr(settings, name)
            for name in self._ROW_SPEECH_SETTINGS
            if hasattr(settings, name)
        }

    def _display_title(self, episode: PodcastEpisode, show: PodcastShow | None) -> str:
        """This episode's title as it should be read.

        A podcast with no cleanup rules gets its title back unchanged, which is
        every podcast until somebody writes one.
        """
        if show is None:
            return episode.title
        from quill.core.podcasts.show_policy import display_title

        return display_title(self._library, show, episode)

    def _episode_status_text(self, episode: PodcastEpisode) -> str:
        """Where the audio is, in words: a failed download and a missing file
        say so and what still works, rather than "Streaming" and "Downloaded"
        (FUX-13, ``episode_availability``)."""
        item = None
        if not episode.downloaded_path:
            item = self._download_queue.get(self._download_item_id(episode))
        return status_words(
            downloaded_path=str(episode.downloaded_path or ""),
            played=bool(episode.played),
            item_status=item.status if item is not None else "",
            item_error=item.error_message if item is not None else "",
        )

    def _set_episode_state_cells(self, row: int, episode: PodcastEpisode) -> None:
        """Rewrite one row's Status and Downloaded cells where those columns are.

        By column id, not position: the columns can be reordered and hidden, so
        "column 3" could be Time Left (FUX-13).
        """
        values = {
            "status": self._episode_status_text(episode),
            "downloaded": downloaded_words(str(episode.downloaded_path or "")),
        }
        for index, column in enumerate(self._episode_columns):
            if column.id in values:
                self._episodes.SetItem(row, index, values[column.id])

    def reapply_columns(self) -> None:
        """Rebuild the episode list after the column layout changed.

        Cast holds this window open across a settings change, so a layout saved
        while it is up takes effect here rather than next time -- a preference
        somebody has to reopen a window to hear is friction this feature exists
        to remove.
        """
        self._build_episode_columns()
        self._fill_episodes(self._current_show)
