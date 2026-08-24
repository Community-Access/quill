"""One line of text for every playback state, in one place.

Extracted from ``RadioPlaybackState.status_text`` in
:mod:`quill.ui.radio.player_controller` for two reasons, in the order that
matters:

1. **Three surfaces read it and none of them owned it.** The focusable status
   bar's "Now playing" cell, the tray tooltip, and the mini-player all render
   the same sentence, and a fourth caller wanting to test the wording had to
   build a controller (and therefore a window) to get at it.
2. **GATE-11.** ``player_controller.py`` sat exactly on its ceiling, and the
   budget is a ratchet that says *extract*, not *rebaseline*. Adding two states
   to the enum had to buy its own room.

**Why it takes a string and not the enum.** ``RadioPlayerState`` is defined in
``player_controller``, which imports this module; taking the enum here would be
a cycle, and the lazy-import dance ``live_reconnect`` needs for the same reason
is not worth repeating for pure string formatting. The caller passes
``state.name``, which is the enum's own stable identity.

wx-free and pure: no state, no I/O, no imports beyond typing.
"""

from __future__ import annotations

#: The prefix every line carries. Both surfaces that show it sit beside other
#: applications' status text (the tray tooltip especially), so the line has to
#: say whose status it is.
_PREFIX = "Radio"


def status_text(
    *,
    state: str,
    station: str = "",
    muted: bool = False,
    message: str = "",
) -> str:
    """The one-line status for *state*, ready for the status bar or a tooltip.

    *state* is a :class:`~quill.ui.radio.player_controller.RadioPlayerState`
    member name. *message* carries whatever detail that state composed for
    itself -- the error text, or the reconnect attempt count -- so this function
    never has to reconstruct a sentence another module already wrote.

    An unknown state name answers the bare prefix rather than raising: a status
    line is the last thing that should be able to take the window down, and a
    new enum member that reaches here before its branch does is a wording bug,
    not a crash.
    """
    label = station.strip()
    if state == "STOPPED" or not label:
        return f"{_PREFIX}: stopped"
    if state == "CONNECTING":
        return f"{_PREFIX}: connecting to {label}..."
    if state == "BUFFERING":
        # Distinct from CONNECTING on purpose. Connecting is "we have not
        # started"; buffering is "we started, the audio ran out, and it is
        # coming back" -- and a status line that says "playing" through a stall
        # is the one thing a listener can already tell is false.
        return f"{_PREFIX}: buffering {label}..."
    if state == "RECONNECTING":
        # live_reconnect already wrote the sentence, attempt count and all, and
        # a second copy here would be the two drifting apart by next release.
        return f"{_PREFIX}: {message}" if message else f"{_PREFIX}: reconnecting to {label}..."
    if state == "PLAYING":
        return f"{_PREFIX}: playing {label}{' (muted)' if muted else ''}"
    if state == "PAUSED":
        return f"{_PREFIX}: paused - {label}"
    if state == "ERROR":
        return f"{_PREFIX}: could not play {label} - {message}"
    return _PREFIX


def transition_announcement(
    *,
    state: str,
    message: str,
    previous_state: str,
    previous_message: str,
) -> str:
    """The sentence a state change owes the listener out loud, or "" for silence.

    **Why almost everything answers "".** Playback transitions are cued with
    earcons rather than spoken (see ``_STATE_SOUNDS``), deliberately: a radio
    that says "playing" every time it starts is a radio nobody can read a
    document beside. This function exists for the one transition that was
    getting *neither* -- the reconnect.

    ``live_reconnect`` composes "Reconnecting to KFI AM 640. Attempt 1 of 3."
    and its own docstring promises that each attempt "is announced with its
    number". It was not. The sentence went into ``RadioPlaybackState.message``,
    which nothing spoke and which ``status_text`` ignored for CONNECTING, so a
    listener heard one connecting earcon and then up to twenty-two seconds of
    silence that is indistinguishable from a hung player. That is the exact
    complaint the module was written to answer.

    **And the other one that was getting neither: a failure.** A play that
    cannot happen ended in ERROR with a perfectly good sentence in ``message``
    -- "could not open that YouTube link", "no audio stream" -- and nothing
    said it. What a listener got was a connecting earcon, an error earcon, and
    a status cell they would have to go and read, which is indistinguishable
    from a hung player (reported 2026-08-23: "it just freezes: Radio:
    connecting to ..."). A failure is news by definition; it is spoken.

    Deduplicated on the message, not the state: three attempts are three
    different sentences and all three are news, while a re-entry into the same
    attempt is not.
    """
    if state not in ("RECONNECTING", "ERROR") or not message:
        return ""
    if previous_state == state and previous_message == message:
        return ""
    return message if state == "RECONNECTING" else f"Could not play. {message}"
