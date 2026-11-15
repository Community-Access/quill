"""Gravity Forms responses filtered on the site, not only in the rows already loaded.

The Filter Builder on Responses writes conditions on a form's own field
filters (``GET gf/v2/forms/{id}/field-filters``): a question's number
(``3``, ``1.3``) or an entry detail (``date_created``, ``is_starred``). Those
conditions are translated here into the ``search`` parameter of
``GET gf/v2/entries`` -- ``{"status": ..., "field_filters": [{"key", "value",
"operator"}, ..., "mode": "all" | "any"]}`` -- and read page by page
(``paging[page_size]``, ``paging[current_page]``), so a filter finds a response
that was never in the first hundred. The site's ``total_count`` is the honest
count: "12 of 40 matching responses are shown".

Operators: *is* becomes Gravity Forms' ``contains`` (part of an answer is
enough, the same as the filter box), *is not* becomes ``isnot`` (Gravity
Forms has no "does not contain"). A ``form:`` condition narrows the forms
asked for (``form_ids``). Every other condition stays on this computer.

:func:`gravity_scope` carries the conditions to the loader the way
:func:`~quill.core.wordpress.workbench_listing.page_limit` carries the page
limit, so no loader signature changes. Wx-free.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any

from quill.core.workbench.filters import Condition, Operator

__all__ = [
    "ENTRY_DETAILS",
    "MODES",
    "GravityScope",
    "count_words",
    "current_scope",
    "gravity_scope",
    "is_site_condition",
    "read_entries",
    "search_json",
]

PAGE_SIZE = 100

MODES = ("all", "any")

ENTRY_DETAILS = frozenset({
    "entry_id",
    "id",
    "date_created",
    "date_updated",
    "is_starred",
    "is_read",
    "ip",
    "source_url",
    "created_by",
    "payment_status",
    "payment_date",
    "payment_amount",
    "transaction_id",
    "user_agent",
})
"""The entry details Gravity Forms' field filters offer besides the questions."""

_QUESTION = re.compile(r"^\d+(\.\d+)?$")

_SITE_OPERATORS = {Operator.IS: "contains", Operator.IS_NOT: "isnot"}


def is_site_condition(condition: Condition) -> bool:
    """Whether Gravity Forms can answer *condition* itself (a question or an entry detail)."""
    if condition.operator not in _SITE_OPERATORS:
        return False
    key = condition.attribute
    return bool(_QUESTION.match(key)) or key in ENTRY_DETAILS


@dataclass
class GravityScope:
    """One load's site-side conditions, and what the site said it matched."""

    conditions: tuple[Condition, ...] = ()
    mode: str = "all"
    form: str = ""
    """The ``form:`` condition's title: only that form's responses are asked for."""
    local: tuple[Condition, ...] = ()
    """The conditions left for this computer."""
    total: int | None = None
    shown: int = 0
    searched: bool = False

    @property
    def active(self) -> bool:
        return bool(self.conditions or self.form)


_SCOPE: ContextVar[GravityScope | None] = ContextVar("gravity_scope", default=None)


@contextmanager
def gravity_scope(conditions: Sequence[Condition], mode: str = "all") -> Iterator[GravityScope]:
    """Within the block, the Gravity Forms loader sends the site-side part of *conditions*."""
    site = tuple(c for c in conditions if is_site_condition(c))
    forms = [c for c in conditions if c.attribute == "form" and c.operator is Operator.IS]
    local = tuple(c for c in conditions if c not in site)
    scope = GravityScope(
        site, mode if mode in MODES else "all", forms[0].value if forms else "", local
    )
    token = _SCOPE.set(scope)
    try:
        yield scope
    finally:
        _SCOPE.reset(token)


def current_scope() -> GravityScope | None:
    return _SCOPE.get()


def search_json(status: str, conditions: Sequence[Condition], mode: str = "all") -> str:
    """The ``search`` parameter of ``gf/v2/entries`` for *status* and *conditions*.

    GFAPI::get_entries reads the mode inside ``field_filters``
    (``$search['field_filters']['mode']``), so the filters travel as a JSON
    object of numbered filters plus ``mode`` -- what PHP's own array becomes.
    """
    search: dict[str, Any] = {"status": status}
    filters = [
        {"key": c.attribute, "value": c.value, "operator": _SITE_OPERATORS[c.operator]}
        for c in conditions
        if is_site_condition(c)
    ]
    if filters:
        numbered: dict[str, Any] = {str(i): f for i, f in enumerate(filters)}
        search["field_filters"] = {**numbered, "mode": mode if mode in MODES else "all"}
    return json.dumps(search)


def read_entries(
    api: Any,
    route: str,
    form_ids: Sequence[str],
    status: str,
    scope: GravityScope | None,
    pages: int,
) -> list[dict[str, Any]]:
    """Responses for *form_ids*, page by page up to *pages*; the site's count goes in *scope*."""
    conditions = scope.conditions if scope else ()
    mode = scope.mode if scope else "all"
    base: dict[str, object] = {
        **{f"form_ids[{i}]": form_id for i, form_id in enumerate(sorted(form_ids))},
        "search": search_json(status, conditions, mode),
        "paging[page_size]": PAGE_SIZE,
    }
    entries: list[dict[str, Any]] = []
    total: int | None = None
    for page in range(1, max(1, pages) + 1):
        answer = api.get(route, **base, **{"paging[current_page]": page})
        found = answer.get("entries", []) if isinstance(answer, dict) else []
        found = [e for e in found if isinstance(e, dict)] if isinstance(found, list) else []
        if isinstance(answer, dict) and str(answer.get("total_count", "")).isdigit():
            total = int(answer["total_count"])
        entries += found
        if len(found) < PAGE_SIZE or (total is not None and len(entries) >= total):
            break
    if scope is not None:
        scope.total, scope.shown, scope.searched = total, len(entries), True
    return entries


def count_words(scope: GravityScope) -> str:
    """What the site matched and what is shown, said honestly; empty when not searched."""
    if not scope.searched or not scope.active:
        return ""
    how = "any of" if scope.mode == "any" and len(scope.conditions) > 1 else "all"
    matched = "the filter" if len(scope.conditions) < 2 else f"{how} the conditions"
    if scope.total is None:
        return f"{scope.shown} responses match {matched} on the site."
    if scope.shown >= scope.total:
        noun = "response matches" if scope.total == 1 else "responses match"
        return f"{scope.total} {noun} {matched} on the site, and all are shown."
    return (
        f"{scope.shown} of the {scope.total} responses that match {matched} on the site are "
        "shown. View > Load More reads more; Load All reads every one."
    )
