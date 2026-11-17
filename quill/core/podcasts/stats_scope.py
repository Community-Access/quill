"""Listening statistics for one folder (earshot.md E9).

Earshot's Listening Stats can be narrowed to all folders, any folder and its
subfolders, or Unfiled, and Cast's could only be narrowed by period. For
somebody who files podcasts by purpose -- work, news, audiobooks -- "how much
did I listen" is mostly a question about one of those.

Three rules, the same as Earshot's:

* **A folder means its whole subtree.** Statistics for "News" include "News /
  Local".
* **A show filed in several places counts once.** The scope is a *set of
  shows*, so a show in two folders of the subtree is in the set once.
* **History follows today's filing.** A session belongs to whichever folders
  its show is in now; nothing about filing is recorded with a session, and
  inventing it after the fact would be guessing.

wx-free, strict-typed, pure.
"""

from __future__ import annotations

from typing import Any

__all__ = ["ALL", "UNFILED", "scope_choices", "show_ids_in"]

#: The two scopes that are not folders.
ALL = ""
UNFILED = "unfiled"


def _placements(library: Any, show: Any) -> tuple[str | None, ...]:
    from quill.core.podcasts.folder_membership import placements

    return placements(library, show)


def _path(library: Any, folder: Any) -> str:
    names: list[str] = []
    seen: set[str] = set()
    current = folder
    while current is not None and current.id not in seen:
        seen.add(current.id)
        names.append(str(current.name))
        parent = current.parent_folder_id
        current = library.find_folder(parent) if parent else None
    return " / ".join(reversed(names))


def _subtree(library: Any, root_id: str) -> set[str]:
    wanted = {root_id}
    grew = True
    while grew:
        grew = False
        for folder in library.folders:
            if folder.parent_folder_id in wanted and folder.id not in wanted:
                wanted.add(folder.id)
                grew = True
    return wanted


def scope_choices(library: Any) -> list[tuple[str, str]]:
    """``(scope, label)`` pairs: All folders, every folder by its path, Unfiled.

    Unfiled is offered only when some podcast has no folder, and the folders
    only when there are any -- an empty choice is a control to tab past.
    """
    choices: list[tuple[str, str]] = [(ALL, "All folders")]
    folders = sorted(
        ((folder.id, _path(library, folder)) for folder in library.folders),
        key=lambda pair: pair[1].casefold(),
    )
    choices.extend(folders)
    if any(set(_placements(library, show)) <= {None} for show in library.shows):
        choices.append((UNFILED, "Unfiled"))
    return choices


def show_ids_in(library: Any, scope: str) -> set[str] | None:
    """The shows a scope covers, or ``None`` for every show."""
    if scope == ALL:
        return None
    if scope == UNFILED:
        return {show.id for show in library.shows if set(_placements(library, show)) <= {None}}
    folders = _subtree(library, scope)
    return {
        show.id
        for show in library.shows
        if any(folder in folders for folder in _placements(library, show) if folder)
    }
