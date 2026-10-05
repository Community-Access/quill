"""Quill Radio as a Windows media player: the types it offers to open, and how.

Somebody with music on an external drive should be able to right-click a song,
choose Open with, and pick Quill Radio -- the way they would pick VLC -- and
should be able to make Quill Radio the app that opens their music when they
double-click it. This module is the data that makes both true. The registering
itself is the editors' (:mod:`quill.core.windows_editor`): one plan, one
writer, one installer generator, with Quill Radio's :data:`RADIO` profile
handed to them instead of an editor's.

The type list is not a wish list. Every type here is one Local Media already
plays (:data:`quill.core.radio.local_media.MEDIA_SUFFIXES`) or reads as a
playlist (:mod:`quill.core.radio.local_media_files`), and a test holds it to
that: offering to open a type the player then cannot play is worse than not
offering at all.

As with the editors, nothing here takes a type over. Windows keeps the choice
of default app for the person, in a key no app may write; registering only puts
Quill Radio on the list they choose from.

wx-free and registry-free.
"""

from __future__ import annotations

from quill.core.windows_editor import AppProfile, ContextVerb

__all__ = [
    "AUDIO_TYPES",
    "ENQUEUE_FLAG",
    "ENQUEUE_VERB",
    "OPEN_WITH_TYPES",
    "PLAYLIST_TYPES",
    "PLAY_VERB",
    "RADIO",
    "VIDEO_TYPES",
]

#: Sound files: everything the request named, each one Local Media plays.
AUDIO_TYPES: tuple[str, ...] = (
    ".mp3",
    ".m4a",
    ".m4b",
    ".aac",
    ".ogg",
    ".oga",
    ".opus",
    ".flac",
    ".wav",
    ".wma",
    ".aiff",
    ".aif",
    ".mka",
)

#: Video Quill Radio's player shows (Show Video) as well as plays the sound of.
VIDEO_TYPES: tuple[str, ...] = (".mp4", ".mkv", ".webm", ".mov")

#: Playlists: opened, they are imported into Local Media and played.
PLAYLIST_TYPES: tuple[str, ...] = (".m3u", ".m3u8", ".pls")

OPEN_WITH_TYPES: tuple[str, ...] = (*AUDIO_TYPES, *VIDEO_TYPES, *PLAYLIST_TYPES)

#: Between the app and the file: add it to the Opened files list rather than
#: starting it now.
ENQUEUE_FLAG = "--enqueue"

PLAY_VERB = ContextVerb("QuillRadio.Play", "Play with Quill Radio")
ENQUEUE_VERB = ContextVerb("QuillRadio.Enqueue", "Add to Quill Radio Playlist", (ENQUEUE_FLAG,))

RADIO = AppProfile(
    app_name="Quill Radio",
    progid="QuillRadio.Media",
    exe_name="QuillRadio.exe",
    capabilities_key=r"Software\QuillRadio\Capabilities",
    extensions=OPEN_WITH_TYPES,
    description=(
        "An accessible radio, podcast and media player for music, audiobooks and "
        "video on your computer, built for screen readers."
    ),
    module="quill.apps.radio",
    launcher_name="QuillRadio.exe",
    icon_name="quill-radio.ico",
    exe_stems=("quillradio",),
    types_phrase="music, audiobooks, video and playlists",
    role="Media Player",
    example_type=".mp3",
    document_kind="Media",
    verbs=(PLAY_VERB, ENQUEUE_VERB),
)
