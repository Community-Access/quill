"""The question asked before unsaved work can be lost (bad.md F12, P2.10).

Two editors asked it two ways. QuillLite named the document -- "Save changes to
notes.txt?" -- and QUILL did not: "You have unsaved changes. Save before
closing?", which is the right question about the wrong number of documents. With
nine tabs open and no way to look at the title bar, "unsaved changes" in which
one is exactly what a listener needs and exactly what the sentence withheld.

The button words matter as much as the sentence. Word, Notepad and WordPad all
say **Save / Don't Save / Cancel**, and "Yes / No" makes a person work out which
of the two irreversible answers "No" is. QUILL deliberately kept the native
labels once (#23) because overriding them on macOS Cocoa also disabled the
Y/N/Escape accelerators, so somebody had to Tab to a button and press Space --
a worse failure than an unclear word. That trade is platform-specific, so the
labels are named here and each editor decides whether its platform can take
them; :func:`can_relabel_buttons` is that decision, written down once.

wx-free, and directly tested.
"""

from __future__ import annotations

import sys

__all__ = [
    "CANCEL",
    "CANCEL_LABEL",
    "DISCARD",
    "DISCARD_ALL",
    "DISCARD_ALL_LABEL",
    "DISCARD_LABEL",
    "SAVE",
    "SAVE_ALL",
    "SAVE_ALL_LABEL",
    "SAVE_LABEL",
    "BulkSavePolicy",
    "bulk_unsaved_question",
    "can_relabel_buttons",
    "describe_bulk_outcome",
    "unsaved_changes_question",
    "unsaved_changes_title",
]

#: What the three buttons say where they can be renamed. Word's words.
SAVE_LABEL = "Save"
DISCARD_LABEL = "Don't Save"
CANCEL_LABEL = "Cancel"

#: The dialog's title. Not the question -- a title bar is announced on arrival
#: and the question is read after it, so repeating the sentence here says it
#: twice.
UNSAVED_TITLE = "Unsaved changes"


def unsaved_changes_title() -> str:
    """The title for the prompt, the same in both editors."""
    return UNSAVED_TITLE


def unsaved_changes_question(document_name: str, action: str = "") -> str:
    """Name the document, and say what is about to happen to it.

    *document_name* is what the editor calls this document -- a file name, or
    "Untitled". An empty name still produces a sentence rather than "Save
    changes to ?", because a document with no name is the one a person is most
    likely to be surprised to lose.

    *action* is optional and names the thing being done ("closing", "reloading",
    "opening another file"). QUILL asks this question from four places and the
    answer to "Save before what?" is different in each.
    """
    name = " ".join(str(document_name).split()) or "this document"
    if action:
        return f"Save changes to {name} before {action}?"
    return f"Save changes to {name}?"


#: The five answers a bulk close can get. Strings rather than an enum so a
#: caller can compare them without importing a type, and so a latched value is
#: readable in a traceback.
SAVE = "save"
SAVE_ALL = "save_all"
DISCARD = "discard"
DISCARD_ALL = "discard_all"
CANCEL = "cancel"

#: The two extra buttons, in Word's words rather than "Yes to All" / "No to
#: All": the same reason the single prompt says Save and Don't Save. "Yes to
#: All" makes a person work out which of two irreversible answers "yes" was,
#: and it is the wrong moment to be doing that arithmetic.
SAVE_ALL_LABEL = "Save All"
DISCARD_ALL_LABEL = "Don't Save Any"


def bulk_unsaved_question(document_name: str, others: int, action: str = "") -> str:
    """The single prompt's question, plus how many more are waiting behind it.

    The count is the whole point of the two extra buttons. Somebody closing
    sixty-eight windows needs to know at the first prompt that there are
    sixty-seven more, because that is what makes "Don't Save Any" the obvious
    answer instead of a button they discover on the fortieth press.
    """
    question = unsaved_changes_question(document_name, action)
    if others <= 0:
        return question
    noun = "document" if others == 1 else "documents"
    verb = "has" if others == 1 else "have"
    return f"{question} {others} other {noun} also {verb} unsaved changes."


class BulkSavePolicy:
    """Remembers a "to all" answer so the rest are not asked about.

    One implementation for both editors, because "Don't Save Any" meaning
    *anything* other than "and never ask me again in this run" would be a
    bug with somebody's work on the end of it. Latching happens here, once.

    ``ask`` is called only when nothing is latched, and returns one of the five
    answers; what comes back from :meth:`answer` is only ever ``SAVE``,
    ``DISCARD`` or ``CANCEL`` -- the caller never has to handle the "all"
    values, which is what stops one of them forgetting to.

    Cancel never latches: stopping is about this moment, not about the rest.
    """

    __slots__ = ("latched",)

    def __init__(self) -> None:
        self.latched = ""

    def answer(self, ask: object) -> str:
        """The decision for the next document, asking only if it has to."""
        if self.latched:
            return self.latched
        choice = ask()  # type: ignore[operator]
        if choice == SAVE_ALL:
            self.latched = SAVE
            return SAVE
        if choice == DISCARD_ALL:
            self.latched = DISCARD
            return DISCARD
        return str(choice)


def describe_bulk_outcome(closed: int, saved: int, discarded: int, left: int) -> str:
    """What happened, in one sentence, counts first.

    Never silent and never vague: "Closed 68 documents" leaves out the only
    part somebody might need to act on, which is how many of them were thrown
    away unsaved.
    """
    if closed <= 0:
        return "Nothing closed."
    noun = "document" if closed == 1 else "documents"
    parts = [f"Closed {closed} other {noun}"]
    if saved:
        parts.append(f"saved {saved}")
    if discarded:
        parts.append(f"discarded {discarded} unsaved")
    sentence = ", ".join(parts) + "."
    if left:
        more = "1 document" if left == 1 else f"{left} documents"
        sentence += f" {more} still open."
    return sentence


def can_relabel_buttons(platform: str = "") -> bool:
    """Whether this platform keeps its keyboard accelerators when relabelled.

    False on macOS: wx's Cocoa backend drops the Y/N/Escape accelerators when
    the labels are overridden, so the clearer words cost the keyboard, which is
    the wrong way round for this app (#23). True everywhere else, where Save /
    Don't Save / Cancel is what every other editor says.
    """
    return (platform or sys.platform) != "darwin"
