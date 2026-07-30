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
        frame._show_message_box(
            "Choosing a specific output device needs the libmpv playback engine. "
            'Switch to it in Preferences (under "Radio playback engine"), then '
            "pick your device here. Until then, Quill Radio uses your system's "
            "default playback device.",
            "Output Device",
            wx.OK | wx.ICON_INFORMATION,
        )
        return

    with wx.SingleChoiceDialog(
        frame.frame,
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
    history.output_device = chosen
    radio_history.save_history(app_data_dir(), history)
    # A station already on air moves to the new device immediately.
    frame._radio_controller.set_output_device(chosen)
    frame._announce(f"Output device: {chosen_label}.")
