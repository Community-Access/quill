"""The main window's transport button: the verb and its object, in the label.

Jeff, 2026-09-30, in QUILL Cast: "I land in the library on favorites, if I tab
I see play, play what?" And the next day, in Quill Radio: "The stop button now
always shows up in the app and doesn't change to a play button when stopped."

Both reports are the same defect seen from two sides. A transport button that
says only its verb has told a screen-reader user half of what they need: not
what it would start, not whether it would resume a place, and -- in the one
state where it does nothing -- not that it does nothing. And a button that says
Stop while nothing is playing is a dead control wearing a live label.

**The object goes in the visible label, not in the accessible name.** On wxMSW a
button is self-labelled: ``set_accessible_name`` is inert on it (MSAA and UIA
never read it), so a button whose name says "Play Thursday's episode" and whose
label says "Play" is heard as "Play". The first attempt at this made exactly
that mistake and was inaudible. So the label carries the object, elided at
:data:`MAX_LABEL_CHARS` so the row never reflows as the selection changes, with
any ``&`` in a title doubled so a podcast called "Rock & Roll" does not grow a
stray access key.

**One rule decides every case: the label describes the effect of pressing it,
not the state of the player.** "Stopped" is a readout wearing a button's
clothes -- the mistake Radio's status bar was redesigned to stop making.

Two apps, one function, one difference. Cast's button pauses while something
plays and has Stop beside it; Radio's main window has one button that starts,
ends, and resumes -- live radio cannot pause, and the window is a list you play
from, not a player. That is ``active_verb``. The mnemonics are per app too,
because each window's menu bar owns a different set of letters (GATE-15), and
:func:`label_samples` hands every label this module can produce to that gate so
no state of the button can ever share Alt+letter with a menu.

wx-free, strict-typed, pure.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "CAST_MNEMONICS",
    "LOADING",
    "MAX_LABEL_CHARS",
    "PAUSED",
    "PLAYING",
    "RADIO_MNEMONICS",
    "STOPPED",
    "ButtonFace",
    "Mnemonics",
    "escape_mnemonic",
    "face",
    "label_samples",
    "object_label",
]

#: The four phases the button distinguishes. Deliberately not either player's
#: enum: this module imports no UI, and the caller already holds the enum.
STOPPED = "stopped"
LOADING = "loading"
PLAYING = "playing"
PAUSED = "paused"

#: Visible characters, mnemonic marker excluded, after which the object is
#: elided. Long enough for a show and an episode ("The Daily, Thursday's
#: episode"); short enough that a forty-word episode title cannot push the
#: buttons after it off the window.
MAX_LABEL_CHARS = 40

_ELLIPSIS = "..."


@dataclass(frozen=True)
class Mnemonics:
    """The four verb labels with their access keys, chosen per window."""

    play: str = "Pla&y"
    pause: str = "Pau&se"
    resume: str = "Re&sume"
    stop: str = "S&top"


#: Cast's main window. The menu bar owns P, E, D, V, Q, W and H, so the row
#: yields: Y, S (Pause and Resume share it -- one button, never both states at
#: once), T.
CAST_MNEMONICS = Mnemonics()

#: Radio's main window. The bar owns A, C, D, E, H, N, P, Q, R, S, V and W --
#: which is every letter of "Resume" but U, so the Volume label moved to O
#: (2026-10-01) to free it. L and T are the letters the button has carried
#: since #1208; the Favorites label has F and the Mute toggle M.
RADIO_MNEMONICS = Mnemonics(play="P&lay", pause="Pau&se", resume="Res&ume", stop="S&top")


@dataclass(frozen=True)
class ButtonFace:
    """What the button reads, says, and does, from one reading of one state."""

    #: The visible label: verb, access key, object, elided.
    label: str
    #: The whole sentence, for the press that does nothing and for a status
    #: line: never elided, mnemonic-free.
    spoken: str
    #: ``play``, ``pause``, ``resume``, ``stop`` -- or ``none`` for the one
    #: state in which pressing it can only explain itself.
    verb: str

    @property
    def enabled(self) -> bool:
        """Always. A dimmed Play with nothing selected is a button that cannot
        say why; an enabled one says so when pressed (principle 11.2)."""
        return True


def escape_mnemonic(text: str) -> str:
    """Double every ampersand so a title cannot claim an access key."""
    return text.replace("&", "&&")


def _elide(text: str, room: int) -> str:
    """*text* cut to *room* characters with an ellipsis, or whole if it fits."""
    text = " ".join(text.split())
    if len(text) <= room:
        return text
    if room <= len(_ELLIPSIS):
        return _ELLIPSIS[:room]
    return text[: room - len(_ELLIPSIS)].rstrip() + _ELLIPSIS


def object_label(verb_label: str, object_name: str, *, max_chars: int = MAX_LABEL_CHARS) -> str:
    """``"Pla&y The Daily"``: a verb label with its object, fitted and escaped.

    The budget is counted in *visible* characters -- the ``&`` marker is free --
    and the object is what gives way, never the verb.
    """
    name = " ".join((object_name or "").split())
    if not name:
        return verb_label
    verb_visible = len(verb_label.replace("&&", "&").replace("&", ""))
    room = max_chars - verb_visible - 1
    if room < 1:
        return verb_label
    return f"{verb_label} {escape_mnemonic(_elide(name, room))}"


def _phrase(show_title: str, episode_title: str) -> str:
    """ "The Daily, Thursday's episode", or whichever half exists."""
    show = (show_title or "").strip()
    episode = (episode_title or "").strip()
    if show and episode:
        return f"{show}, {episode}"
    return episode or show


def face(
    state: str,
    *,
    active_verb: str = "pause",
    object_name: str = "",
    episode_title: str = "",
    selection: str = "",
    can_play_selection: bool = False,
    mnemonics: Mnemonics = CAST_MNEMONICS,
    dead_hint: str = "choose something in the list first",
) -> ButtonFace:
    """The button for *state*.

    *object_name* (and, for an episode, *episode_title*) is what is playing or
    paused. *selection* is what the list cursor is on, and *can_play_selection*
    whether pressing Play would start it -- a folder, a pinned view or an empty
    show is a selection that cannot be played, and a button that says it would
    play "News" when News is a folder has lied about the one thing it was asked.

    *active_verb* is ``"pause"`` (Cast: Stop is a second button) or ``"stop"``
    (Radio's main window: one button starts and ends).

    The stopped-with-nothing-playable case says **what to do instead**, because
    it is the only state in which the button does nothing, and a button that
    does nothing and says only "Play" is indistinguishable from a broken one.
    That was the report.
    """
    if state in (PLAYING, LOADING):
        what = _phrase(object_name, episode_title)
        if active_verb == "stop":
            return ButtonFace(
                object_label(mnemonics.stop, what), f"Stop {what}" if what else "Stop", "stop"
            )
        return ButtonFace(
            object_label(mnemonics.pause, what), f"Pause {what}" if what else "Pause", "pause"
        )
    if state == PAUSED:
        what = _phrase(object_name, episode_title)
        return ButtonFace(
            object_label(mnemonics.resume, what),
            f"Resume {what}" if what else "Resume",
            "resume",
        )
    chosen = " ".join((selection or "").split())
    if can_play_selection and chosen:
        return ButtonFace(object_label(mnemonics.play, chosen), f"Play {chosen}", "play")
    # Stopped, and nothing pressing it would start. The label says so in three
    # words; the sentence names the way out, since the listener is standing in
    # the list and one of the routes is under their cursor.
    return ButtonFace(
        f"{mnemonics.play} -- nothing selected",
        f"Play. Nothing is selected that can be played -- {dead_hint}",
        "none",
    )


def label_samples(mnemonics: Mnemonics, *, active_verb: str) -> list[str]:
    """Every distinct label shape this module can put on the button.

    For GATE-15 (``quill/tools/check_menubar_mnemonics.py``), which reads the
    source for literals and so could not see a label built at run time -- the
    survey of 2026-09-30 found ``&Pause`` reclaiming Alt+P from the Podcasts
    menu the moment anything played, because the gate had read only the
    static ``Pla&y``. A sample per state, with an object, is the whole set of
    access keys the button can ever claim.
    """
    sample = "Sample"
    return [
        face(STOPPED, mnemonics=mnemonics, active_verb=active_verb).label,
        face(
            STOPPED,
            selection=sample,
            can_play_selection=True,
            mnemonics=mnemonics,
            active_verb=active_verb,
        ).label,
        face(PLAYING, object_name=sample, mnemonics=mnemonics, active_verb=active_verb).label,
        face(PAUSED, object_name=sample, mnemonics=mnemonics, active_verb=active_verb).label,
    ]
