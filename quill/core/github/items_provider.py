"""Read-only GitHub items provider: issues, PRs, branches, commits, tags,
releases, and workflow runs (#924).

A sibling of :mod:`quill.core.github.github_provider` (which handles remote
*files*). This module wraps a PyGithub ``Repository`` and surfaces a
repository's items as plain frozen dataclasses, so the UI can render a
list-over-detail viewer without touching PyGithub types directly.

Design (see ``docs`` issue #924 spec):
- Transport is PyGithub (no ``gh`` subprocess, no new deps). PyGithub is
  imported lazily via :func:`require_pygithub` so the module imports cleanly
  when the optional dep is absent.
- wx-free and strict-typed (in ``mypy quill/core`` scope).
- Every fetcher takes an explicit ``limit`` (page cap, default 30) so a repo
  with thousands of items never blocks the dialog on one call; the UI offers a
  "View more" affordance to pull the next page.
- Safe Mode: :func:`refuse_in_safe_mode` raises :class:`GitHubItemsError` when
  ``safe_mode`` is True. The UI mixin calls it before any network so a Safe
  Mode launch never reaches GitHub. The bool is passed in (Safe Mode is a
  runtime/UI concept; core never imports wx).
- Errors raise :class:`GitHubItemsError` (a :class:`CodedError`) so a pasted
  error message carries a greppable support code (GATE-EC).

No ``wx`` imports. Every call goes through PyGithub, the audited transport
for GitHub, with one deliberate exception: ``download_artifact_to_file``
uses ``urllib.request`` directly for the artifact-download redirect, since
GitHub's artifact endpoint 302s to a signed URL on a different host and the
``Authorization`` header must be dropped there by hand rather than relying
on PyGithub's private ``Requester`` internals or an auto-redirect-following
opener that could forward it by accident -- see that method's own docstring,
and ``quill/tools/network_egress_audit.py``.
"""

from __future__ import annotations

import urllib.error
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from quill.core.error_codes import CodedError
from quill.core.github.branch_compare import GitHubBranchComparison, fetch_branch_comparison
from quill.core.github.github_provider import _get_gh_module, require_pygithub
from quill.core.github.notifications import (
    GitHubNotification,
    GitHubSecurityAlert,
    list_notifications,
    list_security_alerts,
)
from quill.core.github.notifications import mark_notification_read as _mark_notification_read_raw
from quill.core.github.workflows import GitHubWorkflow, list_workflows

#: Default page cap for a single fetch. The dialog loads this many, then offers
#: "View more" for the next batch -- mirrors GHManage's 30-at-a-time behaviour.
DEFAULT_PAGE_LIMIT = 30


class GitHubItemsError(CodedError):
    """A GitHub items fetch failed (network, auth, API, or Safe Mode refusal)."""

    code = "QUILL-GITHUB-ITEMS-ERROR"


def refuse_in_safe_mode(safe_mode: bool) -> None:
    """Raise :class:`GitHubItemsError` when Safe Mode is active.

    Safe Mode (``QUILL_SAFE_MODE=1``) disables every network service. The GitHub
    items viewer is a network service, so the UI mixin calls this before
    constructing the provider or touching the network. Kept in core (with the
    flag passed in) so the refusal is unit-testable without wx.
    """
    if safe_mode:
        raise GitHubItemsError(
            "GitHub item browsing is disabled in Safe Mode. "
            "Restart QUILL normally to browse a repository."
        )


# ---------------------------------------------------------------------------
# Models (frozen, slots) -- the field sets mirror GHManage's dataclasses.
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class GitHubItem:
    """A GitHub issue or pull request (one inbox, ``is_pr`` distinguishes).

    The field set mirrors GHManage's ``Item`` (the reference viewer): the PR-only
    ``changed_files`` / ``base_branch`` / ``head_branch`` carry the diff summary
    and the branch flow shown in the details pane. ``review_status`` is the
    review decision; PyGithub does not expose it on the list endpoint, so it is
    populated only when a detail fetch supplies it (left empty in list rows).
    """

    number: int
    title: str
    state: str
    url: str
    is_pr: bool
    author: str = ""
    created_at: str = ""
    updated_at: str = ""
    body: str = ""
    labels: tuple[str, ...] = field(default_factory=tuple)
    assignees: tuple[str, ...] = field(default_factory=tuple)
    comments: int = 0
    is_draft: bool = False
    is_merged: bool = False
    review_status: str = ""
    additions: int = 0
    deletions: int = 0
    changed_files: int = 0
    base_branch: str = ""
    head_branch: str = ""

    @property
    def kind(self) -> str:
        return "PR" if self.is_pr else "ISSUE"

    @property
    def state_display(self) -> str:
        """Upper-cased state, with merged PRs shown as MERGED (GHManage parity)."""
        if self.is_pr and self.is_merged:
            return "MERGED"
        return self.state.upper()


@dataclass(frozen=True, slots=True)
class GitHubBranch:
    """A repository branch."""

    name: str
    commit_sha: str
    commit_message: str = ""
    commit_author: str = ""
    commit_date: str = ""
    protected: bool = False
    ahead: int = 0
    behind: int = 0
    url: str = ""


@dataclass(frozen=True, slots=True)
class GitHubCommit:
    """A commit on a branch (or the default history)."""

    sha: str
    short_sha: str
    message: str
    author: str = ""
    date: str = ""
    url: str = ""
    additions: int = 0
    deletions: int = 0
    files_changed: int = 0


