"""The keys every window of Radio and Cast answers to, named once.

Quill Radio and Quill Cast each have exactly **one** player -- the same
``RadioPlayerController`` object is handed to the main window, the browse tree
and the now-playing surface, so there has never been more than one thing
playing. What there *was* was more than one place that knew how to talk to it,
and only one of them had keys: speed, skip and chapters were bound to the main
frame's menu bar, so standing in Browse Stations you could hear a podcast and
not change its speed (reported 2026-08-18: *"the speed stuff isn't working in
the player in the browse window"*). The window you were in decided which half
of the player existed.

This is the list that fixes that. It is deliberately data, not code: a verb is
an id, a label, a default key and nothing else, so

* :mod:`quill.ui.radio.transport_keys` can install the same accelerators on
  **any** window without that window learning what a chapter is,
* a menu can render its label and key from the same row, so the menu and the
  keyboard can never disagree,
* and the two apps can be compared -- and their drift measured -- by a test
  rather than by reading two menu builders.

Three rules the key choices follow:

**In-app, never OS-global.** These are accelerators on the app's own windows.
Quill Radio does not take a key away from the rest of the computer to do them
(``GlobalHotkeysMixin`` exists for the few that are genuinely worth it, and
this is not that).

**Ctrl+Alt+arrow is off limits.** QUILL's table navigation owns that block, and
a transport verb that fights table navigation is a verb that works everywhere
except where somebody is reading a table.

**A verb that a listener cannot use is not offered.** ``needs_bounded`` marks
the verbs that only mean something for a *recording* -- speed, seeking,
chapters. A live broadcast has no chapters and cannot be sped up, and the UI
reads this field rather than growing its own opinion about it.

wx-free, strict-typed, pure.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Command ids. These are keymap ids too (``APP_KEYMAPS``), so they are stable
#: strings a listener's rebinding is stored against.
PLAY_PAUSE = "transport.play_pause"
STOP = "transport.stop"
VOLUME_UP = "transport.volume_up"
VOLUME_DOWN = "transport.volume_down"
MUTE = "transport.mute"
SKIP_FORWARD = "transport.skip_forward"
SKIP_BACK = "transport.skip_back"
SPEED_UP = "transport.speed_up"
SPEED_DOWN = "transport.speed_down"
SPEED_RESET = "transport.speed_reset"
NEXT_CHAPTER = "transport.next_chapter"
PREVIOUS_CHAPTER = "transport.previous_chapter"
CHAPTER_LIST = "transport.chapter_list"
ANNOUNCE_POSITION = "transport.announce_position"
GO_TO_PLAYER = "transport.go_to_player"
COMMAND_PALETTE = "transport.command_palette"


@dataclass(frozen=True, slots=True)
class TransportCommand:
    """One player verb: what it is called, what key reaches it, what it needs."""

    id: str
    label: str
    key: str
    #: What performs it, resolved by name at press time in this order: the
    #: host's own ``transport_<verb>`` (an escape hatch nothing in the repo
    #: currently defines), then Quill Cast's ``podcast_*``, then
    #: :mod:`quill.ui.radio.bounded_playback_ui`, then the player controller
    #: itself. Names match the controller's where one exists
    #: (``toggle_play_pause``, ``stop``, ``toggle_mute``) so those verbs need
    #: no adapter at all.
    verb: str
    #: Only meaningful for a finished recording (speed, seeking, chapters).
    needs_bounded: bool = False
    #: Only meaningful when something is playing at all.
    needs_playing: bool = True


#: Every transport verb, in the order a Playback menu should list them.
#:
#: The keys that already existed keep their existing values -- Ctrl+P has been
#: play/pause in both apps for a long time and moving it to tidy a table would
#: cost more than the tidiness is worth. The new ones are the verbs that had no
#: key at all: chapters in both apps, speed in Radio, and the jump back to the
#: player from wherever you are.
COMMANDS: tuple[TransportCommand, ...] = (
    TransportCommand(PLAY_PAUSE, "&Play/Pause", "Ctrl+P", "toggle_play_pause", needs_playing=False),
    TransportCommand(STOP, "&Stop", "Ctrl+.", "stop"),
    TransportCommand(VOLUME_UP, "Volume &Up", "Ctrl+Up", "volume_up", needs_playing=False),
    TransportCommand(VOLUME_DOWN, "Volume &Down", "Ctrl+Down", "volume_down", needs_playing=False),
    # Not Ctrl+Shift+M (Cast's Audio Output Mode) and not Ctrl+Shift+U (taken
    # in Radio): the obvious mnemonic keys for Mute were both already spoken
    # for, and a key that two menus claim is a key one of them never gets.
    TransportCommand(MUTE, "&Mute/Unmute", "Ctrl+Shift+O", "toggle_mute", needs_playing=False),
    TransportCommand(SKIP_BACK, "Skip &Back", "Ctrl+Shift+Left", "skip_back", needs_bounded=True),
    TransportCommand(
        SKIP_FORWARD, "Skip &Forward", "Ctrl+Shift+Right", "skip_forward", needs_bounded=True
    ),
    TransportCommand(SPEED_UP, "Speed U&p", "Ctrl+Shift+Up", "speed_up", needs_bounded=True),
    TransportCommand(SPEED_DOWN, "Speed Do&wn", "Ctrl+Shift+Down", "slow_down", needs_bounded=True),
    TransportCommand(
        SPEED_RESET, "Reset Speed to Norma&l", "Ctrl+Shift+0", "reset_speed", needs_bounded=True
    ),
    TransportCommand(
        PREVIOUS_CHAPTER,
        "P&revious Chapter",
        # The "<" and ">" keys, as every media player has used for
        # previous/next since there were media players. Ctrl+Alt+Left/Right
        # (what Radio shipped) is QUILL's table navigation, and the obvious
        # letters were taken: Ctrl+Shift+K is Captions, Ctrl+Shift+N is Next.
        "Ctrl+Shift+,",
        "previous_chapter",
        needs_bounded=True,
    ),
    TransportCommand(
        NEXT_CHAPTER, "&Next Chapter", "Ctrl+Shift+.", "next_chapter", needs_bounded=True
    ),
    TransportCommand(
        CHAPTER_LIST, "&Chapters...", "Ctrl+Shift+C", "open_chapters", needs_bounded=True
    ),
    TransportCommand(
        ANNOUNCE_POSITION,
        "Where Am &I?",
        # Not Ctrl+Shift+I (Video Information) and not Ctrl+Shift+T
        # (Transcript): W for "where".
        "Ctrl+Shift+W",
        "announce_position",
        needs_bounded=True,
    ),
    TransportCommand(
        GO_TO_PLAYER, "&Go to Player", "Ctrl+Shift+G", "go_to_player", needs_playing=False
    ),
    # Not a transport verb, and here anyway: this table is "the keys every
    # window of the app answers to", and the palette is the other one of those.
    # Radio's Help menu already binds Ctrl+Shift+P for it on the main window;
    # this is what carries it into the browse tree, the manager and the rest.
    TransportCommand(
        COMMAND_PALETTE,
        "Command &Palette...",
        "Ctrl+Shift+P",
        "open_command_palette",
        needs_playing=False,
    ),
)

_BY_ID = {command.id: command for command in COMMANDS}


def command(command_id: str) -> TransportCommand | None:
    return _BY_ID.get(command_id)


def keymap_defaults() -> dict[str, str]:
    """``{command id: key}`` for an app's ``APP_KEYMAPS`` entry."""
    return {c.id: c.key for c in COMMANDS}


def available(command_id: str, *, playing: bool, bounded: bool) -> bool:
    """Whether this verb can do anything right now.

    Used to dim a menu item rather than to hide it: a listener who presses
    Speed Up on a live station should learn that live radio has no speed, and a
    verb that comes and going teaches nobody anything.
    """
    found = _BY_ID.get(command_id)
    if found is None:
        return False
    if found.needs_playing and not playing:
        return False
    return not (found.needs_bounded and not bounded)


def refusal(command_id: str, *, playing: bool, bounded: bool) -> str:
    """Why this verb cannot act, in words. "" when it can.

    Spoken rather than swallowed: a key that silently does nothing is
    indistinguishable from a key that is not bound.
    """
    found = _BY_ID.get(command_id)
    if found is None:
        return ""
    if found.needs_playing and not playing:
        return "Nothing is playing."
    if found.needs_bounded and not bounded:
        return (
            "This is live radio, which plays at broadcast speed and has no "
            "chapters or position to move through."
        )
    return ""
