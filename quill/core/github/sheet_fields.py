"""Small builders the GitHub sheet catalogue is written with (GitHub PRD Appendix C).

Each Appendix C object is a :class:`~quill.core.github.sheet_engine.SheetDef`
written in a few dozen lines; these keep those lines about GitHub rather than
about dataclass plumbing: field constructors, safe JSON digging, dates written
out in full (section 15.2: never relative only), colours spoken by name, and
the write shapes GitHub uses again and again.

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any

from quill.core.github.permissions import WriteTier
from quill.core.github.sheet_engine import Ident, Write
from quill.core.workbench.properties import FieldKind, FieldSpec, PageSpec, Value

__all__ = [
    "COLOURS",
    "REACTIONS",
    "colour_hex",
    "colour_name",
    "dig",
    "ed",
    "gql_toggle",
    "logins",
    "lst",
    "names",
    "obj",
    "page",
    "patch",
    "ro",
    "toggle",
    "when",
]

#: GitHub's eight reactions: the API word and the word said.
REACTIONS: tuple[tuple[str, str], ...] = (
    ("+1", "thumbs up"),
    ("-1", "thumbs down"),
    ("laugh", "laugh"),
    ("hooray", "hooray"),
    ("confused", "confused"),
    ("heart", "heart"),
    ("rocket", "rocket"),
    ("eyes", "eyes"),
)

#: Common colours by name, for a label's colour typed or spoken as a word.
COLOURS: dict[str, str] = {
    "red": "d73a4a",
    "orange": "e99695",
    "yellow": "fbca04",
    "green": "0e8a16",
    "light green": "c2e0c6",
    "teal": "006b75",
    "blue": "0075ca",
    "light blue": "a2eeef",
    "navy": "1d76db",
    "purple": "7057ff",
    "violet": "d876e3",
    "pink": "f9d0c4",
    "grey": "cfd3d7",
    "gray": "cfd3d7",
    "black": "000000",
    "white": "ffffff",
    "brown": "8b4513",
}


def ro(
    key: str,
    label: str,
    kind: FieldKind = FieldKind.TEXT,
    help: str = "",  # noqa: A002 - the field's name
) -> FieldSpec:
    """A read-only fact: a read-only text box, never bare static text."""
    return FieldSpec(key, label, kind, readonly=True, help=help)


def ed(
    key: str,
    label: str,
    kind: FieldKind = FieldKind.TEXT,
    help: str = "",  # noqa: A002
    *,
    requirement: str = "",
    choices: tuple[str, ...] = (),
    create: str = "",
) -> FieldSpec:
    """An editable field; its :class:`Write` (in the sheet's writes) says what it needs."""
    return FieldSpec(
        key, label, kind, requirement=requirement, help=help, choices=choices, create=create
    )


def page(key: str, title: str, *fields: FieldSpec) -> PageSpec:
    return PageSpec(key, title, tuple(fields))


def patch(
    path: str,
    requirement: str,
    tier: WriteTier,
    body_key: str = "",
    encode: Callable[[Value, Mapping[str, object], Ident], dict[str, object]] | None = None,
    *,
    undo: bool = True,
    method: str = "PATCH",
) -> Write:
    return Write(path, requirement, tier, method, "patch", body_key, encode, undo)


def toggle(path: str, requirement: str, tier: WriteTier, *, off_path: str = "") -> Write:
    """PUT when on, DELETE when off: star, follow, block, lock."""
    return Write(path, requirement, tier, "PUT", "toggle", off_path=off_path)


def gql_toggle(on: str, off: str, requirement: str, tier: WriteTier) -> Write:
    """A GraphQL mutation for on and another for off, each taking ``$id``."""

    def encode(_value: Value, _choices: Mapping[str, object], ident: Ident) -> dict[str, object]:
        return {"id": ident.get("node_id", "")}

    return Write(on, requirement, tier, "POST", "graphql", encode=encode, off_path=off)


def dig(data: Mapping[str, Any] | None, *path: str) -> Any:
    """``data[a][b][c]``, or ``None`` the moment one step is missing."""
    found: Any = data
    for step in path:
        if not isinstance(found, Mapping):
            return None
        found = found.get(step)
    return found


def lst(data: Mapping[str, Any] | None, key: str) -> list[Any]:
    """``data[key]`` when it is a JSON list, else an empty one."""
    found = (data or {}).get(key)
    return found if isinstance(found, list) else []


def obj(data: Mapping[str, Any] | None, key: str) -> Mapping[str, Any]:
    """``data[key]`` when it is a JSON object, else an empty one."""
    found = (data or {}).get(key)
    return found if isinstance(found, Mapping) else {}


def names(rows: object, key: str = "name") -> tuple[str, ...]:
    """The *key* of each object in a JSON list (label names, team slugs)."""
    if not isinstance(rows, list):
        return ()
    return tuple(str(row.get(key, "")) for row in rows if isinstance(row, Mapping) and row.get(key))


def logins(rows: object) -> tuple[str, ...]:
    return names(rows, "login")


def when(stamp: object, now: datetime | None = None) -> str:
    """ "9 November 2026, 14:05, 3 hours ago": written out, never relative only."""
    if not isinstance(stamp, str) or not stamp:
        return ""
    try:
        moment = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError:
        return stamp
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    reference = now or datetime.now(UTC)
    seconds = int((reference - moment).total_seconds())
    if seconds < 0:
        ago = "in the future"
    elif seconds < 3600:
        ago = f"{max(1, seconds // 60)} minutes ago"
    elif seconds < 86400:
        ago = f"{seconds // 3600} hours ago"
    else:
        ago = f"{seconds // 86400} days ago"
    local = moment.astimezone()
    return f"{local.day} {local:%B %Y, %H:%M}, {ago}"


def colour_hex(text: str) -> str:
    """A colour typed as a name ("green") or as hex ("#0e8a16"), as GitHub's six digits."""
    word = text.strip().lower().lstrip("#")
    if word in COLOURS:
        return COLOURS[word]
    if len(word) == 6 and all(ch in "0123456789abcdef" for ch in word):
        return word
    raise ValueError(f"{text} is not a colour: type a name such as green, or six hex digits.")


def colour_name(hex_text: str) -> str:
    """The nearest common colour's name for six hex digits: "green (0e8a16)"."""
    word = hex_text.strip().lower().lstrip("#")
    if len(word) != 6:
        return hex_text
    try:
        red, green, blue = (int(word[i : i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return hex_text

    def distance(other: str) -> int:
        r, g, b = (int(other[i : i + 2], 16) for i in (0, 2, 4))
        return (r - red) ** 2 + (g - green) ** 2 + (b - blue) ** 2

    nearest = min((name for name in COLOURS if name != "gray"), key=lambda n: distance(COLOURS[n]))
    return f"{nearest} ({word})"
