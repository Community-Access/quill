"""A site's own content types in the Navigator, each with its status lists (WP-B).

Posts and Pages have a child node per status (Published, Drafts, ...). A
site's own types are *dynamic* nodes (``custom_type``), one per type the
site describes, and the shared tree keeps a dynamic node childless and the
tree four levels deep (:mod:`quill.core.workbench.tree`). So each type's
status lists are dynamic siblings placed straight after it, labelled
"Events, Drafts", under More Content Types.

Nothing is guessed. The type's kind is its discovered REST base (or whole
route outside ``wp/v2``, :mod:`~quill.core.wordpress.site_types`), and the
statuses are WordPress's six plus every status the site lists at
``wp/v2/statuses`` (:func:`~quill.core.wordpress.site_types.statuses_for`).
Every status node is an ordinary ``items:custom`` list, so filters go to the
site, batch works on the selection, and New Here makes an item of the type.

A node's instance is ``site SEP kind`` for the type itself and ``site SEP
kind STATUS_SEP status`` for one of its status lists. Wx-free.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence

__all__ = [
    "CORE_STATUS_LABELS",
    "STATUS_SEP",
    "split_type",
    "type_children",
]

STATUS_SEP = "\x1e"
"""Between a type's kind and one of its statuses in a dynamic node's instance."""

CORE_STATUS_LABELS: Mapping[str, str] = {
    "publish": "Published",
    "draft": "Drafts",
    "pending": "Pending",
    "future": "Scheduled",
    "private": "Private",
    "trash": "Trash",
}
"""The words Posts and Pages use for their status children, so every type says the same."""


def split_type(dynamic: str) -> tuple[str, str]:
    """``(kind, status)`` from a dynamic type node's kind ("" status for the whole type)."""
    kind, _sep, status = dynamic.partition(STATUS_SEP)
    return kind, status


def _status_label(status: str, label: str) -> str:
    return CORE_STATUS_LABELS.get(status) or label or status.replace("_", " ").title()


def type_children(
    site: str,
    sep: str,
    types: Iterable[tuple[str, str]],
    statuses: Sequence[tuple[str, str]],
) -> tuple[tuple[str, str], ...]:
    """Each type's node, then one node per status, as ``(instance, label)`` pairs."""
    found: list[tuple[str, str]] = []
    for kind, label in types:
        found.append((f"{site}{sep}{kind}", label))
        found += [
            (f"{site}{sep}{kind}{STATUS_SEP}{status}", f"{label}, {_status_label(status, name)}")
            for status, name in statuses
            if status
        ]
    return tuple(found)
