"""Copy to Site's order and its terms (PRD 15.2), split from workbench_site_copy (GATE-11).

- :func:`ordered`: what a thing needs is copied before it. Terms, then pictures
  and files, then patterns and forms, then posts and pages, then menus (which
  link to them), whatever order the selection was made in.
- :func:`term_id`: a term the target already has -- found by name, or because
  WordPress answers ``term_exists`` (an earlier line of the same copy made it,
  or someone else just did) -- is that term, "already there", never a failure.

Wx-free.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from quill.core.wordpress.api import WordPressApi, WordPressApiError

__all__ = ["ALREADY_THERE", "ordered", "term_id"]

#: The outcome word for a term the target already had.
ALREADY_THERE = "Already there:"

_RANK = {"term": 0, "picture or file": 1, "pattern": 2, "form": 3, "gravity_form": 3, "menu": 5}
_ITEMS = 4  # posts, pages and anything else


def ordered(lines: Sequence[Any]) -> list[Any]:
    """*lines* with what others need first; the selection's order kept within a kind."""
    return sorted(lines, key=lambda line: _RANK.get(str(line.kind), _ITEMS))


def _by_name(target: WordPressApi, route: str, name: str) -> Mapping[str, Any] | None:
    try:
        found = target.get(route, search=name, _fields="id,name")
    except WordPressApiError:
        return None
    rows = [f for f in found if isinstance(f, dict)] if isinstance(found, list) else []
    return next((t for t in rows if str(t.get("name", "")).casefold() == name.casefold()), None)


def term_id(target: WordPressApi, route: str, body: Mapping[str, Any]) -> tuple[int, bool]:
    """(the target's id for the term *body* names, whether it was already there).

    Made when the target has no term of that name; otherwise that term, by
    name or by the id WordPress gives with ``term_exists``. Any other refusal
    is raised.
    """
    name = str(body.get("name", "") or "")
    match = _by_name(target, route, name) if name else None
    if match is not None:
        return int(match.get("id", 0) or 0), True
    try:
        made = target.post(route, dict(body))
    except WordPressApiError as exc:
        if exc.wp_code != "term_exists":
            raise
        data = exc.body.get("data") if isinstance(exc.body, dict) else None
        ident = int(data.get("term_id", 0) or 0) if isinstance(data, dict) else 0
        if not ident:
            again = _by_name(target, route, name)
            ident = int(again.get("id", 0) or 0) if again is not None else 0
        if not ident:
            raise
        return ident, True
    return (int(made.get("id", 0) or 0) if isinstance(made, dict) else 0), False
