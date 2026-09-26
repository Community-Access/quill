"""Ask, once, whether a new portable copy should bring an earlier copy's favorites.

Runs in ``quill.apps.radio.main`` after ``wx.App`` exists and before anything
reads the data folder, so a copied favorites file, history and schedule are
simply what the app loads -- nothing has to be reloaded behind the listener's
back. The decisions are all in :mod:`quill.core.radio.portable_migration`.
"""

from __future__ import annotations

_CAPTION = "Favorites from an earlier Quill Radio"


def offer_earlier_favorites() -> None:
    """Offer the profile's favorites to a portable copy that has none. Never raises."""
    try:
        from quill.core.paths import app_data_dir, portable_bundle_root
        from quill.core.radio import portable_migration as pm

        if portable_bundle_root() is None:
            return  # an installed copy already reads the profile
        bundle_data = app_data_dir()
        earlier = pm.find_earlier_data(bundle_data, pm.host_profile_dir())
        if earlier is None:
            return
        import wx

        from quill.ui.dialog_contract import show_message_box

        count = earlier.favorites
        stations = "1 favorite station" if count == 1 else f"{count} favorite stations"
        answer = show_message_box(
            f"An earlier Quill Radio on this computer has {stations}. Copy them, "
            "with your settings, recording schedule and reminders, into this "
            "portable copy?\n\nThe earlier copy is left exactly as it is. Choose "
            "No to start empty; you will not be asked again.",
            _CAPTION,
            wx.YES_NO | wx.YES_DEFAULT | wx.ICON_QUESTION,
        )
        copied = answer == wx.YES
        if copied:
            pm.copy_earlier_data(earlier, bundle_data)
        pm.remember_answer(bundle_data, copied=copied)
    except Exception:  # noqa: BLE001 - an offer must never stop the app starting
        import logging

        logging.getLogger(__name__).exception("Portable favorites offer failed")
