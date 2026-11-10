"""Properties sheets for GitHub issues and pull requests (GitHub PRD 15, Appendix C).

The Phase 1 spike's sheets are read-only and built from what the list
already loaded (a :class:`~quill.core.github.items_provider.GitHubItem`), so
opening one costs no request. Later phases add the editable fields, the
remaining pages from Appendix C, and the fresh load and conflict check that
section 15.3 asks for; the page and field keys here stay as they are.
"""

from __future__ import annotations

from quill.core.github.items_provider import GitHubItem
from quill.core.workbench.properties import FieldKind, FieldSpec, PageSpec, SheetSpec, Value

__all__ = ["ISSUE_SHEET", "PULL_REQUEST_SHEET", "sheet_for", "sheet_title", "values_for"]

_RO = True


def _f(key: str, label: str, kind: FieldKind = FieldKind.TEXT, help: str = "") -> FieldSpec:  # noqa: A002
    return FieldSpec(key, label, kind, readonly=_RO, help=help)


_GENERAL = (
    _f("number", "Number", FieldKind.NUMBER),
    _f("title", "Title", help="The title as GitHub shows it."),
    _f("state", "State", help="Open, closed, or for a pull request, merged."),
    _f("author", "Author"),
    _f("created", "Created", FieldKind.DATE),
    _f("updated", "Updated", FieldKind.DATE),
    _f("comments", "Comments", FieldKind.NUMBER),
    _f("url", "Address", FieldKind.LINK, help="Ctrl+C copies it."),
)
_ORGANIZE = PageSpec(
    "organize",
    "Organize",
    (
        _f("labels", "Labels", FieldKind.LIST, "Changing labels needs triage access."),
        _f("assignees", "Assignees", FieldKind.LIST, "Changing assignees needs triage access."),
    ),
)
_DESCRIPTION = PageSpec(
    "description", "Description", (_f("body", "Description", FieldKind.MULTILINE),)
)

ISSUE_SHEET = SheetSpec(
    "issue", "Issue", (PageSpec("general", "General", _GENERAL), _ORGANIZE, _DESCRIPTION)
)
PULL_REQUEST_SHEET = SheetSpec(
    "pull_request",
    "Pull Request",
    (
        PageSpec(
            "general",
            "General",
            (*_GENERAL, _f("draft", "Draft", FieldKind.CHECK), _f("review", "Review decision")),
        ),
        _ORGANIZE,
        PageSpec(
            "branches",
            "Branches",
            (
                _f("head", "From branch"),
                _f("base", "Into branch"),
                _f("merged", "Merged", FieldKind.CHECK),
            ),
        ),
        PageSpec(
            "files",
            "Files",
            (
                _f("changed_files", "Files changed", FieldKind.NUMBER),
                _f("additions", "Lines added", FieldKind.NUMBER),
                _f("deletions", "Lines removed", FieldKind.NUMBER),
            ),
        ),
        _DESCRIPTION,
    ),
)


def sheet_for(item: GitHubItem) -> SheetSpec:
    return PULL_REQUEST_SHEET if item.is_pr else ISSUE_SHEET


def sheet_title(item: GitHubItem, repository: str) -> str:
    """ "Issue #42 Properties - owner/name", the sheet's window title."""
    kind = "Pull Request" if item.is_pr else "Issue"
    return sheet_for(item).heading(f"{kind} #{item.number}", repository)


def values_for(item: GitHubItem) -> dict[str, Value]:
    """The sheet's values, from the row the list already holds."""
    values: dict[str, Value] = {
        "number": item.number,
        "title": item.title,
        "state": item.state_display.capitalize(),
        "author": item.author,
        "created": item.created_at,
        "updated": item.updated_at,
        "comments": item.comments,
        "url": item.url,
        "labels": item.labels,
        "assignees": item.assignees,
        "body": item.body,
    }
    if item.is_pr:
        values.update({
            "draft": item.is_draft,
            "review": item.review_status,
            "head": item.head_branch,
            "base": item.base_branch,
            "merged": item.is_merged,
            "changed_files": item.changed_files,
            "additions": item.additions,
            "deletions": item.deletions,
        })
    return values
