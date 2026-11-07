"""Repository actions for the shared workbench (Wave 4).

Sync a fork with its upstream, list and delete Actions caches, list secret
and variable *names* (never values), create a repository from a template, set
topics, archive and unarchive, choose a watch level, follow and unfollow a
person, and delete a repository. Every call goes through
:func:`~quill.core.github.rest_transport.request_json`, so the token stays on
``api.github.com`` and rate limits are tracked in one place.

Each write says only what GitHub confirmed: a status code it did not promise
is an error, and a reply that contradicts the request (an archive that did not
archive) is reported as such. Failures carry the next step through
:func:`~quill.core.github.rest_transport.rest_failure_message`, which uses
:func:`~quill.core.github.auth_diagnostics.github_exception_hint`.

No ``wx`` imports; strict-typed.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from typing import Any
from urllib.parse import quote

from quill.core.github.explore_models import ExploreRow
from quill.core.github.items_errors import GitHubItemsError
from quill.core.github.rest_transport import (
    GitHubRestError,
    RestResponse,
    request_json,
    rest_failure_message,
)
from quill.core.github.run_actions import repo_path

WATCH_LEVELS: tuple[tuple[str, str], ...] = (
    ("watching", "Watching: all activity"),
    ("releases", "Releases only"),
    ("ignoring", "Ignoring: never notified"),
    ("not_watching", "Not watching: only when participating or mentioned"),
)
_TOPIC = re.compile(r"^[a-z0-9][a-z0-9-]{0,49}$")
_LOGIN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")
MAX_TOPICS = 20


def _call(
    action: str, call: Callable[[], RestResponse], *, expect: tuple[int, ...]
) -> RestResponse:
    try:
        response = call()
    except GitHubRestError as exc:
        message = rest_failure_message(action, exc)
        if exc.status == 403 and "delete" in action and "repository" in action:
            message += (
                " Deleting a repository needs the token's delete_repo scope, or for a "
                "fine-grained token, write access to the repository's Administration."
            )
        raise GitHubItemsError(message) from exc
    if response.status not in expect:
        raise GitHubItemsError(
            f"Could not {action}. GitHub answered HTTP {response.status} without confirming it."
        )
    return response


def _size(size: int) -> str:
    value = float(size)
    for unit in ("bytes", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:,.0f} {unit}" if unit == "bytes" else f"{value:,.1f} {unit}"
        value /= 1024
    return f"{size:,} bytes"


def normalize_topics(text: str | Sequence[str]) -> tuple[str, ...]:
    """Split, lower-case and check topics the way GitHub will; raise on a bad one."""
    raw = text.replace(",", " ").split() if isinstance(text, str) else list(text)
    topics = tuple(dict.fromkeys(word.strip().lower() for word in raw if word.strip()))
    bad = [topic for topic in topics if not _TOPIC.match(topic)]
    if bad:
        raise GitHubItemsError(
            f"GitHub topics are lower-case letters, numbers and hyphens, up to 50 characters: "
            f"{', '.join(bad)} will not be accepted."
        )
    if len(topics) > MAX_TOPICS:
        raise GitHubItemsError(
            f"GitHub allows at most {MAX_TOPICS} topics; you gave {len(topics)}."
        )
    return topics


def sync_sentence(merge_type: str, commits: int | None, upstream: str, message: str) -> str:
    """ "Already up to date" or "Merged 3 commits from owner:main", from GitHub's reply."""
    if merge_type in ("", "none") or "not behind" in message.casefold():
        return f"Already up to date with {upstream}." if upstream else "Already up to date."
    where = f" from {upstream}" if upstream else ""
    if commits:
        return f"Merged {commits} commit{'' if commits == 1 else 's'}{where}."
    how = "fast-forwarded" if merge_type == "fast-forward" else "merged"
    return f"GitHub {how} the fork{where}."


