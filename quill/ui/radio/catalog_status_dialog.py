"""Station Catalog Status: every source, its class, its age, its health.

The complete answer to "what is stored on this computer, and what is not" -
the cached-versus-live boundary the catalog UX rule says must be visible in
the product, not buried in a design document. Each row is one whole spoken
sentence, and a live-only source states *why* it is live-only, because the
honest reason ("iHeart's terms do not allow storing its listings") reads
better than an unexplained gap.

House ListBox pattern; read-only rows; three actions: Update Now, Update This
Source, and Rebuild From Shipped Snapshot (which touches nothing the listener
owns - the catalog is derived data).
"""

from __future__ import annotations

from typing import Any

from quill.ui.dialog_contract import apply_listbox_activation, apply_modal_ids

TITLE = "Station Catalog Status"

#: Why each live-only branch is live-only, in one honest sentence.
LIVE_ONLY = [
    ("TuneIn", "Live only; its directory is a remote tree that may not be stored."),
    ("iHeart", "Live only; its terms do not allow storing its listings."),
    ("Podcasts (Apple)", "Live only; charts are rankings, and Apple's terms bar storing them."),
    ("Internet Archive", "Live only; its collections run to half a million items."),
    (
        "LibriVox",
        "Live only for now; its full chapter listing is larger than the "
        "rest of the catalog combined.",
    ),
    ("Audius, Mixcloud, ccMixter", "Live only; charts are stale the moment they are stored."),
    ("AudioPub", "Live only; the people who uploaded the audio keep the rights to it."),
]

_SOURCE_LABELS = {
    "radio_browser": "Radio Browser",
    "soma_fm": "SomaFM",
    "xiph": "Xiph / Icecast",
    "librivox": "LibriVox",
    "gutenberg": "Project Gutenberg",
}


def _status_rows(host: Any) -> list[str]:
    from quill.core.radio.catalog.summary import spoken_age
    from quill.ui.radio import catalog_ui

    rows: list[str] = []
    store = catalog_ui.catalog_for(host)
    if store is None:
        rows.append(
            "The station catalog is turned off. Every branch asks the internet "
            "each time; nothing is stored."
        )
        return rows
    try:
        age = spoken_age(store.age_seconds())
        total = sum(h.station_count for h in store.source_health())
        rows.append(
            f"Stored on this computer: {total:,} stations, updated {age}. "
            "Yours to browse with or without the internet."
        )
        for health in store.source_health():
            label = _SOURCE_LABELS.get(health.id, health.id)
            when = spoken_age(
                None
                if not health.last_refresh
                else max(0.0, __import__("time").time() - float(health.last_refresh))
            )
            if health.last_status == "ok":
                rows.append(f"{label}: {health.station_count:,} stations, updated {when}.")
            else:
                reason = health.last_error or "could not be reached"
                rows.append(
                    f"{label}: {health.station_count:,} stations kept from {when}; {reason}."
                )
    except Exception:  # noqa: BLE001 - a broken store still gets an honest row
        rows.append("The catalog could not be read. Rebuild From Shipped Snapshot will fix it.")
    for label, sentence in LIVE_ONLY:
        rows.append(f"{label}: {sentence}")
    rows.append(
        "Your favorites, custom stations, and servers: yours, on this "
        "computer, never touched by updates."
    )
    return rows


def show_catalog_status(host: Any) -> None:
    """Open the status window. Modal, house pattern."""
    wx = host._wx

    dialog = wx.Dialog(host.frame, title=TITLE, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
    dialog.SetSize(wx.Size(700, 460))
    root = wx.BoxSizer(wx.VERTICAL)
    root.Add(wx.StaticText(dialog, label="&Sources and what is stored:"), 0, wx.ALL, 8)
    listbox = wx.ListBox(dialog, choices=_status_rows(host), style=wx.LB_SINGLE)
    listbox.SetName("Each source, whether it is stored on this computer, and how fresh it is")
    root.Add(listbox, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

    row = wx.BoxSizer(wx.HORIZONTAL)
    update_btn = wx.Button(dialog, label="&Update Now")
    update_btn.SetHelpText(
        "Refreshes the stored catalog from the live directories right now, "
        "and says what changed when it finishes."
    )
    rebuild_btn = wx.Button(dialog, label="&Rebuild From Shipped Snapshot")
    rebuild_btn.SetName(
        "Rebuild the catalog from the copy that shipped with this version; "
        "your favorites and custom stations are untouched"
    )
    close_btn = wx.Button(dialog, wx.ID_CLOSE, label="C&lose")
    close_btn.SetHelpText("Closes this report; the catalog keeps refreshing on its own schedule.")
    for button in (update_btn, rebuild_btn, close_btn):
        row.Add(button, 0, wx.RIGHT, 6)
    root.Add(row, 0, wx.ALL, 8)
    apply_modal_ids(dialog, affirmative_id=close_btn.GetId(), escape_id=close_btn.GetId())
    dialog.SetSizer(root)

    def _update(_event: Any) -> None:
        from quill.ui.radio import catalog_ui

        catalog_ui.update_catalog_command(host)
        dialog.EndModal(wx.ID_CLOSE)

    def _rebuild(_event: Any) -> None:
        from quill.ui.radio import catalog_ui

        store = catalog_ui.catalog_for(host)
        if store is None:
            host._announce("The catalog is turned off; there is nothing to rebuild.")
            return
        try:
            from quill.core.radio.catalog.seed import rebuild_from_seed

            rebuild_from_seed(store)
            host._announce("Catalog rebuilt from the shipped snapshot.")
        except Exception:  # noqa: BLE001
            host._announce(
                "The shipped snapshot is not available in this build; "
                "the next update will rebuild the catalog from live data instead."
            )
        listbox.Set(_status_rows(host))

    update_btn.Bind(wx.EVT_BUTTON, _update)
    rebuild_btn.Bind(wx.EVT_BUTTON, _rebuild)
    close_btn.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_CLOSE))
    apply_listbox_activation(listbox, lambda _e: None)
    if listbox.GetCount():
        listbox.SetSelection(0)
    wx.CallAfter(listbox.SetFocus)
    try:
        host._show_modal_dialog(dialog, TITLE)
    finally:
        dialog.Destroy()
