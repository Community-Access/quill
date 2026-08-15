"""Abbreviation expansion library — bare-word TextExpander-style shortcuts.

Abbreviations differ from snippets: no trigger prefix is required. The user
types "btw " and the editor silently replaces "btw" with "by the way". A
sound can be played on expansion if configured.
"""

from __future__ import annotations

import datetime
import os
import uuid
from collections.abc import Callable
from dataclasses import dataclass

_TRIGGER_CHARS: frozenset[str] = frozenset({
    " ",
    "\n",
    "\t",
    ".",
    ",",
    ";",
    ":",
    "!",
    "?",
    ")",
    "]",
    "}",
    '"',
    "'",
})

_ABBREVIATIONS_FILE = "abbreviations.json"


#: Which trigger characters an entry accepts (``triggers``). ``"manual"`` never
#: auto-expands -- the entry is only reachable from Quick Insert, which is the
#: safe home for long or destructive expansions.
TRIGGER_MODES: tuple[str, ...] = ("both", "space", "punctuation", "manual")

#: What is announced when an entry expands (``speak_mode``).
SPEAK_MODES: tuple[str, ...] = ("silent", "name", "expansion")

#: Per-entry override of the global expansion sound (``sound``).
SOUND_MODES: tuple[str, ...] = ("inherit", "on", "off")

#: Whitespace trigger characters, as opposed to punctuation ones. Used to decide
#: whether an entry whose ``triggers`` is ``"space"`` or ``"punctuation"``
#: accepts the character that actually fired.
_SPACE_TRIGGERS: frozenset[str] = frozenset({" ", "\n", "\t"})

#: The current on-disk schema. v1 files (no per-entry settings) load unchanged
#: because every v2 field has a default; a v2 file read by an older build simply
#: ignores the extra keys and still expands.
SCHEMA_VERSION = 2


@dataclass(slots=True)
class Abbreviation:
    id: str
    abbreviation: str
    expansion: str
    case_sensitive: bool = False
    enabled: bool = True
    description: str = ""
    #: Free-text grouping ("" is Uncategorised). Filters the manager list and
    #: Quick Insert; also the unit Quill Inkwell enables or disables as a set.
    category: str = ""
    #: "silent" | "name" | "expansion" -- what is spoken on expansion.
    speak_mode: str = "silent"
    #: "inherit" | "on" | "off" -- per-entry override of the global sound.
    sound: str = "inherit"
    #: Append a space after the expansion (after the trigger punctuation, when
    #: punctuation is what fired, so the text still reads correctly).
    trailing_space: bool = False
    #: "both" | "space" | "punctuation" | "manual" -- see TRIGGER_MODES.
    triggers: str = "both"
    #: Quick Insert sorts by recency of use; both are maintained at the call site.
    usage_count: int = 0
    last_used: str = ""
    #: Applications this entry may fire in, by executable name without the
    #: extension and lowercase ("outlook", "code"). Empty means everywhere,
    #: which is what every existing entry is and stays.
    #:
    #: This only bites system-wide (Quill Inkwell): inside QUILL's own editor
    #: there is one application and scoping to it would be a setting that could
    #: only ever switch an entry off. A signature belongs in a mail client, a
    #: code snippet belongs in an editor, and an expander that fires both
    #: everywhere is one people turn off.
    apps: tuple[str, ...] = ()

    def matches_app(self, process_name: str) -> bool:
        """Whether this entry may fire in the application currently in front.

        An entry with no apps fires anywhere -- that is the default and the
        overwhelming majority. When the caller cannot tell what is in front
        (no process name), a *scoped* entry does not fire: the safe direction
        for "I do not know where this would land" is not to type into it.
        """
        if not self.apps:
            return True
        name = str(process_name or "").strip().lower()
        if not name:
            return False
        stem = name.rsplit(".", 1)[0] if name.endswith(".exe") else name
        return stem in self.apps

    def accepts_trigger(self, char: str) -> bool:
        """Whether this entry may be fired by trigger character *char*."""
        if self.triggers == "manual":
            return False
        if self.triggers == "space":
            return char in _SPACE_TRIGGERS
        if self.triggers == "punctuation":
            return char not in _SPACE_TRIGGERS
        return True


