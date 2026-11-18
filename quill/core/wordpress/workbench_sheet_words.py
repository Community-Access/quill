"""Sheet values a person hears: choices by name, terms and people by name and id.

Split from :mod:`quill.core.wordpress.workbench_sheets` (GATE-11). Review item
28: a sheet says "Published" and "Monday", never ``publish`` and ``1``.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

from quill.core.workbench.properties import FieldKind, FieldSpec

__all__ = ["choice_words", "labelled", "setting_value", "term_ids"]


#: What a stored choice is called aloud (item 28): "Published", never "publish".
_CHOICE_WORDS: dict[str, str] = {
    "publish": "Published",
    "draft": "Draft",
    "pending": "Pending review",
    "future": "Scheduled",
    "private": "Private",
    "approved": "Approved",
    "hold": "Waiting for approval",
    "spam": "Spam",
    "trash": "Trash",
}


def choice_words(choices: tuple[str, ...]) -> tuple[str, ...]:
    """Each stored choice in words: a known word, or the value with its underscores spoken."""
    return tuple(
        _CHOICE_WORDS.get(c, c.replace("_", " ").replace("-", " ").strip().capitalize() or c)
        for c in choices
    )


def setting_value(key: str) -> FieldSpec | None:
    """The Value field of setting *key* as a named choice, or None if it is free text."""
    from quill.core.wordpress.site_admin import CHOICES

    pairs = CHOICES.get(key)
    if not pairs:
        return None
    return FieldSpec(
        "value",
        "Value",
        FieldKind.CHOICE,
        requirement="manage_options",
        choices=tuple(code for code, _word in pairs),
        choice_words=tuple(word for _code, word in pairs),
    )


def labelled(name: str, ident: int) -> str:
    """ "News (12)": a term or person by name, with the id that saves it."""
    return f"{name} ({ident})" if name else str(ident)


_ID_AT_END = re.compile(r"\((\d+)\)\s*$")


def term_ids(values: Sequence[str], names: Mapping[str, int]) -> tuple[list[int], list[str]]:
    """Ids for "News (12)", "12" or "News"; and the names that match nothing."""
    ids: list[int] = []
    unknown: list[str] = []
    folded = {name.casefold(): ident for name, ident in names.items()}
    for value in values:
        text = value.strip()
        if not text:
            continue
        match = _ID_AT_END.search(text)
        if match:
            ids.append(int(match.group(1)))
        elif text.isdigit():
            ids.append(int(text))
        elif text.casefold() in folded:
            ids.append(folded[text.casefold()])
        else:
            unknown.append(text)
    return ids, unknown
