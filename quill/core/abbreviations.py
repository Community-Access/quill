"""Abbreviation expansion library — bare-word TextExpander-style shortcuts.

Abbreviations differ from snippets: no trigger prefix is required. The user
types "btw " and the editor silently replaces "btw" with "by the way". A
sound can be played on expansion if configured.
"""

from __future__ import annotations

import datetime
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


@dataclass(slots=True)
class Abbreviation:
    id: str
    abbreviation: str
    expansion: str
    case_sensitive: bool = False
    enabled: bool = True
    description: str = ""


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
    if clipboard_text:
        text = text.replace("${clipboard}", clipboard_text)
    text = text.replace("${date}", datetime.date.today().strftime("%B %d, %Y"))
    text = text.replace("${time}", datetime.datetime.now().strftime("%I:%M %p"))
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
) -> AbbreviationMatch | None:
    """Check for an abbreviation ending just before the character at caret-1.

    caret-1 must be a trigger character (space, punctuation, etc.).
    Returns an AbbreviationMatch or None.
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
        if abbr.case_sensitive:
            match = token == abbr.abbreviation
        else:
            match = token.lower() == abbr.abbreviation.lower()
        if match:
            resolved, cursor_offset, has_cursor = resolve_expansion(abbr.expansion, clipboard_text)
            return AbbreviationMatch(
                token_start=token_start,
                token_end=token_end,
                resolved_text=resolved,
                cursor_offset=cursor_offset,
                has_cursor=has_cursor,
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
            "version": library.version,
            "abbreviations": [
                {
                    "id": a.id,
                    "abbreviation": a.abbreviation,
                    "expansion": a.expansion,
                    "case_sensitive": a.case_sensitive,
                    "enabled": a.enabled,
                    "description": a.description,
                }
                for a in library.abbreviations
            ],
        },
    )
