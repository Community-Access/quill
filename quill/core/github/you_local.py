"""Pin in the Workbench and Favorite, on the You page (GitHub PRD 16.7).

Both live on this device, not on GitHub: Favorites is the Workbench's
Favorites node, and pinning a repository keeps it under Repositories >
Pinned. The menu rows **Add to or Remove from Favorites** and **Pin** change
the same store (:class:`quill.core.github.saved_items.SavedItems`), so the
You page and the rows can never disagree.

They are not GitHub writes, so the sheet's engine never sees them: the
window adds these fields to the You page when it opens a sheet
(:func:`with_local_fields`), and saving applies them here first
(:func:`apply_local`) and hands the rest to the one checked save path.
wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from quill.core.workbench.properties import FieldChange, FieldKind, FieldSpec, PageSpec, SheetSpec

__all__ = ["LOCAL_YOU", "apply_local", "local_values", "with_local_fields"]

FAVORITE, PINNED = "in_favorites", "workbench_pinned"

#: Each kind's local relationships, in the order they follow GitHub's on its You page.
LOCAL_YOU: dict[str, tuple[str, ...]] = {
    "repository": (FAVORITE, PINNED),
    "issue": (FAVORITE,),
    "pull_request": (FAVORITE,),
}

_SPECS = {
    FAVORITE: FieldSpec(
        FAVORITE,
        "In Favorites",
        FieldKind.CHECK,
        help="Keep it in the Workbench's Favorites node, on this computer. Add to or Remove "
        "from Favorites on the row does the same.",
    ),
    PINNED: FieldSpec(
        PINNED,
        "Pinned in the Workbench",
        FieldKind.CHECK,
        help="Keep it under Repositories > Pinned, on this computer. Pin on the row does the same.",
    ),
}
_KIND_WORD = {"issue": "issue", "pull_request": "pr", "repository": "repository"}


def with_local_fields(sheet: SheetSpec, kind: str) -> SheetSpec:
    """*sheet* with this device's relationships at the end of its You page."""
    keys = LOCAL_YOU.get(kind, ())
    if not keys:
        return sheet
    pages = []
    for page in sheet.pages:
        if page.key == "you":
            have = {spec.key for spec in page.fields}
            extra = tuple(_SPECS[key] for key in keys if key not in have)
            page = PageSpec(page.key, page.title, (*page.fields, *extra))
        pages.append(page)
    return SheetSpec(sheet.kind, sheet.title, tuple(pages))


def _repository(ident: Mapping[str, str]) -> str:
    return ident.get("repo", "")


def local_values(saved: Any, kind: str, ident: Mapping[str, str], url: str) -> dict[str, bool]:
    """Whether the object is in Favorites, and (a repository) pinned in the Workbench."""
    keys = LOCAL_YOU.get(kind, ())
    found: dict[str, bool] = {}
    if FAVORITE in keys:
        found[FAVORITE] = any(f.url == url for f in saved.favorites)
    if PINNED in keys:
        found[PINNED] = bool(saved.is_pinned(_repository(ident)))
    return found


def apply_local(
    saved: Any,
    kind: str,
    ident: Mapping[str, str],
    url: str,
    title: str,
    changes: Sequence[FieldChange],
) -> tuple[list[str], list[FieldChange]]:
    """Apply the local changes; return what was done, in words, and the GitHub changes left."""
    from quill.core.github.saved_items import FavoriteItem

    keys = LOCAL_YOU.get(kind, ())
    said: list[str] = []
    rest: list[FieldChange] = []
    for change in changes:
        if change.key not in keys:
            rest.append(change)
            continue
        on = change.after is True
        if change.key == FAVORITE:
            existing = next((f for f in saved.favorites if f.url == url), None)
            if on and existing is None:
                saved.add_favorite(FavoriteItem(_repository(ident), _KIND_WORD[kind], url, title))
            elif not on and existing is not None:
                saved.remove_favorite(existing.key)
            said.append(
                f"{'Added' if on else 'Removed'} {title} {'to' if on else 'from'} Favorites."
            )
        else:
            repo = _repository(ident)
            if on:
                saved.pin_repo(repo)
            else:
                saved.unpin_repo(repo)
            said.append(f"{'Pinned' if on else 'Unpinned'} {repo} in the Workbench.")
    if said:
        saved.save()
    return said, rest