@dataclass(slots=True)
class AbbreviationLibrary:
    version: int
    abbreviations: list[Abbreviation]

    def add(self, abbreviation: str, expansion: str, **kwargs: object) -> Abbreviation:
        abbr = Abbreviation(
            id=str(uuid.uuid4()),
            abbreviation=abbreviation,
            expansion=expansion,
            **kwargs,  # type: ignore[arg-type]
        )
        self.abbreviations.append(abbr)
        return abbr

    def remove(self, id: str) -> None:
        self.abbreviations = [a for a in self.abbreviations if a.id != id]

    def enable(self, id: str) -> None:
        for a in self.abbreviations:
            if a.id == id:
                a.enabled = True

    def disable(self, id: str) -> None:
        for a in self.abbreviations:
            if a.id == id:
                a.enabled = False

    def update(self, id: str, **fields: object) -> Abbreviation:
        for a in self.abbreviations:
            if a.id == id:
                for k, v in fields.items():
                    object.__setattr__(a, k, v)
                return a
        raise KeyError(id)

    def all(self) -> list[Abbreviation]:
        return list(self.abbreviations)

    def enabled_only(self) -> list[Abbreviation]:
        return [a for a in self.abbreviations if a.enabled]

    def find_by_trigger(self, text: str, case_sensitive: bool = False) -> Abbreviation | None:
        for a in sorted(self.abbreviations, key=lambda x: len(x.abbreviation), reverse=True):
            if not a.enabled:
                continue
            if a.case_sensitive or case_sensitive:
                if a.abbreviation == text:
                    return a
            else:
                if a.abbreviation.lower() == text.lower():
                    return a
        return None


@dataclass(slots=True)
class AbbreviationMatch:
    token_start: int
    token_end: int
    resolved_text: str
    cursor_offset: int
    has_cursor: bool
    #: The entry that matched, so the call site can honor its per-entry speech
    #: and sound settings without looking it up again. Optional for backward
    #: compatibility with callers constructing a match directly.
    abbreviation: Abbreviation | None = None
    #: Insert one space *after* the trigger character. Only ever set when the
    #: entry asked for a trailing space and the trigger was punctuation -- a
    #: space trigger already leaves one, and doubling it reads badly.
    trailing_space: bool = False


_BUILTINS: list[tuple[str, str, str]] = [
    ("afaik", "as far as I know", ""),
    ("afaict", "as far as I can tell", ""),
    ("asap", "as soon as possible", ""),
    ("atm", "at the moment", ""),
    ("btw", "by the way", "Common shorthand"),
    ("fwiw", "for what it's worth", ""),
    ("imo", "in my opinion", ""),
    ("imho", "in my humble opinion", ""),
    ("irl", "in real life", ""),
    ("omw", "on my way", ""),
    ("tbh", "to be honest", ""),
    ("tbc", "to be confirmed", ""),
    ("tbd", "to be determined", ""),
    ("ttyl", "talk to you later", ""),
    ("wrt", "with regard to", ""),
]


def _make_default_library() -> AbbreviationLibrary:
    return AbbreviationLibrary(
        version=1,
        abbreviations=[
            Abbreviation(
                id=str(uuid.uuid4()),
                abbreviation=abbr,
                expansion=exp,
                description=desc,
            )
            for abbr, exp, desc in _BUILTINS
        ],
    )


def resolve_expansion(expansion: str, clipboard_text: str = "") -> tuple[str, int, bool]:
    """Resolve variables in an abbreviation expansion body.

    Returns (resolved_text, cursor_offset, has_cursor_marker).
    cursor_offset is relative to the start of resolved_text.
    """
    text = expansion
    # An empty clipboard deliberately leaves ``${clipboard}`` in place rather
    # than silently inserting nothing: the visible token tells the user why the
    # expansion looks wrong, and re-copying and expanding again fixes it.
    if clipboard_text:
        text = text.replace("${clipboard}", clipboard_text)
    now = datetime.datetime.now()
    text = text.replace("${datetime}", now.strftime("%B %d, %Y %I:%M %p"))
    text = text.replace("${date}", datetime.date.today().strftime("%B %d, %Y"))
    text = text.replace("${time}", now.strftime("%I:%M %p"))
    text = text.replace("${day}", now.strftime("%d").lstrip("0") or "0")
    text = text.replace("${month}", now.strftime("%B"))
    text = text.replace("${year}", now.strftime("%Y"))
    text = text.replace("${username}", os.environ.get("USERNAME", os.environ.get("USER", "")))
    has_cursor = "${cursor}" in text
    cursor_offset = len(text)
    if has_cursor:
        cursor_offset = text.index("${cursor}")
        text = text.replace("${cursor}", "")
    return text, cursor_offset, has_cursor


