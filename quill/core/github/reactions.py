"""Reactions on issues, pull requests and their comments, said in words.

GitHub's eight reactions are named the way a person says them ("thumbs up",
not ``+1``), and a comment's counts read as one phrase: "3 thumbs up, 1 heart".
Adding and removing go through :func:`~quill.core.github.rest_transport.request_json`
(api.github.com only, no redirects followed).

Removing needs the reaction's own ID, so :meth:`GitHubReactionsMixin.remove_reaction`
lists the target's reactions of that kind and deletes only the one the
signed-in account made; it never touches anyone else's.

No ``wx`` imports; strict-typed.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from functools import partial
from typing import Any, Protocol

from quill.core.github.items_errors import GitHubItemsError
from quill.core.github.rest_transport import (
    GitHubRestError,
    RestResponse,
    request_json,
    rest_failure_message,
)
from quill.core.github.run_actions import repo_path

#: (GitHub content key, spoken singular, spoken plural), in GitHub's own order.
REACTIONS: tuple[tuple[str, str, str], ...] = (
    ("+1", "thumbs up", "thumbs up"),
    ("-1", "thumbs down", "thumbs down"),
    ("laugh", "laugh", "laughs"),
    ("hooray", "hooray", "hoorays"),
    ("confused", "confused", "confused"),
    ("heart", "heart", "hearts"),
    ("rocket", "rocket", "rockets"),
    ("eyes", "eyes", "eyes"),
)

_NAMES = {content: singular for content, singular, _plural in REACTIONS}

#: What a reaction is attached to, and the REST collection that holds it.
REACTION_TARGETS: dict[str, str] = {
    "issue": "issues/{id}/reactions",  # an issue or a pull request itself
    "issue_comment": "issues/comments/{id}/reactions",
    "review_comment": "pulls/comments/{id}/reactions",
}

_MAX_REACTION_PAGES = 10


def reaction_name(content: str) -> str:
    """The spoken name for a GitHub reaction key; the key itself if unknown."""
    return _NAMES.get(content, content)


def reaction_counts_in_words(reactions: object) -> str:
    """``{"+1": 3, "heart": 1, ...}`` as "3 thumbs up, 1 heart"; "" when none."""
    if not isinstance(reactions, Mapping):
        return ""
    parts: list[str] = []
    for content, singular, plural in REACTIONS:
        count = reactions.get(content)
        if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
            continue
        parts.append(f"{count} {singular if count == 1 else plural}")
    return ", ".join(parts)


def reaction_choices(mine: frozenset[str] | set[str]) -> tuple[tuple[str, str], ...]:
    """(content, list label) rows for the chooser, saying which ones are yours."""
    return tuple(
        (
            content,
            f"{singular}, yours: choose to remove it" if content in mine else singular,
        )
        for content, singular, _plural in REACTIONS
    )


class _ReactionAccess(Protocol):
    _token: str | None

    def _require_write_access(self, action: str) -> None: ...

    def fetch_viewer_login(self) -> str: ...


def _collection(full_name: str, kind: str, target_id: int) -> str:
    template = REACTION_TARGETS.get(kind)
    if template is None:
        raise GitHubItemsError(f"QUILL cannot react to a {kind!r}.")
    if isinstance(target_id, bool) or not isinstance(target_id, int) or target_id <= 0:
        raise GitHubItemsError("This item has no GitHub ID to react to.")
    return f"{repo_path(full_name)}/{template.format(id=target_id)}"


def _content(content: str) -> str:
    if content not in _NAMES:
        raise GitHubItemsError(f"{content!r} is not one of GitHub's eight reactions.")
    return content


def _call(action: str, call: Callable[[], RestResponse], expect: tuple[int, ...]) -> RestResponse:
    try:
        response = call()
    except GitHubRestError as exc:
        raise GitHubItemsError(rest_failure_message(action, exc)) from exc
    if response.status not in expect:
        raise GitHubItemsError(
            f"Could not {action}. GitHub answered HTTP {response.status} without confirming it."
        )
    return response


def _rows(data: Any) -> list[dict[str, Any]]:
    return [row for row in data if isinstance(row, dict)] if isinstance(data, list) else []


def _user_login(row: Mapping[str, Any]) -> str:
    user = row.get("user")
    return str(user.get("login") or "") if isinstance(user, Mapping) else ""


class GitHubReactionsMixin:
    """List, add and remove the signed-in account's reactions."""

    def fetch_my_reactions(
        self: _ReactionAccess, full_name: str, kind: str, target_id: int
    ) -> frozenset[str]:
        """The reaction keys the signed-in account has already left on a target."""
        self._require_write_access("read your reactions")
        path = _collection(full_name, kind, target_id)
        login = self.fetch_viewer_login().casefold()
        mine: set[str] = set()
        for page in range(1, _MAX_REACTION_PAGES + 1):
            response = _call(
                "read reactions",
                partial(
                    request_json,
                    self._token,
                    "GET",
                    path,
                    query={"per_page": "100", "page": str(page)},
                ),
                (200,),
            )
            rows = _rows(response.data)
            mine.update(
                str(row.get("content") or "")
                for row in rows
                if _user_login(row).casefold() == login
            )
            if len(rows) < 100:
                break
        return frozenset(content for content in mine if content in _NAMES)

    def add_reaction(
        self: _ReactionAccess, full_name: str, kind: str, target_id: int, content: str
    ) -> str:
        """Add one reaction and return what GitHub confirmed, in words."""
        name = reaction_name(_content(content))
        self._require_write_access("add a reaction")
        path = _collection(full_name, kind, target_id)
        response = _call(
            f"add {name}",
            lambda: request_json(self._token, "POST", path, body={"content": content}),
            (200, 201),
        )
        data = response.data if isinstance(response.data, Mapping) else {}
        if data.get("content") != content:
            raise GitHubItemsError(f"GitHub did not confirm the {name} reaction.")
        if response.status == 200:
            return f"You had already reacted with {name}."
        return f"Added {name}."

    def remove_reaction(
        self: _ReactionAccess, full_name: str, kind: str, target_id: int, content: str
    ) -> str:
        """Delete the signed-in account's own reaction of this kind."""
        name = reaction_name(_content(content))
        self._require_write_access("remove a reaction")
        path = _collection(full_name, kind, target_id)
        login = self.fetch_viewer_login().casefold()
        reaction_id = 0
        for page in range(1, _MAX_REACTION_PAGES + 1):
            response = _call(
                "read reactions",
                partial(
                    request_json,
                    self._token,
                    "GET",
                    path,
                    query={"content": content, "per_page": "100", "page": str(page)},
                ),
                (200,),
            )
            rows = _rows(response.data)
            for row in rows:
                identifier = row.get("id")
                if (
                    _user_login(row).casefold() == login
                    and isinstance(identifier, int)
                    and not isinstance(identifier, bool)
                ):
                    reaction_id = identifier
                    break
            if reaction_id or len(rows) < 100:
                break
        if not reaction_id:
            return f"You have no {name} reaction here, so there was nothing to remove."
        _call(
            f"remove {name}",
            lambda: request_json(self._token, "DELETE", f"{path}/{reaction_id}"),
            (204,),
        )
        return f"Removed {name}."


__all__ = [
    "REACTIONS",
    "REACTION_TARGETS",
    "GitHubReactionsMixin",
    "reaction_choices",
    "reaction_counts_in_words",
    "reaction_name",
]
