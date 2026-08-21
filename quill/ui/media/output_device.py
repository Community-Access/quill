"""Which sound card the audio comes out of -- for whichever engine is playing.

Quill Radio has had a device picker since #1253, and QUILL Cast has had nothing:
grep for ``output_device`` across ``ui/podcasts`` and ``core/podcasts`` returned
empty. So a listener with a USB headset and desk speakers could route the radio
and not the podcast.

**The honest answer is not one picker.** Radio's picker works because Radio can
play through libmpv, which enumerates devices and can be told to use one. Cast
plays through ``wx.media``, which has no such control at all, and it does not
bundle libmpv -- 110 MB for one menu item is not a trade worth making for an
app whose whole design is to stay small.

An item that opened a picker doing nothing would be worse than no item. So this
module answers the question two ways, and says which one it is using:

* **The engine can do it** -- hand over to the engine's own picker.
* **The engine cannot** -- say so in one sentence, and offer the thing that
  *does* work: Windows' own per-app sound settings, where this app can be
  pointed at any output device permanently. That is a real capability, it is
  accessible, and it is two keystrokes away once somebody knows it exists.

The one thing this must never do is imply it did something it did not.
"""

from __future__ import annotations

from typing import Any

__all__ = ["WINDOWS_APP_VOLUME_URI", "choose_output_device", "explain_no_engine_support"]

#: Windows' per-app volume and device page. Every app on the machine is listed
#: with its own output picker, and the setting persists across restarts.
WINDOWS_APP_VOLUME_URI = "ms-settings:apps-volume"

_NO_ENGINE_SUPPORT = (
    "QUILL Cast plays through Windows' default playback device. It cannot "
    "switch devices from inside the app, because the player it uses does not "
    "offer that. Windows can do it for you and it sticks: in Sound settings, "
    "under Volume mixer, every app has its own output device. Open that now?"
)


def explain_no_engine_support() -> str:
    """The sentence said when the engine cannot route audio itself."""
    return _NO_ENGINE_SUPPORT


def _engine_can_choose() -> bool:
    """Whether a device picker would actually do anything on this machine."""
    try:
        from quill.ui.radio.mpv_radio_engine import mpv_output_device_available

        return bool(mpv_output_device_available())
    except Exception:  # noqa: BLE001 - no engine is simply "cannot"
        return False


def open_windows_app_volume() -> bool:
    """Open Windows' per-app volume page. Returns whether it opened."""
    try:
        import os

        os.startfile(WINDOWS_APP_VOLUME_URI)  # type: ignore[attr-defined]  # noqa: S606
    except Exception:  # noqa: BLE001 - an OS that will not open it is not an error
        return False
    return True


def choose_output_device(host: Any) -> None:
    """Route this app's audio, by whichever route this app actually has.

    *host* needs ``_announce`` and, for the engine path, whatever
    ``ui.radio.output_device_ui`` already asks of a Radio frame.
    """
    import wx

    announce = getattr(host, "_announce", None) or (lambda _m: None)

    if _engine_can_choose() and getattr(host, "_radio_history", None) is not None:
        from quill.ui.radio.output_device_ui import choose_output_device as pick

        pick(host)
        return

    from quill.ui.dialog_contract import show_message_box

    answer = show_message_box(
        _NO_ENGINE_SUPPORT,
        "Audio Output Device",
        wx.YES_NO | wx.ICON_QUESTION,
        getattr(host, "frame", None) or host,
        announce=announce,
    )
    if answer != wx.YES:
        return
    if open_windows_app_volume():
        announce(
            "Sound settings opened. Find QUILL Cast under Volume mixer and choose "
            "its output device."
        )
    else:
        announce("Windows Sound settings could not be opened on this machine.")