class GitHubRepoActions:
    """Wave 4 repository writes and name-only reads for one signed-in session."""

    def __init__(self, token: str | None) -> None:
        self._token = token

    def _require_write_access(self, action: str) -> None:
        if not self._token:
            raise GitHubItemsError(
                f"To {action} you need a signed-in GitHub account; "
                "the anonymous viewer is read-only."
            )

    def _send(
        self,
        action: str,
        method: str,
        path: str,
        *,
        expect: tuple[int, ...],
        body: dict[str, object] | None = None,
        query: dict[str, str] | None = None,
    ) -> RestResponse:
        return _call(
            action,
            lambda: request_json(self._token, method, path, body=body, query=query),
            expect=expect,
        )

    # -- Fork sync -----------------------------------------------------------

    def sync_fork(self, repo: str) -> str:
        """Merge the upstream default branch into the fork's; say what happened."""
        self._require_write_access("sync a fork")
        base = repo_path(repo)
        info = self._send("read the fork", "GET", base, expect=(200,)).data
        info = info if isinstance(info, dict) else {}
        parent = info.get("parent") if isinstance(info.get("parent"), dict) else None
        if not parent:
            raise GitHubItemsError(f"{repo} is not a fork, so there is no upstream to sync from.")
        branch = str(info.get("default_branch") or "main")
        upstream_name = str(parent.get("full_name") or "")
        upstream_branch = str(parent.get("default_branch") or branch)
        owner = str((info.get("owner") or {}).get("login") or repo.split("/")[0])
        behind: int | None = None
        try:
            compare = request_json(
                self._token,
                "GET",
                f"{repo_path(upstream_name)}/compare/{quote(owner, safe='')}:"
                f"{quote(branch, safe='')}...{quote(upstream_branch, safe='')}",
            ).data
            if isinstance(compare, dict):
                behind = int(compare.get("ahead_by") or 0)
        except (GitHubRestError, GitHubItemsError, TypeError, ValueError):
            behind = None
        reply = self._send(
            f"sync {repo} with its upstream",
            "POST",
            f"{base}/merge-upstream",
            expect=(200,),
            body={"branch": branch},
        ).data
        reply = reply if isinstance(reply, dict) else {}
        upstream = str(reply.get("base_branch") or f"{upstream_name}:{upstream_branch}")
        return sync_sentence(
            str(reply.get("merge_type") or ""), behind, upstream, str(reply.get("message") or "")
        )

    # -- Actions caches ------------------------------------------------------

    def list_caches(self, repo: str, *, limit: int, warnings: list[str]) -> list[ExploreRow]:
        self._require_write_access("list Actions caches")
        base = repo_path(repo)
        per_page = str(max(1, min(limit, 100)))
        data = self._send(
            "list the Actions caches",
            "GET",
            f"{base}/actions/caches",
            expect=(200,),
            query={"per_page": per_page, "sort": "last_accessed_at", "direction": "desc"},
        ).data
        body = data if isinstance(data, dict) else {}
        caches = [row for row in body.get("actions_caches") or () if isinstance(row, dict)]
        total = int(body.get("total_count") or len(caches))
        used = sum(int(row.get("size_in_bytes") or 0) for row in caches)
        if total > len(caches):
            warnings.append(f"showing {len(caches)} of {total} caches")
        page = f"https://github.com/{repo}/actions/caches"
        rows = [
            ExploreRow(
                f"{total} Actions cache{'' if total == 1 else 's'} in {repo}, {_size(used)} listed",
                f"Actions caches for {repo}\n{total} in all; the ones listed use {_size(used)}.\n"
                f"{page}",
                page,
                repo,
                "cache_summary",
            )
        ]
        for row in caches[:limit]:
            key = str(row.get("key") or "")
            ref = str(row.get("ref") or "")
            used_at = str(row.get("last_accessed_at") or "")[:16].replace("T", " ")
            size = _size(int(row.get("size_in_bytes") or 0))
            rows.append(
                ExploreRow(
                    f"{key}, {size}, branch {ref.removeprefix('refs/heads/')}, last used {used_at}",
                    f"Cache key: {key}\nSize: {size}\nRef: {ref}\nLast used: {used_at}\n"
                    f"Created: {row.get('created_at', '')}\nCache ID: {row.get('id', '')}\n{page}",
                    page,
                    repo,
                    "cache",
                    str(row.get("id") or ""),
                )
            )
        return rows

    def delete_cache(self, repo: str, cache_id: str) -> None:
        self._require_write_access("delete an Actions cache")
        if not cache_id.isdecimal():
            raise GitHubItemsError("This cache has no GitHub cache ID.")
        self._send(
            "delete the cache",
            "DELETE",
            f"{repo_path(repo)}/actions/caches/{cache_id}",
            expect=(204,),
        )

    # -- Secret and variable names --------------------------------------------

    def _names(self, action: str, path: str, field: str) -> list[tuple[str, str]]:
        data = self._send(action, "GET", path, expect=(200,), query={"per_page": "100"}).data
        rows = data.get(field) if isinstance(data, dict) else None
        # Only the name and the date leave this function: a variable's value never does.
        return [
            (str(row.get("name")), str(row.get("updated_at") or "")[:10])
            for row in rows or ()
            if isinstance(row, dict) and row.get("name")
        ]

    def list_secret_names(self, repo: str, *, limit: int, warnings: list[str]) -> list[ExploreRow]:
        """Repository and environment secrets and variables, by name only."""
        self._require_write_access("list secret names")
        base = repo_path(repo)
        settings = f"https://github.com/{repo}/settings/secrets/actions"
        rows: list[ExploreRow] = []

        def add(scope: str, kind: str, names: list[tuple[str, str]]) -> None:
            for name, updated in names:
                when = f", updated {updated}" if updated else ""
                rows.append(
                    ExploreRow(
                        f"{scope} {kind}: {name}{when}",
                        f"{scope} {kind}: {name}\nUpdated: {updated or 'not reported'}\n"
                        "QUILL lists names only; values are never read.\n" + settings,
                        settings,
                        repo,
                        "secret",
                        name,
                    )
                )

        for kind, path, field in (
            ("secret", f"{base}/actions/secrets", "secrets"),
            ("variable", f"{base}/actions/variables", "variables"),
        ):
            try:
                add("Repository", kind, self._names(f"list repository {kind}s", path, field))
            except GitHubItemsError as exc:
                warnings.append(str(exc))
        try:
            envs = self._send(
                "list environments", "GET", f"{base}/environments", expect=(200,)
            ).data
        except GitHubItemsError as exc:
            warnings.append(str(exc))
            envs = {}
        for env in (envs.get("environments") if isinstance(envs, dict) else None) or ():
            name = str(env.get("name") or "") if isinstance(env, dict) else ""
            if not name:
                continue
            env_base = f"{base}/environments/{quote(name, safe='')}"
            for kind, field in (("secret", "secrets"), ("variable", "variables")):
                try:
                    found = self._names(
                        f"list {kind}s for environment {name}", f"{env_base}/{field}", field
                    )
                except GitHubItemsError as exc:
                    warnings.append(str(exc))
                    continue
                add(f"Environment {name}", kind, found)
        if len(rows) > limit:
            warnings.append(f"showing the first {limit} of {len(rows)} names")
        return rows[:limit]

    # -- Template, topics, archive --------------------------------------------

    def create_from_template(
        self,
        template: str,
        name: str,
        *,
        owner: str = "",
        description: str = "",
        private: bool = True,
        include_all_branches: bool = False,
    ) -> tuple[str, str]:
        """Create *name* from *template*; return GitHub's ``(full_name, html_url)``."""
        self._require_write_access("create a repository from a template")
        if not name.strip():
            raise GitHubItemsError("Enter a name for the new repository.")
        body: dict[str, object] = {
            "name": name.strip(),
            "private": private,
            "include_all_branches": include_all_branches,
        }
        if owner.strip():
            body["owner"] = owner.strip()
        if description.strip():
            body["description"] = description.strip()
        data = self._send(
            f"create {name.strip()} from {template}",
            "POST",
            f"{repo_path(template)}/generate",
            expect=(201,),
            body=body,
        ).data
        data = data if isinstance(data, dict) else {}
        full_name = str(data.get("full_name") or "")
        if not full_name:
            raise GitHubItemsError(
                "GitHub answered without naming the new repository; check github.com before "
                "trying again."
            )
        return full_name, str(data.get("html_url") or f"https://github.com/{full_name}")

    def get_topics(self, repo: str) -> tuple[str, ...]:
        data = self._send("read the topics", "GET", f"{repo_path(repo)}/topics", expect=(200,)).data
        names = data.get("names") if isinstance(data, dict) else None
        return tuple(str(name) for name in names or ())

    def set_topics(self, repo: str, topics: str | Sequence[str]) -> tuple[str, ...]:
        """Replace the topics; return the list GitHub now holds."""
        self._require_write_access("set topics")
        wanted = normalize_topics(topics)
        data = self._send(
            "set the topics",
            "PUT",
            f"{repo_path(repo)}/topics",
            expect=(200,),
            body={"names": list(wanted)},
        ).data
        names = data.get("names") if isinstance(data, dict) else None
        return tuple(str(name) for name in names or ())

    def set_archived(self, repo: str, archived: bool) -> None:
        verb = "archive" if archived else "unarchive"
        self._require_write_access(f"{verb} a repository")
        data = self._send(
            f"{verb} {repo}", "PATCH", repo_path(repo), expect=(200,), body={"archived": archived}
        ).data
        if isinstance(data, dict) and "archived" in data and bool(data["archived"]) != archived:
            raise GitHubItemsError(
                f"GitHub answered, but {repo} is still {'not ' if archived else ''}archived."
            )

    # -- Watching and following ------------------------------------------------

    def get_watch_level(self, repo: str) -> str:
        """``watching``, ``ignoring`` or ``not_watching``.

        GitHub's API cannot see Releases only (or other custom choices); such a
        subscription reads as watching, and the UI says so.
        """
        self._require_write_access("read your watch setting")
        try:
            response = request_json(self._token, "GET", f"{repo_path(repo)}/subscription")
        except GitHubRestError as exc:
            if exc.status == 404:
                return "not_watching"
            raise GitHubItemsError(rest_failure_message("read your watch setting", exc)) from exc
        data = response.data if isinstance(response.data, dict) else {}
        if data.get("ignored"):
            return "ignoring"
        return "watching" if data.get("subscribed") else "not_watching"

    def set_watch_level(self, repo: str, level: str) -> None:
        self._require_write_access("change how you watch a repository")
        path = f"{repo_path(repo)}/subscription"
        if level == "releases":
            raise GitHubItemsError(
                "GitHub's API cannot set Releases only. Choose it on the repository's page "
                "with the Watch button."
            )
        if level == "not_watching":
            self._send("stop watching", "DELETE", path, expect=(204,))
            return
        if level not in ("watching", "ignoring"):
            raise GitHubItemsError(f"Unknown watch level: {level}")
        body: dict[str, object] = {"subscribed": True} if level == "watching" else {"ignored": True}
        data = self._send("change the watch level", "PUT", path, expect=(200,), body=body).data
        if isinstance(data, dict):
            confirmed = (
                bool(data.get("ignored")) if level == "ignoring" else bool(data.get("subscribed"))
            )
            if not confirmed:
                raise GitHubItemsError("GitHub answered, but the watch level did not change.")

    def set_following(self, login: str, follow: bool) -> None:
        verb = "follow" if follow else "unfollow"
        self._require_write_access(f"{verb} a person")
        name = login.strip().lstrip("@")
        if not _LOGIN.match(name):
            raise GitHubItemsError(f"{login!r} is not a GitHub username.")
        self._send(
            f"{verb} @{name}",
            "PUT" if follow else "DELETE",
            f"/user/following/{name}",
            expect=(204,),
        )

    # -- Delete ----------------------------------------------------------------

    def delete_repository(self, repo: str) -> None:
        self._require_write_access("delete a repository")
        self._send(f"delete repository {repo}", "DELETE", repo_path(repo), expect=(204,))


def watch_level_words(level: str) -> str:
    return dict(WATCH_LEVELS).get(level, level)


def wrap_errors(call: Callable[[], Any], error: type[Exception]) -> Any:
    """Run *call*, re-raising :class:`GitHubItemsError` as *error* with the same words."""
    try:
        return call()
    except GitHubItemsError as exc:
        raise error(str(exc.args[0]) if exc.args else str(exc)) from exc


__all__ = [
    "MAX_TOPICS",
    "WATCH_LEVELS",
    "GitHubRepoActions",
    "normalize_topics",
    "sync_sentence",
    "watch_level_words",
    "wrap_errors",
]