@dataclass(frozen=True, slots=True)
class GitHubTag:
    """A git tag."""

    name: str
    commit_sha: str = ""
    url: str = ""


@dataclass(frozen=True, slots=True)
class GitHubRelease:
    """A published (or draft/prerelease) release."""

    tag: str
    name: str
    draft: bool = False
    prerelease: bool = False
    created_at: str = ""
    url: str = ""
    body: str = ""


@dataclass(frozen=True, slots=True)
class GitHubPullFile:
    """One changed file in a pull request (the PR diff viewer's row model)."""

    filename: str
    status: str = ""  # added / removed / modified / renamed
    additions: int = 0
    deletions: int = 0
    changes: int = 0
    previous_filename: str = ""
    patch: str = ""


@dataclass(frozen=True, slots=True)
class GitHubPullDiff:
    """A pull request's changed-file inventory plus the refs to fetch content at."""

    number: int
    title: str
    base_ref: str
    base_sha: str
    head_ref: str
    head_sha: str
    files: tuple[GitHubPullFile, ...] = ()


@dataclass(frozen=True, slots=True)
class GitHubRepoForkInfo:
    """Whether a repository is a fork, and its upstream's full name if so."""

    is_fork: bool
    parent_full_name: str = ""


@dataclass(frozen=True, slots=True)
class GitHubWorkflowRun:
    """A GitHub Actions workflow run."""

    name: str
    status: str
    conclusion: str = ""
    branch: str = ""
    event: str = ""
    created_at: str = ""
    url: str = ""
    run_number: int = 0


@dataclass(frozen=True, slots=True)
class GitHubWorkflowJob:
    """One job within a workflow run -- the practical "Actions log" surface:
    per-job status/conclusion instead of raw log text (GitHub's log download
    is a redirect to a zip archive, out of scope for a first pass; job-level
    status is the same information a glance at the Actions tab gives)."""

    name: str
    status: str
    conclusion: str = ""
    started_at: str = ""
    completed_at: str = ""
    url: str = ""


@dataclass(frozen=True, slots=True)
class GitHubArtifact:
    """One build artifact from a workflow run -- the "redirect to a zip
    archive" case ``GitHubWorkflowJob`` above scoped out for logs, now built
    deliberately (with the redirect's auth-header handling done correctly;
    see :meth:`GitHubItemsProvider.download_artifact_to_file`)."""

    id: int
    name: str
    size_bytes: int
    expired: bool
    archive_download_url: str

    @property
    def size_display(self) -> str:
        size = float(self.size_bytes)
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024 or unit == "GB":
                return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} GB"


# ---------------------------------------------------------------------------
# Mapping helpers -- defensive per-item so one bad row never blanks the list.
# ---------------------------------------------------------------------------


def _safe_str(value: object) -> str:
    try:
        return str(value) if value is not None else ""
    except Exception:  # noqa: BLE001 - PyGithub attribute access can raise
        return ""


def _iso(value: object) -> str:
    """Return an ISO-8601 string for a PyGithub datetime, or "" if unavailable."""
    if value is None:
        return ""
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        try:
            return str(isoformat())
        except Exception:  # noqa: BLE001
            return ""
    return _safe_str(value)


def _login_of(obj: object) -> str:
    """Read ``obj.login`` defensively (users/assignees/authors)."""
    login = getattr(obj, "login", None)
    return _safe_str(login)


def _names_of(items: Any) -> tuple[str, ...]:
    """Read ``item.name`` off each item in an iterable (labels)."""
    out: list[str] = []
    try:
        for item in items or ():
            out.append(_safe_str(getattr(item, "name", "")))
    except Exception:  # noqa: BLE001
        pass
    return tuple(out)


def _logins_of(items: Any) -> tuple[str, ...]:
    """Read ``item.login`` off each item in an iterable (assignees/reviewers)."""
    out: list[str] = []
    try:
        for item in items or ():
            out.append(_login_of(item))
    except Exception:  # noqa: BLE001
        pass
    return tuple(out)


def _take(iterable: Any, limit: int) -> list[Any]:
    """Return up to *limit* items from *iterable* (PyGithub paginated lists)."""
    out: list[Any] = []
    try:
        for item in iterable or ():
            out.append(item)
            if len(out) >= limit:
                break
    except Exception:  # noqa: BLE001
        pass
    return out


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------


