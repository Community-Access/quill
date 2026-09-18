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
    "CANCEL_LABEL",
    "DISCARD_LABEL",
    "SAVE_LABEL",
    "can_relabel_buttons",
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


def can_relabel_buttons(platform: str = "") -> bool:
    """Whether this platform keeps its keyboard accelerators when relabelled.

    False on macOS: wx's Cocoa backend drops the Y/N/Escape accelerators when
    the labels are overridden, so the clearer words cost the keyboard, which is
    the wrong way round for this app (#23). True everywhere else, where Save /
    Don't Save / Cancel is what every other editor says.
    """
    return (platform or sys.platform) != "darwin"
