"""F1's words about the selected row of Quill Studio's Your Books tree (FUX-10).

The tree's name says "Enter opens the selected book in the Chapter Workbench",
which is true of a book and not of the group rows (Favorites, In Progress,
Recently Played, Inbox and your folders), where Enter opens nothing. A book
whose file has moved is listed as if it were still there. F1 now says both.

wx-free; :mod:`quill.apps.studio_library_window` reads the tree.
"""

from __future__ import annotations

__all__ = ["GROUP_ROW", "enter_on", "missing_book", "row_situation"]

#: The group rows: a view (Favorites, In Progress...) or one of your folders.
GROUP_ROW = (
    "This row is a group, not a book, so Enter opens nothing. Down Arrow reaches "
    "the books in it, if it has any. Here the context menu offers only New Folder."
)


def enter_on(kind: str) -> str:
    """What Enter says when the selected row is not a book: a group, or nothing."""
    if kind in ("view", "folder"):
        return "This is a group; arrow down to a book."
    return "No book selected. Narrate documents or build from recordings first."


def missing_book(title: str) -> str:
    """The one sentence for a book whose file is gone, wherever it is said."""
    return f"{title} is no longer where it was; it may have been moved or renamed."


def row_situation(kind: str, *, title: str = "", exists: bool = True) -> str:
    """The selected row's paragraph, or "" for a book that is where it was.

    *kind* is the tree's tag ("view", "folder" or "book").
    """
    if kind in ("view", "folder"):
        return GROUP_ROW
    if kind == "book" and not exists:
        return (
            f"{missing_book(title)} Enter only warns that it is gone. Delete, or Remove "
            "from Library on the context menu, asks and then takes it out of the "
            "library; no file is deleted."
        )
    return ""