def try_expand(
    text: str,
    caret: int,
    library: AbbreviationLibrary,
    clipboard_text: str = "",
    *,
    clipboard_provider: Callable[[], str] | None = None,
) -> AbbreviationMatch | None:
    """Check for an abbreviation ending just before the character at caret-1.

    caret-1 must be a trigger character (space, punctuation, etc.).
    Returns an AbbreviationMatch or None.

    *clipboard_provider*, when given, is called instead of *clipboard_text* --
    and only once an abbreviation has actually matched and its expansion
    contains ``${clipboard}`` (#1346 follow-up). The Windows clipboard is a
    shared, single-owner OS resource: opening it is a cross-process
    synchronization point that can block behind a clipboard manager or a screen
    reader's own clipboard polling. The old contract made the caller fetch it
    up front, which in practice meant one clipboard open *per keystroke*;
    matches are rare and ``${clipboard}`` expansions rarer, so the provider
    turns that into approximately never.
    """
    if caret < 2 or caret > len(text):
        return None
    trigger_char = text[caret - 1]
    if trigger_char not in _TRIGGER_CHARS:
        return None
    token_end = caret - 1
    token_start = token_end
    while token_start > 0 and not text[token_start - 1].isspace():
        token_start -= 1
    if token_start >= token_end:
        return None
    token = text[token_start:token_end]
    candidates = sorted(
        (a for a in library.abbreviations if a.enabled),
        key=lambda a: len(a.abbreviation),
        reverse=True,
    )
    for abbr in candidates:
        if not abbr.accepts_trigger(trigger_char):
            continue
        if abbr.case_sensitive:
            match = token == abbr.abbreviation
        else:
            match = token.lower() == abbr.abbreviation.lower()
        if match:
            clip = clipboard_text
            if clipboard_provider is not None and "${clipboard}" in abbr.expansion:
                clip = clipboard_provider()
            resolved, cursor_offset, has_cursor = resolve_expansion(abbr.expansion, clip)
            return AbbreviationMatch(
                token_start=token_start,
                token_end=token_end,
                resolved_text=resolved,
                cursor_offset=cursor_offset,
                has_cursor=has_cursor,
                abbreviation=abbr,
                trailing_space=abbr.trailing_space and trigger_char not in _SPACE_TRIGGERS,
            )
    return None


# Quillin-contributed abbreviations moved to their own module under GATE-11
# (extract, never rebaseline); re-exported so every existing import still works.
from quill.core.abbreviations_contributed import (  # noqa: E402
    build_contributed_library as build_contributed_library,
)
from quill.core.abbreviations_contributed import (  # noqa: E402
    contributed_abbreviation_id as contributed_abbreviation_id,
)

# The on-disk half moved to its own module under GATE-11 (extract, never
# rebaseline); re-exported so every existing import still works.
from quill.core.abbreviations_store import (  # noqa: E402
    load_abbreviation_library as load_abbreviation_library,
)
from quill.core.abbreviations_store import (  # noqa: E402
    save_abbreviation_library as save_abbreviation_library,
)


def record_use(library: AbbreviationLibrary, abbreviation_id: str) -> None:
    """Note that an entry was just used (Quick Insert sorts on this)."""
    for a in library.abbreviations:
        if a.id == abbreviation_id:
            a.usage_count += 1
            a.last_used = datetime.datetime.now(datetime.UTC).isoformat()
            return


def categories(library: AbbreviationLibrary) -> list[str]:
    """Every category in use, in first-seen order. "" (Uncategorised) is
    reported as the empty string and sorts first at the call site."""
    seen: list[str] = []
    for a in library.abbreviations:
        if a.category not in seen:
            seen.append(a.category)
    return seen


def quick_insert_order(library: AbbreviationLibrary) -> list[Abbreviation]:
    """Enabled entries ordered for the Quick Insert picker: most-used first,
    then alphabetically. ``manual`` entries are included -- Quick Insert is the
    only way to reach them."""
    return sorted(
        library.enabled_only(),
        key=lambda a: (-a.usage_count, a.abbreviation.lower()),
    )
