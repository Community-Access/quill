"""What Windows itself says is playing: the now-playing card, display only.

Windows keeps one "now playing" card per app -- the panel that appears on the
volume flyout when you press a volume key, and on the lock screen. It is
`SystemMediaTransportControls`, and the modern Windows Media engine owns one
already; nothing filled it in, so Quill's card was blank while every other
media app on the machine had a title in it.

**Display only, and deliberately so.** SMTC has two halves: the card, and the
buttons that route the keyboard's media keys. This module touches the first and
explicitly refuses the second, because the QuillVille apps already claim the
media keys themselves through ``RegisterHotKey``
(:meth:`quill.ui.app_shell.AppShellFrame._register_media_keys`), which is a
system-wide claim that works from the tray and without focus. Letting SMTC
claim them too is a fight the app can only lose quietly -- which is exactly why
:mod:`quill.ui.audio.winrt_engine` disables the command manager. Every button
flag here is set to False on purpose; the assertion that they stay False is a
test, not a comment.

### Why this is an accessibility feature, not decoration

The card is read by the screen reader when the volume flyout appears, and it is
what Windows' own "what is playing?" surfaces answer from. For a listener who
cannot see a taskbar thumbnail, the OS being able to say "Quill Radio -- BBC
Radio 4" is the difference between the machine knowing what is playing and only
the app knowing.

And it costs no speech of ours. The app must not *announce* what it puts here:
the reader already reads the flyout when it opens, and saying it again is the
over-announcing GATE-13 exists to stop. Nothing in this module speaks.

Every call is best effort. A machine without the modern engine, an engine mid
teardown, or a Windows build that refuses the call costs the card and never the
playback.
"""

from __future__ import annotations

import logging
from typing import Any

__all__ = [
    "MEDIA_KIND_MUSIC",
    "MEDIA_KIND_VIDEO",
    "clear_now_playing",
    "set_playback_status",
    "supports_now_playing",
    "update_now_playing",
]

_log = logging.getLogger(__name__)

#: What kind of thing is playing. Windows lays the card out differently for
#: each: music gets artist and album, video gets a subtitle.
MEDIA_KIND_MUSIC = "music"
MEDIA_KIND_VIDEO = "video"

#: The button flags SMTC offers. All of them stay False: the apps own the
#: media keys through RegisterHotKey, and a second claimant makes which one
#: answers a matter of timing.
_BUTTON_FLAGS = (
    "is_play_enabled",
    "is_pause_enabled",
    "is_stop_enabled",
    "is_next_enabled",
    "is_previous_enabled",
    "is_rewind_enabled",
    "is_fast_forward_enabled",
    "is_channel_up_enabled",
    "is_channel_down_enabled",
    "is_record_enabled",
)

#: Playback states Windows understands, in the app's own vocabulary.
_STATUS_NAMES = ("closed", "changing", "stopped", "playing", "paused")


def _controls(engine: Any) -> Any:
    """The engine's transport controls, or None when it has none.

    Asked of the engine rather than of the machine: only the modern Windows
    Media engine has a card, and which engine is playing is the thing that
    decides.
    """
    ask = getattr(engine, "media_transport_controls", None)
    if not callable(ask):
        return None
    try:
        return ask()
    except Exception:  # noqa: BLE001 - no controls is not a failure
        return None


def supports_now_playing(engine: Any) -> bool:
    """Whether *engine* can show a now-playing card at all."""
    return _controls(engine) is not None


def _claim_no_buttons(controls: Any) -> None:
    """Show the card; claim none of the keys. See the module docstring."""
    for flag in _BUTTON_FLAGS:
        try:
            setattr(controls, flag, False)
        except Exception:  # noqa: BLE001 - a flag this build lacks is fine
            continue


def update_now_playing(
    engine: Any,
    *,
    app_name: str,
    title: str,
    artist: str = "",
    album: str = "",
    kind: str = MEDIA_KIND_MUSIC,
) -> bool:
    """Put *title* (and the rest) on Windows' now-playing card. Did it show?

    *app_name* is what the card calls this app. *title* is the one field that
    matters -- a station, an episode, a chapter -- and an empty one clears the
    card rather than showing a blank row, because a card that says nothing is
    worse than no card.
    """
    controls = _controls(engine)
    if controls is None:
        return False
    if not str(title).strip():
        return clear_now_playing(engine)
    try:
        from winrt.windows.media import MediaPlaybackType

        controls.is_enabled = True
        _claim_no_buttons(controls)
        updater = controls.display_updater
        updater.type = (
            MediaPlaybackType.VIDEO if kind == MEDIA_KIND_VIDEO else MediaPlaybackType.MUSIC
        )
        updater.app_media_id = app_name
        if kind == MEDIA_KIND_VIDEO:
            updater.video_properties.title = str(title)
            if artist:
                updater.video_properties.subtitle = str(artist)
        else:
            music = updater.music_properties
            music.title = str(title)
            music.artist = str(artist or app_name)
            if album:
                music.album_title = str(album)
        updater.update()
    except Exception:  # noqa: BLE001 - the card is never worth the playback
        _log.debug("Now-playing card could not be updated", exc_info=True)
        return False
    return True


def set_playback_status(engine: Any, status: str) -> bool:
    """Tell Windows whether this app is playing, paused or stopped.

    Without it the card keeps saying "playing" after a pause, which is the kind
    of small lie that makes people stop trusting the surface. *status* is one of
    :data:`_STATUS_NAMES`; anything else is ignored rather than guessed at.
    """
    controls = _controls(engine)
    if controls is None or status not in _STATUS_NAMES:
        return False
    try:
        from winrt.windows.media import MediaPlaybackStatus

        controls.playback_status = getattr(MediaPlaybackStatus, status.upper())
    except Exception:  # noqa: BLE001 - best effort, always
        _log.debug("Now-playing status could not be set", exc_info=True)
        return False
    return True


def clear_now_playing(engine: Any) -> bool:
    """Take this app's card down -- nothing is playing any more."""
    controls = _controls(engine)
    if controls is None:
        return False
    try:
        from winrt.windows.media import MediaPlaybackStatus

        updater = controls.display_updater
        updater.clear_all()
        updater.update()
        controls.playback_status = MediaPlaybackStatus.CLOSED
    except Exception:  # noqa: BLE001 - best effort, always
        _log.debug("Now-playing card could not be cleared", exc_info=True)
        return False
    return True
