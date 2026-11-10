"""Sheets for discussions, comments and issue types (GitHub PRD Appendix C).

A discussion's title and body (GraphQL updateDiscussion), a comment's body,
and an organization's issue type (name, description, colour, enabled; saved
whole, as GitHub wants).

wx-free and strict-typed.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from quill.core.github.permissions import WriteTier
from quill.core.github.sheet_engine import Ident, Read, SheetDef, Write
from quill.core.github.sheet_fields import (
    dig,
    ed,
    lst,
    page,
    patch,
    ro,
    when,
)
from quill.core.workbench.properties import FieldKind, SheetSpec, Value

__all__ = ["COMMENT", "DISCUSSION", "ISSUE_TYPE"]

_O, _V, _A, _D = (
    WriteTier.ORGANIZING,
    WriteTier.VISIBLE,
    WriteTier.ACCESS,
    WriteTier.DESTRUCTIVE,
)
_K = FieldKind


_DISCUSSION_QUERY = (
    "query($owner:String!,$name:String!,$number:Int!){repository(owner:$owner,name:$name){"
    "discussion(number:$number){id title body locked upvoteCount createdAt url "
    "category{name} author{login} answer{author{login}} comments{totalCount} "
    "viewerCanUpdate viewerCanReact viewerCanSubscribe viewerSubscription}}}"
)


def _discussion(data: Mapping[str, Any]) -> dict[str, Value]:
    found = dig(data, "repository", "discussion") or {}
    return {
        "node_id": str(found.get("id") or ""),
        "title": str(found.get("title") or ""),
        "body": str(found.get("body") or ""),
        "category": str(dig(found, "category", "name") or ""),
        "author": str(dig(found, "author", "login") or ""),
        "answered_by": str(dig(found, "answer", "author", "login") or ""),
        "upvotes": int(found.get("upvoteCount") or 0),
        "comments": int(dig(found, "comments", "totalCount") or 0),
        "locked": bool(found.get("locked")),
        "subscribed": found.get("viewerSubscription") == "SUBSCRIBED",
        "created": when(found.get("createdAt")),
        "url": str(found.get("url") or ""),
        **{k: bool(v) for k, v in found.items() if str(k).startswith("viewerCan")},
    }


def _update_discussion(key: str) -> Write:
    mutation = (
        f"mutation($id:ID!,${key}:String!){{updateDiscussion(input:{{discussionId:$id,"
        f"{key}:${key}}}){{discussion{{id}}}}}}"
    )
    return Write(
        mutation,
        "viewer:viewerCanUpdate",
        _V,
        "POST",
        "graphql",
        encode=lambda v, _c, i: {"id": i.get("node_id", ""), key: str(v or "")},
    )


DISCUSSION = SheetDef(
    "discussion",
    SheetSpec(
        "discussion",
        "Discussion",
        (
            page(
                "general",
                "General",
                ed("title", "Title"),
                ro("author", "Author"),
                ro("created", "Started", _K.DATE),
                ro("url", "Address", _K.LINK),
            ),
            page(
                "you",
                "You",
                ro("subscribed", "Subscribed", _K.CHECK),
                ro("upvotes", "Upvotes", _K.NUMBER),
            ),
            page(
                "category",
                "Category",
                ro(
                    "category",
                    "Category",
                    help="Categories are managed on GitHub's page; it has no API yet.",
                ),
            ),
            page("answer", "Answer", ro("answered_by", "Answered by")),
            page(
                "conversation",
                "Conversation",
                ed("body", "Body", _K.MULTILINE),
                ro("comments", "Comments", _K.NUMBER),
                ro("locked", "Locked", _K.CHECK),
            ),
            page("poll", "Poll", ro("poll_note", "Poll", help="Open the thread to vote.")),
        ),
    ),
    (
        Read(
            graphql=_DISCUSSION_QUERY,
            variables=lambda i: {
                "owner": i["repo"].partition("/")[0],
                "name": i["repo"].partition("/")[2],
                "number": int(i["number"]),
            },
            extract=_discussion,
        ),
    ),
    {"title": _update_discussion("title"), "body": _update_discussion("body")},
    title=lambda ident: f"Discussion #{ident['number']}",
    url=lambda ident: f"https://github.com/{ident['repo']}/discussions/{ident['number']}",
)


def _comment(data: Mapping[str, Any]) -> dict[str, Value]:
    return {
        "author": str(dig(data, "user", "login") or ""),
        "body": str(data.get("body") or ""),
        "created": when(data.get("created_at")),
        "updated": str(data.get("updated_at") or ""),
        "url": str(data.get("html_url") or ""),
    }


COMMENT = SheetDef(
    "comment",
    SheetSpec(
        "comment",
        "Comment",
        (
            page(
                "general",
                "General",
                ed("body", "Comment", _K.MULTILINE, "Yours, or anyone's with permission."),
                ro("author", "Author"),
                ro("created", "Written", _K.DATE),
                ro("url", "Address", _K.LINK),
            ),
            page("history", "History", ro("updated", "Last edited", _K.DATE)),
        ),
    ),
    (Read("/repos/{repo}/issues/comments/{id}", _comment),),
    {"body": patch("/repos/{repo}/issues/comments/{id}", "sign_in", _V)},
    title=lambda ident: f"Comment {ident['id']}",
)


def _issue_type(data: Mapping[str, Any], ident: Ident) -> dict[str, Value]:
    for row in lst(data, "items"):
        if isinstance(row, Mapping) and str(row.get("id")) == ident.get("id"):
            return {
                "name": str(row.get("name") or ""),
                "description": str(row.get("description") or ""),
                "colour": str(row.get("color") or ""),
                "enabled": bool(row.get("is_enabled")),
                "raw_json": json.dumps(dict(row)),
            }
    return {}


def _compose_type(
    ident: Ident, edits: Mapping[str, Value]
) -> list[tuple[str, str, dict[str, object]]]:
    raw = json.loads(ident.get("raw_json") or "{}")
    body = {
        "name": str(edits.get("name", raw.get("name", ""))),
        "description": str(edits.get("description", raw.get("description") or "")),
        "color": str(edits.get("colour", raw.get("color") or "gray")),
        "is_enabled": bool(edits.get("enabled", raw.get("is_enabled", True))),
    }
    return [("PUT", f"/orgs/{ident['org']}/issue-types/{ident['id']}", body)]


ISSUE_TYPE = SheetDef(
    "issue_type",
    SheetSpec(
        "issue_type",
        "Issue Type",
        (
            page(
                "general",
                "General",
                ed("name", "Name"),
                ed("description", "Description"),
                ed(
                    "colour",
                    "Colour",
                    help="GitHub's colour names: gray, blue, green, yellow, orange, "
                    "red, pink or purple.",
                ),
                ed("enabled", "Enabled", _K.CHECK),
            ),
        ),
    ),
    (Read("/orgs/{org}/issue-types", pick=_issue_type),),
    {
        key: Write("/orgs/{org}/issue-types/{id}", "org:owner", _A, "PUT", "put")
        for key in ("name", "description", "colour", "enabled")
    },
    title=lambda ident: f"Issue Type {ident.get('name') or ident['id']}",
    compose=_compose_type,
    adopt=("raw_json",),
)
