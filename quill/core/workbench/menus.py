"""A Workbench window's menu bar as data, and the accelerator rule checked on it.

The house rule (CLAUDE.md, "Menu accelerators"): every enabled row shows a
keyboard route in its label, and no two rows in one bar claim the same key.
The access-key rule (GATE-14) adds that no two titles on the bar, and no two
rows in one menu, share an ``&`` letter. A provider's bar is a tuple of
:class:`MenuSpec`; :func:`problems` lists every breach, so a test can fail on
the first one and the window can be built without a second look.

Keys here are the defaults. The window renders whatever is bound, so a key
the person changes follows the row.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass

__all__ = ["MenuRow", "MenuSpec", "access_letter", "problems", "rows"]


@dataclass(frozen=True)
class MenuRow:
    """One row: its command id, its label (with an ``&`` letter) and default key."""

    command_id: str
    label: str
    key: str = ""
    help: str = ""


@dataclass(frozen=True)
class MenuSpec:
    title: str
    rows: tuple[MenuRow | None, ...]  # None is a separator


def access_letter(label: str) -> str:
    """The ``&`` letter of *label*, lower-cased ("" when it has none)."""
    index = label.replace("&&", "").find("&")
    clean = label.replace("&&", "")
    return clean[index + 1].lower() if 0 <= index < len(clean) - 1 else ""


def rows(bar: Sequence[MenuSpec]) -> Iterator[tuple[MenuSpec, MenuRow]]:
    for menu in bar:
        for row in menu.rows:
            if row is not None:
                yield menu, row


def problems(bar: Sequence[MenuSpec]) -> list[str]:
    """Every breach of the accelerator and access-key rules, as sentences."""
    found: list[str] = []
    titles = [access_letter(menu.title) for menu in bar]
    for letter in {t for t in titles if t}:
        if titles.count(letter) > 1:
            found.append(f"The bar's titles share the access key {letter!r}.")
    if "" in titles:
        found.append("A menu title has no access key.")
    seen_keys: dict[str, str] = {}
    seen_ids: set[str] = set()
    for menu in bar:
        letters = [access_letter(row.label) for row in menu.rows if row is not None]
        for letter in {item for item in letters if item}:
            if letters.count(letter) > 1:
                found.append(f"{menu.title} has two rows on the access key {letter!r}.")
    for menu, row in rows(bar):
        if not row.key:
            found.append(f"{menu.title} > {row.label} shows no key.")
            continue
        canonical = row.key.lower().replace(" ", "")
        if canonical in seen_keys:
            found.append(f"{row.key} is claimed by {seen_keys[canonical]} and {row.label}.")
        seen_keys[canonical] = row.label
        if row.command_id in seen_ids:
            found.append(f"{row.command_id} appears twice on the bar.")
        seen_ids.add(row.command_id)
    return found
