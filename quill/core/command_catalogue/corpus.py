"""The Command Key's test corpus format (docs/design/command-key.md 14.1).

One JSON-lines file per app, ``tests/fixtures/command_key/<app>.jsonl``. Each
line is one thing a person might type or say, the context it was said in, and
what must happen: one command (with its arguments), or a refusal of a named
kind. The corpus is the spec of the matcher; the matcher is tuned to it and
gated on it.

This module only reads and checks the format. It is wx-free and has no idea
how a request is resolved, so a malformed row fails here, with its line number,
rather than as a confusing miss in a resolver test.
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from pathlib import Path

from quill.core.error_codes import CodedError

__all__ = [
    "MODES",
    "REFUSALS",
    "SETS",
    "CorpusError",
    "CorpusRow",
    "load_corpus",
    "parse_row",
]

#: How the words arrived.
MODES = frozenset({"typed", "dictated", "misheard"})
#: The kinds of "no" a row can expect.
REFUSALS = frozenset({"not_here", "never", "ask", "other_app", "disabled"})
#: Tuning rows, and the held-out rows that are never tuned on.
SETS = frozenset({"train", "held_out"})


class CorpusError(CodedError, ValueError):
    """A corpus row that does not have the documented shape."""

    code = "QUILL-CORE-COMMANDCORPUS-BAD-ROW"


@dataclass(frozen=True, slots=True)
class CorpusRow:
    """One phrasing and what it must do."""

    text: str
    app: str
    mode: str = "typed"
    surface: str = ""
    #: The ids enabled for this row, or None for "whatever the app enables".
    enabled: tuple[str, ...] | None = None
    heard_alternatives: tuple[str, ...] = ()
    recent: tuple[str, ...] = ()
    last_offer: tuple[str, ...] = ()
    expect_id: str = ""
    expect_args: Mapping[str, object] = field(default_factory=dict)
    expect_refuse: str = ""
    pointer: str = ""
    #: The highest tier allowed to settle it: 1 exact, 2 fuzzy, 3 Jev, 4 your AI.
    tier_max: int = 2
    set: str = "train"
    line: int = 0

    @property
    def is_refusal(self) -> bool:
        return bool(self.expect_refuse)


def _strings(value: object, name: str, line: int) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise CorpusError(f"line {line}: {name} must be a list of strings")
    return tuple(value)


def parse_row(raw: Mapping[str, object], *, line: int = 0) -> CorpusRow:
    """Check one decoded row and return it as a :class:`CorpusRow`."""
    text = raw.get("text")
    app = raw.get("app")
    if not isinstance(text, str) or not text.strip():
        raise CorpusError(f"line {line}: text is missing")
    if not isinstance(app, str) or not app:
        raise CorpusError(f"line {line}: app is missing")
    mode = raw.get("mode", "typed")
    if mode not in MODES:
        raise CorpusError(f"line {line}: mode {mode!r} is not one of {sorted(MODES)}")
    row_set = raw.get("set", "train")
    if row_set not in SETS:
        raise CorpusError(f"line {line}: set {row_set!r} is not one of {sorted(SETS)}")
    tier_max = raw.get("tier_max", 2)
    if not isinstance(tier_max, int) or not 1 <= tier_max <= 4:
        raise CorpusError(f"line {line}: tier_max must be 1 to 4")
    expect = raw.get("expect")
    if not isinstance(expect, Mapping):
        raise CorpusError(f"line {line}: expect is missing")
    expect_id = expect.get("id", "")
    refuse = expect.get("refuse", "")
    if bool(expect_id) == bool(refuse):
        raise CorpusError(f"line {line}: expect needs exactly one of id or refuse")
    if refuse and refuse not in REFUSALS:
        raise CorpusError(f"line {line}: refuse {refuse!r} is not one of {sorted(REFUSALS)}")
    args = expect.get("args", {})
    if not isinstance(args, Mapping):
        raise CorpusError(f"line {line}: expect.args must be an object")
    enabled_raw = raw.get("enabled")
    enabled = None if enabled_raw in (None, "default") else _strings(enabled_raw, "enabled", line)
    pointer = expect.get("pointer", "")
    return CorpusRow(
        text=text,
        app=app,
        mode=str(mode),
        surface=str(raw.get("surface", "") or ""),
        enabled=enabled,
        heard_alternatives=_strings(raw.get("heard_alternatives"), "heard_alternatives", line),
        recent=_strings(raw.get("recent"), "recent", line),
        last_offer=_strings(raw.get("last_offer"), "last_offer", line),
        expect_id=str(expect_id or ""),
        expect_args=dict(args),
        expect_refuse=str(refuse or ""),
        pointer=str(pointer or ""),
        tier_max=tier_max,
        set=str(row_set),
        line=line,
    )


def iter_corpus(path: Path) -> Iterator[CorpusRow]:
    """Yield every row of one corpus file; blank lines and ``//`` lines are skipped."""
    for number, text in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = text.strip()
        if not stripped or stripped.startswith("//"):
            continue
        try:
            raw = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise CorpusError(f"{path.name} line {number}: not JSON ({exc.msg})") from exc
        if not isinstance(raw, Mapping):
            raise CorpusError(f"{path.name} line {number}: a row must be an object")
        yield parse_row(raw, line=number)


def load_corpus(path: Path) -> tuple[CorpusRow, ...]:
    """Every row of one corpus file, checked."""
    return tuple(iter_corpus(path))
