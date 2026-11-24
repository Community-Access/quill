"""Dictate Here in Quill Cast and Quill Radio, through QUILL Transcribe (dict.md D-16).

Cast and Radio have no speech engine, and are not going to get one: a search
box is a field like any other, and QUILL Transcribe already types into any
field. Edit > Dictate Here (Ctrl+F11, the editors' Start Dictation key, so the
same verb keeps the same chord: family rule 2) asks QUILL Transcribe to start
dictating into the field that has the focus, which is the field the person was
in when they pressed it -- a menu accelerator never moves the focus.

What it does, decided by :func:`dictate_here` from who owns Dictate Anywhere
(:func:`quill.core.dictation_owner.current_owner`):

* **QUILL Transcribe is running** (it holds the owner lock): a ``start``
  request (:func:`~quill.core.dictation_owner.send_request`). QUILL Transcribe
  answers it on its next tick, under a second, and says "Dictation on" with its
  own sound and words; this app says nothing, so the person hears it once.
  Already dictating, the request changes nothing.
* **Quill Inkwell is dictating** (it holds the lock for one session): nothing
  is sent, and the refusal names Inkwell, as every busy sentence does.
* **Nobody owns it**: QUILL Transcribe is launched in its tray
  (``--tray --dictate-here``), and starts dictating once it is ready -- unless
  it opens its window instead (first run, no tray), when it only opens. A copy
  without QUILL Transcribe is told so in a sentence.

The same commands and words work as anywhere else, because it *is* QUILL
Transcribe dictating: My Words and Phrases, the command word, the never-type
list and the field lock all apply.

**Only the field it was pressed in** (FUX-07, 2026-11-23). QUILL Transcribe
answers a moment later -- under a second when it is running, several seconds
when it has to start -- and until then the request named no field, so if the
focus had moved, dictation began wherever it had gone. The request now carries
the field's :data:`Place` (window, process, focused control window) as it was
when the key was pressed, and QUILL Transcribe starts only if that field is
still in front (:func:`still_there`); otherwise it says :func:`left_sentence`
and starts nothing.

wx-free.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

__all__ = [
    "LAUNCH_ARGS",
    "PLACE_ARG",
    "DictateHereOutcome",
    "Place",
    "dictate_here",
    "format_place",
    "left_sentence",
    "parse_place",
    "place_from_argv",
    "still_there",
]

#: A field, as an identity and never its text: the top-level window handle,
#: its process id, and the focused control's own window handle.
Place = tuple[int, int, int]

#: The launch argument that carries the :data:`Place` to a starting QUILL
#: Transcribe, followed by :func:`format_place`'s text.
PLACE_ARG = "--dictate-here-place"


#: How QUILL Transcribe is started for Dictate Here: in its tray, so the field
#: keeps the focus, and told to start once it is ready.
LAUNCH_ARGS: tuple[str, ...] = ("--tray", "--dictate-here")


@dataclass(frozen=True, slots=True)
class DictateHereOutcome:
    """What happened, and what to say (empty: say nothing, QUILL Transcribe will)."""

    #: ``asked``, ``launching``, ``busy``, ``unreachable`` or ``missing``.
    kind: str
    sentence: str


def format_place(place: Place) -> str:
    """*place* as launch-argument text, ``"window:process:control"``."""
    return ":".join(str(int(part)) for part in place)


def parse_place(text: object) -> Place | None:
    """A :data:`Place` from :func:`format_place`'s text or a JSON list; ``None``
    when it is not one (three non-negative whole numbers, the window not 0)."""
    parts = text.split(":") if isinstance(text, str) else text
    if not isinstance(parts, list | tuple) or len(parts) != 3:
        return None
    try:
        values = tuple(int(part) for part in parts)
    except (TypeError, ValueError):
        return None
    if any(value < 0 for value in values) or not values[0]:
        return None
    return (values[0], values[1], values[2])


def place_from_argv(argv: list[str]) -> Place | None:
    """The :data:`Place` after :data:`PLACE_ARG` in *argv*, or ``None``."""
    try:
        return parse_place(argv[argv.index(PLACE_ARG) + 1])
    except (ValueError, IndexError):
        return None


def still_there(place: Place | None, now: Place | None) -> bool:
    """Whether the field Dictate Here was pressed in is the one in front now.

    A request that names no field (from an older copy of Quill Cast or Quill
    Radio) is answered as before. Windows unable to say what is in front now
    is never "the same field".
    """
    if place is None:
        return True
    return now is not None and tuple(now) == tuple(place)


def left_sentence() -> str:
    """Said by QUILL Transcribe when the box is no longer in front. The same
    words for Quill Cast and Quill Radio, and whether QUILL Transcribe was
    running or had to start: the guides call it "the box"."""
    return (
        "Dictation did not start, because you moved away from the box you pressed "
        "Dictate Here in; go back to that box and press Dictate Here again."
    )


def dictate_here(
    app: str,
    *,
    place: Place | None = None,
    owner: Callable[[], str] | None = None,
    send: Callable[[str, str], bool] | None = None,
    launch: Callable[[], bool] | None = None,
) -> DictateHereOutcome:
    """Ask QUILL Transcribe to dictate into the focused field of *app*
    (``"cast"`` or ``"radio"``). *place* is that field (:data:`Place`), carried
    to QUILL Transcribe so it starts there or nowhere. The callables are for
    tests; by default they are the real owner lock, request file and launcher."""
    from quill.core import dictation_owner

    if owner is None:
        owner = dictation_owner.current_owner
    if send is None:

        def send(command: str, sender: str) -> bool:
            return dictation_owner.send_request(command, sender=sender, place=place)

    if launch is None:

        def launch() -> bool:
            return _launch_transcribe(place)

    holder = owner()
    if holder == "transcribe":
        if send("start", app):
            return DictateHereOutcome("asked", "")
        return DictateHereOutcome(
            "unreachable", "QUILL Transcribe is running, and could not be reached."
        )
    if holder:
        return DictateHereOutcome("busy", dictation_owner.busy_sentence(holder, asker=app))
    if launch():
        return DictateHereOutcome(
            "launching", "Starting QUILL Transcribe. Dictation starts here when it is ready."
        )
    return DictateHereOutcome(
        "missing",
        "Dictate Here needs QUILL Transcribe, which is not installed with this copy.",
    )


def _launch_transcribe(place: Place | None = None) -> bool:
    from quill.core.app_launcher import is_app_released, launch_app

    args = LAUNCH_ARGS if place is None else (*LAUNCH_ARGS, PLACE_ARG, format_place(place))
    return is_app_released("transcribe") and launch_app("transcribe", extra_args=args)
