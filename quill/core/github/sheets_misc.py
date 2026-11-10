"""The rest of Appendix C: gists, Codespaces, notifications, webhooks and deploy keys.

Security alerts are in :mod:`quill.core.github.sheets_security`; discussions,
comments and issue types in :mod:`quill.core.github.sheets_talk`.

Each sheet is the object's facts as read-only text boxes and every field
GitHub's API can change as a control: a gist's description and star; a
Codespace's display name; an alert's state with GitHub's own reasons; a
notification's subscription; a discussion's title and body; a comment's body;
an issue type's name, description, colour and whether it is on; a webhook's
address, events, content type and whether it is active. A deploy key cannot
be changed, only removed, and its sheet says so.

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
    toggle,
    when,
)
from quill.core.workbench.properties import FieldKind, SheetSpec, Value

__all__ = [
    "CODESPACE",
    "DEPLOY_KEY",
    "GIST",
    "NOTIFICATION",
    "WEBHOOK",
]

_O, _V, _A, _D = (
    WriteTier.ORGANIZING,
    WriteTier.VISIBLE,
    WriteTier.ACCESS,
    WriteTier.DESTRUCTIVE,
)
_K = FieldKind


def _gist(data: Mapping[str, Any]) -> dict[str, Value]:
    files = data.get("files") if isinstance(data.get("files"), Mapping) else {}
    return {
        "description": str(data.get("description") or ""),
        "public": bool(data.get("public")),
        "owner": str(dig(data, "owner", "login") or ""),
        "files": tuple(str(name) for name in files or {}),
        "comments": int(data.get("comments") or 0),
        "created": when(data.get("created_at")),
        "updated": str(data.get("updated_at") or ""),
        "url": str(data.get("html_url") or ""),
    }


GIST = SheetDef(
    "gist",
    SheetSpec(
        "gist",
        "Gist",
        (
            page(
                "general",
                "General",
                ed("description", "Description"),
                ro(
                    "public",
                    "Public",
                    _K.CHECK,
                    "A secret gist can be made public on "
                    "GitHub; GitHub cannot make a public gist secret again.",
                ),
                ro("owner", "Owner"),
                ro("created", "Created", _K.DATE),
                ro("url", "Address", _K.LINK),
            ),
            page("you", "You", ed("starred", "Starred", _K.CHECK)),
            page("files", "Files", ro("files", "Files", _K.TABLE, "Edit Gist changes them.")),
            page("comments", "Comments", ro("comments", "Comments", _K.NUMBER)),
        ),
    ),
    (
        Read("/gists/{id}", _gist),
        Read(
            "/gists/{id}/star",
            lambda _d: {"starred": True},
            optional=True,
            fallback={"starred": False},
        ),
    ),
    {
        "description": patch("/gists/{id}", "sign_in+scope:gist", _V),
        "starred": toggle("/gists/{id}/star", "sign_in+scope:gist", _O),
    },
    title=lambda ident: f"Gist {ident['id'][:7]}",
    url=lambda ident: f"https://gist.github.com/{ident['id']}",
)


def _codespace(data: Mapping[str, Any]) -> dict[str, Value]:
    return {
        "display_name": str(data.get("display_name") or ""),
        "name": str(data.get("name") or ""),
        "state": str(data.get("state") or ""),
        "repository": str(dig(data, "repository", "full_name") or ""),
        "branch": str(dig(data, "git_status", "ref") or ""),
        "machine": str(dig(data, "machine", "display_name") or ""),
        "idle_timeout": f"{int(data.get('idle_timeout_minutes') or 0)} minutes",
        "retention": f"{int(data.get('retention_period_minutes') or 0)} minutes",
        "last_used": when(data.get("last_used_at")),
        "url": str(data.get("web_url") or ""),
    }


CODESPACE = SheetDef(
    "codespace",
    SheetSpec(
        "codespace",
        "Codespace",
        (
            page(
                "general",
                "General",
                ed("display_name", "Display name"),
                ro("name", "Name"),
                ro("state", "State"),
                ro("repository", "Repository"),
                ro("branch", "Branch"),
                ro("last_used", "Last used", _K.DATE),
                ro("url", "Address", _K.LINK),
            ),
            page(
                "machine",
                "Machine",
                ro(
                    "machine",
                    "Machine type",
                    help="Changing the machine type can cost more; GitHub's page does it.",
                ),
            ),
            page(
                "usage",
                "Usage",
                ro("idle_timeout", "Stops after idle"),
                ro("retention", "Deleted after stopped"),
            ),
        ),
    ),
    (Read("/user/codespaces/{name}", _codespace),),
    {"display_name": patch("/user/codespaces/{name}", "sign_in+scope:codespace", _O)},
    title=lambda ident: f"Codespace {ident['name']}",
)


def _notification(data: Mapping[str, Any]) -> dict[str, Value]:
    return {
        "reason": str(data.get("reason") or "").replace("_", " "),
        "repository": str(dig(data, "repository", "full_name") or ""),
        "subject": str(dig(data, "subject", "title") or ""),
        "kind": str(dig(data, "subject", "type") or ""),
        "unread": bool(data.get("unread")),
        "updated": when(data.get("updated_at")),
    }


NOTIFICATION = SheetDef(
    "notification",
    SheetSpec(
        "notification",
        "Notification",
        (
            page(
                "general",
                "General",
                ro("subject", "About"),
                ro("kind", "Kind"),
                ro("repository", "Repository"),
                ro("reason", "Why you got it"),
                ro("unread", "Unread", _K.CHECK),
                ro("updated", "Last update", _K.DATE),
            ),
            page(
                "you",
                "You",
                ed(
                    "subscribed",
                    "Subscribed to this thread",
                    _K.CHECK,
                    "Clear it to stop notifications from this thread; Mark "
                    "Read, Mark Done and Snooze are on the context menu.",
                ),
            ),
        ),
    ),
    (
        Read("/notifications/threads/{id}", _notification),
        Read(
            "/notifications/threads/{id}/subscription",
            lambda d: {"subscribed": bool(d.get("subscribed")) and not d.get("ignored")},
            optional=True,
            fallback={"subscribed": False},
        ),
    ),
    {"subscribed": toggle("/notifications/threads/{id}/subscription", "sign_in", _O)},
    title=lambda ident: f"Notification {ident['id']}",
)


def _hook(data: Mapping[str, Any]) -> dict[str, Value]:
    return {
        "address": str(dig(data, "config", "url") or ""),
        "content_type": str(dig(data, "config", "content_type") or "form"),
        "events": tuple(str(e) for e in lst(data, "events")),
        "active": bool(data.get("active")),
        "updated": when(data.get("updated_at")),
        "last_response": str(dig(data, "last_response", "message") or ""),
        "raw_json": json.dumps(dict(data)),
    }


def _compose_hook(
    ident: Ident, edits: Mapping[str, Value]
) -> list[tuple[str, str, dict[str, object]]]:
    raw = json.loads(ident.get("raw_json") or "{}")
    config = dict(raw.get("config") or {})
    config.pop("secret", None)
    if "address" in edits:
        config["url"] = str(edits["address"])
    if "content_type" in edits:
        config["content_type"] = str(edits["content_type"])
    body: dict[str, object] = {"config": config}
    if "active" in edits:
        body["active"] = bool(edits["active"])
    if "events" in edits and isinstance(edits["events"], tuple):
        body["events"] = list(edits["events"])
    return [("PATCH", f"/repos/{ident['repo']}/hooks/{ident['id']}", body)]


WEBHOOK = SheetDef(
    "webhook",
    SheetSpec(
        "webhook",
        "Webhook",
        (
            page(
                "general",
                "General",
                ed("address", "Payload address"),
                ed("content_type", "Content type", _K.CHOICE, choices=("json", "form")),
                ed(
                    "events",
                    "Events",
                    _K.LIST,
                    "GitHub's event names, comma-separated, such as push, "
                    "pull_request, issues; * for every event.",
                ),
                ed("active", "Active", _K.CHECK),
                ro("last_response", "Last delivery"),
                ro("updated", "Updated", _K.DATE),
            ),
        ),
    ),
    (Read("/repos/{repo}/hooks/{id}", _hook),),
    {
        key: Write(
            "/repos/{repo}/hooks/{id}", "repo:admin+scope:admin:repo_hook", _A, "PATCH", "patch"
        )
        for key in ("address", "content_type", "events", "active")
    },
    title=lambda ident: f"Webhook {ident['id']}",
    compose=_compose_hook,
    adopt=("raw_json",),
)


def _key(data: Mapping[str, Any]) -> dict[str, Value]:
    return {
        "title": str(data.get("title") or ""),
        "access": "read-only" if data.get("read_only") else "read and write",
        "verified": bool(data.get("verified")),
        "created": when(data.get("created_at")),
        "last_used": when(data.get("last_used")),
    }


DEPLOY_KEY = SheetDef(
    "deploy_key",
    SheetSpec(
        "deploy_key",
        "Deploy Key",
        (
            page(
                "general",
                "General",
                ro("title", "Title"),
                ro(
                    "access",
                    "Access",
                    help="GitHub cannot "
                    "change a deploy key; remove it and add "
                    "it again with the access you want.",
                ),
                ro("verified", "Verified", _K.CHECK),
                ro("created", "Added", _K.DATE),
                ro("last_used", "Last used", _K.DATE),
            ),
        ),
    ),
    (Read("/repos/{repo}/keys/{id}", _key),),
    title=lambda ident: f"Deploy Key {ident['id']}",
)
