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

wx-free.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

__all__ = ["LAUNCH_ARGS", "DictateHereOutcome", "dictate_here"]

#: How QUILL Transcribe is started for Dictate Here: in its tray, so the field
#: keeps the focus, and told to start once it is ready.
LAUNCH_ARGS: tuple[str, ...] = ("--tray", "--dictate-here")


@dataclass(frozen=True, slots=True)
class DictateHereOutcome:
    """What happened, and what to say (empty: say nothing, QUILL Transcribe will)."""

    #: ``asked``, ``launching``, ``busy``, ``unreachable`` or ``missing``.
    kind: str
    sentence: str


def dictate_here(
    app: str,
    *,
    owner: Callable[[], str] | None = None,
    send: Callable[[str, str], bool] | None = None,
    launch: Callable[[], bool] | None = None,
) -> DictateHereOutcome:
    """Ask QUILL Transcribe to dictate into the focused field of *app*
    (``"cast"`` or ``"radio"``). The callables are for tests; by default they
    are the real owner lock, request file and launcher."""
    from quill.core import dictation_owner

    if owner is None:
        owner = dictation_owner.current_owner
    if send is None:

        def send(command: str, sender: str) -> bool:
            return dictation_owner.send_request(command, sender=sender)

    if launch is None:
        launch = _launch_transcribe
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


def _launch_transcribe() -> bool:
    from quill.core.app_launcher import is_app_released, launch_app

    return is_app_released("transcribe") and launch_app("transcribe", extra_args=LAUNCH_ARGS)
