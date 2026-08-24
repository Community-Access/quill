"""Quill Radio's media keys, on every window rather than only the menu bar.

The transport keys (play, stop, speed, chapters) have travelled with the
listener since :mod:`quill.ui.radio.transport_keys` landed. The *media* keys
did not: Show Video, Captions, Transcript, Audio and Described Audio, and Video
Information are menu items on the app frame, and **a menu accelerator only
fires for the frame that owns the menu bar**. So standing in Browse Stations,
in Manage Favorites, in Song History -- or in the Video Window itself -- none
of them existed, and the only clue was that nothing happened ("many of the
hotkeys are not working in each window that should be", 2026-08-23).

Kept out of ``transport_commands`` deliberately, and this is the whole reason
this module exists rather than five more rows in that table: those rows are
**shared with Quill Cast**, which binds Ctrl+Shift+K to Audio Output Device.
A key that means Captions in one app and an output device in the other is
worse than a key that is missing from one of them. So these are Radio's, and
they are added only when the host's player is Radio's -- asked by capability
(``caption_track``), the same way ``video_commands`` asks whether an engine can
show a picture.

Refusals are the commands' own: a station with no video, no captions or no
described audio says so, from any window, exactly as it does from the menu.
"""

from __future__ import annotations

from typing import Any

#: Key -> the verb it runs. The keys are the ones already printed in the
#: Playback, Audio and Video menus: a key that travels must be the same key,
#: or the menu is teaching the wrong one.
MEDIA_KEYS: tuple[tuple[str, str], ...] = (
    ("Ctrl+Shift+V", "video"),
    ("Ctrl+Shift+K", "captions"),
    ("Ctrl+Shift+T", "transcript"),
    ("Ctrl+Shift+A", "audio_tracks"),
    ("Ctrl+Shift+I", "information"),
    ("Ctrl+Alt+D", "described"),
)


def is_radio_host(host: Any) -> bool:
    """Whether *host*'s player is Quill Radio's, asked by capability.

    Quill Cast installs the same transport table and must not acquire Radio's
    media keys with it; its controller has no caption track to offer.
    """
    from quill.ui.radio.transport_keys import _controller_of

    controller = _controller_of(host)
    return controller is not None and hasattr(controller, "caption_track")


def perform(host: Any, verb: str) -> None:
    """Run one media verb against the app frame behind *host*.

    The frame, not the window the key was pressed in: these commands open
    dialogs, submit background work and read the player, so they want the
    object that has ``frame``, ``_task_manager`` and ``_show_message_box`` --
    which a modeless surface reaches through its ``_download_host``.
    """
    from quill.ui.radio import transcript_command, video_commands

    app = host if hasattr(host, "frame") else getattr(host, "_download_host", host)
    if verb == "video":
        video_commands.toggle_video(app)
    elif verb == "captions":
        video_commands.toggle_captions(app)
    elif verb == "information":
        video_commands.video_information(app)
    elif verb == "transcript":
        transcript_command.open_transcript(app)
    elif verb == "audio_tracks":
        transcript_command.open_audio_tracks(app)
    elif verb == "described":
        transcript_command.play_described_audio(app)


def entries(window: Any, host: Any, wx: Any) -> list:
    """Accelerator entries for the media keys, bound on *window*.

    Handed to ``transport_keys.install`` so one table carries the transport,
    the window traversal and these -- wx has no way to append to an accelerator
    table, and a second ``SetAcceleratorTable`` silently replaces the first
    (the bug that killed Ctrl+Tab on every surface with the transport).
    """
    if not is_radio_host(host):
        return []
    built: list[Any] = []
    refs: list[Any] = []
    for key, verb in MEDIA_KEYS:
        command_id = wx.NewIdRef()
        entry = wx.AcceleratorEntry(cmd=int(command_id))
        try:
            parsed = bool(entry.FromString("\t" + key)) and bool(entry.GetKeyCode())
        except Exception:  # noqa: BLE001 - an unparsable key is a skipped key
            parsed = False
        if not parsed:
            continue
        built.append(entry)
        refs.append(command_id)
        window.Bind(wx.EVT_MENU, lambda _e, v=verb: perform(host, v), id=int(command_id))
    # Pinned: wx frees an unreferenced NewIdRef, and a freed id is an
    # accelerator that fires nothing.
    window._media_key_refs = refs
    return built
