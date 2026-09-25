"""Where the caret lands: word movement and pages, decided once for both editors.

Windows has an answer to "what does Ctrl+Right do" and it is not the one either
editor was implementing. Both walked to the next run of whitespace, so
``foo.bar`` and ``end.`` and ``(x)`` were each a single word -- press Ctrl+Right
in ``self.editor.SetSelection`` and you go past the whole expression, where
Notepad, WordPad, Word and every edit control on the platform stop at each
``.`` on the way.

The rule Windows actually uses, and this implements: **a word is a run of word
characters, or a run of punctuation, and whitespace is neither.** Moving forward
lands on the start of the next run; moving backward lands on the start of the
run you are in, or the one before it if you are already there. That is what
``EM_SETWORDBREAKPROC``'s default does, and it is what a person's hands expect
because every other text box on the machine does it.

It lives in core rather than beside a key handler because **three** places in
the product move a caret by a word -- QUILL's extend-selection mode, QUILL Lite's,
and the reveal-codes navigator -- and the first two had two different wrong
answers (bad.md P1.2a, 5.3a).
"""

from __future__ import annotations

__all__ = ["lines_per_page", "word_boundary"]


def _kind(character: str) -> str:
    """``"space"``, ``"word"`` or ``"punct"`` -- the three things a run can be.

    ``str.isalnum`` plus the underscore rather than ``\\w``: an identifier is one
    word to anybody editing code, and splitting ``read_text`` into two is the
    kind of correctness nobody asked for.
    """
    if character.isspace():
        return "space"
    if character.isalnum() or character == "_":
        return "word"
    return "punct"


def word_boundary(text: str, position: int, *, reverse: bool) -> int:
    """The next word boundary from *position*, Windows' definition of "word".

    Returns *position* itself when there is nowhere further to go, so a caller
    can tell "I moved" from "I was already at the end" without comparing against
    a length it would have to compute.
    """
    length = len(text)
    caret = max(0, min(position, length))
    if reverse:
        if caret == 0:
            return 0
        index = caret
        # Step back over whitespace first: the run before the gap is the target.
        while index > 0 and _kind(text[index - 1]) == "space":
            index -= 1
        if index == 0:
            return 0
        kind = _kind(text[index - 1])
        while index > 0 and _kind(text[index - 1]) == kind:
            index -= 1
        return index
    if caret >= length:
        return length
    index = caret
    kind = _kind(text[index])
    if kind != "space":
        # Leave the run you are standing in...
        while index < length and _kind(text[index]) == kind:
            index += 1
    # ...then cross any whitespace to the start of the next one.
    while index < length and _kind(text[index]) == "space":
        index += 1
    return index


def lines_per_page(client_height: int, char_height: int, *, fallback: int = 10) -> int:
    """How many lines a page key should move, from the window's own measurements.

    Page Up and Page Down were hardcoded to ten in QUILL's extend-selection
    movement, which is a page on nobody's screen: it undershoots on a maximised
    window and overshoots on a short one, and either way the caret does not end
    where the same key would have put it with the control doing the moving.

    *fallback* is used when the control cannot answer -- a window not yet shown
    reports a zero client height -- because ten wrong lines is still better than
    a page key that does nothing.
    """
    if client_height <= 0 or char_height <= 0:
        return max(1, fallback)
    # One line short, as every editor does: the line at the boundary stays on
    # screen so there is something to read back against.
    return max(1, client_height // char_height - 1)
