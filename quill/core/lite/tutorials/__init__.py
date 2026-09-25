"""QUILL Lite's guided tutorials: its tracks, and its lessons assembled.

Nine lessons in two tracks, and the number is the point. QUILL has twenty-one
in six, because QUILL is an environment somebody moves into; QUILL Lite is a
Notepad replacement, and a Notepad replacement with a twenty-one-lesson course
attached to it is advertising that it is not one.

The engine -- what a step is, how one renders, where progress is kept -- is the
shared :mod:`quill.core.tutorials`, the same one Quill Radio, QUILL Cast, Quill
Weather and QUILL use. This is only the content, and it follows that module's
wording rules: one action per step, say *why* rather than only what, say what
you should **hear**, and never promise a key in prose -- name the command and
let the key render, so somebody who has rebound it reads their own key.

Two tracks, and they answer the two questions this product exists for:

* **Your first documents** is the promise: open a file, get it back unchanged,
  and know what kind of thing you are in. Somebody who does only this track can
  use QUILL Lite all day.
* **Working in a document** is the part that has no sighted equivalent --
  selecting text you cannot see the extent of, finding your way back, skimming
  something long, hearing that a word is wrong without being interrupted
  mid-sentence, and asking a question about a document rather than reading it
  end to end to find one fact. That last one earns a lesson despite the
  restraint above, because it is the only feature here that sends anything off
  the machine -- a thing somebody should be taught deliberately rather than
  discover.

What is deliberately not here: a tour of everything. The menus, the command
palette and the user guide cover the rest, and a lesson that duplicates the
keyboard reference is a keyboard reference with extra words (bad.md P3.2).
"""

from __future__ import annotations

from quill.core.lite.tutorials import first_documents, working_in_it
from quill.core.tutorials.model import Track, TutorialSet, build

#: QUILL Lite's tracks, in teaching order.
TRACKS: tuple[Track, ...] = (
    Track(
        "first-documents",
        "Your first documents",
        "Open a file and give it back unchanged, learn where the facts about it "
        "live, learn what kind of document you are in, and find your way "
        "between the ones you have open.",
    ),
    Track(
        "working-in-it",
        "Working in a document",
        "Selecting more than a few words, finding your way back to where you "
        "were, skimming something long, spelling without a red squiggle, and "
        "asking a question about the document in front of you.",
    ),
)

#: The set the tutorials window and the printed book both read.
CATALOGUE: TutorialSet = build(
    "quilllite",
    TRACKS,
    first_documents.TUTORIALS,
    working_in_it.TUTORIALS,
)

__all__ = ["CATALOGUE", "TRACKS"]
