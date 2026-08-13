"""Where the audio comes out: stereo, mono, or one ear only.

Shared by every QuillVille app that plays audio -- Quill Radio and Quill Cast
today, Studio and the Converter through the same filter graph -- because the
reason someone needs this has nothing to do with which app is playing.

Who this is for, since it explains every decision below:

* **One working ear, or one hearing aid.** Hard-panned content simply vanishes
  in one ear. "Mono" blends both channels into both outputs so nothing is ever
  lost, which is the difference between a usable programme and half of one.
* **Sharing your ears with a screen reader.** "Left ear" and "right ear" put
  *all* of the programme into one ear and silence the other, leaving the other
  free for NVDA or JAWS. This is why they blend rather than simply dropping a
  channel: a listener who puts the radio in one ear must still hear all of it.

The ffmpeg filters themselves live in :mod:`quill.core.audio_enhance`
(``_CHANNEL_FILTERS``), which is what actually applies them, and both radio and
podcast playback already route through that graph. What was missing -- and what
this module is -- is the shared *vocabulary*: the mode order, the words spoken
for each, and how a single command cycles between them. Two apps inventing
their own labels for the same four modes would mean a listener learning it
twice.

wx-free, strict-typed, pure.
"""

from __future__ import annotations

from quill.core.audio_enhance import CHANNEL_MODES

#: Cycle order for a single "change audio output" command. Stereo first because
#: it is the default and the one people return to; mono next because it is by
#: far the most-used alternative; the single-ear modes last.
CYCLE_ORDER: tuple[str, ...] = ("stereo", "mono", "left", "right")

#: What each mode is called in menus and dialogs.
MODE_LABELS: dict[str, str] = {
    "stereo": "Stereo",
    "mono": "Mono",
    "left": "Left ear only",
    "right": "Right ear only",
}

#: The one-line explanation each mode gets where there is room for it -- said
#: in terms of what the listener will hear, never in terms of channels.
MODE_DESCRIPTIONS: dict[str, str] = {
    "stereo": "Normal stereo, left and right as broadcast.",
    "mono": "Both channels blended into both ears, so nothing is lost in either one.",
    "left": "Everything in your left ear, right ear silent.",
    "right": "Everything in your right ear, left ear silent.",
}

DEFAULT_MODE = "stereo"


def normalize(mode: str) -> str:
    """A valid mode, whatever was stored. Unknown values fall back to stereo.

    Settings files outlive the code that wrote them, so a mode this build does
    not recognise must play normally rather than refuse or silence an ear.
    """
    candidate = str(mode or "").strip().lower()
    return candidate if candidate in CHANNEL_MODES else DEFAULT_MODE


def label(mode: str) -> str:
    """The menu/dialog name for *mode*."""
    return MODE_LABELS[normalize(mode)]


def description(mode: str) -> str:
    """The one-line explanation of what *mode* sounds like."""
    return MODE_DESCRIPTIONS[normalize(mode)]


def next_mode(mode: str) -> str:
    """The mode after *mode* in the cycle, wrapping around."""
    current = normalize(mode)
    index = CYCLE_ORDER.index(current)
    return CYCLE_ORDER[(index + 1) % len(CYCLE_ORDER)]


def announce(mode: str) -> str:
    """What to say when the mode changes.

    Both the name and what it means: "Mono" alone tells someone who chose it
    deliberately what they wanted to know, and tells someone who hit the
    shortcut by accident nothing at all.
    """
    return f"{label(mode)}. {description(mode)}"


def is_active(mode: str) -> bool:
    """Whether *mode* changes the audio (i.e. is anything but stereo)."""
    return normalize(mode) != DEFAULT_MODE
