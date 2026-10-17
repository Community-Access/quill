"""AutoCorrect for misspellings: ``teh`` and a space becomes ``the`` and a space.

QUILL and QUILL Lite already changed text as you type in two ways --
typography (:mod:`quill.core.autoformat`: curly quotes, em dashes) and your own
abbreviations (:mod:`quill.core.abbreviations`). Neither corrected a
misspelling, which is the AutoCorrect most people mean. This module is that
feature's rules, shared by both editors.

**Where corrections come from.** Two layers, merged by :func:`lookup`:

* A **built-in list** of common English misspellings, shipped as data in
  ``quill/core/data/autocorrect_en.json`` with its source written into the
  file. Every key is checked (by ``tests/unit/core/test_autocorrect.py``) to be
  a non-word: the list must never "correct" something somebody spelled right.
* **Your own entries**, which are ordinary entries in the abbreviation library
  -- the same ``abbreviations.json``, saved by the same store, backed up by the
  same Back Up Settings -- marked with the
  :data:`~quill.core.abbreviations.AUTOCORRECT_CATEGORY` category. There is no
  second file. An entry of yours with the same typed word as a built-in one
  wins; a *disabled* entry of yours stops the built-in one (that is what
  "Stop" in the AutoCorrect Entries window writes), and removing your entry
  brings the built-in one back.

**When a correction fires** (:func:`find_correction`), all of these hold:

* The *Correct common misspellings as I type* setting is on (off by default,
  in both editors) -- checked by the caller.
* The document is prose (:func:`autocorrect_allows`): never in a file the
  shared rule calls code or configuration, the same rule that keeps the live
  spell check out of them.
* A **space** (or Enter) has just ended the word. The word is everything back
  to the previous space or line break, with opening and closing punctuation
  trimmed off, so ``(teh,`` corrects the ``teh`` and keeps the bracket and the
  comma. What is left must be letters only (an apostrophe inside is allowed):
  anything holding a dot, slash, colon, ``@``, digit or underscore -- a web
  address, an email address, a path, an identifier -- is never touched.
* The word is not inside a Markdown code span, a fenced code block, or a web or
  email address (the caller supplies that check from
  :func:`quill.core.spellcheck_live.live_alert_suppressed`).
* The word is not in capitals throughout. ``TEH`` is left alone, because a word
  typed all in capitals is far more often an acronym than a misspelling.

**Case** (:func:`match_case`): ``teh`` becomes ``the``; ``Teh`` becomes
``The``. A correction with capitals of its own (``febuary`` becomes
``February``) keeps them. An entry marked *match case* fires only on exactly
what was typed and puts in exactly what it says.

**Taking a correction back.** The correction is written as one undo step, so
Ctrl+Z straight after it puts back what you typed. And a word you have taken a
correction back from is not corrected again in that window this session: the
caller records it with :func:`note_declined` when it sees the uncorrected word
come back in the same place, so a second space after the undo does not undo
your undo.

wx-free and strict-typed.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType

from quill.core.abbreviations import AUTOCORRECT_CATEGORY, Abbreviation, AbbreviationLibrary

__all__ = [
    "AUTOCORRECT_CATEGORY",
    "AutocorrectMatch",
    "CorrectionRow",
    "ORIGIN_BUILT_IN",
    "ORIGIN_CHANGED",
    "ORIGIN_YOURS",
    "WINDOW",
    "autocorrect_allows",
    "correction_rows",
    "default_corrections",
    "default_source",
    "delete_correction",
    "find_correction",
    "is_correction_entry",
    "lookup",
    "match_case",
    "note_declined",
    "resume_correction",
    "set_correction",
    "stop_correction",
    "validate_entry",
]

_DATA_FILE = Path(__file__).resolve().parent / "data" / "autocorrect_en.json"

#: How far back from the caret a caller needs to read to find the word. A
#: whitespace-free run longer than this is never a misspelling (it is a web
#: address, a hash or a path), so nothing longer is ever examined.
WINDOW = 64

ORIGIN_BUILT_IN = "built-in"
ORIGIN_YOURS = "yours"
ORIGIN_CHANGED = "changed"

#: A word: letters, optionally joined by apostrophes (``don't``, ``o'clock``).
_WORD = re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)*")

#: Trimmed from the front and back of a token before it is looked up, and
#: put back around the correction. ``*`` and ``_`` are Markdown emphasis.
_OPENERS = "([{<\"'“‘*_"
_CLOSERS = ".,;:!?)]}>\"'”’*_"

#: Document kinds a correction never fires in, whatever the file is called.
_LITERAL_KINDS = frozenset({"code", "json", "yaml", "toml", "ini", "conf"})


@lru_cache(maxsize=1)
def _load_data() -> tuple[Mapping[str, str], str]:
    try:
        raw = json.loads(_DATA_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return MappingProxyType({}), ""
    entries = raw.get("entries", {}) if isinstance(raw, dict) else {}
    table = {
        str(key).strip().lower(): str(value)
        for key, value in (entries.items() if isinstance(entries, dict) else ())
        if str(key).strip() and str(value).strip()
    }
    source = str(raw.get("source", "")) if isinstance(raw, dict) else ""
    return MappingProxyType(table), source


def default_corrections() -> Mapping[str, str]:
    """The built-in list: lower-case misspelling to correction. Read once."""
    return _load_data()[0]


def default_source() -> str:
    """Where the built-in list came from, as written in its data file."""
    return _load_data()[1]


def is_correction_entry(entry: Abbreviation) -> bool:
    """Whether a library entry is an AutoCorrect correction, not an abbreviation."""
    return entry.category == AUTOCORRECT_CATEGORY


@dataclass(frozen=True, slots=True)
class CorrectionRow:
    """One correction as the AutoCorrect Entries window lists it."""

    typed: str
    replacement: str
    origin: str
    active: bool
    entry_id: str = ""
    case_sensitive: bool = False

    def describe(self) -> str:
        """The list row: what is typed, what it becomes, and whose it is."""
        whose = {
            ORIGIN_BUILT_IN: "built in",
            ORIGIN_YOURS: "yours",
            ORIGIN_CHANGED: "built in, changed by you",
        }.get(self.origin, self.origin)
        state = "" if self.active else ", stopped"
        case = ", match case" if self.case_sensitive else ""
        return f"{self.typed} becomes {self.replacement}, {whose}{case}{state}"


def _user_entries(library: AbbreviationLibrary | None) -> dict[str, Abbreviation]:
    if library is None:
        return {}
    found: dict[str, Abbreviation] = {}
    for entry in getattr(library, "abbreviations", ()):
        if is_correction_entry(entry) and entry.abbreviation.strip():
            found.setdefault(entry.abbreviation.strip().lower(), entry)
    return found


def _row_for(key: str, entry: Abbreviation | None, defaults: Mapping[str, str]) -> CorrectionRow:
    built_in = defaults.get(key)
    if entry is None:
        return CorrectionRow(key, built_in or "", ORIGIN_BUILT_IN, True)
    origin = ORIGIN_YOURS if built_in is None else ORIGIN_CHANGED
    if built_in is not None and not entry.enabled and entry.expansion == built_in:
        origin = ORIGIN_BUILT_IN  # a plain "stop" of the built-in one
    return CorrectionRow(
        entry.abbreviation.strip(),
        entry.expansion,
        origin,
        bool(entry.enabled),
        entry.id,
        bool(entry.case_sensitive),
    )


def lookup(library: AbbreviationLibrary | None, word: str) -> CorrectionRow | None:
    """The correction for *word* (any case), active or stopped, or ``None``."""
    key = word.strip().lower()
    if not key:
        return None
    defaults = default_corrections()
    entry = _user_entries(library).get(key)
    if entry is None and key not in defaults:
        return None
    return _row_for(key, entry, defaults)


def correction_rows(library: AbbreviationLibrary | None) -> list[CorrectionRow]:
    """Every correction, built-in and yours, sorted by the typed word."""
    defaults = default_corrections()
    entries = _user_entries(library)
    keys = sorted(set(defaults) | set(entries))
    return [_row_for(key, entries.get(key), defaults) for key in keys]


def match_case(typed: str, replacement: str) -> str | None:
    """*replacement* in the case *typed* was in, or ``None`` to leave it alone.

    ``None`` for a word typed all in capitals (two letters or more): that is an
    acronym far more often than a misspelling.
    """
    letters = [c for c in typed if c.isalpha()]
    if len(letters) > 1 and all(c.isupper() for c in letters):
        return None
    if typed[:1].isupper() and replacement[:1].islower():
        return replacement[:1].upper() + replacement[1:]
    return replacement


@dataclass(frozen=True, slots=True)
class AutocorrectMatch:
    """A correction to make: ``text[start:end]`` (*original*) becomes *replacement*."""

    start: int
    end: int
    original: str
    replacement: str


def find_correction(
    before: str,
    offset: int,
    library: AbbreviationLibrary | None,
    *,
    declined: frozenset[str] | set[str] = frozenset(),
    suppressed: Callable[[int, int], bool] | None = None,
) -> AutocorrectMatch | None:
    """The correction for the word just before the caret, or ``None``.

    *before* is the text immediately before the caret -- the space or Enter
    that ends the word has **not** been inserted yet -- and *offset* is the
    document position of ``before[0]``; read :data:`WINDOW` characters back, or
    to the start of the document. *declined* holds lower-case words the person
    has taken a correction back from. *suppressed*, when given, is asked about
    the word's span last, because it is the one check that may need the whole
    document (a fenced code block starts somewhere above).
    """
    cut = max(before.rfind(" "), before.rfind("\n"), before.rfind("\t"), before.rfind("\r"))
    if cut < 0 and offset > 0:
        return None  # a run with no space in WINDOW characters is not a word
    token = before[cut + 1 :]
    start = cut + 1
    while token and token[0] in _OPENERS:
        token = token[1:]
        start += 1
    while token and token[-1] in _CLOSERS:
        token = token[:-1]
    if not token or _WORD.fullmatch(token) is None:
        return None
    key = token.lower().replace("’", "'")
    if key in declined:
        return None
    row = lookup(library, key)
    if row is None or not row.active or not row.replacement:
        return None
    if row.case_sensitive:
        if token != row.typed:
            return None
        replacement: str | None = row.replacement
    else:
        replacement = match_case(token, row.replacement)
    if replacement is None or replacement == token:
        return None
    absolute = offset + start
    if suppressed is not None and suppressed(absolute, absolute + len(token)):
        return None
    return AutocorrectMatch(absolute, absolute + len(token), token, replacement)


def note_declined(
    last: AutocorrectMatch | None, before: str, offset: int, declined: set[str]
) -> bool:
    """Record that the person took *last* back, when the text says they did.

    Called with the same *before*/*offset* as :func:`find_correction`, on the
    next space or Enter. If the word that was corrected is back, as typed, in
    the same place -- Ctrl+Z, or deleting the correction and retyping -- its
    lower-case form joins *declined* and ``True`` comes back, so the caller
    leaves it alone this time and every time after in this window.
    """
    if last is None:
        return False
    rel_start = last.start - offset
    rel_end = rel_start + len(last.original)
    if rel_start < 0 or rel_end > len(before):
        return False
    if before[rel_start:rel_end] != last.original:
        return False
    if before[rel_end:].strip(_CLOSERS):
        return False
    declined.add(last.original.lower().replace("’", "'"))
    return True


def autocorrect_allows(kind: str | None, name: str | Path | None) -> bool:
    """Whether corrections may fire in a document of this *kind* and *name*.

    Prose only: never in a file the shared code-and-configuration rule names
    (:func:`quill.core.spellcheck_filetypes.is_code_filename`) and never in a
    literal kind. Plain text, Markdown, rich text and an untitled note are all
    prose. Unlike curly quotes, plain text is *in*: a misspelling is as wrong in
    a ``.txt`` as anywhere, and the correction is a word, not a character that
    could break a file format.
    """
    from quill.core.spellcheck_filetypes import is_code_filename

    if is_code_filename(name):
        return False
    return (kind or "").strip().lower() not in _LITERAL_KINDS


# -- managing your own entries -------------------------------------------- #


def validate_entry(typed: str, replacement: str) -> str | None:
    """Why this pair cannot be saved, in a sentence, or ``None`` when it can."""
    word = typed.strip()
    if not word:
        return "Type the word to correct."
    if _WORD.fullmatch(word) is None:
        return (
            "The word to correct must be letters only, with no spaces, digits or "
            "punctuation (an apostrophe inside the word is allowed)."
        )
    fixed = replacement.strip()
    if not fixed:
        return "Type what the word should become."
    if "\n" in fixed or len(fixed) > 200:
        return "A correction must be one line of 200 characters or fewer."
    if fixed == word:
        return "The correction is the same as the word, so it would change nothing."
    return None


def set_correction(
    library: AbbreviationLibrary,
    typed: str,
    replacement: str,
    *,
    case_sensitive: bool = False,
) -> Abbreviation | None:
    """Add or change a correction of yours; returns the library entry.

    Saving a pair identical to the built-in one removes your entry instead
    (and returns ``None``): there is nothing of yours left to keep.
    """
    word = typed.strip()
    fixed = replacement.strip()
    key = word.lower()
    entry = _user_entries(library).get(key)
    if default_corrections().get(key) == fixed and not case_sensitive:
        if entry is not None:
            library.remove(entry.id)
        return None
    if entry is None:
        return library.add(
            word, fixed, category=AUTOCORRECT_CATEGORY, case_sensitive=case_sensitive
        )
    entry.abbreviation = word
    entry.expansion = fixed
    entry.case_sensitive = case_sensitive
    entry.enabled = True
    return entry


def stop_correction(library: AbbreviationLibrary, typed: str) -> bool:
    """Stop one correction firing, built-in or yours. ``True`` when it changed."""
    key = typed.strip().lower()
    entry = _user_entries(library).get(key)
    if entry is not None:
        changed = bool(entry.enabled)
        entry.enabled = False
        return changed
    built_in = default_corrections().get(key)
    if built_in is None:
        return False
    library.add(key, built_in, category=AUTOCORRECT_CATEGORY, enabled=False)
    return True


def resume_correction(library: AbbreviationLibrary, typed: str) -> bool:
    """Start a stopped correction again. ``True`` when it changed."""
    key = typed.strip().lower()
    entry = _user_entries(library).get(key)
    if entry is None or entry.enabled:
        return False
    if default_corrections().get(key) == entry.expansion and not entry.case_sensitive:
        library.remove(entry.id)  # it was only ever a stop of the built-in one
        return True
    entry.enabled = True
    return True


def delete_correction(library: AbbreviationLibrary, typed: str) -> str:
    """Remove your entry for *typed*, and say what that did.

    ``"removed"``: it was yours and is gone. ``"restored"``: it changed or
    stopped a built-in one, which is back as shipped. ``"built-in"``: there is
    nothing of yours to remove -- a built-in correction cannot be deleted, only
    stopped. ``"missing"``: no such correction.
    """
    key = typed.strip().lower()
    entry = _user_entries(library).get(key)
    if entry is None:
        return "built-in" if key in default_corrections() else "missing"
    library.remove(entry.id)
    return "restored" if key in default_corrections() else "removed"
