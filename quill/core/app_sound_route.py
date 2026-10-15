"""Where a QUILL app's own sounds play: the family's one answer. wx-free.

Every app in the family plays short sounds of its own -- a station connecting,
a document saved, a weather alert -- and until October 2026 every one of them
played on the system default device, because ``winsound`` can play nowhere
else. That was wrong for anybody who routes audio at all. A broadcaster sends
Quill Radio to an on-air card and needs "playing" and "stream error" on that
card, not on the desk speakers (Rick Lewis, QUILLVille, against Radio 3.2.0);
somebody else wants the editor's sounds in a headset and nothing in the room.

So each app has one setting, **App sounds play on**, with the same choices in
the same order everywhere:

* **Same as the app's audio** (:data:`FOLLOW`) -- only in an app that has an
  output device of its own (Quill Radio, QUILL Cast, the Media Player, Audio
  Studio), where it is the default. The sounds go wherever the app's audio
  goes, including every later change to it.
* **System default** (``""``) -- the family's existing spelling for "where
  Windows sends sound". The default in every app with no audio of its own.
* **None (no sounds)** (:data:`NONE`) -- this app makes no sounds at all.
  Speech, playback and the screen reader carry on; the family-wide sound
  switch is separate and untouched.
* **Any sound card by name** -- a device name in the spelling the audio
  engines already use, ``wasapi/{guid}``.

Routing itself lives in :mod:`quill.platform.sound_routing`; this module only
says what a stored value means and what the chooser offers.
"""

from __future__ import annotations

__all__ = [
    "FOLLOW",
    "HELP_TAIL",
    "LABEL",
    "NONE",
    "NONE_LABEL",
    "SYSTEM_DEFAULT_LABEL",
    "choices",
    "default_for",
    "describe",
    "effective_device",
    "normalize",
    "toggled",
]

#: "Wherever this app's own audio plays." The default in apps that have audio.
FOLLOW = "follow"
#: "This app makes no sounds."
NONE = "none"

#: The Preferences row's label, the same in every app. No access key: the
#: windows it joins have already spent the letters in it, and a duplicate would
#: advertise a key that does not work (GATE-14).
LABEL = "App sounds play on:"
SYSTEM_DEFAULT_LABEL = "System default"
NONE_LABEL = "None (no sounds)"
_UNAVAILABLE = " (not currently available)"

#: The part of every app's help sentence that does not depend on the app.
HELP_TAIL = (
    "System default leaves them where Windows sends sound. None (no sounds) "
    "turns this app's sounds off, and Alt+Shift+M turns them off and back on "
    "from anywhere in the app. Or choose a sound card to give them their "
    "own. After a change you hear one sound on the new card. If that card is "
    "unplugged, the sounds play on the system default until it is back, and "
    "the app says so. Your screen reader is never moved."
)


def default_for(has_own_audio: bool) -> str:
    """Where a fresh install starts: with the app's audio when it has some."""
    return FOLLOW if has_own_audio else ""


def normalize(value: object, *, has_own_audio: bool) -> str:
    """A stored value as the code expects it.

    Anything unreadable starts at the app's default. ``"radio"`` is read as
    :data:`FOLLOW`: it was Quill Radio's spelling in the 3.2.0 build 3 testing
    packages, before every app shared one.
    """
    if not isinstance(value, str):
        return default_for(has_own_audio)
    value = value.strip()
    if value == "radio":
        value = FOLLOW
    if value == FOLLOW and not has_own_audio:
        return ""
    return value


def effective_device(choice: str, own_device: str = "") -> str:
    """What to route to: a device name, ``""`` for the default, or :data:`NONE`."""
    if choice == FOLLOW:
        return str(own_device or "").strip()
    return str(choice or "").strip()


def toggled(choice: str, remembered: str | None, *, has_own_audio: bool) -> tuple[str, str | None]:
    """``(new_choice, new_remembered)`` for the on/off key.

    Off means :data:`NONE` and remembers what it replaced; on goes back to that,
    or to the app's default if nothing was remembered. ``None`` is "nothing";
    ``""`` is the system default, a place like any other.
    """
    if choice == NONE:
        back = remembered if remembered is not None and remembered != NONE else None
        return (default_for(has_own_audio) if back is None else back), None
    return NONE, choice


def _label_for(device: str, devices: list[tuple[str, str]]) -> str:
    if not device:
        return SYSTEM_DEFAULT_LABEL
    for name, description in devices:
        if name == device:
            return description or name
    return device


def choices(
    devices: list[tuple[str, str]],
    choice: str,
    *,
    own_device: str | None = None,
    own_audio_name: str = "the app",
) -> tuple[list[str], list[str], int]:
    """``(labels, values, selected)`` for the chooser.

    *own_device* is the app's own output device, or None for an app with no
    audio of its own -- which is what decides whether "Same as" is offered.
    That row names today's card, so nobody has to look it up. A saved card
    that is unplugged stays in the list, marked, rather than being quietly
    swapped for something nobody chose.
    """
    labels: list[str] = []
    values: list[str] = []
    if own_device is not None:
        labels.append(f"Same as {own_audio_name} (now: {_label_for(own_device, devices)})")
        values.append(FOLLOW)
    labels += [SYSTEM_DEFAULT_LABEL, NONE_LABEL]
    values += ["", NONE]
    for name, description in devices:
        labels.append(description or name)
        values.append(name)
    if choice not in values:
        labels.append(f"{choice}{_UNAVAILABLE}")
        values.append(choice)
    return labels, values, values.index(choice)


def describe(choice: str, devices: list[tuple[str, str]], *, own_device: str = "") -> str:
    """Where the sounds go, as words for an announcement."""
    if choice == NONE:
        return "nowhere: this app's sounds are off"
    return _label_for(effective_device(choice, own_device), devices)
