"""What happens to a brand-new episode (QUILL Cast 1.1.0).

A feed refresh used to end at "N new episodes for X". This mixin owns
everything that now happens next -- the acquisition layer QUILL Cast did not
have:

- **Auto-Queue**: a show marked for it sends its new episodes straight into
  the Play Queue, skipping the Inbox.
- **Per-show announcement**: a show marked for it has its new episodes named
  out loud, in braille, and in a tray balloon.
- **Auto-download**: the newest N episodes (plus anything queued or in the
  Inbox, per the toggles) are fetched without being asked.
- **Episode Filters**: the podcast's own rules are asked first, and each of
  the three routes above then asks for its own scope -- so one feature covers
  "do not queue it", "do not download it" and "do not tell me about it"
  without any of them implying the others.

Split out of ``main_frame_podcasts.py`` rather than appended to it: that
module owns the player, the download queue, and the refresh call itself, and
this is a distinct decision -- *what should exist on disk and in the queue* --
that is worth reading on its own.

Every path here is gated: Safe Mode fetches nothing, a paused show is left
alone, and everything it does is announced (A-4).
"""

from __future__ import annotations

from quill.core.podcasts.episode_filter_maintenance import IngestOutcome
from quill.core.podcasts.models import PodcastEpisode, PodcastShow


