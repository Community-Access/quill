"""Properties sheets for issues, pull requests, labels and milestones (GitHub PRD Appendix C).

Phase 7's first sheets, in full: every page Appendix C lists, every field a
labelled control, each editable field with the write that saves it and the
requirement and tier GATE-GITHUB-PERM holds it to. Values come from the REST
object and, for issues and pull requests, one GraphQL query for the viewer
fields of Appendix F.1 (``viewerCanUpdate``, ``viewerCanLabel`` and their
kin), the repository role, your reactions and subscription, and the node id
GraphQL mutations need.

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quill.core.github.permissions import WriteTier, repo_role
from quill.core.github.sheet_engine import Ident, Options, Read, SheetDef, Write
from quill.core.github.sheet_fields import (
    REACTIONS,
    dig,
    ed,
    gql_toggle,
    logins,
    names,
    page,
    patch,
    ro,
    toggle,
    when,
)
from quill.core.workbench.properties import FieldKind, SheetSpec, Value

__all__ = [
    "ISSUE",
    "ISSUE_STATES",
    "VIEWER_ITEM_QUERY",
    "item_variables",
]

_O, _V, _A = WriteTier.ORGANIZING, WriteTier.VISIBLE, WriteTier.ACCESS
_K = FieldKind

ISSUE_STATES: tuple[str, ...] = (
    "open",
    "closed as completed",
    "closed as not planned",
    "closed as duplicate",
)
_STATE_REASON = {
    "closed as completed": "completed",
    "closed as not planned": "not_planned",
    "closed as duplicate": "duplicate",
}

#: The viewer fields of Appendix F.1 for an issue or pull request, with the
#: repository role, your reactions, subscription and pin, and the node id.
VIEWER_ITEM_QUERY = (
    "query($owner:String!,$name:String!,$number:Int!){repository(owner:$owner,name:$name){"
    "viewerPermission issueOrPullRequest(number:$number){__typename "
    "... on Issue{id isPinned viewerCanUpdate viewerCanClose viewerCanReopen viewerCanLabel "
    "viewerCanAssign viewerCanSetMilestone viewerCanSubscribe viewerSubscription viewerCanReact "
    "viewerCanDelete viewerCanType reactionGroups{content viewerHasReacted} "
    "projectItems(first:20){nodes{project{title}}} "
    "parent{number title} subIssues(first:50){nodes{number title}} "
    "closedByPullRequestsReferences(first:10){nodes{number title}}} "
    "... on PullRequest{id viewerCanUpdate viewerCanClose viewerCanReopen viewerCanLabel "
    "viewerCanAssign viewerCanSubscribe viewerSubscription viewerCanReact "
    "viewerCanEnableAutoMerge viewerCanDisableAutoMerge viewerCanUpdateBranch "
    "viewerCanDeleteHeadRef viewerCanMergeAsAdmin autoMergeRequest{mergeMethod} "
    "reactionGroups{content viewerHasReacted} projectItems(first:20){nodes{project{title}}} "
    "closingIssuesReferences(first:10){nodes{number title}}}}}}"
)

_REACTION_ENUM = {
    "+1": "THUMBS_UP",
    "-1": "THUMBS_DOWN",
    "laugh": "LAUGH",
    "hooray": "HOORAY",
    "confused": "CONFUSED",
    "heart": "HEART",
    "rocket": "ROCKET",
    "eyes": "EYES",
}
_REACTION_WORDS = {_REACTION_ENUM[api]: word for api, word in REACTIONS}
_REACTION_CHOICES = tuple(word for _api, word in REACTIONS)


def item_variables(ident: Ident) -> dict[str, object]:
    owner, _, name = ident["repo"].partition("/")
    return {"owner": owner, "name": name, "number": int(ident["number"])}


def _numbers(rows: object) -> tuple[str, ...]:
    nodes = rows if isinstance(rows, list) else []
    return tuple(
        f"#{node.get('number')} {node.get('title', '')}".strip()
        for node in nodes
        if isinstance(node, Mapping)
    )


def _viewer(data: Mapping[str, Any]) -> dict[str, Value]:
    repo = dig(data, "repository") or {}
    item = dig(repo, "issueOrPullRequest") or {}
    found: dict[str, Value] = {
        key: bool(value) for key, value in item.items() if key.startswith("viewerCan")
    }
    found["your_access"] = repo_role(repo.get("viewerPermission"))
    found["node_id"] = str(item.get("id", ""))
    found["subscribed"] = item.get("viewerSubscription") == "SUBSCRIBED"
    found["pinned"] = bool(item.get("isPinned"))
    found["reactions"] = tuple(
        _REACTION_WORDS.get(str(group.get("content")), str(group.get("content")).lower())
        for group in item.get("reactionGroups") or ()
        if isinstance(group, Mapping) and group.get("viewerHasReacted")
    )
    found["projects"] = tuple(
        str(dig(node, "project", "title") or "")
        for node in dig(item, "projectItems", "nodes") or ()
    )
    parent = _numbers([item["parent"]] if item.get("parent") else [])
    found["parent"] = parent[0] if parent else ""
    found["sub_issues"] = _numbers(dig(item, "subIssues", "nodes"))
    linked = dig(item, "closedByPullRequestsReferences", "nodes") or dig(
        item, "closingIssuesReferences", "nodes"
    )
    found["linked"] = _numbers(linked)
    found["auto_merge"] = bool(item.get("autoMergeRequest"))
    return found


def _state_word(data: Mapping[str, Any]) -> str:
    if data.get("state") != "closed":
        return "open"
    reason = data.get("state_reason") or "completed"
    return {"not_planned": "closed as not planned", "duplicate": "closed as duplicate"}.get(
        str(reason), "closed as completed"
    )


def _common(data: Mapping[str, Any]) -> dict[str, Value]:
    return {
        "number": int(data.get("number") or 0),
        "title": str(data.get("title") or ""),
        "body": str(data.get("body") or ""),
        "author": str(dig(data, "user", "login") or ""),
        "created": when(data.get("created_at")),
        "updated": str(data.get("updated_at") or ""),
        "closed": when(data.get("closed_at")),
        "comments": int(data.get("comments") or 0),
        "url": str(data.get("html_url") or ""),
        "labels": names(data.get("labels")),
        "assignees": logins(data.get("assignees")),
        "milestone": str(dig(data, "milestone", "title") or ""),
        "locked": bool(data.get("locked")),
        "lock_reason": str(data.get("active_lock_reason") or ""),
    }


def _issue(data: Mapping[str, Any]) -> dict[str, Value]:
    found = _common(data)
    found["state"] = _state_word(data)
    found["issue_type"] = str(dig(data, "type", "name") or "")
    return found


def _state_encode(value: Value, _choices: Mapping[str, object], _ident: Ident) -> dict[str, object]:
    word = str(value or "open")
    if word == "open":
        return {"state": "open"}
    return {"state": "closed", "state_reason": _STATE_REASON.get(word, "completed")}


def _milestone_encode(
    value: Value, choices: Mapping[str, object], _ident: Ident
) -> dict[str, object]:
    return {"milestone": choices.get(str(value)) if value else None}


def _subscription(value: Value, _choices: Mapping[str, object], ident: Ident) -> dict[str, object]:
    return {"id": ident.get("node_id", ""), "state": "SUBSCRIBED" if value else "UNSUBSCRIBED"}


_SUBSCRIBE_MUTATION = (
    "mutation($id:ID!,$state:SubscriptionState!){updateSubscription(input:"
    "{subscribableId:$id,state:$state}){subscribable{id}}}"
)
_ADD_REACTION = (
    "mutation($id:ID!,$content:ReactionContent!){addReaction(input:"
    "{subjectId:$id,content:$content}){reaction{content}}}"
)
_REMOVE_REACTION = (
    "mutation($id:ID!,$content:ReactionContent!){removeReaction(input:"
    "{subjectId:$id,content:$content}){reaction{content}}}"
)
_REACTIONS_WRITE = Write(
    _ADD_REACTION, "viewer:viewerCanReact", _O, "POST", "set_graphql", off_path=_REMOVE_REACTION
)
_SUBSCRIBE_WRITE = Write(
    _SUBSCRIBE_MUTATION,
    "viewer:viewerCanSubscribe",
    _O,
    "POST",
    "graphql",
    encode=_subscription,
)
_FIXED_REACTIONS = {
    "reactions": {word: _REACTION_ENUM[api] for api, word in REACTIONS},
}

_ISSUE_PATH = "/repos/{repo}/issues/{number}"
_OPTIONS = {
    "labels": Options("/repos/{repo}/labels", lambda row: str(row.get("name", ""))),
    "assignees": Options("/repos/{repo}/assignees", lambda row: str(row.get("login", ""))),
    "milestone": Options(
        "/repos/{repo}/milestones",
        lambda row: str(row.get("title", "")),
        lambda row: row.get("number"),
        query={"state": "all"},
    ),
}

_YOU = page(
    "you",
    "You",
    ed(
        "subscribed",
        "Subscribed",
        _K.CHECK,
        "Get notified of all activity on it, or only when you are mentioned or participating.",
    ),
    ed(
        "reactions",
        "Your reactions",
        _K.CHECKLIST,
        "Your reactions, each a check box.",
        choices=_REACTION_CHOICES,
    ),
)
_ORGANIZE = page(
    "organize",
    "Organize",
    ed(
        "labels",
        "Labels",
        _K.CHECKLIST,
        "Each label, checked when it is on.",
        create="New Label...",
    ),
    ed("assignees", "Assignees", _K.CHECKLIST, "Who it is assigned to; up to ten people."),
    ed(
        "milestone",
        "Milestone",
        _K.CHOICE,
        "The milestone it belongs to, or none.",
        create="New Milestone...",
    ),
)
_RELATIONSHIPS = page(
    "relationships",
    "Relationships",
    ro("parent", "Parent issue", help="The issue this one is a sub-issue of."),
    ro("sub_issues", "Sub-issues", _K.LIST, "Its sub-issues, in order."),
    ro("linked", "Linked pull requests", _K.LIST, "Pull requests that close it when merged."),
)
_CONVERSATION = page(
    "conversation",
    "Conversation",
    ed(
        "locked",
        "Locked",
        _K.CHECK,
        "A locked conversation takes comments only from people with write access.",
    ),
    ro("lock_reason", "Lock reason"),
    ro("comments", "Comments", _K.NUMBER),
)
_ISSUE_CONVERSATION = page(
    "conversation",
    "Conversation",
    *_CONVERSATION.fields,
    ed(
        "pinned",
        "Pinned to the repository",
        _K.CHECK,
        "A pinned issue shows at the top of the repository's Issues; up to three.",
    ),
)
_ACCESS = page(
    "access",
    "Access",
    ro(
        "your_access",
        "Your access",
        help="Your role on the repository, as GitHub reports it. "
        "Labels, assignees and milestones need triage; locking needs write.",
    ),
)

ISSUE = SheetDef(
    "issue",
    SheetSpec(
        "issue",
        "Issue",
        (
            page(
                "general",
                "General",
                ro("number", "Number", _K.NUMBER),
                ed("title", "Title", help="The title. Ctrl+S saves and keeps the sheet open."),
                ed("state", "State", _K.CHOICE, "Open, or closed and why.", choices=ISSUE_STATES),
                ed(
                    "issue_type",
                    "Issue type",
                    help="The organization's issue type, such as Bug or Feature. Empty for none.",
                ),
                ro("author", "Author"),
                ro("created", "Created", _K.DATE),
                ro("closed", "Closed", _K.DATE),
                ro("url", "Address", _K.LINK, "Ctrl+C copies it."),
            ),
            _YOU,
            _ORGANIZE,
            page(
                "projects",
                "Projects",
                ro(
                    "projects",
                    "Projects",
                    _K.LIST,
                    "The Projects it is in. A project item's own sheet edits its fields.",
                ),
            ),
            _RELATIONSHIPS,
            page(
                "description",
                "Description",
                ed("body", "Description", _K.MULTILINE, "Markdown. Ctrl+Enter saves."),
            ),
            _ISSUE_CONVERSATION,
            page(
                "timeline",
                "Timeline",
                ro(
                    "updated",
                    "Last changed",
                    _K.DATE,
                    "View Timeline on the context menu lists everything that happened to it.",
                ),
            ),
            _ACCESS,
        ),
    ),
    (
        Read(_ISSUE_PATH, _issue),
        Read(graphql=VIEWER_ITEM_QUERY, variables=item_variables, extract=_viewer, optional=True),
    ),
    {
        "title": patch(_ISSUE_PATH, "viewer:viewerCanUpdate", _V),
        "body": patch(_ISSUE_PATH, "viewer:viewerCanUpdate", _V),
        "state": patch(_ISSUE_PATH, "viewer:viewerCanUpdate", _V, encode=_state_encode),
        "issue_type": patch(_ISSUE_PATH, "repo:triage", _O, "type"),
        "labels": patch(_ISSUE_PATH, "repo:triage+viewer:viewerCanLabel", _O),
        "assignees": patch(_ISSUE_PATH, "repo:triage+viewer:viewerCanAssign", _O),
        "milestone": patch(_ISSUE_PATH, "repo:triage", _O, encode=_milestone_encode),
        "locked": toggle(_ISSUE_PATH + "/lock", "repo:write", _V),
        "pinned": gql_toggle(
            "mutation($id:ID!){pinIssue(input:{issueId:$id}){issue{id}}}",
            "mutation($id:ID!){unpinIssue(input:{issueId:$id}){issue{id}}}",
            "repo:triage",
            _V,
        ),
        "subscribed": _SUBSCRIBE_WRITE,
        "reactions": _REACTIONS_WRITE,
    },
    _OPTIONS,
    title=lambda ident: f"Issue #{ident['number']}",
    url=lambda ident: f"https://github.com/{ident['repo']}/issues/{ident['number']}",
    fixed=_FIXED_REACTIONS,
)
