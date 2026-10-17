"""Station Details: search the station pack, and read what it knows.

The client half of the station enrichment program (Jeff's todo P2 #33). The
facts, the search and every sentence are wx-free in
:mod:`quill.core.radio.enrichment`; this is the window, its menu row and its
key (View > Station Details..., Alt+Shift+I, I for information).

One window, three controls, top to bottom, each with its own label and F1
sentence:

- **Find** -- a search field. Results follow as you type (silently: the list
  is not focused, and a count read on every keystroke would be chatter); Enter
  moves to the results, or says plainly that nothing matched.
- **Results** -- one row per station, saying *why* it matched ("KUOW, matched
  frequency: 94.9 FM"), which a listener cannot otherwise know without opening
  every row (GATE-13 allows it: it is information the reader cannot know).
- **Details** -- read-only text, one labelled line per fact ("Call sign:
  KUOW"), then where the facts came from and any credit a licence requires.
  Read-only on purpose: these are the pack's facts, not the listener's notes.

When a station is playing and the pack knows it, the window opens with that
station already in the list and its details showing.

The pack is installed (verified against the bundled publisher key) the first
time the window opens, on the task manager when there is one, so a large pack
never freezes the window. A refused pack is said once, in one sentence; the
facts already installed stay as they were.
"""

from __future__ import annotations

import logging
from typing import Any

from quill.ui.dialog_contract import apply_modal_ids, bind_close_button, set_accessible_name

logger = logging.getLogger(__name__)

TITLE = "Station Details"
COMMAND = "radio.station_details"


def register(app: Any) -> None:
    app.commands.try_register(
        COMMAND, "Station Details", lambda: open_station_details(app), feature_id="core.radio"
    )


def append_menu_item(host: Any, menu: Any, wx: Any) -> Any:
    """Append View > Station Details..., bound to *host*. Returns the id."""
    item_id = wx.NewIdRef()
    item = menu.Append(item_id, host._menu_label("Station Deta&ils...", COMMAND))
    item.SetHelp(
        "Search stations by name, call sign, frequency, slogan or place, and "
        "read what the station pack knows about each one."
    )
    host.frame.Bind(wx.EVT_MENU, lambda _e: open_station_details(host), id=item_id)
    return item_id


# -- the store, installed once per session ------------------------------------


def _prepare_store(host: Any) -> tuple[Any, str]:
    """Open the store and install the bundled pack. Returns (store, sentence).

    The sentence is the outcome worth saying, or "" when there is nothing to
    say (no bundled pack, or it was already installed).
    """
    from quill.core.paths import machine_local_dir
    from quill.core.radio.enrichment import EnrichmentError, PackRefusedError
    from quill.core.radio.enrichment.client import (
        install_bundled,
        open_store,
        outcome_sentence,
        refusal_sentence,
    )

    # machine_local_dir, like the station catalog: regenerable rows that a
    # synced data folder should not carry between machines.
    store = open_store(machine_local_dir())
    try:
        result = install_bundled(store)
    except (PackRefusedError, EnrichmentError) as error:
        logger.warning("Station pack not installed: %s", error)
        return store, refusal_sentence(error)
    return store, (outcome_sentence(result) if result is not None else "")


def open_station_details(host: Any) -> None:
    """The command: make sure the store is ready, then show the window."""
    store = getattr(host, "_radio_enrichment", None)
    if store is not None:
        show_station_details(host, store)
        return
    if getattr(host, "_radio_enrichment_opening", False):
        return  # a second press while the first is still preparing opens nothing
    host._radio_enrichment_opening = True

    def _ready(prepared: tuple[Any, str]) -> None:
        host._radio_enrichment_opening = False
        store, sentence = prepared
        host._radio_enrichment = store
        if sentence:
            host._announce(sentence)
        show_station_details(host, store)

    def _failed(_op: str, error: BaseException) -> None:
        host._radio_enrichment_opening = False
        logger.warning("Station details unavailable", exc_info=error)
        host._announce("The station details could not be opened.")

    task_manager = getattr(host, "_task_manager", None)
    if task_manager is None:
        try:
            _ready(_prepare_store(host))
        except Exception as error:  # noqa: BLE001 - a broken store is a sentence
            _failed("station-details", error)
        return
    task_manager.submit(
        "radio-station-details",
        lambda **_kwargs: _prepare_store(host),
        on_success=lambda _op, prepared: _ready(prepared),
        on_failure=_failed,
    )


def _playing_station(host: Any) -> Any:
    controller = getattr(host, "_radio_controller", None)
    return getattr(getattr(controller, "state", None), "station", None)


# -- the window -----------------------------------------------------------------