class PodcastAcquisitionMixin:
    """Auto-Queue, per-show notification, and auto-download on refresh."""

    def _podcast_filter_new_episodes(
        self, show: PodcastShow, arrived: list[PodcastEpisode]
    ) -> IngestOutcome:
        """Ask this podcast's Episode Filter about what just arrived.

        First in the chain on purpose: Auto-Queue, the per-show announcement
        and the auto-download pass all act on the answer, so a rejected episode
        never reaches a surface it would then have to be removed from.

        It changes nothing. Every episode that arrived is in the podcast's
        list; the outcome only says which of them the rules rejected, and each
        route asks for its own scope through
        :meth:`_podcast_filter_scope`. A podcast with no filter gets the whole
        list back for every scope, which is the compatibility story in one
        sentence.
        """
        from quill.core.podcasts.episode_filter_maintenance import route_refresh

        return route_refresh(self._podcast_library, show, arrived)

    def _podcast_filter_scope(
        self, show: PodcastShow, outcome: IngestOutcome, scope: str
    ) -> list[PodcastEpisode]:
        """The new episodes one scope of the filter allows through.

        A scope the podcast's filter does not govern gets everything that
        arrived, exactly as it would have with no filter at all -- so "keep it
        out of my Inbox but still tell me about it" is a thing somebody can
        actually have.
        """
        from quill.core.podcasts.episode_filter_maintenance import governs

        return outcome.for_scope(scope, governs(self._podcast_library, show, scope))

    def _podcast_announce_episode_filter(self, show: PodcastShow, outcome: IngestOutcome) -> None:
        """Say what a filter took, and warn when it took everything.

        Two sentences, and both of them exist because of how the silence would
        read. A refresh that says "2 new episodes" when the feed published
        five is quiet arithmetic that looks like a bug, so the count that was
        filtered is spoken -- naming the scopes that *hide*, since somebody
        who cannot find an episode afterwards needs to have been told where to
        look -- and it says nothing was deleted. And a
        Keep-matching rule that rejected the *whole* refresh is far more often
        a rule that means something other than what was intended, so it is
        raised as a warning: forced, because a rule silently swallowing a
        podcast is exactly the news that must not queue behind whatever is
        being read out.
        """
        from quill.core.podcasts.episode_filters import (
            describe_needs_review,
            describe_refresh_outcome,
        )

        if outcome.any_filtered:
            message = describe_refresh_outcome(
                show.title,
                len(outcome.kept),
                len(outcome.filtered),
                hidden=outcome.hidden_from,
            )
            if message:
                self._announce(message)
        if outcome.raised_review:
            self._announce(describe_needs_review(show.title), force=True)

    def _podcast_play_earcon(self, show: PodcastShow) -> None:
        """This podcast's own new-episode sound, when it has been given one.

        Played *instead of* the shared new-episode sound rather than as well,
        so a podcast with a sound of its own is distinguishable rather than
        merely louder. Best-effort throughout: a sound that will not play must
        never break a refresh.
        """
        from quill.core.podcasts.show_policy import earcon

        event = earcon(self._podcast_library, show)
        if not event:
            return
        try:
            from quill.ui.sound_manager import post_sound

            post_sound(event)
        except Exception:  # noqa: BLE001 - a silent earcon never stops a refresh
            pass

    def _podcast_file_to_default_playlist(
        self, show: PodcastShow, fresh: list[PodcastEpisode]
    ) -> int:
        """Add this podcast's new episodes to the playlist it names.

        The missing middle between Auto-Queue and doing nothing: routing
        without committing to an order. It adds to that list only -- it does
        not queue, download, or take anything out of the Inbox.
        """
        from quill.core.podcasts.models import QueueItem
        from quill.core.podcasts.show_policy import default_playlist

        wanted = default_playlist(self._podcast_library, show)
        if not wanted or not fresh:
            return 0
        target = next(
            (p for p in self._podcast_library.playlists if p.name == wanted and p.kind == "manual"),
            None,
        )
        if target is None:
            return 0
        known = {(item.show_id, item.episode_guid) for item in target.items}
        added = 0
        for episode in fresh:
            if (show.id, episode.guid) in known:
                continue
            target.items.append(QueueItem(show_id=show.id, episode_guid=episode.guid))
            added += 1
        return added

    def _podcast_route_new_episodes(self, show: PodcastShow, fresh: list[PodcastEpisode]) -> int:
        """Auto-Queue: a show marked auto_queue sends its new episodes
        straight to the Play Queue, skipping the Inbox. Returns how many."""
        from quill.core.podcasts.acquisition import route_new_episodes

        return route_new_episodes(self._podcast_library, show, fresh)

    def _podcast_new_episode_message(self, show: PodcastShow, new_count: int, queued: int) -> str:
        """One sentence covering what arrived and where it went, rather than
        a count now and a separate "and they were queued" later."""
        message = f"{new_count} new episode(s) for {show.title}"
        if queued:
            message += f"; {queued} added to the Play Queue"
        return message

    def _podcast_resurface_republished(
        self, show: PodcastShow, republished: list[str]
    ) -> list[PodcastEpisode]:
        """Bring re-issued episodes back to the Inbox, and say so.

        Runs *before* the Inbox trim that follows a refresh, so an episode that
        returns is judged against that show's caps like everything else rather
        than surviving the refresh on a technicality.

        The rules live in :func:`quill.core.podcasts.inbox.resurface_republished`
        -- played, started, queued and hand-filed episodes are all left alone.
        """
        from quill.core.podcasts import inbox
        from quill.core.podcasts.show_policy import republished_as_new

        # Some feeds re-stamp their whole back catalogue on every rebuild,
        # which turns this kindness into a flood. Per podcast, because it is a
        # fact about one publisher's tooling rather than about the listener
        # (7.21). Off still hides nothing: the episode is where it always was.
        if not republished_as_new(self._podcast_library, show):
            return []
        returned = inbox.resurface_republished(self._podcast_library, show, republished)
        if returned:
            self._announce(self._podcast_republished_message(show, returned))
        return returned

    def _podcast_republished_message(
        self, show: PodcastShow, returned: list[PodcastEpisode]
    ) -> str:
        """What to say when a re-issued episode comes back to the Inbox.

        Deliberately not phrased as "new episodes". The publisher re-issued
        something you already had -- a corrected file, a re-cut -- and calling
        that new would misdescribe what happened. Names the episode when there
        is one, because a name is more use than a count.
        """
        title = show.title or "this podcast"
        if len(returned) == 1:
            name = returned[0].title or "An episode"
            return f"{name} was re-published by {title}, so it is back in your Inbox."
        return (
            f"{len(returned)} episodes were re-published by {title}, "
            "so they are back in your Inbox."
        )

    def _podcast_notify_new_episodes(self, show: PodcastShow, fresh: list[PodcastEpisode]) -> None:
        """Per-show notification, at the priority this podcast was given.

        The desktop answer to a push notification is a spoken/braille
        announcement plus a tray balloon -- and it is per show on purpose:
        being told about every feed is being told about nothing.

        Three positions rather than the boolean this used to be, because "tell
        me by name", "count it in the summary" and "say nothing" are three
        different instructions:

        * **urgent** names the episodes and interrupts;
        * **normal** says nothing here -- the shared count has already been
          spoken, and repeating it per show is how a twenty-podcast morning
          became unusable;
        * **quiet** says nothing anywhere, and the episodes still arrive,
          download and queue exactly as they would.

        The podcast's own name is spoken through the pronunciation override
        (7.4) and its episode titles through the tidying rules (7.3), so the
        announcement reads the way its list does.
        """
        from quill.core.podcasts.settings_defs_show import PRIORITY_INTERRUPT
        from quill.core.podcasts.show_policy import (
            display_title,
            notify_priority,
            spoken_show_name,
        )

        if not fresh:
            return
        if notify_priority(self._podcast_library, show) != PRIORITY_INTERRUPT:
            return
        titles = ", ".join(
            display_title(self._podcast_library, show, episode) for episode in fresh[:3]
        )
        if len(fresh) > 3:
            titles += f", and {len(fresh) - 3} more"
        message = f"{spoken_show_name(self._podcast_library, show)}: {titles}"
        self._announce(message, force=True)
        self._podcast_play_earcon(show)
        tray_icon = getattr(self, "_tray_icon", None)
        if tray_icon is None:
            return
        try:
            tray_icon.ShowBalloon("New episode", message, 8000, self._wx.ICON_INFORMATION)
        except Exception:  # noqa: BLE001 - a balloon must never break a refresh
            pass

    def _podcast_apply_auto_download(self, show: PodcastShow) -> None:
        """Fetch what the acquisition policy says should be on disk.

        Gated with the rest of the network paths: Safe Mode downloads
        nothing, and neither does a paused show.
        """
        if self._safe_mode or show.paused:
            return
        from quill.core.podcasts.acquisition import episodes_to_auto_download
        from quill.core.podcasts.inbox import inbox_pairs
        from quill.ui.podcasts.show_actions import enqueue_episode_download

        queued_guids = frozenset(
            item.episode_guid for item in self._podcast_library.queue if item.show_id == show.id
        )
        inbox_guids = frozenset(
            episode.guid
            for inbox_show, episode in inbox_pairs(self._podcast_library)
            if inbox_show.id == show.id
        )
        wanted = episodes_to_auto_download(
            self._podcast_library, show, queued_guids=queued_guids, inbox_guids=inbox_guids
        )
        started = 0
        for episode in wanted:
            item_id = f"{show.id}:{episode.guid}"
            if self._podcast_download_queue.get(item_id) is not None:
                continue
            enqueue_episode_download(
                self._podcast_download_queue,
                self._podcast_download_root(),
                show,
                episode,
                item_id=item_id,
                library=self._podcast_library,
            )
            started += 1
        if started:
            self._announce(f"Downloading {started} episode(s) of {show.title} automatically")
