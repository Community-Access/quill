"""The formatting chords the native control answers whether we want it to or not.

Both editors build **every** document on a Windows Rich Edit control -- plain
text and Markdown included, because that is what gives the braille display and
the screen reader a text surface worth reading. The cost is that the control
brings its own keyboard: ``Ctrl+U`` underlines, ``Ctrl+L``, ``Ctrl+R``,
``Ctrl+E`` and ``Ctrl+J`` re-align, ``Ctrl+Shift+=`` and ``Ctrl+=`` shift the
baseline. In a Rich Text document that is exactly right. In a Markdown or plain
document it is a formatting run applied to a document that has no formatting:
not marked dirty, not announced, and not saved -- but really there, on the undo
stack, and visible to anyone who can see the screen (bad.md R9).

For a sighted user that is a confusing flicker. For the person this editor is
built for it is worse than invisible: the document now differs from what will
be written to disk, and nothing in the app will ever mention it.

So a chord in this table, in a document that has no formatting, is swallowed --
and said once per document, because a key that does nothing and explains nothing
is indistinguishable from a key that is broken, and a key that explains itself
every time becomes noise within a minute.

wx-free on purpose: the UI layer resolves the modifiers and the key code, this
module answers what the native control *would* have done, and both editors ask
the same question and get the same sentence.
"""

from __future__ import annotations

__all__ = [
    "NATIVE_FORMATTING_CHORDS",
    "native_formatting_effect",
    "native_formatting_notice",
    "notice_kind_label",
]

#: How each kind of document is *named* in the sentence below. One table,
#: because the two editors spell their own kinds differently -- QuillLite's
#: status cell says "Plain text" and QUILL's markup kind says "html" -- and
#: the sentence has to come out identical either way. QuillLite lower-cased
#: its own label before handing it over, which turned "HTML" into "html" and
#: so into "a html document" while QUILL said "an HTML document": the one
#: thing this module exists to prevent.
_NOTICE_KIND_LABELS: dict[str, str] = {
    "markdown": "Markdown",
    "md": "Markdown",
    "html": "HTML",
    "htm": "HTML",
    "xhtml": "HTML",
    "rich text": "rich text",
    "rich": "rich text",
    "plain text": "plain text",
    "plain": "plain text",
    "text": "plain text",
    "txt": "plain text",
}

#: ``(ctrl, shift, key)`` -> what the native control would do. Alt is never
#: part of one of these: the control's own chords are Ctrl and Ctrl+Shift.
#: ``key`` is the upper-case character, or the literal for a punctuation key.
_NATIVE_EFFECTS: dict[tuple[bool, bool, str], str] = {
    (True, False, "U"): "Underline",
    (True, False, "E"): "Centre alignment",
    (True, False, "L"): "Left alignment",
    (True, False, "R"): "Right alignment",
    (True, False, "J"): "Justified alignment",
    (True, False, "="): "Subscript",
    (True, True, "="): "Superscript",
    (True, True, "A"): "All capitals",
    (True, True, "D"): "Double underline",
    (True, True, "H"): "Hidden text",
    (True, True, "K"): "Small capitals",
}


def native_formatting_effect(*, ctrl: bool, shift: bool, alt: bool, key: str) -> str | None:
    """What the native Rich Edit control would do for this chord, or ``None``.

    ``key`` is a single character; case does not matter. ``alt`` being held
    means the chord belongs to somebody else -- the control claims none of
    these with Alt -- so it is answered ``None`` rather than swallowed.
    """
    if not ctrl or alt or len(key) != 1:
        return None
    return _NATIVE_EFFECTS.get((True, bool(shift), key.upper()))


#: The same chords written the way a keymap and a user guide write them.
#: Derived, not retyped: the documentation-chord gate needs to know which
#: chords a guide may name without anything binding them, and a second
#: hand-kept copy of this list would be the thing that drifts.
NATIVE_FORMATTING_CHORDS: tuple[str, ...] = tuple(
    "+".join(("Ctrl", *(("Shift",) if shift else ()), key)) for _ctrl, shift, key in _NATIVE_EFFECTS
)


def notice_kind_label(raw: str) -> str:
    """The canonical name for a kind of document, for the notice below.

    Anything unrecognised is ``plain text``, which is what an editor falls
    back to for a file it has no markup reader for -- and the right answer
    for the sentence, because a document with no markup is what the notice is
    about.
    """
    return _NOTICE_KIND_LABELS.get(raw.strip().lower(), "plain text")


def native_formatting_notice(effect: str, kind_label: str) -> str:
    """The one sentence both editors say, once, when such a chord is swallowed.

    Names the effect and the kind of document rather than the key, because the
    person pressing it knows perfectly well which key they pressed and does not
    know why this document is different from the last one.

    The article is chosen by **sound**, not by spelling, because this sentence
    is going to be spoken: an initialism is read letter by letter, so "HTML" is
    "aitch tee em ell" and takes "an" exactly where "hypertext" would take "a".
    """
    first = kind_label[:1]
    if kind_label.isupper():
        # Letters whose spoken NAME starts with a vowel: eff, aitch, ell, em,
        # en, ar, ess, ex -- plus the vowels themselves.
        vowel_sound = first.upper() in set("AEIOUFHLMNRSX")
    else:
        vowel_sound = first.lower() in "aeiou"
    article = "an" if vowel_sound else "a"
    return f"{effect} has no meaning in {article} {kind_label} document."
