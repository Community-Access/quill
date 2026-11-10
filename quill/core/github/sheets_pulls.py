"""The Pull Request sheet (GitHub PRD Appendix C): fourteen pages, every editable field.

Shares the issue sheet's You, Organize and Conversation pages and its viewer
query (:mod:`quill.core.github.sheets_items`), and adds Branches, Reviews,
Checks, Merge, Files and Commits. Labels, assignees and milestone are written
through the issues endpoint, as GitHub wants; draft and auto-merge through
GraphQL; reviewers through requested_reviewers, added and removed.

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quill.core.github.sheet_engine import Ident, Options, Read, SheetDef, Write
from quill.core.github.sheet_fields import (
    dig,
    ed,
    gql_toggle,
    logins,
    names,
    page,
    patch,
    ro,
    toggle,
)
from quill.core.github.sheets_items import (
    _CONVERSATION,
    _FIXED_REACTIONS,
    _ISSUE_PATH,
    _K,
    _O,
    _OPTIONS,
    _ORGANIZE,
    _REACTIONS_WRITE,
    _SUBSCRIBE_WRITE,
    _V,
    _YOU,
    VIEWER_ITEM_QUERY,
    _common,
    _milestone_encode,
    _viewer,
    item_variables,
)
from quill.core.workbench.properties import SheetSpec, Value

__all__ = ["PULL_REQUEST"]

# ---------------------------------------------------------------------------

_PULL_PATH = "/repos/{repo}/pulls/{number}"


def _pull(data: Mapping[str, Any]) -> dict[str, Value]:
    found = _common(data)
    found["state"] = "merged" if data.get("merged") else str(data.get("state") or "open")
    found.update({
        "draft": bool(data.get("draft")),
        "base": str(dig(data, "base", "ref") or ""),
        "head": str(dig(data, "head", "ref") or ""),
        "merged": bool(data.get("merged")),
        "mergeable": str(data.get("mergeable_state") or ""),
        "maintainer_can_modify": bool(data.get("maintainer_can_modify")),
        "reviewers": logins(data.get("requested_reviewers")),
        "team_reviewers": names(data.get("requested_teams"), "slug"),
        "commits": int(data.get("commits") or 0),
        "changed_files": int(data.get("changed_files") or 0),
        "additions": int(data.get("additions") or 0),
        "deletions": int(data.get("deletions") or 0),
        "review_comments": int(data.get("review_comments") or 0),
    })
    return found


def _auto_merge(value: Value, _choices: Mapping[str, object], ident: Ident) -> dict[str, object]:
    return {"id": ident.get("node_id", "")}


PULL_REQUEST = SheetDef(
    "pull_request",
    SheetSpec(
        "pull_request",
        "Pull Request",
        (
            page(
                "general",
                "General",
                ro("number", "Number", _K.NUMBER),
                ed("title", "Title"),
                ed(
                    "state",
                    "State",
                    _K.CHOICE,
                    "Open or closed. Merging is Item, Merge.",
                    choices=("open", "closed"),
                ),
                ed(
                    "draft",
                    "Draft",
                    _K.CHECK,
                    "A draft cannot be merged; clear it when it is ready for review.",
                ),
                ro("author", "Author"),
                ro("created", "Created", _K.DATE),
                ro("url", "Address", _K.LINK, "Ctrl+C copies it."),
            ),
            _YOU,
            _ORGANIZE,
            page("projects", "Projects", ro("projects", "Projects", _K.LIST)),
            page(
                "branches",
                "Branches",
                ro("head", "From branch"),
                ed(
                    "base",
                    "Into branch",
                    help="The branch it merges into. Changing it re-targets the pull request.",
                ),
                ed(
                    "maintainer_can_modify",
                    "Maintainers may edit",
                    _K.CHECK,
                    "Let people with write access to the base repository push to your branch.",
                ),
            ),
            page(
                "reviews",
                "Reviews",
                ed(
                    "reviewers",
                    "Reviewers",
                    _K.CHECKLIST,
                    "People asked to review it.",
                    create="Add Reviewer...",
                ),
                ed(
                    "team_reviewers",
                    "Team reviewers",
                    _K.CHECKLIST,
                    "Teams asked to review.",
                    create="Add Team...",
                ),
                ro("review_comments", "Review comments", _K.NUMBER),
            ),
            page(
                "checks",
                "Checks",
                ro(
                    "mergeable",
                    "Merge state",
                    help="GitHub's word for "
                    "whether it can merge: clean, blocked, behind, dirty, unstable.",
                ),
            ),
            page(
                "merge",
                "Merge",
                ro("merged", "Merged", _K.CHECK),
                ed(
                    "auto_merge",
                    "Merge automatically when ready",
                    _K.CHECK,
                    "Auto-merge: GitHub merges it once reviews and checks pass.",
                ),
            ),
            page(
                "files",
                "Files",
                ro("changed_files", "Files changed", _K.NUMBER),
                ro("additions", "Lines added", _K.NUMBER),
                ro("deletions", "Lines removed", _K.NUMBER),
            ),
            page("commits", "Commits", ro("commits", "Commits", _K.NUMBER)),
            page("relationships", "Relationships", ro("linked", "Issues it closes", _K.LIST)),
            page(
                "description",
                "Description",
                ed("body", "Description", _K.MULTILINE, "Markdown. Ctrl+Enter saves."),
            ),
            _CONVERSATION,
            page("timeline", "Timeline", ro("updated", "Last changed", _K.DATE)),
        ),
    ),
    (
        Read(_PULL_PATH, _pull),
        Read(graphql=VIEWER_ITEM_QUERY, variables=item_variables, extract=_viewer, optional=True),
    ),
    {
        "title": patch(_PULL_PATH, "viewer:viewerCanUpdate", _V),
        "body": patch(_PULL_PATH, "viewer:viewerCanUpdate", _V),
        "state": patch(_PULL_PATH, "viewer:viewerCanUpdate", _V),
        "base": patch(_PULL_PATH, "repo:write", _V),
        "maintainer_can_modify": patch(_PULL_PATH, "viewer:viewerCanUpdate", _O),
        "labels": patch(_ISSUE_PATH, "repo:triage+viewer:viewerCanLabel", _O),
        "assignees": patch(_ISSUE_PATH, "repo:triage+viewer:viewerCanAssign", _O),
        "milestone": patch(_ISSUE_PATH, "repo:triage", _O, encode=_milestone_encode),
        "draft": gql_toggle(
            "mutation($id:ID!){convertPullRequestToDraft(input:{pullRequestId:$id})"
            "{pullRequest{id}}}",
            "mutation($id:ID!){markPullRequestReadyForReview(input:{pullRequestId:$id})"
            "{pullRequest{id}}}",
            "viewer:viewerCanUpdate",
            _V,
        ),
        "reviewers": Write(
            _PULL_PATH + "/requested_reviewers", "repo:triage", _V, "POST", "set", "reviewers"
        ),
        "team_reviewers": Write(
            _PULL_PATH + "/requested_reviewers", "repo:triage", _V, "POST", "set", "team_reviewers"
        ),
        "auto_merge": Write(
            "mutation($id:ID!){enablePullRequestAutoMerge(input:{pullRequestId:$id})"
            "{pullRequest{id}}}",
            "viewer:viewerCanEnableAutoMerge",
            _V,
            "POST",
            "graphql",
            encode=_auto_merge,
            off_path="mutation($id:ID!){disablePullRequestAutoMerge(input:{pullRequestId:$id})"
            "{pullRequest{id}}}",
        ),
        "locked": toggle(_ISSUE_PATH + "/lock", "repo:write", _V),
        "subscribed": _SUBSCRIBE_WRITE,
        "reactions": _REACTIONS_WRITE,
    },
    {
        **_OPTIONS,
        "reviewers": Options("/repos/{repo}/collaborators", lambda r: str(r.get("login", ""))),
        "team_reviewers": Options("/repos/{repo}/teams", lambda r: str(r.get("slug", ""))),
    },
    title=lambda ident: f"Pull Request #{ident['number']}",
    url=lambda ident: f"https://github.com/{ident['repo']}/pull/{ident['number']}",
    fixed=_FIXED_REACTIONS,
)
