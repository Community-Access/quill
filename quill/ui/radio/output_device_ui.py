"""Playback-menu "Output Device..." quick picker for Quill Radio (#1253).

A dedicated, keyboard-shortcut-reachable way to change the audio output device
(sound card) without opening full Preferences. Thin wx wiring over the existing
device engine in :mod:`quill.ui.radio.mpv_radio_engine` and the same
``history.output_device`` persistence Preferences already uses. Kept out of
radio.py so that at-budget module stays lean (mirrors :mod:`backup_ui`).

The host ``frame`` provides: ``frame.frame`` (the wx.Frame), ``frame._announce``,
``frame._show_message_box``, ``frame._radio_history``, ``frame._radio_controller``.
"""

from __future__ import annotations

from typing import Any

from quill.ui import modal_stack


def choose_output_device(frame: Any) -> None:
    """Prompt for an audio output device and route playback to it immediately."""
    import wx

    from quill.core.paths import app_data_dir
    from quill.core.radio import history as radio_history
    from quill.ui.radio.mpv_radio_engine import (
        list_audio_devices,
        mpv_output_device_available,
        output_device_choices,
    )

    history = frame._radio_history
    device_labels, device_names, device_index = output_device_choices(
        list_audio_devices(), history.output_device
    )
    if not mpv_output_device_available():
        # No mpv, so no device list of our own: Windows Media is playing, and
        # the device it plays on is the one Windows gives this app.
        _open_windows_route(
            frame,
            "Quill Radio is playing through Windows Media, because the mpv engine "
            "is not installed in this copy.",
        )
        return

    with wx.SingleChoiceDialog(
        modal_stack.parent_window(frame),
        "Send Quill Radio's audio to which device?",
        "Output Device",
        device_labels,
    ) as dialog:
        if device_index >= 0:
            dialog.SetSelection(device_index)
        if dialog.ShowModal() != wx.ID_OK:
            return
        chosen = device_names[dialog.GetSelection()]
        chosen_label = device_labels[dialog.GetSelection()]

    if chosen == history.output_device:
        frame._announce(f"Output device unchanged: {chosen_label}.")
        return
    if chosen and history.playback_engine == "wx":
        # Windows Media (classic) plays on the device Windows gives this app,
        # and nothing in wx.media takes a device name (2026-09-29). The engine
        # preference is the listener's and stays; the route that works under
        # it is Windows' own per-app device, the same answer QUILL Cast gives
        # (ui/media/output_device). Jeff: "why is it forcing automatic mode
        # and mpv when switching if windows media is selected, that should
        # not be necessary at all. What if mpv is not enabled?" And no
        # question first: "drop the yes/no directly, no need to ask."
        _open_windows_route(
            frame,
            f"The playback engine is Windows Media (classic), so this list cannot "
            f"send the radio to {chosen_label}.",
        )
        return
    history.output_device = chosen
    radio_history.save_history(app_data_dir(), history)
    # A station already on air moves to the new device immediately.
    frame._radio_controller.set_output_device(chosen)
    frame._announce(f"Output device: {chosen_label}.")


def _open_windows_route(frame: Any, reason: str) -> None:
    """Windows Media cannot take a device from us; Windows' Sound settings can
    give Quill Radio one, so open them straight away and say why in one
    sentence. No question first. The setting here is left alone, because it
    would be naming a device this engine does not use."""
    from quill.ui.media.output_device import open_windows_app_volume

    if open_windows_app_volume():
        frame._announce(
            f"{reason} Windows' Sound settings opened: find Quill Radio under Volume "
            "mixer and choose its output device there."
        )
    else:
        frame._announce(
            f"{reason} Give Quill Radio its device in Windows' Sound settings, under "
            "Volume mixer; that page could not be opened from here."
        )
