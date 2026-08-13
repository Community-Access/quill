"""Abbreviation expansion library — bare-word TextExpander-style shortcuts.

Abbreviations differ from snippets: no trigger prefix is required. The user
types "btw " and the editor silently replaces "btw" with "by the way". A
sound can be played on expansion if configured.
"""

from __future__ import annotations

import datetime
import os
import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

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


def contributed_abbreviation_id(quillin_id: str, trigger: str) -> str:
    """Return a stable, namespaced id for a Quillin-contributed abbreviation."""
    return f"quillin:{quillin_id}:{trigger}"


def build_contributed_library(
    contributions: Iterable[tuple[str, Iterable[object]]],
    *,
    is_enabled: Callable[[str, str, bool], bool] | None = None,
) -> AbbreviationLibrary:
    """Build an in-memory library from Quillin-contributed abbreviation dicts.

    *contributions* pairs a ``quillin_id`` with that manifest's raw
    ``contributes.abbreviations`` entries. Only *static* abbreviations (those
    with an ``expansion``) are included; handler-based entries are skipped
    because the bare-word expander cannot run a handler mid-type (use a smart
    trigger or menu command for those). ``is_enabled(quillin_id, trigger,
    enabled_by_default)`` decides inclusion; when omitted the entry's
    ``enabled_by_default`` (default True) is used. Ids are deterministic so this
    library can be rebuilt on every Quillin reload without churn, and is kept
    separate from the user's saved library (it is never persisted).
    """
    abbreviations: list[Abbreviation] = []
    for quillin_id, entries in contributions:
        for raw in entries:
            if not isinstance(raw, dict):
                continue
            trigger = str(raw.get("trigger", "")).strip()
            expansion = raw.get("expansion")
            if not trigger or not isinstance(expansion, str):
                continue
            default_enabled = bool(raw.get("enabled_by_default", True))
            if is_enabled is not None:
                if not is_enabled(quillin_id, trigger, default_enabled):
                    continue
            elif not default_enabled:
                continue
            abbreviations.append(
                Abbreviation(
                    id=contributed_abbreviation_id(quillin_id, trigger),
                    abbreviation=trigger,
                    expansion=expansion,
                    description=str(raw.get("description", "")),
                    case_sensitive=bool(raw.get("case_sensitive", False)),
                )
            )
    return AbbreviationLibrary(version=1, abbreviations=abbreviations)


def _one_of(value: object, allowed: tuple[str, ...], default: str) -> str:
    """*value* when it is one of *allowed*, else *default* (unknown values in a
    hand-edited file degrade to the safe setting rather than breaking the load)."""
    text = str(value) if value is not None else ""
    return text if text in allowed else default


def _as_int(value: object) -> int:
    return int(value) if isinstance(value, int) and not isinstance(value, bool) else 0


def load_abbreviation_library(data_dir: Path | None = None) -> AbbreviationLibrary:
    from quill.core import paths
    from quill.core.storage import read_json

    base = data_dir if data_dir is not None else paths.app_data_dir()
    path = base / _ABBREVIATIONS_FILE
    if not path.exists():
        return _make_default_library()
    # read_json returns its default (not a raise) on a corrupt/unreadable file.
    # Use a sentinel so a present-but-corrupt file degrades to the built-in
    # defaults rather than an empty library (passing default={} would look like
    # a valid-but-empty payload and silently wipe the user's abbreviations).
    corrupt = object()
    try:
        data = read_json(path, default=corrupt)
    except Exception:  # noqa: BLE001
        return _make_default_library()
    if data is corrupt or not isinstance(data, dict):
        return _make_default_library()
    abbreviations: list[Abbreviation] = []
    for raw in data.get("abbreviations", []):
        if not isinstance(raw, dict):
            continue
        try:
            abbreviations.append(
                Abbreviation(
                    id=str(raw.get("id", uuid.uuid4())),
                    abbreviation=str(raw.get("abbreviation", "")),
                    expansion=str(raw.get("expansion", "")),
                    case_sensitive=bool(raw.get("case_sensitive", False)),
                    enabled=bool(raw.get("enabled", True)),
                    description=str(raw.get("description", "")),
                    # v2 per-entry settings. Every one defaults, so a v1 file
                    # (which has none of these keys) loads unchanged.
                    category=str(raw.get("category", "")),
                    speak_mode=_one_of(raw.get("speak_mode"), SPEAK_MODES, "silent"),
                    sound=_one_of(raw.get("sound"), SOUND_MODES, "inherit"),
                    trailing_space=bool(raw.get("trailing_space", False)),
                    triggers=_one_of(raw.get("triggers"), TRIGGER_MODES, "both"),
                    usage_count=_as_int(raw.get("usage_count")),
                    last_used=str(raw.get("last_used", "")),
                )
            )
        except Exception:  # noqa: BLE001
            continue
    return AbbreviationLibrary(
        version=int(data.get("version", 1)),
        abbreviations=abbreviations,
    )


def save_abbreviation_library(library: AbbreviationLibrary, data_dir: Path | None = None) -> None:
    from quill.core import paths
    from quill.core.storage import write_json_atomic

    base = data_dir if data_dir is not None else paths.app_data_dir()
    path = base / _ABBREVIATIONS_FILE
    write_json_atomic(
        path,
        {
            "version": SCHEMA_VERSION,
            "abbreviations": [
                {
                    "id": a.id,
                    "abbreviation": a.abbreviation,
                    "expansion": a.expansion,
                    "case_sensitive": a.case_sensitive,
                    "enabled": a.enabled,
                    "description": a.description,
                    "category": a.category,
                    "speak_mode": a.speak_mode,
                    "sound": a.sound,
                    "trailing_space": a.trailing_space,
                    "triggers": a.triggers,
                    "usage_count": a.usage_count,
                    "last_used": a.last_used,
                }
                for a in library.abbreviations
            ],
        },
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
