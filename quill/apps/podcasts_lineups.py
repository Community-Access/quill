"""Quill Cast's Lineups commands: the window, Add to Lineup, the start Lineup.

A mixin on ``PodcastsAppFrame``, so Cast's frame gains one base class and one
call rather than a feature (GATE-11). The window itself is shared with Quill
Radio (``quill.ui.lineups``); what is Cast's is here and in
``quill.ui.podcasts.lineups_host``.
"""

from __future__ import annotations

from typing import Any


class CastLineupsMixin:
    """Lineups on Cast's frame."""

    def _init_cast_lineups(self) -> None:
        """Register the commands; copy old queue snapshots in and open the start Lineup."""
        commands = getattr(self, "commands", None)
        if commands is not None:
            for command_id, title, handler in (
                ("podcasts.lineups", "Lineups", self.open_lineups),
                ("podcasts.add_to_lineup", "Add to Lineup...", self.podcast_add_to_lineup),
            ):
                commands.try_register(command_id, title, handler, self._binding_for(command_id))  # type: ignore[attr-defined]
        self._when_cast_library_ready(self._cast_lineups_at_launch)  # type: ignore[attr-defined]

    def _lineups_host(self) -> Any:
        from quill.ui.podcasts.lineups_host import CastLineupsHost

        return CastLineupsHost(self)

    def open_lineups(self, lineup_id: str = "") -> None:
        """Lineups...: QUILL Lineups, the same window as in Quill Radio."""
        from quill.ui.lineups.window import open_window

        open_window(self._lineups_host(), lineup_id=lineup_id)

    def podcast_add_to_lineup(self) -> None:
        """Add to Lineup...: the selected episode, or the selected podcast."""
        from quill.core.lineups.sources import episode_facts, show_facts
        from quill.ui.lineups.add_to import offer

        selected = self._selected_episode()  # type: ignore[attr-defined]
        if selected is not None:
            show, episode = selected
            offer(self._lineups_host(), [episode_facts(show, episode)], parent=self.frame)  # type: ignore[attr-defined]
            return
        show = self._selected_show()  # type: ignore[attr-defined]
        if show is not None:
            offer(self._lineups_host(), [show_facts(show)], parent=self.frame)  # type: ignore[attr-defined]
            return
        self._announce("Select an episode or a podcast to add to a lineup.")  # type: ignore[attr-defined]

    def _add_to_lineup(self, show: Any, episode: Any = None) -> None:
        """The row verb's body (episode and podcast menus)."""
        from quill.core.lineups.sources import episode_facts, show_facts
        from quill.ui.lineups.add_to import offer

        facts = episode_facts(show, episode) if episode is not None else show_facts(show)
        offer(self._lineups_host(), [facts], parent=getattr(self, "frame", None))

    def _cast_lineups_at_launch(self) -> None:
        from quill.ui.podcasts.lineups_queue import import_snapshots_once

        import_snapshots_once(self._podcast_library)  # type: ignore[attr-defined]
        host = self._lineups_host()
        lineup_id = host.start_lineup_id()
        if not lineup_id or self._cast_first_run_due():
            return
        from quill.core.lineups.store import LineupStore

        try:
            book = LineupStore(host.data_dir).load()
        except Exception:  # noqa: BLE001 - launch carries on as usual
            return
        if book.find(lineup_id) is None:
            host.set_start_lineup_id("")
            host.announce("Your start lineup no longer exists. Quill Cast opened as usual.")
            return
        self.open_lineups(lineup_id)

    def _cast_first_run_due(self) -> bool:
        """First run wins: the start Lineup applies from the next launch."""
        history = getattr(self, "_podcast_history", None)
        onboarding = getattr(history, "onboarding", None)
        library = getattr(self, "_podcast_library", None)
        has_shows = bool(getattr(library, "shows", None))
        return bool(onboarding is not None and not onboarding.completed_first_run and not has_shows)


__all__ = ["CastLineupsMixin"]
