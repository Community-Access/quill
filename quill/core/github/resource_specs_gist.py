"""One gist's comments, history and forks, for the resource engine.

Not tree nodes: a gist's row reaches them (Comments..., History..., Forks...),
with the gist's id as the target, the way an environment's row reaches its
secrets. Forking a gist is its own command (``fork_gist``). wx-free and
strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quill.core.github.resource_engine import Field, ResourceError, ResourceSpec
from quill.core.github.rest_transport import GitHubRestError
from quill.core.github.sheet_fields import dig

__all__ = ["GIST_SPECS", "fork_gist", "gist_spec"]

_PAGE = "https://gist.github.com/{target}"


def _when(raw: Mapping[str, Any], key: str) -> str:
    return str(raw.get(key) or "")[:10]


def _comment(raw: Mapping[str, Any]) -> str:
    text = " ".join(str(raw.get("body") or "").split())[:160]
    return f"{dig(raw, 'user', 'login') or 'Someone'}, {_when(raw, 'created_at')}: {text}"


def _version(raw: Mapping[str, Any]) -> str:
    status = raw.get("change_status") or {}
    added, deleted = int(status.get("additions") or 0), int(status.get("deletions") or 0)
    who = dig(raw, "user", "login") or "someone"
    return (
        f"{_when(raw, 'committed_at')} by {who}: {added} lines added, {deleted} removed "
        f"(version {str(raw.get('version') or '')[:7]})."
    )


def _fork(raw: Mapping[str, Any]) -> str:
    who = dig(raw, "owner", "login") or dig(raw, "user", "login") or "Someone"
    return f"{who}, {_when(raw, 'created_at')}."


GIST_SPECS: tuple[ResourceSpec, ...] = (
    ResourceSpec(
        key="gist_comments",
        label="Gist Comments",
        scope="gist",
        parent="",
        noun="comment",
        list_path="{base}/comments",
        id_field="id",
        id_param="{comment_id}",
        sentence=_comment,
        help="The gist's comments, oldest first. Add one, or change or delete your own.",
        page=_PAGE,
        create=(Field("body", "Your comment:", "multiline"),),
        edit=(Field("body", "The comment:", "multiline"),),
    ),
    ResourceSpec(
        key="gist_history",
        label="Gist History",
        scope="gist",
        parent="",
        noun="version",
        list_path="{base}/commits",
        id_field="version",
        sentence=_version,
        help="Every saved version of the gist, newest first, with how much changed.",
        page=_PAGE + "/revisions",
        delete=False,
    ),
    ResourceSpec(
        key="gist_forks",
        label="Gist Forks",
        scope="gist",
        parent="",
        noun="fork",
        list_path="{base}/forks",
        id_field="id",
        sentence=_fork,
        help="Who forked the gist, and when.",
        page=_PAGE + "/forks",
        delete=False,
    ),
)


def gist_spec(key: str) -> ResourceSpec | None:
    return next((spec for spec in GIST_SPECS if spec.key == key), None)


def fork_gist(api: Any, gist_id: str) -> str:
    """Copy someone's gist to your own account; returns the sentence to say."""
    from urllib.parse import quote

    try:
        data = api.rest("POST", f"/gists/{quote(gist_id, safe='')}/forks").data
    except GitHubRestError as exc:
        if exc.status == 422:
            raise ResourceError("GitHub would not fork it; you cannot fork your own gist.") from exc
        raise ResourceError(f"Could not fork the gist: {exc}") from exc
    new = str(data.get("id") or "") if isinstance(data, Mapping) else ""
    return f"Forked the gist. Your copy{' ' + new if new else ''} is in My Gists."
