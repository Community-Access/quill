"""Single GitHub calls on rows the Workbench already lists, as one table.

Many of GitHub's remaining operations are one call about one thing the
Workbench already shows: a repository's languages, a runner group's runners,
a team's pending invitations, a discussion to close. Each is a
:class:`Quick`: the rows it is for, what it asks (a text, a choice, a pick
from a list it reads first), whether it asks before it acts, the call it
makes, and what it says afterwards. The Workbench's menus
(:data:`QUICK_ROWS`), its permission table (:data:`QUICK_REQUIREMENTS`),
the live-run list (:data:`QUICK_LIVE`) and the API coverage table all read
the same rows, so a command cannot be in one and missing from another.

The entries themselves are in ``quick_table_*.py``; this module is the
shape and the helpers they share. wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote

from quill.core.error_codes import CodedError
from quill.core.github.rest_transport import GitHubRestError

__all__ = [
    "Ask",
    "Quick",
    "QuickError",
    "bulleted",
    "call",
    "fill",
    "gql",
    "plain",
    "refusal",
    "repository_id",
]


class QuickError(CodedError):
    """A quick command could not do what it said; the message is spoken."""

    code = "QUILL-GITHUB-QUICK"


@dataclass(frozen=True)
class Ask:
    """One question a command asks before it acts."""

    key: str
    question: str
    kind: str = "text"  # text, number, choice, yesno
    choices: tuple[str, ...] = ()
    values: tuple[str, ...] = ()
    default: str = ""
    optional: bool = False


@dataclass(frozen=True)
class Quick:
    """One command: where it is, what it asks, what it calls and what it says."""

    verb: str
    label: str
    menu: tuple[str, ...]  # the action table's row types it is listed on
    kinds: frozenset[str]  # the Workbench's row kinds it fits ("view" for a node's own list)
    help: str
    endpoints: tuple[str, ...]  # the API coverage rows it answers: "GET /repos/{owner}/{repo}/x"
    run: Callable[[Any, dict[str, str]], Any]
    said: Callable[[Any, dict[str, str]], str] = field(default=lambda data, _ctx: plain(data))
    tier: str = ""  # "", or O, V, A, D: what it changes (PRD 18.4)
    need: str = ""  # what GitHub needs of you (write_requirements' vocabulary)
    asks: tuple[Ask, ...] = ()
    confirm: str = ""  # asked first, with the context filled in
    report: bool = False  # the answer is long: show it in a window to read
    live: str = ""  # the live run's reason, for a write
    reload: bool = False  # the list changes afterwards
    pick: Callable[[Any, dict[str, str]], list[tuple[str, str]]] | None = None
    pick_key: str = ""
    pick_question: str = ""
    needs: tuple[str, ...] = ()  # context keys that must be known: repo, org, key, number, login
    node: str = ""  # with kinds {"view"}: the node key it belongs to
    copies: str = ""  # the answer holds a secret: put it on the clipboard, and say this
    #: Reads every page, stoppable: called as ``paged(api, ctx, paging)`` behind a Cancel button.
    paged: Callable[[Any, dict[str, str], Any], Any] | None = None
    # Asked just before the call, off the UI thread: a sentence refuses it (no self-lockout).
    guard: Callable[[Any, dict[str, str]], str] | None = None
    typed: str = ""  # a context key whose value must be typed to go ahead (tier 3)

    @property
    def writes(self) -> bool:
        return bool(self.tier)


def fill(template: str, ctx: Mapping[str, str]) -> str:
    """A path with ``{repo}`` kept whole and every other ``{name}`` quoted as one segment."""
    out = template
    for key, value in ctx.items():
        token = "{" + key + "}"
        if token in out:
            out = out.replace(token, value if key == "repo" else quote(str(value), safe=""))
    return out


def call(api: Any, method: str, template: str, ctx: Mapping[str, str], body: Any = None) -> Any:
    """One REST call, its refusal said plainly. A ``?a=b`` in *template* is its query."""
    from urllib.parse import parse_qsl

    template, _sep, raw_query = template.partition("?")
    path = fill(template, ctx)
    query = dict(parse_qsl(raw_query)) if raw_query else None
    try:
        kwargs: dict[str, Any] = {}
        if body is not None:
            kwargs["body"] = body
        if query:
            kwargs["query"] = query
        return api.rest(method, path, **kwargs).data
    except GitHubRestError as exc:
        raise refusal(exc) from exc


def refusal(exc: GitHubRestError) -> QuickError:
    """GitHub's refusal as the sentence a quick command says."""
    if exc.status in (401, 403):
        return QuickError(f"GitHub refused: {exc}. You may need more access here.")
    if exc.status == 404:
        return QuickError("GitHub does not show that to you, or it is gone.")
    return QuickError(f"GitHub could not do it: {exc}")


def gql(api: Any, query: str, variables: Mapping[str, Any]) -> dict[str, Any]:
    """One GraphQL call; GitHub's refusal said plainly."""
    from quill.core.github.items_provider import GitHubItemsError

    try:
        data: dict[str, Any] = api.graphql(query, dict(variables))
        return data
    except GitHubItemsError as exc:
        raise QuickError(str(exc)) from exc


def repository_id(api: Any, name: str) -> int:
    """A repository's id from its owner/name."""
    data = call(api, "GET", "/repos/{repo}", {"repo": name.strip()})
    found = data.get("id") if isinstance(data, Mapping) else None
    if not isinstance(found, int):
        raise QuickError(f"There is no repository {name} that you can see.")
    return found


def _scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    if value is None or value == "":
        return "none"
    return str(value)


def plain(data: Any, limit: int = 40) -> str:
    """Any reply as sentences a listener can follow: "name: value" a line."""
    if data is None or data == "" or data == {}:
        return "Done."
    if isinstance(data, str):
        return data
    if isinstance(data, Sequence) and not isinstance(data, (str, bytes)):
        rows = [plain(item, limit) for item in list(data)[:limit]]
        more = f"\n... and {len(data) - limit} more." if len(data) > limit else ""
        return ("\n".join(rows) + more) if rows else "None."
    if isinstance(data, Mapping):
        lines = []
        for key, value in data.items():
            if isinstance(value, Mapping):
                inner = ", ".join(
                    f"{k}: {_scalar(v)}"
                    for k, v in value.items()
                    if not isinstance(v, (Mapping, list))
                )
                lines.append(f"{key}: {inner or 'more detail on GitHub'}")
            elif isinstance(value, list):
                names = [
                    str(v.get("name") or v.get("login") or v.get("full_name") or v)
                    if isinstance(v, Mapping)
                    else str(v)
                    for v in value[:limit]
                ]
                lines.append(f"{key}: {', '.join(names) or 'none'}")
            elif not str(key).endswith("_url") and key not in ("node_id", "url"):
                lines.append(f"{key}: {_scalar(value)}")
        return "\n".join(lines) or "Done."
    return str(data)


def bulleted(rows: Sequence[str], none: str) -> str:
    """Rows a line each, or *none* when there are none."""
    return "\n".join(rows) if rows else none
