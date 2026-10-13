"""Quill Radio's Lineups commands: open the window, Add to Lineup, the start Lineup.

Everything Radio does with Lineups goes through here, so the app's own modules
(``main_frame_radio``, ``radio_menu_bar``, ``browse_tree_menu`` ...) gain one
call each rather than a feature each.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from quill.core.lineups.fields import ItemFacts

#: ``(command id, palette title, handler factory)``.
COMMANDS: tuple[tuple[str, str, Any], ...] = (
    ("radio.lineups", "Internet Radio: Lineups...", lambda host: open_window(host)),
    ("radio.lineups_go_to", "Lineups: Go to a Lineup...", lambda host: go_to_lineup(host)),
)


def _app(host: Any) -> Any:
    from quill.ui.radio.local_media_ui import app_of

    return app_of(host)


def _host(host: Any) -> Any:
    from quill.ui.radio.lineups_host import RadioLineupsHost

    return RadioLineupsHost(_app(host))


def open_window(host: Any, *, lineup_id: str = "") -> Any:
    """Lineups...: open the window, or bring it forward (on *lineup_id*)."""
    from quill.ui.lineups.window import open_window as open_lineups

    return open_lineups(_host(host), lineup_id=lineup_id)


def go_to_lineup(host: Any) -> None:
    """Choose a Lineup by name and open it: quicker than arrowing with many."""
    from quill.core.lineups.store import LineupStore
    from quill.ui.lineups import dialogs

    lineups_host = _host(host)
    book = LineupStore(lineups_host.data_dir).load()
    if not book.lineups:
        open_window(host)
        return
    index = dialogs.choose(
        lineups_host,
        lineups_host.frame,
        "Open which lineup?",
        "Go to a Lineup",
        [lineup.name for lineup in book.lineups],
    )
    if index is not None:
        open_window(host, lineup_id=book.lineups[index].id)


def register(host: Any) -> None:
    """Put Lineups in the Command Palette."""
    for command_id, title, factory in COMMANDS:
        host.commands.try_register(
            command_id,
            title,
            lambda f=factory: f(host),
            host._binding_for(command_id),
            feature_id="core.radio",
        )


def append_menu_item(app: Any, menu: Any, wx: Any) -> None:
    """Playback > Lineups...: the keyboard route shown, the id kept alive."""
    item_id = wx.NewIdRef()
    menu.Append(item_id, app._menu_label("Line&ups...", "radio.lineups"))
    app.frame.Bind(wx.EVT_MENU, lambda _e: open_window(app), id=item_id)
    keep = getattr(app, "_keep_menu_ids", None)
    if callable(keep):
        keep(item_id)
    else:
        app._lineups_menu_id = item_id


def add(host: Any, items: Sequence[ItemFacts], *, parent: Any = None) -> bool:
    """Add to Lineup... for any row in Radio."""
    from quill.ui.lineups.add_to import offer

    return offer(_host(host), items, parent=parent)


def add_station(host: Any, station: Any, *, parent: Any = None) -> bool:
    """Add to Lineup... for a ``RadioStation`` row (a station, a place, a YouTube item)."""
    from quill.core.lineups.sources import station_facts

    if station is None:
        _host(host).announce("There is nothing here to add to a lineup.")
        return False
    return add(host, [station_facts(station)], parent=parent)


def open_start_lineup(app: Any) -> None:
    """At launch: the Lineup pinned with Start Here, if there is one and it exists."""
    from quill.core.lineups.store import LineupStore

    lineups_host = _host(app)
    lineup_id = lineups_host.start_lineup_id()
    if not lineup_id or _first_run_is_due(app):
        return
    try:
        book = LineupStore(lineups_host.data_dir).load()
    except Exception:  # noqa: BLE001 - launch carries on as usual
        return
    if book.find(lineup_id) is None:
        lineups_host.set_start_lineup_id("")
        lineups_host.announce("Your start lineup no longer exists. Quill Radio opened as usual.")
        return
    open_window(app, lineup_id=lineup_id)


def _first_run_is_due(app: Any) -> bool:
    """First run wins: the start Lineup applies from the next launch."""
    try:
        from quill.core.radio.onboarding import needs_first_run

        history = getattr(app, "_radio_history", None)
        favorites = getattr(getattr(app, "_radio_favorites", None), "favorites", None)
        return bool(
            history is not None
            and needs_first_run(history.onboarding, has_favorites=bool(favorites))
        )
    except Exception:  # noqa: BLE001 - when in doubt, do not open a second window
        return True


def play_handoff(app: Any, path: Path) -> None:
    """Play a Lineup row Quill Cast handed over (it cannot play stations or video)."""
    from quill.core.lineups.handoff import read_request
    from quill.core.lineups.store import LineupStore

    request = read_request(path)
    lineups_host = _host(app)
    if request is None:
        return
    book = LineupStore(lineups_host.data_dir).load()
    lineup = book.find(request.lineup_id)
    if lineup is None:
        lineups_host.announce("The lineup Quill Cast asked for no longer exists.")
        return
    refs = [row.ref for row in lineup.rows if row.ref.token in set(request.tokens)]
    order = {token: index for index, token in enumerate(request.tokens)}
    refs.sort(key=lambda ref: order.get(ref.token, 0))
    catalogue = lineups_host.catalogue(lineups_host.now())
    facts = [catalogue.lookup(ref)[1] for ref in refs]
    message = lineups_host.play(lineup, refs, 0, facts)
    lineups_host.announce(message)


__all__ = [
    "COMMANDS",
    "add",
    "add_station",
    "append_menu_item",
    "go_to_lineup",
    "open_start_lineup",
    "open_window",
    "play_handoff",
    "register",
]
