"""A Workbench window's menu bar as data, and the accelerator rule checked on it.

The house rule (CLAUDE.md, "Menu accelerators"): every enabled row shows a
keyboard route in its label, and no two rows in one bar claim the same key.
The access-key rule (GATE-14) adds that no two titles on the bar, and no two
rows in one menu, share an ``&`` letter. A provider's bar is a tuple of
:class:`MenuSpec`; :func:`problems` lists every breach, so a test can fail on
the first one and the window can be built without a second look.

Keys here are the defaults. The window renders whatever is bound, so a key
the person changes follows the row.

A menu may hold a :class:`MenuSub`, a submenu (View > Show, Go > Pinned).
Its rows follow the same rules, with one difference: a submenu row may go
without a key when it has an access letter, because a submenu of twenty
filter toggles cannot each have a chord (decision 11) and the letter is the
keyboard route the house rule asks for. A *dynamic* submenu is filled by the
provider each time its menu opens (the person's own pins and searches); its
rows carry numbered access letters, the way a recent-files list does.
A row may be a check item (*check*) or one of a radio group (*radio*, the
group's name); the provider says which are on.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass

__all__ = ["MenuRow", "MenuSpec", "MenuSub", "access_letter", "all_rows", "problems", "rows"]


@dataclass(frozen=True)
class MenuRow:
    """One row: its command id, its label (with an ``&`` letter) and default key."""

    command_id: str
    label: str
    key: str = ""
    help: str = ""
    check: bool = False
    radio: str = ""


@dataclass(frozen=True)
class MenuSub:
    """A submenu: its title (with an ``&`` letter), its rows, or a *dynamic* key."""

    title: str
    rows: tuple[MenuRow | None, ...] = ()
    dynamic: str = ""
    help: str = ""


@dataclass(frozen=True)
class MenuSpec:
    title: str
    rows: tuple[MenuRow | MenuSub | None, ...]  # None is a separator


def access_letter(label: str) -> str:
    """The ``&`` letter of *label*, lower-cased ("" when it has none)."""
    index = label.replace("&&", "").find("&")
    clean = label.replace("&&", "")
    return clean[index + 1].lower() if 0 <= index < len(clean) - 1 else ""


def rows(bar: Sequence[MenuSpec]) -> Iterator[tuple[MenuSpec, MenuRow]]:
    """Every top-level row of every menu (the ones that carry keys); submenus skipped."""
    for menu in bar:
        for row in menu.rows:
            if isinstance(row, MenuRow):
                yield menu, row


def all_rows(bar: Sequence[MenuSpec]) -> Iterator[tuple[MenuSpec, MenuRow]]:
    """Every row, submenus' static rows included."""
    for menu in bar:
        for row in menu.rows:
            if isinstance(row, MenuRow):
                yield menu, row
            elif isinstance(row, MenuSub):
                for inner in row.rows:
                    if inner is not None:
                        yield menu, inner


def _letters_problems(where: str, labels: Sequence[str]) -> list[str]:
    letters = [access_letter(label) for label in labels]
    return [
        f"{where} has two rows on the access key {letter!r}."
        for letter in sorted({item for item in letters if item})
        if letters.count(letter) > 1
    ]


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
        labels = [row.label if isinstance(row, MenuRow) else row.title for row in menu.rows if row]
        found.extend(_letters_problems(menu.title, labels))
        for sub in menu.rows:
            if not isinstance(sub, MenuSub):
                continue
            if not access_letter(sub.title):
                found.append(f"{menu.title} > {sub.title} has no access key.")
            if sub.dynamic and sub.rows:
                found.append(f"{menu.title} > {sub.title} is dynamic and also has rows.")
            inner = [row for row in sub.rows if row is not None]
            found.extend(_letters_problems(f"{menu.title} > {sub.title}", [r.label for r in inner]))
            for row in inner:
                if not row.key and not access_letter(row.label):
                    found.append(f"{menu.title} > {sub.title} > {row.label} shows no key route.")
    for menu, row in all_rows(bar):
        if not row.key:
            if isinstance(row, MenuRow) and any(r is row for r in menu.rows):
                found.append(f"{menu.title} > {row.label} shows no key.")
            if row.command_id in seen_ids:
                found.append(f"{row.command_id} appears twice on the bar.")
            seen_ids.add(row.command_id)
            continue
        canonical = row.key.lower().replace(" ", "")
        if canonical in seen_keys:
            found.append(f"{row.key} is claimed by {seen_keys[canonical]} and {row.label}.")
        seen_keys[canonical] = row.label
        if row.command_id in seen_ids:
            found.append(f"{row.command_id} appears twice on the bar.")
        seen_ids.add(row.command_id)
    return found
