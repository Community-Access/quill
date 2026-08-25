"""Community > Community Picks... and Suggest a Station or Podcast...

The second user of the shared picker, and the proof the sharing was worth it:
this module is fetch-and-map. The window, its two lists, its ordering rule and
every line of its accessibility work came free from the ACB Media Podcasts
build.

Design: docs/design/community-picks.md.
"""

from __future__ import annotations

from typing import Any

from quill.core.community_picks import Catalogue, load_bundled
from quill.ui.radio.catalogue_picker_dialog import PickableItem, choose_from_catalogue

_TITLE = "Community Picks"
_FOLDER = "Community Picks"
_HEADING = (
    "Stations and podcasts the community recommends. Arrow the list on the "
    "left to hear what each one is, add the ones you want, then arrange them "
    "however you like."
)


def register(app: Any) -> None:
    commands: Any = app.commands
    commands.try_register(
        "radio.community_picks",
        "Community Picks...",
        lambda: open_picks(app),
        feature_id="core.radio",
    )
    commands.try_register(
        "radio.suggest_pick",
        "Suggest a Station or Podcast...",
        lambda: open_suggest(app),
        feature_id="core.radio",
    )


def append_menu_items(host: Any, menu: Any, wx: Any) -> tuple[Any, ...]:
    """Two items: browse the list, and add to it. The caller pins the ids."""
    ids = []
    for label, command, handler in (
        ("Comm&unity Picks...", "radio.community_picks", lambda: open_picks(host)),
        ("Su&ggest a Station or Podcast...", "radio.suggest_pick", lambda: open_suggest(host)),
    ):
        item_id = wx.NewIdRef()
        menu.Append(item_id, host._menu_label(label, command))
        host.frame.Bind(wx.EVT_MENU, lambda _e, h=handler: h(), id=item_id)
        ids.append(item_id)
    host._keep_menu_ids(*ids)
    return tuple(ids)


def open_suggest(host: Any) -> None:
    from quill.ui.radio.suggest_pick_dialog import open_suggest_dialog

    open_suggest_dialog(host)


def open_picks(host: Any) -> None:
    """Offer the catalogue. Falls back to the bundled copy, never to nothing."""
    from quill.core.community_picks import (
        PICKS_SIGNATURE_URL,
        PICKS_URL,
        CommunityPicksError,
        _fetch,
        parse,
        verify,
    )

    tasks = getattr(host, "_task_manager", None)
    safe = bool(getattr(host, "_safe_mode", False))

    def _work(**_kwargs: Any) -> Catalogue:
        if safe:
            return load_bundled()
        import json

        try:
            raw = _fetch(PICKS_URL)
            signature = _fetch(PICKS_SIGNATURE_URL)
        except CommunityPicksError:
            # The bundled copy is why this is a degraded experience rather than
            # an error message: the picker still works, it is just not fresh.
            return load_bundled()
        trusted, why = verify(raw, signature)
        if not trusted:
            # Fail closed. An unsigned or altered catalogue is exactly the file
            # somebody would substitute to point listeners somewhere else, and
            # the bundled copy means refusing costs a stale list, not a dead
            # window. Recorded so it is findable an hour later, not just spoken.
            _report_problem(host, f"The Community Picks list was not used: {why}.")
            return load_bundled()
        try:
            fetched = parse(json.loads(raw.decode("utf-8", "replace")), app="radio")
        except (CommunityPicksError, ValueError):
            return load_bundled()
        return fetched if not fetched.is_empty else load_bundled()

    def _done(_op: str, catalogue: Any) -> None:
        _offer(host, catalogue)

    if tasks is None:
        _done("", _work())
        return
    host._announce("Reading the Community Picks list...")
    tasks.submit(
        "radio-community-picks",
        _work,
        on_success=lambda op, catalogue: host._wx.CallAfter(_done, op, catalogue),
        on_failure=lambda op, _e: host._wx.CallAfter(_done, op, load_bundled()),
    )


def _report_problem(host: Any, message: str) -> None:
    """Recent Problems, not just a spoken line: a transient announcement is
    gone by the time somebody wonders why the list looks old."""
    record = getattr(host, "record_recent_problem", None)
    if callable(record):
        try:
            record(message)
            return
        except Exception:  # noqa: BLE001 - reporting must never be the failure
            pass
    announce = getattr(host, "_announce", None)
    if callable(announce):
        announce(message)


def _offer(host: Any, catalogue: Catalogue) -> None:
    if catalogue.is_empty:
        host._announce("The Community Picks list is empty just now.")
        return
    library = _library()
    subscribed = {
        (show.feed_url or "").strip().lower() for show in getattr(library, "shows", []) or []
    }
    favorites = getattr(host, "_radio_favorites", None)
    saved = {
        (getattr(fav.station, "stream_url", "") or "").strip().lower()
        for fav in getattr(favorites, "favorites", []) or []
    }

    items = []
    for collection in catalogue.collections:
        for pick in collection.picks:
            have = (pick.feed_url or "").strip().lower() in subscribed or (
                pick.stream_url or ""
            ).strip().lower() in saved
            items.append(
                PickableItem(
                    key=pick.id,
                    # The collection is in the row because the two lists are
                    # flat: without it, "ACB Media 1" the station and the
                    # podcast of the same name read identically.
                    title=f"{pick.title} -- {collection.title}",
                    description=pick.description,
                    kind="podcast" if pick.feed_url else "station",
                    already_have=have,
                    payload=pick,
                )
            )

    heading = _HEADING
    if catalogue.bundled:
        heading += " (Showing the list that came with the app.)"
    chosen = choose_from_catalogue(
        host, title=_TITLE, heading=heading, items=items, chosen_label="What you are adding"
    )
    if chosen:
        _apply(host, chosen, library)


def _library() -> Any:
    try:
        from quill.core.paths import app_data_dir
        from quill.core.podcasts.subscriptions import load_library

        return load_library(app_data_dir())
    except Exception:  # noqa: BLE001 - a missing library is not a crash
        return None


def _apply(host: Any, chosen: list[PickableItem], library: Any) -> None:
    from quill.core.paths import app_data_dir
    from quill.core.podcasts.pick_apply import PickToApply, apply_picks
    from quill.core.podcasts.subscriptions import save_library

    picks = [
        PickToApply(
            title=item.payload.title,
            feed_url=item.payload.feed_url,
            stream_url=item.payload.stream_url,
            node_id=item.payload.node_id,
            homepage=item.payload.homepage,
            description=item.payload.description,
            language=item.payload.language,
        )
        for item in chosen
    ]
    favorites = getattr(host, "_radio_favorites", None)
    outcome = apply_picks(
        picks,
        library=library,
        favorites=favorites,
        folder=_FOLDER,
        stream_source="Community Picks",
    )
    if library is not None and outcome.subscribed:
        save_library(app_data_dir(), library)
    if favorites is not None and outcome.favorited:
        save = getattr(host, "_save_radio_favorites", None)
        if callable(save):
            save()
    host._announce(_said(outcome))


def _said(outcome: Any) -> str:
    if outcome.nothing_happened:
        return "Nothing was added; you already had all of them."
    parts = []
    if outcome.subscribed:
        shows = "show" if outcome.subscribed == 1 else "shows"
        parts.append(f"Subscribed to {outcome.subscribed} {shows}")
    if outcome.favorited:
        parts.append(f"added {outcome.favorited} to Favorites under {_FOLDER}, in your order")
    said = ", and ".join(parts) + "."
    return said[0].upper() + said[1:]


__all__ = ["append_menu_items", "open_picks", "open_suggest", "register"]