def show_station_details(host: Any, store: Any) -> None:
    """Build and show the window. Modal, house pattern."""
    wx = host._wx
    from quill.core.radio.enrichment.client import details_text, status_sentence
    from quill.core.radio.enrichment.store import SearchHit

    dialog = wx.Dialog(host.frame, title=TITLE, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
    dialog.SetMinSize(wx.Size(620, 480))
    root = wx.BoxSizer(wx.VERTICAL)

    status = wx.StaticText(dialog, label=status_sentence(store))
    status.Wrap(580)
    root.Add(status, 0, wx.ALL, 8)

    root.Add(
        wx.StaticText(
            dialog, label="&Find stations by name, call sign, frequency, slogan or place:"
        ),
        0,
        wx.LEFT | wx.RIGHT,
        8,
    )
    query = wx.TextCtrl(dialog, style=wx.TE_PROCESS_ENTER)
    set_accessible_name(query, "Find stations by name, call sign, frequency, slogan or place")
    query.SetHelpText(
        "Type any part of what you know about a station: its name, its call "
        "sign such as KUOW, its frequency such as 94.9, a word from its "
        "slogan or description, or a city. The results below follow as you "
        "type; press Enter to move to them, or, when nothing matched, to look "
        "for names spelled close to what you typed."
    )
    root.Add(query, 0, wx.EXPAND | wx.ALL, 8)

    root.Add(wx.StaticText(dialog, label="&Results:"), 0, wx.LEFT | wx.RIGHT, 8)
    results = wx.ListBox(dialog, choices=[], style=wx.LB_SINGLE)
    set_accessible_name(results, "Results")
    results.SetHelpText(
        "Stations the station pack knows that match your search, best first. "
        "Each row says what matched, such as the frequency or a word from the "
        "slogan. The details of the highlighted station are below."
    )
    root.Add(results, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

    root.Add(wx.StaticText(dialog, label="Deta&ils:"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
    details = wx.TextCtrl(dialog, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2)
    set_accessible_name(details, "Details")
    details.SetHelpText(
        "What the station pack knows about the highlighted station, one "
        "labelled line per fact, then where those facts came from. Read only; "
        "arrow through it, or select and copy any line."
    )
    root.Add(details, 1, wx.EXPAND | wx.ALL, 8)

    buttons = wx.BoxSizer(wx.HORIZONTAL)
    close_btn = wx.Button(dialog, wx.ID_CANCEL, "Close")
    close_btn.SetHelpText("Closes Station Details. Nothing is changed by closing.")
    buttons.AddStretchSpacer()
    buttons.Add(close_btn)
    root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
    dialog.SetSizer(root)

    hits: list[Any] = []

    def _show_details() -> None:
        index = results.GetSelection()
        if index == wx.NOT_FOUND or index >= len(hits):
            details.ChangeValue("")
            return
        try:
            facts = store.details(hits[index].key)
            details.ChangeValue(details_text(facts, store.sources()))
        except Exception:  # noqa: BLE001 - an unreadable row is a sentence
            logger.debug("Station details could not be read", exc_info=True)
            details.ChangeValue("The details for this station could not be read.")

    def _fill(new_hits: list[Any]) -> None:
        hits[:] = new_hits
        results.Set([hit.row_text for hit in hits])
        if hits:
            results.SetSelection(0)
        _show_details()

    def _search(*, fuzzy: bool = False) -> None:
        text = query.GetValue().strip()
        if not text:
            _fill([])
            return
        try:
            _fill(store.search(text, fuzzy=fuzzy))
        except Exception:  # noqa: BLE001 - a failed search is "no results"
            logger.debug("Station search failed", exc_info=True)
            _fill([])

    def _on_enter(_event: Any) -> None:
        if not hits:
            # Close spellings only now: that fallback reads every name, which
            # is too slow to run on every keystroke of a large pack.
            _search(fuzzy=True)
        if hits:
            results.SetFocus()
            return
        text = query.GetValue().strip()
        if text:
            # The list is empty and unfocused: the reader cannot say so.
            host._announce(f"No stations match {text}.")

    query.Bind(wx.EVT_TEXT, lambda _e: _search())
    query.Bind(wx.EVT_TEXT_ENTER, _on_enter)
    results.Bind(wx.EVT_LISTBOX, lambda _e: _show_details())

    station = _playing_station(host)
    if station is not None:
        try:
            facts = store.find_for_station(
                str(getattr(station, "station_uuid", "") or ""),
                str(getattr(station, "stream_url", "") or ""),
                str(getattr(station, "name", "") or ""),
            )
        except Exception:  # noqa: BLE001 - no playing-station row is fine
            facts = None
        if facts is not None:
            _fill([SearchHit(key=facts.key, name=facts.name, note="playing now")])

    bind_close_button(dialog, close_btn, modeless=False)
    apply_modal_ids(dialog, cancel_id=wx.ID_CANCEL, escape_id=wx.ID_CANCEL)
    dialog.Fit()
    dialog.CentreOnParent()
    wx.CallAfter(query.SetFocus)
    try:
        host._show_modal_dialog(dialog, TITLE)
    finally:
        dialog.Destroy()


__all__ = [
    "COMMAND",
    "TITLE",
    "append_menu_item",
    "open_station_details",
    "register",
    "show_station_details",
]
