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

No ``wx`` imports. No direct ``urlopen``/``urlretrieve`` -- every call goes
through PyGithub, which is the single audited transport for GitHub (see
``quill/tools/network_egress_audit.py``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from quill.core.error_codes import CodedError
from quill.core.github.github_provider import _get_gh_module, require_pygithub

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

    # ------------------------------------------------------------------
    # Detail (a single item with its comment thread for the details pane)

    def fetch_issue_comments(self, full_name: str, number: int) -> list[dict[str, str]]:
        """Return the comment thread on an issue/PR as plain dicts.

        Each dict has ``author``, ``created_at``, and ``body``. Used by the
        details pane; the list view only carries the comment count.
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
                "author": _login_of(getattr(comment, "user", None)),
                "created_at": _iso(getattr(comment, "created_at", None)),
                "body": _safe_str(getattr(comment, "body", "")),
            })
        return out

    def close(self) -> None:
        """Release the underlying GitHub session."""
        try:
            self._gh.close()
        except Exception:  # noqa: BLE001
            pass


__all__ = [
    "DEFAULT_PAGE_LIMIT",
    "GitHubBranch",
    "GitHubCommit",
    "GitHubItem",
    "GitHubItemsError",
    "GitHubItemsProvider",
    "GitHubRelease",
    "GitHubTag",
    "GitHubWorkflowRun",
    "refuse_in_safe_mode",
    "require_pygithub",
]
