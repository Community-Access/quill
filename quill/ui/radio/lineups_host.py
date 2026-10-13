"""Quill Radio's side of the Lineups window: how a row plays, which menus sit beside it.

Radio plays every kind a Lineup holds -- stations, YouTube, podcast episodes,
Local Media files and recordings -- through its own player, one after another
(``lineups_playback``). A saved place or a YouTube channel is somewhere to
browse rather than something to play; Enter on one opens Browse Stations.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from quill.core.lineups.fields import ItemFacts
from quill.core.lineups.merge import Catalogue
from quill.core.lineups.model import Lineup
from quill.core.lineups.refs import KIND_PLACE, KIND_YT_CHANNEL, ItemRef
from quill.ui.lineups.host import LineupsHost
from quill.ui.radio import lineups_playback as playback


class RadioLineupsHost(LineupsHost):
    app_key = "radio"
    app_name = "Quill Radio"

    def install_menus(self, win: Any, menu_bar: Any, refs: list[Any]) -> None:
        import wx

        from quill.ui.radio import surface_app_menu

        refs.extend(
            surface_app_menu.install(
                win=win, host=self.app, menu_bar=menu_bar, wx=wx, skip=("open_lineups",)
            )
        )
        super().install_menus(win, menu_bar, refs)

    def install_keys(self, win: Any) -> None:
        import wx

        from quill.ui.radio import transport_keys

        windows = self.windows
        extra = windows.accelerator_entries() if windows is not None else ()
        transport_keys.install(win, self.app, wx=wx, extra_entries=extra)

    def catalogue(self, now: float) -> Catalogue:
        from quill.core.lineups.sources import build_catalogue

        settings = getattr(self.app, "_radio_recording_settings", None)

        def recordings() -> list[Any]:
            from quill.core.radio.recordings_index import list_recordings

            return list(list_recordings(settings)) if settings is not None else []

        return build_catalogue(
            self.data_dir, now=now, recordings=recordings if settings is not None else None
        )

    def play(
        self, lineup: Lineup, refs: Sequence[ItemRef], start: int, facts: Sequence[ItemFacts | None]
    ) -> str:
        if 0 <= start < len(refs) and refs[start].kind in (KIND_PLACE, KIND_YT_CHANNEL):
            name = facts[start].name if facts[start] is not None else "That"  # type: ignore[union-attr]
            opener = getattr(self.app, "open_browse_stations", None)
            if callable(opener):
                opener()
            return (
                f"{name} is a place to browse. Browse Stations is open; "
                "it is under Favorites if you saved it there."
            )
        return playback.start(self.app, lineup, refs, start, facts)

    def play_next(
        self, refs: Sequence[ItemRef], facts: Sequence[ItemFacts | None], *, at_end: bool
    ) -> str:
        from quill.ui.lineups.window import open_window_of

        window = open_window_of(self.app_key)
        lineup = window.current_lineup() if window is not None else None
        if lineup is None:
            return "No lineup is selected."
        return playback.queue(self.app, lineup, refs, facts, at_end=at_end)

    def step(self, delta: int) -> str:
        return playback.step(self.app, delta)

    def stop_after_current(self) -> str:
        return playback.stop_after(self.app)

    def start_lineup_id(self) -> str:
        history = getattr(self.app, "_radio_history", None)
        return str(getattr(history, "start_lineup_id", "") or "")

    def set_start_lineup_id(self, lineup_id: str) -> None:
        history = getattr(self.app, "_radio_history", None)
        if history is None:
            return
        history.start_lineup_id = lineup_id
        save = getattr(self.app, "_save_radio_history", None)
        if callable(save):
            save()


def host_for(app: Any) -> RadioLineupsHost:
    return RadioLineupsHost(app)


__all__ = ["RadioLineupsHost", "host_for"]