class GitHubItemsProvider:
    """Read-only GitHub items fetcher backed by PyGithub.

    Construct with a token (authenticated) or ``None`` (anonymous, public repos
    only), mirroring :class:`~quill.core.github.github_provider.GitHubRemoteProvider`.
    Each fetcher resolves ``owner/repo`` to a PyGithub ``Repository`` and maps
    the results onto the frozen models above.
    """

    def __init__(self, token: str | None = None) -> None:
        gh = _get_gh_module()
        if token:
            self._gh: Any = gh.Github(auth=gh.Auth.Token(token))
        else:
            self._gh = gh.Github()
        self._token = token

    @property
    def is_authenticated(self) -> bool:
        """True when the session carries a token (batch actions require one)."""
        return bool(self._token)

    @property
    def token(self) -> str | None:
        """The token this session was constructed with, for callers that need
        to spin up a sibling provider (e.g. GitHubRepoAdminProvider for a
        branch-delete action reached from the items viewer)."""
        return self._token

    def _repo(self, full_name: str) -> Any:
        gh = _get_gh_module()
        try:
            return self._gh.get_repo(full_name)
        except gh.GithubException as exc:
            status = getattr(exc, "status", None)
            if status == 404:
                raise GitHubItemsError(
                    f"Repository not found: {full_name!r}. Check owner/repo and access."
                ) from exc
            if status == 401:
                raise GitHubItemsError("GitHub token is invalid or has expired.") from exc
            if status == 403:
                raise GitHubItemsError(
                    "Access denied. Your token may need 'repo' scope for private repositories."
                ) from exc
            msg = exc.data.get("message", str(exc)) if hasattr(exc, "data") else str(exc)
            raise GitHubItemsError(f"GitHub error {status}: {msg}") from exc

    def fetch_fork_info(self, full_name: str) -> GitHubRepoForkInfo:
        """Whether *full_name* is a fork, and its parent's full name if so --
        the single-repo ``GET`` response is the only one PyGithub's
        ``Repository.parent`` populates from (a list-response row omits it,
        so this always needs its own call rather than reusing an already-
        loaded row -- see ``Repository.get_repo`` vs ``get_repos``)."""
        repo = self._repo(full_name)
        if not bool(getattr(repo, "fork", False)):
            return GitHubRepoForkInfo(is_fork=False)
        parent = getattr(repo, "parent", None)
        parent_name = str(getattr(parent, "full_name", "") or "") if parent is not None else ""
        return GitHubRepoForkInfo(is_fork=True, parent_full_name=parent_name)

    # ------------------------------------------------------------------
    # Issues and pull requests (one inbox; is_pr distinguishes)

    def fetch_issues(
        self,
        full_name: str,
        *,
        state: str = "open",
        limit: int = DEFAULT_PAGE_LIMIT,
    ) -> list[GitHubItem]:
        repo = self._repo(full_name)
        try:
            rows = _take(repo.get_issues(state=state), limit)
        except Exception as exc:  # noqa: BLE001 - surface as a coded error
            raise GitHubItemsError(f"Could not list issues: {exc}") from exc
        return [self._map_issue(row, is_pr=False) for row in rows]

    def fetch_pulls(
        self,
        full_name: str,
        *,
        state: str = "open",
        limit: int = DEFAULT_PAGE_LIMIT,
    ) -> list[GitHubItem]:
        repo = self._repo(full_name)
        try:
            rows = _take(repo.get_pulls(state=state), limit)
        except Exception as exc:  # noqa: BLE001
            raise GitHubItemsError(f"Could not list pull requests: {exc}") from exc
        return [self._map_issue(row, is_pr=True) for row in rows]

    def _map_issue(self, row: Any, *, is_pr: bool) -> GitHubItem:
        # ``pull_request`` attribute presence on an issue row means it is a PR;
        # for rows from get_pulls() is_pr is forced True already.
        pr_link = getattr(row, "pull_request", None)
        effective_pr = is_pr or pr_link is not None
        review_status = ""
        additions = 0
        deletions = 0
        changed_files = 0
        base_branch = ""
        head_branch = ""
        is_merged = False
        is_draft = bool(getattr(row, "draft", False))
        if effective_pr:
            is_merged = bool(getattr(row, "merged", False))
            additions = int(getattr(row, "additions", 0) or 0)
            deletions = int(getattr(row, "deletions", 0) or 0)
            changed_files = int(getattr(row, "changed_files", 0) or 0)
            # reviewDecision is a gh-CLI field; PyGithub does not expose it on the
            # list endpoint, so review_status stays empty in list rows (a detail
            # fetch could populate it; v1 leaves it blank rather than burn an
            # extra API call per row).
            base = getattr(row, "base", None)
            head = getattr(row, "head", None)
            base_branch = _safe_str(getattr(base, "ref", "")) if base is not None else ""
            head_branch = _safe_str(getattr(head, "ref", "")) if head is not None else ""
        return GitHubItem(
            number=int(getattr(row, "number", 0) or 0),
            title=_safe_str(getattr(row, "title", "")),
            state=_safe_str(getattr(row, "state", "")),
            url=_safe_str(getattr(row, "html_url", "")),
            is_pr=effective_pr,
            author=_login_of(getattr(row, "user", None)),
            created_at=_iso(getattr(row, "created_at", None)),
            updated_at=_iso(getattr(row, "updated_at", None)),
            body=_safe_str(getattr(row, "body", "")),
            labels=_names_of(getattr(row, "labels", None)),
            assignees=_logins_of(getattr(row, "assignees", None)),
            comments=int(getattr(row, "comments", 0) or 0),
            is_draft=is_draft,
            is_merged=is_merged,
            review_status=review_status,
            additions=additions,
            deletions=deletions,
            changed_files=changed_files,
            base_branch=base_branch,
            head_branch=head_branch,
        )

    # ------------------------------------------------------------------
    # Branches and commits

    def fetch_branches(
        self,
        full_name: str,
        *,
        limit: int = DEFAULT_PAGE_LIMIT,
    ) -> list[GitHubBranch]:
        repo = self._repo(full_name)
        try:
            rows = _take(repo.get_branches(), limit)
        except Exception as exc:  # noqa: BLE001
            raise GitHubItemsError(f"Could not list branches: {exc}") from exc
        return [self._map_branch(row, repo) for row in rows]

    def _map_branch(self, row: Any, repo: Any) -> GitHubBranch:
        name = _safe_str(getattr(row, "name", ""))
        commit = getattr(row, "commit", None)
        commit_sha = _safe_str(getattr(commit, "sha", "")) if commit is not None else ""
        commit_message = ""
        commit_author = ""
        commit_date = ""
        if commit is not None:
            inner = getattr(commit, "commit", None)
            if inner is not None:
                commit_message = _safe_str(getattr(inner, "message", ""))
                author_obj = getattr(inner, "author", None)
                if author_obj is not None:
                    commit_author = _safe_str(getattr(author_obj, "name", ""))
                    commit_date = _iso(getattr(author_obj, "date", None))
        protected = bool(getattr(row, "protected", False))
        url = f"{repo.html_url}/tree/{name}" if getattr(repo, "html_url", "") else ""
        # ahead/behind need a compare() call per branch (expensive at scale); v1
        # leaves them at 0 -- a follow-up can populate them on demand from the
        # detail pane, where a single branch's divergence is cheap to fetch.
        return GitHubBranch(
            name=name,
            commit_sha=commit_sha,
            commit_message=commit_message,
            commit_author=commit_author,
            commit_date=commit_date,
            protected=protected,
            ahead=0,
            behind=0,
            url=url,
        )

    def fetch_commits(
        self,
        full_name: str,
        *,
        branch: str | None = None,
        limit: int = DEFAULT_PAGE_LIMIT,
    ) -> list[GitHubCommit]:
        repo = self._repo(full_name)
        kwargs: dict[str, Any] = {}
        if branch:
            kwargs["sha"] = branch
        try:
            rows = _take(repo.get_commits(**kwargs), limit)
        except Exception as exc:  # noqa: BLE001
            raise GitHubItemsError(f"Could not list commits: {exc}") from exc
        return [self._map_commit(row, repo) for row in rows]

    def _map_commit(self, row: Any, repo: Any) -> GitHubCommit:
        sha = _safe_str(getattr(row, "sha", ""))
        inner = getattr(row, "commit", None)
        message = ""
        author = ""
        date = ""
        if inner is not None:
            message = _safe_str(getattr(inner, "message", ""))
            author_obj = getattr(inner, "author", None)
            if author_obj is not None:
                author = _safe_str(getattr(author_obj, "name", ""))
                date = _iso(getattr(author_obj, "date", None))
        stats = getattr(row, "stats", None)
        additions = int(getattr(stats, "additions", 0) or 0) if stats is not None else 0
        deletions = int(getattr(stats, "deletions", 0) or 0) if stats is not None else 0
        files = getattr(row, "files", None)
        files_changed = len(files) if files is not None else 0
        url = _safe_str(getattr(row, "html_url", ""))
        return GitHubCommit(
            sha=sha,
            short_sha=sha[:7],
            message=message,
            author=author,
            date=date,
            url=url,
            additions=additions,
            deletions=deletions,
            files_changed=files_changed,
        )

    def compare_branches(
        self,
        full_name: str,
        base: str,
        head: str,
        *,
        limit: int = DEFAULT_PAGE_LIMIT,
    ) -> GitHubBranchComparison:
        """Ahead/behind counts, the commits between *base* and *head*, and
        the changed files -- GHManage's "Compare Branches" (Ctrl+Shift+B).
        The mapping itself lives in :mod:`quill.core.github.branch_compare`
        (split out to keep this module under its GATE-11 size budget)."""
        repo = self._repo(full_name)
        try:
            return fetch_branch_comparison(
                repo,
                base,
                head,
                map_commit=lambda row: self._map_commit(row, repo),
                take=_take,
                limit=limit,
            )
        except Exception as exc:  # noqa: BLE001
            raise GitHubItemsError(f"Could not compare {base!r}...{head!r}: {exc}") from exc

    # ------------------------------------------------------------------
    # Tags, releases, workflow runs

    def fetch_tags(
        self,
        full_name: str,
        *,
        limit: int = DEFAULT_PAGE_LIMIT,
    ) -> list[GitHubTag]:
        repo = self._repo(full_name)
        try:
            rows = _take(repo.get_tags(), limit)
        except Exception as exc:  # noqa: BLE001
            raise GitHubItemsError(f"Could not list tags: {exc}") from exc
        out: list[GitHubTag] = []
        for row in rows:
            commit = getattr(row, "commit", None)
            commit_sha = _safe_str(getattr(commit, "sha", "")) if commit is not None else ""
            name = _safe_str(getattr(row, "name", ""))
            repo_url = _safe_str(getattr(repo, "html_url", ""))
            out.append(
                GitHubTag(
                    name=name,
                    commit_sha=commit_sha,
                    url=f"{repo_url}/releases/tag/{name}" if repo_url else "",
                )
            )
        return out

    def fetch_releases(
        self,
        full_name: str,
        *,
        limit: int = DEFAULT_PAGE_LIMIT,
    ) -> list[GitHubRelease]:
        repo = self._repo(full_name)
        try:
            rows = _take(repo.get_releases(), limit)
        except Exception as exc:  # noqa: BLE001
            raise GitHubItemsError(f"Could not list releases: {exc}") from exc
        out: list[GitHubRelease] = []
        for row in rows:
            out.append(
                GitHubRelease(
                    tag=_safe_str(getattr(row, "tag_name", "")),
                    name=_safe_str(getattr(row, "title", "") or getattr(row, "name", "")),
                    draft=bool(getattr(row, "draft", False)),
                    prerelease=bool(getattr(row, "prerelease", False)),
                    created_at=_iso(getattr(row, "created_at", None)),
                    url=_safe_str(getattr(row, "html_url", "")),
                    body=_safe_str(getattr(row, "body", "")),
                )
            )
        return out

    def fetch_workflow_runs(
        self,
        full_name: str,
        *,
        limit: int = DEFAULT_PAGE_LIMIT,
    ) -> list[GitHubWorkflowRun]:
        repo = self._repo(full_name)
        try:
            rows = _take(repo.get_workflow_runs(), limit)
        except Exception as exc:  # noqa: BLE001
            raise GitHubItemsError(f"Could not list workflow runs: {exc}") from exc
        out: list[GitHubWorkflowRun] = []
        for row in rows:
            out.append(
                GitHubWorkflowRun(
                    name=_safe_str(getattr(row, "name", "")),
                    status=_safe_str(getattr(row, "status", "")),
                    conclusion=_safe_str(getattr(row, "conclusion", "")),
                    branch=_safe_str(getattr(row, "head_branch", "")),
                    event=_safe_str(getattr(row, "event", "")),
                    created_at=_iso(getattr(row, "created_at", None)),
                    url=_safe_str(getattr(row, "html_url", "")),
                    run_number=int(getattr(row, "run_number", 0) or 0),
                )
            )
        return out

    def fetch_workflows(
        self, full_name: str, *, limit: int = DEFAULT_PAGE_LIMIT
    ) -> list[GitHubWorkflow]:
        """Workflow *definitions* (not runs) -- GHManage's Workflows view.
        Mapping lives in :mod:`quill.core.github.workflows` (GATE-11)."""
        repo = self._repo(full_name)
        try:
            return list_workflows(repo, limit=limit, take=_take)
        except Exception as exc:  # noqa: BLE001
            raise GitHubItemsError(f"Could not list workflows: {exc}") from exc

    # ------------------------------------------------------------------
    # Detail (a single item with its comment thread for the details pane)

    def fetch_pull_diff(self, full_name: str, number: int) -> GitHubPullDiff:
        """The changed-file inventory for PR *number* (the diff viewer's model).

        Carries base/head refs and shas so file *content* can be fetched at
        both sides and run through QUILL's own compare engine — an accessible
        difference walk instead of a raw unified patch.
        """
        repo = self._repo(full_name)
        try:
            pull = repo.get_pull(number)
            rows = _take(pull.get_files(), 300)
        except Exception as exc:  # noqa: BLE001 - surface as a coded error
            raise GitHubItemsError(f"Could not load the pull request's files: {exc}") from exc
        files = tuple(
            GitHubPullFile(
                filename=_safe_str(getattr(row, "filename", "")),
                status=_safe_str(getattr(row, "status", "")),
                additions=int(getattr(row, "additions", 0) or 0),
                deletions=int(getattr(row, "deletions", 0) or 0),
                changes=int(getattr(row, "changes", 0) or 0),
                previous_filename=_safe_str(getattr(row, "previous_filename", "") or ""),
                patch=_safe_str(getattr(row, "patch", "") or ""),
            )
            for row in rows
        )
        base = getattr(pull, "base", None)
        head = getattr(pull, "head", None)
        return GitHubPullDiff(
            number=number,
            title=_safe_str(getattr(pull, "title", "")),
            base_ref=_safe_str(getattr(base, "ref", "")) if base is not None else "",
            base_sha=_safe_str(getattr(base, "sha", "")) if base is not None else "",
            head_ref=_safe_str(getattr(head, "ref", "")) if head is not None else "",
            head_sha=_safe_str(getattr(head, "sha", "")) if head is not None else "",
            files=files,
        )

    def fetch_file_text(self, full_name: str, path: str, ref: str) -> str:
        """A file's text content at *ref*, for the compare engine's two sides.

        Returns ``""`` for a file that does not exist at that ref (an added
        file has no base side; a deleted file has no head side) and raises a
        clear coded error for binary or over-1MB content the API cannot
        deliver.
        """
        repo = self._repo(full_name)
        gh = _get_gh_module()
        try:
            blob = repo.get_contents(path, ref=ref)
        except gh.GithubException as exc:
            if getattr(exc, "status", None) == 404:
                return ""
            raise GitHubItemsError(f"Could not fetch {path} at {ref[:12]}: {exc}") from exc
        except Exception as exc:  # noqa: BLE001
            raise GitHubItemsError(f"Could not fetch {path} at {ref[:12]}: {exc}") from exc
        try:
            data = blob.decoded_content
        except Exception as exc:  # noqa: BLE001 - >1MB or submodule content
            raise GitHubItemsError(
                f"{path} cannot be compared here (binary or over GitHub's 1 MB "
                f"content limit): {exc}"
            ) from exc
        try:
            return bytes(data).decode("utf-8")
        except (UnicodeDecodeError, TypeError) as exc:
            raise GitHubItemsError(f"{path} is not a text file (binary content).") from exc

    def update_items(
        self,
        full_name: str,
        numbers: Sequence[int],
        *,
        state: str | None = None,
        add_labels: Sequence[str] = (),
    ) -> list[str]:
        """Apply a batch change to issues/PRs; returns per-item error strings.

        The one deliberate exception to the viewer's read-only rule (Unified
        GitHub Management "Batch Operations"), and still tightly scoped:
        close/reopen (``state``) and adding labels — no deletions, no content
        edits. Requires an authenticated session (the anonymous viewer stays
        fully read-only), and the UI gates every call behind an explicit
        consent dialog naming the exact items. Failures are collected
        per-item so one bad number never aborts the rest.
        """
        if not self._token:
            raise GitHubItemsError(
                "Batch changes need a signed-in GitHub account; the anonymous viewer is read-only."
            )
        if state not in (None, "open", "closed"):
            raise GitHubItemsError(f"Unknown state {state!r}; use open or closed.")
        repo = self._repo(full_name)
        errors: list[str] = []
        for number in numbers:
            try:
                issue = repo.get_issue(number=int(number))
                if state is not None:
                    issue.edit(state=state)
                if add_labels:
                    issue.add_to_labels(*[str(label) for label in add_labels])
            except Exception as exc:  # noqa: BLE001 - collect, keep going
                errors.append(f"#{number}: {exc}")
        return errors

    def search_items(
        self,
        full_name: str,
        query: str,
        *,
        limit: int = DEFAULT_PAGE_LIMIT,
    ) -> list[GitHubItem]:
        """Full GitHub search syntax over one repository's issues and PRs.

        The Unified GitHub Management review's "Advanced Filtering" item:
        *query* is passed to GitHub's issue search verbatim — labels
        (``label:bug``), authors (``author:x``), text, ``is:pr``,
        ``no:assignee``, date ranges, everything the syntax supports — with a
        ``repo:`` qualifier pinned in front so results never leave the loaded
        repository. Search API results are issue-shaped for both issues and
        PRs (the ``pull_request`` link distinguishes them), matching
        ``_map_issue``'s dual handling.
        """
        text = query.strip()
        if not text:
            return []
        try:
            rows = _take(self._gh.search_issues(f"repo:{full_name} {text}"), limit)
        except Exception as exc:  # noqa: BLE001 - surface as a coded error
            raise GitHubItemsError(
                f"Search failed: {exc}. Check the GitHub search syntax."
            ) from exc
        return [self._map_issue(row, is_pr=False) for row in rows]

    def fetch_issue_comments(self, full_name: str, number: int) -> list[dict[str, str]]:
        """Return the comment thread on an issue/PR as plain dicts.

        Each dict has ``id``, ``author``, ``created_at``, and ``body``. Used
        by the details pane; the list view only carries the comment count.
        ``id`` is the comment's numeric GitHub id (as a string), needed by
        :meth:`edit_comment` and :meth:`delete_comment` to address a specific
        comment in the thread.
        """
        repo = self._repo(full_name)
        try:
            issue = repo.get_issue(number=number)
            comments = _take(issue.get_comments(), DEFAULT_PAGE_LIMIT)
        except Exception as exc:  # noqa: BLE001
            raise GitHubItemsError(f"Could not load comments: {exc}") from exc
        out: list[dict[str, str]] = []
        for comment in comments:
            out.append({
                "id": _safe_str(getattr(comment, "id", "")),
                "author": _login_of(getattr(comment, "user", None)),
                "created_at": _iso(getattr(comment, "created_at", None)),
                "body": _safe_str(getattr(comment, "body", "")),
            })
        return out

    # ------------------------------------------------------------------
    # Creating issues, pull requests, and comments — and merging/re-running

    def create_issue(
        self,
        full_name: str,
        title: str,
        body: str = "",
    ) -> GitHubItem:
        """File a new issue. Requires an authenticated session."""
        self._require_write_access("create an issue")
        repo = self._repo(full_name)
        try:
            row = repo.create_issue(title=title, body=body)
        except Exception as exc:  # noqa: BLE001
            raise GitHubItemsError(f"Could not create issue: {exc}") from exc
        return self._map_issue(row, is_pr=False)

    def create_pull_request(
        self,
        full_name: str,
        title: str,
        body: str,
        head: str,
        base: str,
    ) -> GitHubItem:
        """Open a new pull request from *head* into *base*."""
        self._require_write_access("open a pull request")
        repo = self._repo(full_name)
        try:
            row = repo.create_pull(title=title, body=body, head=head, base=base)
        except Exception as exc:  # noqa: BLE001
            raise GitHubItemsError(f"Could not open pull request: {exc}") from exc
        return self._map_issue(row, is_pr=True)

    def merge_pull_request(
        self,
        full_name: str,
        number: int,
        *,
        merge_method: str = "squash",
        commit_title: str = "",
        commit_message: str = "",
    ) -> str:
        """Merge pull request *number*. Returns the merge commit SHA.

        Raises :class:`GitHubItemsError` if the PR is not mergeable (merge
        conflicts, failing required checks, or already merged/closed) —
        GitHub reports this as the merge call itself failing rather than as
        a distinct pre-check, so this call surfaces whatever reason GitHub
        gives verbatim.
        """
        if merge_method not in ("merge", "squash", "rebase"):
            raise GitHubItemsError(f"Unknown merge method {merge_method!r}.")
        self._require_write_access("merge a pull request")
        repo = self._repo(full_name)
        try:
            pull = repo.get_pull(number)
            result = pull.merge(
                merge_method=merge_method,
                commit_title=commit_title or None,
                commit_message=commit_message or None,
            )
        except Exception as exc:  # noqa: BLE001
            raise GitHubItemsError(f"Could not merge #{number}: {exc}") from exc
        if not getattr(result, "merged", False):
            raise GitHubItemsError(
                f"GitHub declined to merge #{number}: "
                f"{_safe_str(getattr(result, 'message', 'not mergeable'))}"
            )
        return _safe_str(getattr(result, "sha", ""))

    def rerun_workflow_run(self, full_name: str, run_id: int) -> None:
        """Re-run a completed (or failed) GitHub Actions workflow run."""
        self._require_write_access("re-run a workflow")
        repo = self._repo(full_name)
        try:
            run = repo.get_workflow_run(run_id)
            run.rerun()
        except Exception as exc:  # noqa: BLE001
            raise GitHubItemsError(f"Could not re-run workflow run {run_id}: {exc}") from exc

    def fetch_workflow_jobs(self, full_name: str, run_id: int) -> list[GitHubWorkflowJob]:
        """Per-job status for a workflow run -- read-only, no token required."""
        repo = self._repo(full_name)
        try:
            run = repo.get_workflow_run(run_id)
            rows = _take(run.jobs(), DEFAULT_PAGE_LIMIT)
        except Exception as exc:  # noqa: BLE001
            raise GitHubItemsError(f"Could not list jobs for run {run_id}: {exc}") from exc
        return [
            GitHubWorkflowJob(
                name=_safe_str(getattr(row, "name", "")),
                status=_safe_str(getattr(row, "status", "")),
                conclusion=_safe_str(getattr(row, "conclusion", "")),
                started_at=_iso(getattr(row, "started_at", None)),
                completed_at=_iso(getattr(row, "completed_at", None)),
                url=_safe_str(getattr(row, "html_url", "")),
            )
            for row in rows
        ]

    def fetch_workflow_run_artifacts(self, full_name: str, run_id: int) -> list[GitHubArtifact]:
        """A run's build artifacts -- read-only, no token required for a
        public repo (a private repo needs one, same as everything else here)."""
        repo = self._repo(full_name)
        try:
            run = repo.get_workflow_run(run_id)
            rows = _take(run.get_artifacts(), DEFAULT_PAGE_LIMIT)
        except Exception as exc:  # noqa: BLE001
            raise GitHubItemsError(f"Could not list artifacts for run {run_id}: {exc}") from exc
        return [
            GitHubArtifact(
                id=int(getattr(row, "id", 0)),
                name=_safe_str(getattr(row, "name", "")),
                size_bytes=int(getattr(row, "size_in_bytes", 0) or 0),
                expired=bool(getattr(row, "expired", False)),
                archive_download_url=_safe_str(getattr(row, "archive_download_url", "")),
            )
            for row in rows
        ]

    def download_artifact_to_file(
        self,
        artifact: GitHubArtifact,
        dest_path: Path,
        *,
        progress: Callable[[int, int], None] | None = None,
        should_cancel: Callable[[], bool] | None = None,
    ) -> Path:
        """Stream *artifact* to *dest_path* (a zip; GitHub always packages
        artifacts that way), calling ``progress(downloaded_bytes, total_bytes)``
        as it goes. Raises :class:`GitHubItemsError` for an expired artifact,
        a missing token, or any download failure.

        GitHub's artifact endpoint 302-redirects to a short-lived signed URL
        on a *different* host (typically Azure Blob Storage) -- the
        ``Authorization`` header must never be forwarded there, or the token
        leaks to a third party. ``urllib`` does not strip it automatically on
        a cross-host redirect the way ``requests`` does, so the redirect is
        followed manually here with the header dropped for the second
        request, rather than relying on default redirect-following behavior
        or reaching into PyGithub's private ``Requester`` internals.
        """
        if artifact.expired:
            raise GitHubItemsError(
                f"Artifact {artifact.name!r} has expired and cannot be downloaded."
            )
        if not self._token:
            raise GitHubItemsError("Downloading an artifact needs a signed-in GitHub account.")
        if not artifact.archive_download_url.lower().startswith("https://"):
            raise GitHubItemsError("Refusing a non-HTTPS artifact download URL.")

        request = urllib.request.Request(
            artifact.archive_download_url,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )

        class _NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *_args: object, **_kwargs: object) -> None:
                return None  # signal the opener: do not auto-follow

        opener = urllib.request.build_opener(_NoRedirect)
        try:
            final_request = request
            try:
                probe = opener.open(request, timeout=60)  # noqa: S310 - HTTPS enforced above
            except urllib.error.HTTPError as exc:
                if exc.code in (301, 302, 303, 307, 308):
                    location = exc.headers.get("Location", "")
                    if not location.lower().startswith("https://"):
                        raise GitHubItemsError("Artifact redirect target was not HTTPS.") from exc
                    # Deliberately no Authorization header on the redirect target.
                    final_request = urllib.request.Request(location)
                    probe = urllib.request.urlopen(final_request, timeout=60)  # noqa: S310
                else:
                    raise GitHubItemsError(f"Could not download artifact: {exc}") from exc
            with probe as response:
                total = int(response.headers.get("Content-Length") or artifact.size_bytes or 0)
                downloaded = 0
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                with dest_path.open("wb") as out:
                    while True:
                        if should_cancel is not None and should_cancel():
                            raise GitHubItemsError("Download cancelled.")
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        out.write(chunk)
                        downloaded += len(chunk)
                        if progress is not None:
                            progress(downloaded, total)
        except GitHubItemsError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise GitHubItemsError(f"Could not download artifact {artifact.name!r}: {exc}") from exc
        return dest_path

    def dispatch_workflow(
        self,
        full_name: str,
        workflow_id: str,
        ref: str,
        *,
        inputs: dict[str, str] | None = None,
    ) -> None:
        """Trigger a ``workflow_dispatch`` run. *workflow_id* is the workflow
        file name (e.g. ``"ci.yml"``) or its numeric id."""
        self._require_write_access("dispatch a workflow")
        repo = self._repo(full_name)
        try:
            workflow = repo.get_workflow(workflow_id)
            ok = workflow.create_dispatch(ref, inputs=inputs or {})
        except Exception as exc:  # noqa: BLE001
            raise GitHubItemsError(f"Could not dispatch workflow {workflow_id}: {exc}") from exc
        if not ok:
            raise GitHubItemsError(
                f"GitHub declined to dispatch {workflow_id} on {ref!r} "
                "(check that the workflow accepts workflow_dispatch)."
            )

    def fetch_notifications(self, *, limit: int = DEFAULT_PAGE_LIMIT) -> list[GitHubNotification]:
        """The authenticated account's GitHub notifications inbox, across
        every repository -- a real inbox, not scoped to one repo. Mapping
        lives in :mod:`quill.core.github.notifications` (GATE-11)."""
        self._require_write_access("read notifications")
        try:
            return list_notifications(self._gh, limit=limit, take=_take)
        except Exception as exc:  # noqa: BLE001
            raise GitHubItemsError(f"Could not list notifications: {exc}") from exc

    def mark_notification_read(self, notification_id: str) -> None:
        self._require_write_access("mark a notification as read")
        try:
            _mark_notification_read_raw(self._gh, notification_id)
        except Exception as exc:  # noqa: BLE001
            raise GitHubItemsError(f"Could not mark notification as read: {exc}") from exc

    def fetch_security_alerts(
        self, full_name: str, *, limit: int = DEFAULT_PAGE_LIMIT
    ) -> list[GitHubSecurityAlert]:
        """Open Dependabot security alerts for a repository. Mapping lives in
        :mod:`quill.core.github.notifications` (GATE-11)."""
        repo = self._repo(full_name)
        try:
            return list_security_alerts(repo, limit=limit, take=_take)
        except Exception as exc:  # noqa: BLE001
            raise GitHubItemsError(f"Could not list security alerts: {exc}") from exc

    def create_comment(self, full_name: str, number: int, body: str) -> dict[str, str]:
        """Post a comment on issue/PR *number* (also used to reply — GitHub's
        comment thread is flat, so a reply is simply another comment)."""
        self._require_write_access("post a comment")
        repo = self._repo(full_name)
        try:
            issue = repo.get_issue(number=number)
            comment = issue.create_comment(body)
        except Exception as exc:  # noqa: BLE001
            raise GitHubItemsError(f"Could not post comment: {exc}") from exc
        return {
            "id": _safe_str(getattr(comment, "id", "")),
            "author": _login_of(getattr(comment, "user", None)),
            "created_at": _iso(getattr(comment, "created_at", None)),
            "body": _safe_str(getattr(comment, "body", "")),
        }

    def edit_comment(self, full_name: str, comment_id: int, body: str) -> dict[str, str]:
        """Edit an existing comment. GitHub allows this only for its author."""
        self._require_write_access("edit a comment")
        repo = self._repo(full_name)
        try:
            comment = repo.get_issue_comment(comment_id)
            comment.edit(body)
        except Exception as exc:  # noqa: BLE001
            raise GitHubItemsError(f"Could not edit comment: {exc}") from exc
        return {
            "id": _safe_str(getattr(comment, "id", "")),
            "author": _login_of(getattr(comment, "user", None)),
            "created_at": _iso(getattr(comment, "created_at", None)),
            "body": _safe_str(getattr(comment, "body", "")),
        }

    def delete_comment(self, full_name: str, comment_id: int) -> None:
        """Delete a comment. GitHub allows this only for its author (or an
        admin); a non-owner's attempt surfaces GitHub's 403 verbatim."""
        self._require_write_access("delete a comment")
        repo = self._repo(full_name)
        try:
            comment = repo.get_issue_comment(comment_id)
            comment.delete()
        except Exception as exc:  # noqa: BLE001
            raise GitHubItemsError(f"Could not delete comment: {exc}") from exc

    def _require_write_access(self, action: str) -> None:
        if not self._token:
            raise GitHubItemsError(
                f"To {action} you need a signed-in GitHub account; "
                "the anonymous viewer is read-only."
            )

    def close(self) -> None:
        """Release the underlying GitHub session."""
        try:
            self._gh.close()
        except Exception:  # noqa: BLE001
            pass


__all__ = [
    "DEFAULT_PAGE_LIMIT",
    "GitHubBranch",
    "GitHubBranchComparison",
    "GitHubCommit",
    "GitHubItem",
    "GitHubItemsError",
    "GitHubItemsProvider",
    "GitHubNotification",
    "GitHubRelease",
    "GitHubSecurityAlert",
    "GitHubTag",
    "GitHubWorkflow",
    "GitHubWorkflowJob",
    "GitHubWorkflowRun",
    "refuse_in_safe_mode",
    "require_pygithub",
]
