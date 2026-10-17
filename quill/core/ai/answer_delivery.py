"""Where an AI answer goes: the AI Result window, the cursor, or the clipboard.

The answer delivery mode (2026-10-15), shared by QUILL and QUILL Lite through
the hosted-AI commands (:mod:`quill.ui.hosted_ai_answers`) and stored in both
editors' settings under one name, ``ai_answer_delivery``. No planning document
specified it, so this is the sensible minimum written down once:

* ``window`` -- the AI Result window, the default and the only mode that offers
  Replace, Review Changes, Insert Below, Try Again and Follow Up. An answer is a
  proposal, and this is where a proposal is read before it is used.
* ``cursor`` -- the answer goes straight into the document at the cursor, as one
  undo step, and is said aloud with how to take it back. For somebody who asks
  a lot of short questions and wants the answers in the text.
* ``clipboard`` -- the answer goes on the clipboard and is said aloud; nothing
  in the document changes. For pasting somewhere else.

The choice is made in the AI Assistant window ("Put the answer in") and holds
until it is changed. It applies to every answer that would open the AI Result
window: the pad, the Chat Key, and a prompt run from the Prompt Library.

wx-free and strict-typed.
"""

from __future__ import annotations

__all__ = [
    "CLIPBOARD",
    "CURSOR",
    "DEFAULT",
    "DELIVERY_LABELS",
    "DELIVERY_MODES",
    "WINDOW",
    "normalise",
]

WINDOW = "window"
CURSOR = "cursor"
CLIPBOARD = "clipboard"

#: The modes, in the order the chooser lists them.
DELIVERY_MODES: tuple[str, ...] = (WINDOW, CURSOR, CLIPBOARD)

DEFAULT = WINDOW

#: What each mode is called in the chooser: where the answer goes.
DELIVERY_LABELS: dict[str, str] = {
    WINDOW: "The AI Result window",
    CURSOR: "My document, at the cursor",
    CLIPBOARD: "The clipboard",
}


def normalise(value: object) -> str:
    """A stored value as a known mode; anything else is the default."""
    text = str(value or "").strip().lower()
    return text if text in DELIVERY_MODES else DEFAULT
