"""Community > ACB Media Podcasts...: pick from ACB's lineup, keep the order.

The first user of the shared picker
(:mod:`quill.ui.radio.catalogue_picker_dialog`). Everything app-shaped lives
here -- fetching off the UI thread, working out what you already have, saving
both stores, and saying what happened -- so the dialog itself stays a dialog
and Community Picks can reuse it unchanged.

Reading ACB's directory is a network call, so it is refused in Safe Mode and
never made on the UI thread: forty feeds' worth of OPML over a slow connection
is several seconds, and a window that freezes for several seconds is a window
somebody reports as crashed.
"""

from __future__ import annotations

from typing import Any

from quill.core.podcasts.acb_media_podcasts import ACB_PICKED_FOLDER
from quill.ui.radio.catalogue_picker_dialog import PickableItem, choose_from_catalogue

_TITLE = "ACB Media Podcasts"
_HEADING = (
    "Everything ACB Media publishes. Arrow the list on the left to hear what "
    "each one is, add the ones you want, then arrange them however you like."
)


def register(app: Any) -> None:
    """Register the command, beside the other Community verbs."""
    commands: Any = app.commands
    commands.try_register(
        "radio.acb_podcasts",
        "ACB Media Podcasts...",
        lambda: open_picker(app),
        feature_id="core.radio",
    )


def append_menu_item(host: Any, menu: Any, wx: Any) -> Any:
    """One item on the Community menu. The caller pins the id."""
    item_id = wx.NewIdRef()
    menu.Append(item_id, host._menu_label("ACB Media &Podcasts...", "radio.acb_podcasts"))
    host.frame.Bind(wx.EVT_MENU, lambda _e: open_picker(host), id=item_id)
    host._keep_menu_ids(item_id)
    return item_id


def open_picker(host: Any) -> None:
    """Fetch the directory, then offer it. Never raises into the menu."""
    if getattr(host, "_safe_mode", False):
        host._announce("Safe Mode is on, so ACB's podcast directory is not fetched.")
        return

    from quill.core.podcasts.acb_media_podcasts import fetch_acb_media_catalog

    tasks = getattr(host, "_task_manager", None)

    def _work(**_kwargs: Any) -> Any:
        return fetch_acb_media_catalog()

    def _done(_op: str, shows: Any) -> None:
        _offer(host, list(shows))

    def _failed(_op: str, error: BaseException) -> None:
        host._announce(f"ACB's podcast directory could not be read. {error}.")

    host._announce("Reading ACB's podcast directory...")
    if tasks is None:
        try:
            _done("", _work())
        except Exception as error:  # noqa: BLE001 - reported, never raised at a menu
            _failed("", error)
        return
    tasks.submit(
        "radio-acb-podcast-directory",
        _work,
        on_success=lambda op, shows: host._wx.CallAfter(_done, op, shows),
        on_failure=lambda op, error: host._wx.CallAfter(_failed, op, error),
    )


def _library(host: Any) -> Any:
    """The podcast library, loaded fresh. ``None`` when this app has none."""
    try:
        from quill.core.paths import app_data_dir
        from quill.core.podcasts.subscriptions import load_library

        return load_library(app_data_dir())
    except Exception:  # noqa: BLE001 - a missing library is not a crash
        return None


def _offer(host: Any, shows: list[Any]) -> None:
    if not shows:
        host._announce("ACB's podcast directory is empty just now. Try again later.")
        return
    library = _library(host)
    subscribed = {
        (show.feed_url or "").strip().lower() for show in getattr(library, "shows", []) or []
    }
    items = [
        PickableItem(
            key=show.feed_url,
            title=show.title,
            description=show.description,
            already_have=show.feed_url.strip().lower() in subscribed,
            payload=show,
        )
        for show in shows
    ]
    already = sum(1 for item in items if item.already_have)
    heading = _HEADING
    if already:
        heading += f" You already have {already} of these."

    chosen = choose_from_catalogue(
        host, title=_TITLE, heading=heading, items=items, chosen_label="What you are adding"
    )
    if not chosen:
        return
    _apply(host, chosen, library)


def _apply(host: Any, chosen: list[PickableItem], library: Any) -> None:
    from quill.core.paths import app_data_dir
    from quill.core.podcasts.pick_apply import PickToApply, apply_picks
    from quill.core.podcasts.subscriptions import save_library

    picks = [
        PickToApply(
            title=item.payload.title,
            feed_url=item.payload.feed_url,
            homepage=item.payload.homepage,
            description=item.payload.description,
            language=item.payload.language,
            category=item.payload.category,
        )
        for item in chosen
    ]
    favorites = getattr(host, "_radio_favorites", None)
    outcome = apply_picks(
        picks,
        library=library,
        favorites=favorites,
        folder=ACB_PICKED_FOLDER,
        stream_source="ACB Media",
    )
    if library is not None and outcome.subscribed:
        save_library(app_data_dir(), library)
    if favorites is not None and outcome.favorited:
        save = getattr(host, "_save_radio_favorites", None)
        if callable(save):
            save()
    host._announce(_said(outcome))


def _said(outcome: Any) -> str:
    """What happened, in numbers -- a verb that touches many rows says how many."""
    if outcome.nothing_happened:
        return "Nothing was added; you already had all of them."
    parts = []
    if outcome.subscribed:
        shows = "show" if outcome.subscribed == 1 else "shows"
        parts.append(f"Subscribed to {outcome.subscribed} {shows}")
    if outcome.favorited:
        parts.append(
            f"added {outcome.favorited} to Favorites under {ACB_PICKED_FOLDER}, in your order"
        )
    said = ", and ".join(parts) + "."
    if outcome.already_subscribed:
        said += f" {outcome.already_subscribed} you already had."
    return said[0].upper() + said[1:]


__all__ = ["append_menu_item", "open_picker", "register"]
