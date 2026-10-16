"""Differences between two texts: a unified diff, and one said for listening.

:func:`build_unified_diff` is the line-based diff the editor's Compare shows.
:func:`spoken_changes` is the word-level one dictation's review says after
every AI revision (D-2 of the 2026-10-13 dictation plan): at most two plain
sentences -- "Changed next Thursday to Friday. Removed um, so." -- computed
here from the two texts, never taken from the model's own account of what it
did, because a model can say it changed one word and have changed ten.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher, unified_diff

__all__ = [
    "LARGE_CHANGE",
    "build_unified_diff",
    "change_fraction",
    "spoken_changes",
]

#: More of the words than this changed: the summary leads with "Large change".
LARGE_CHANGE = 0.5
#: A quoted stretch longer than this many words is described, not quoted.
_QUOTE_WORDS = 6
_PUNCTUATION = re.compile(r"[^\w']+")


def build_unified_diff(
    current_text: str,
    other_text: str,
    current_label: str = "Current document",
    other_label: str = "Other file",
) -> str:
    current_lines = current_text.splitlines(keepends=True)
    other_lines = other_text.splitlines(keepends=True)
    diff_lines = list(
        unified_diff(
            other_lines,
            current_lines,
            fromfile=other_label,
            tofile=current_label,
            lineterm="",
            n=3,
        )
    )
    if not diff_lines:
        return ""
    return "\n".join(diff_lines) + "\n"


def _folded(word: str) -> str:
    """*word* as compared: lower case, punctuation off ("Friday," is "friday")."""
    return _PUNCTUATION.sub("", word.lower())


def _words(text: str) -> list[str]:
    return text.split()


def change_fraction(before: str, after: str) -> float:
    """How much of the text changed, 0.0 to 1.0, by words (punctuation aside)."""
    old = [_folded(word) for word in _words(before)]
    new = [_folded(word) for word in _words(after)]
    if not old and not new:
        return 0.0
    matcher = SequenceMatcher(None, old, new, autojunk=False)
    same = sum(block.size for block in matcher.get_matching_blocks())
    return 1.0 - (2.0 * same) / (len(old) + len(new))


def _quoted(words: list[str]) -> str:
    """Words as said: up to six quoted, longer stretches counted."""
    shown = " ".join(words).strip(" ,;:")
    if len(words) <= _QUOTE_WORDS:
        return shown
    start = " ".join(words[:3]).strip(" ,;:")
    return f"{len(words)} words starting {start}"


def _ends_sentence(words: list[str]) -> bool:
    return bool(words) and words[-1][-1:] in ".?!"


def _fragments(before: str, after: str) -> tuple[list[str], bool]:
    """Each word-level change, phrased; and whether punctuation or capitals
    changed somewhere the words did not."""
    old_raw, new_raw = _words(before), _words(after)
    old = [_folded(word) for word in old_raw]
    new = [_folded(word) for word in new_raw]
    matcher = SequenceMatcher(None, old, new, autojunk=False)
    fragments: list[str] = []
    marks = False
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        gone, added = old_raw[i1:i2], new_raw[j1:j2]
        if tag == "equal":
            marks = marks or gone != added
        elif tag == "replace":
            fragments.append(f"Changed {_quoted(gone)} to {_quoted(added)}")
        elif tag == "delete":
            fragments.append(f"Removed {_quoted(gone)}")
        elif i1 == len(old_raw) and _ends_sentence(added) and len(added) > _QUOTE_WORDS:
            fragments.append("Added a sentence at the end")
        else:
            fragments.append(f"Added {_quoted(added)}")
    return fragments, marks


def spoken_changes(before: str, after: str) -> str:
    """What changed from *before* to *after*, in no more than two sentences.

    * Nothing: "No change."
    * Only punctuation or capitals: "Changed punctuation or capitals only."
    * More than half the words: "Large change: 70 percent of the words are
      different. Read it before you insert it."
    * Otherwise the first change, then the second or how many more there are:
      "Changed next Thursday to Friday. Removed um, so."
    """
    if before == after:
        return "No change."
    fragments, marks = _fragments(before, after)
    if not fragments:
        return "Changed punctuation or capitals only." if marks else "Changed spacing only."
    fraction = change_fraction(before, after)
    longest = max(len(_words(before)), len(_words(after)))
    if fraction > LARGE_CHANGE and longest > 3:  # a three-word phrase is quoted instead
        percent = int(round(fraction * 100))
        return (
            f"Large change: {percent} percent of the words are different. "
            "Read it before you insert it."
        )
    first = fragments[0] + "."
    if len(fragments) == 1:
        return first + (" Punctuation or capitals changed too." if marks else "")
    if len(fragments) == 2:
        return f"{first} {fragments[1]}."
    more = len(fragments) - 1
    return f"{first} And {more} more changes."
