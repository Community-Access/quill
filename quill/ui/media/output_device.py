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

from collections.abc import Callable
from typing import Any, NamedTuple

__all__ = [
    "WINDOWS_APP_VOLUME_URI",
    "OutputDeviceBinding",
    "choose_output_device",
    "explain_no_engine_support",
    "pick_output_device",
]


class OutputDeviceBinding(NamedTuple):
    """What an app has to say to get the family's output-device picker.

    Four things, because four are all it takes and asking for a frame type
    would tie the picker to one app's shape -- which is how Cast ended up
    with a menu item that could only ever say no.

    * *app_name* -- what the prompt and the announcements call this app.
    * *engine* -- the engine ACTUALLY playing, not a guess from what the
      machine has installed: a computer with libmpv can still be on the
      classic control, and only the live engine knows.
    * *current* -- the device saved for this app ("" = system default).
    * *save* -- persist the new choice for the next launch.
    """

    app_name: str
    engine: Any
    current: str
    save: Callable[[str], None]


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
        from quill.ui.audio.output_routing import output_device_routing_available

        return bool(output_device_routing_available())
    except Exception:  # noqa: BLE001 - no engine is simply "cannot"
        return False


def _binding(host: Any) -> OutputDeviceBinding | None:
    """The app's own answer, or None when it has not opted in.

    Never raises: an app whose engine is still starting (or already gone)
    falls through to the routes below rather than costing the listener the
    command.
    """
    ask = getattr(host, "audio_output_binding", None)
    if not callable(ask):
        return None
    try:
        binding = ask()
    except Exception:  # noqa: BLE001 - no answer is "not opted in"
        return None
    return binding if isinstance(binding, OutputDeviceBinding) else None


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

    # An app that can say what it plays through gets the real list. This is the
    # opt-in every app but Radio lacked: the engines could not be pointed at a
    # device when this module was written, and once the modern Windows Media
    # engine could (2026-09-29) the only thing still missing was each app
    # saying which engine and which setting are its own.
    binding = _binding(host)
    if binding is not None:
        pick_output_device(
            getattr(host, "frame", None) or host,
            app_name=binding.app_name,
            current=binding.current,
            engine=binding.engine,
            announce=announce,
            save=binding.save,
        )
        return

    # Radio keeps its own path: it has an engine PREFERENCE as well as an
    # engine, and the interplay between the two (a device chosen while the
    # classic control is pinned) is Radio's to explain.
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


def pick_output_device(
    parent: Any,
    *,
    app_name: str,
    current: str,
    engine: Any,
    announce: Any,
    save: Any,
) -> None:
    """Choose the sound card *app_name* plays through. The family's one picker.

    Quill Radio has had a picker since #1253 and every other app had the
    "Windows can do it for you" sentence, because the engines those apps play
    through had no device API. That stopped being true when the modern Windows
    Media engine arrived (2026-09-29): it can be pointed at a device, and so
    can libmpv, so the honest answer for the rest of the family is now a real
    list rather than a redirect.

    The redirect survives for the one case where it is still the truth: the
    classic ``wx.media`` control, which has no device API at all. There the
    route that works is Windows' own per-app setting, and saying so beats a
    list that would do nothing.

    *engine* is the engine actually playing -- not a guess from what the
    machine has installed, because a machine with libmpv can still be on the
    classic control. *save* persists the choice for the next launch; *announce*
    is the app's own speech. Says only what the screen reader does not: the
    dialog names itself, so only the outcome is spoken (GATE-13).
    """
    import wx

    from quill.ui import modal_stack
    from quill.ui.audio.output_routing import (
        engine_routes_devices,
        list_output_devices,
        set_engine_output_device,
    )
    from quill.ui.radio.mpv_radio_engine import output_device_choices

    if not engine_routes_devices(engine):
        _open_windows_route(
            parent,
            announce,
            app_name,
            f"{app_name} is playing through the classic Windows Media engine, which "
            "cannot be pointed at a device from here.",
        )
        return

    labels, names, index = output_device_choices(list_output_devices(), current)
    with wx.SingleChoiceDialog(
        modal_stack.parent_window(parent),
        f"Send {app_name}'s audio to which device?",
        "Output Device",
        labels,
    ) as dialog:
        if index >= 0:
            dialog.SetSelection(index)
        if dialog.ShowModal() != wx.ID_OK:
            return
        chosen = names[dialog.GetSelection()]
        chosen_label = labels[dialog.GetSelection()]

    if chosen == current:
        announce(f"Output device unchanged: {chosen_label}.")
        return
    if not set_engine_output_device(engine, chosen):
        # The device is in the list and the engine still would not take it: a
        # headset asleep, a card another program holds, an id Windows changed.
        # The setting is NOT saved -- a saved device the engine cannot open is
        # exactly the split between what the app says and what you hear that
        # this whole area exists to end.
        announce(f"{chosen_label} could not be opened, so the output device is unchanged.")
        return
    save(chosen)
    announce(f"Output device: {chosen_label}.")


def _open_windows_route(parent: Any, announce: Any, app_name: str, reason: str) -> None:
    """Windows' own per-app device page, opened at once and explained in one
    sentence. No question first: the list cannot help and this can."""
    if open_windows_app_volume():
        announce(
            f"{reason} Windows' Sound settings opened: find {app_name} under Volume "
            "mixer and choose its output device there."
        )
    else:
        announce(
            f"{reason} Give {app_name} its device in Windows' Sound settings, under "
            "Volume mixer; that page could not be opened from here."
        )
