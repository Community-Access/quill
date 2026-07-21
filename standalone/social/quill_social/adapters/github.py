"""GitHub as a read/act surface (PRD 24.1, 24.2).

GitHub is not a microblog; it is a project-collaboration surface QUILL reads and
acts on -- notifications, issues, pull requests, discussions, and releases. This
module follows the same honest-boundary pattern as the Mastodon and Bluesky
adapters (PRD 6.3, 29.1): a stable dataclass contract plus the exact point where
the live GitHub client is required, rather than a half-working live client.

``GitHubAdapter`` implements :class:`GitHubSurface` and raises a clear
:class:`~quill_social.adapters.base.AdapterError` (``kind="permission"``) for
every network method until the live client is wired and an account with
least-privilege scopes (PRD 31.1) is connected. ``available()`` reports whether
a GitHub client library is importable. ``MockGitHub`` is a deterministic,
credential-free subclass -- the reference content the app reads out of the box,
mirroring ``adapters/mock.py``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from quill_social.adapters.base import AdapterError

_NOT_ENABLED = (
    "live GitHub not enabled: install the 'github' extra and connect an account "
    "with least-privilege scopes to read and act on GitHub."
)


# -- dataclasses --------------------------------------------------------------


@dataclass
class GitHubIssue:
    """A GitHub issue (PRD 24.1)."""

    id: str = ""
    repo: str = ""
    number: int = 0
    title: str = ""
    body: str = ""
    state: str = "open"
    labels: list[str] = field(default_factory=list)
    author: str = ""
    url: str = ""
    updated: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "repo": self.repo,
            "number": self.number,
            "title": self.title,
            "body": self.body,
            "state": self.state,
            "labels": list(self.labels),
            "author": self.author,
            "url": self.url,
            "updated": self.updated,
        }

    @classmethod
    def from_dict(cls, d: dict) -> GitHubIssue:
        return cls(
            id=d.get("id", ""),
            repo=d.get("repo", ""),
            number=int(d.get("number", 0) or 0),
            title=d.get("title", ""),
            body=d.get("body", ""),
            state=d.get("state", "open"),
            labels=list(d.get("labels", [])),
            author=d.get("author", ""),
            url=d.get("url", ""),
            updated=int(d.get("updated", 0) or 0),
        )


@dataclass
class GitHubPullRequest:
    """A GitHub pull request (PRD 24.1, 24.4)."""

    id: str = ""
    repo: str = ""
    number: int = 0
    title: str = ""
    body: str = ""
    state: str = "open"  # open | closed | merged
    labels: list[str] = field(default_factory=list)
    author: str = ""
    url: str = ""
    updated: int = 0

    @property
    def merged(self) -> bool:
        return self.state == "merged"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "repo": self.repo,
            "number": self.number,
            "title": self.title,
            "body": self.body,
            "state": self.state,
            "labels": list(self.labels),
            "author": self.author,
            "url": self.url,
            "updated": self.updated,
        }

    @classmethod
    def from_dict(cls, d: dict) -> GitHubPullRequest:
        return cls(
            id=d.get("id", ""),
            repo=d.get("repo", ""),
            number=int(d.get("number", 0) or 0),
            title=d.get("title", ""),
            body=d.get("body", ""),
            state=d.get("state", "open"),
            labels=list(d.get("labels", [])),
            author=d.get("author", ""),
            url=d.get("url", ""),
            updated=int(d.get("updated", 0) or 0),
        )


@dataclass
class GitHubDiscussion:
    """A GitHub discussion thread (PRD 24.1, 24.4)."""

    id: str = ""
    repo: str = ""
    number: int = 0
    title: str = ""
    body: str = ""
    state: str = "open"
    labels: list[str] = field(default_factory=list)
    author: str = ""
    url: str = ""
    updated: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "repo": self.repo,
            "number": self.number,
            "title": self.title,
            "body": self.body,
            "state": self.state,
            "labels": list(self.labels),
            "author": self.author,
            "url": self.url,
            "updated": self.updated,
        }

    @classmethod
    def from_dict(cls, d: dict) -> GitHubDiscussion:
        return cls(
            id=d.get("id", ""),
            repo=d.get("repo", ""),
            number=int(d.get("number", 0) or 0),
            title=d.get("title", ""),
            body=d.get("body", ""),
            state=d.get("state", "open"),
            labels=list(d.get("labels", [])),
            author=d.get("author", ""),
            url=d.get("url", ""),
            updated=int(d.get("updated", 0) or 0),
        )


@dataclass
class GitHubNotification:
    """A GitHub notification (PRD 24.1). ``state`` carries the notify reason."""

    id: str = ""
    repo: str = ""
    number: int = 0
    title: str = ""
    body: str = ""
    state: str = "unread"  # unread | read; reason lives in ``reason``
    labels: list[str] = field(default_factory=list)
    author: str = ""
    url: str = ""
    updated: int = 0
    reason: str = ""  # mention | assign | review_requested | subscribed | ...

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "repo": self.repo,
            "number": self.number,
            "title": self.title,
            "body": self.body,
            "state": self.state,
            "labels": list(self.labels),
            "author": self.author,
            "url": self.url,
            "updated": self.updated,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, d: dict) -> GitHubNotification:
        return cls(
            id=d.get("id", ""),
            repo=d.get("repo", ""),
            number=int(d.get("number", 0) or 0),
            title=d.get("title", ""),
            body=d.get("body", ""),
            state=d.get("state", "unread"),
            labels=list(d.get("labels", [])),
            author=d.get("author", ""),
            url=d.get("url", ""),
            updated=int(d.get("updated", 0) or 0),
            reason=d.get("reason", ""),
        )


@dataclass
class GitHubRelease:
    """A GitHub release (PRD 24.1, 24.4). ``title`` is the release name/tag."""

    id: str = ""
    repo: str = ""
    number: int = 0
    title: str = ""
    body: str = ""
    state: str = "published"  # draft | published | prerelease
    labels: list[str] = field(default_factory=list)
    author: str = ""
    url: str = ""
    updated: int = 0
    tag: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "repo": self.repo,
            "number": self.number,
            "title": self.title,
            "body": self.body,
            "state": self.state,
            "labels": list(self.labels),
            "author": self.author,
            "url": self.url,
            "updated": self.updated,
            "tag": self.tag,
        }

    @classmethod
    def from_dict(cls, d: dict) -> GitHubRelease:
        return cls(
            id=d.get("id", ""),
            repo=d.get("repo", ""),
            number=int(d.get("number", 0) or 0),
            title=d.get("title", ""),
            body=d.get("body", ""),
            state=d.get("state", "published"),
            labels=list(d.get("labels", [])),
            author=d.get("author", ""),
            url=d.get("url", ""),
            updated=int(d.get("updated", 0) or 0),
            tag=d.get("tag", ""),
        )


# -- response -> model mapping ------------------------------------------------
#
# These consume PyGithub objects (attribute access), so they are testable with
# lightweight fakes (e.g. ``types.SimpleNamespace``) without a live client.


def _to_ms(value: Any) -> int:
    """Normalize a PyGithub timestamp (datetime | ISO string | epoch) to ms."""
    if value is None or isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, datetime):
        dt = value if value.tzinfo else value.replace(tzinfo=UTC)
        return int(dt.timestamp() * 1000)
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return 0
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return 0
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return int(dt.timestamp() * 1000)
    return 0


def _label_names(obj: Any) -> list[str]:
    out: list[str] = []
    for lbl in getattr(obj, "labels", None) or []:
        name = getattr(lbl, "name", None)
        out.append(name if name is not None else str(lbl))
    return out


def _login(obj: Any) -> str:
    user = getattr(obj, "user", None)
    login = getattr(user, "login", None) if user is not None else None
    return f"@{login}" if login else ""


def _issue_to_model(issue: Any, repo: str) -> GitHubIssue:
    return GitHubIssue(
        id=str(getattr(issue, "id", "") or ""),
        repo=repo,
        number=int(getattr(issue, "number", 0) or 0),
        title=getattr(issue, "title", "") or "",
        body=getattr(issue, "body", "") or "",
        state=getattr(issue, "state", "open") or "open",
        labels=_label_names(issue),
        author=_login(issue),
        url=getattr(issue, "html_url", "") or "",
        updated=_to_ms(getattr(issue, "updated_at", None)),
    )


def _pr_to_model(pr: Any, repo: str) -> GitHubPullRequest:
    state = "merged" if getattr(pr, "merged", False) else (getattr(pr, "state", "open") or "open")
    return GitHubPullRequest(
        id=str(getattr(pr, "id", "") or ""),
        repo=repo,
        number=int(getattr(pr, "number", 0) or 0),
        title=getattr(pr, "title", "") or "",
        body=getattr(pr, "body", "") or "",
        state=state,
        labels=_label_names(pr),
        author=_login(pr),
        url=getattr(pr, "html_url", "") or "",
        updated=_to_ms(getattr(pr, "updated_at", None)),
    )


def _discussion_to_model(disc: Any, repo: str) -> GitHubDiscussion:
    return GitHubDiscussion(
        id=str(getattr(disc, "id", "") or ""),
        repo=repo,
        number=int(getattr(disc, "number", 0) or 0),
        title=getattr(disc, "title", "") or "",
        body=getattr(disc, "body", "") or "",
        state=getattr(disc, "state", "open") or "open",
        labels=_label_names(disc),
        author=_login(disc),
        url=getattr(disc, "html_url", "") or "",
        updated=_to_ms(getattr(disc, "updated_at", None)),
    )


def _release_to_model(rel: Any, repo: str) -> GitHubRelease:
    if getattr(rel, "draft", False):
        state = "draft"
    elif getattr(rel, "prerelease", False):
        state = "prerelease"
    else:
        state = "published"
    return GitHubRelease(
        id=str(getattr(rel, "id", "") or ""),
        repo=repo,
        title=getattr(rel, "title", None) or getattr(rel, "tag_name", "") or "",
        body=getattr(rel, "body", "") or "",
        state=state,
        author=_login(rel),
        url=getattr(rel, "html_url", "") or "",
        updated=_to_ms(getattr(rel, "published_at", None) or getattr(rel, "created_at", None)),
        tag=getattr(rel, "tag_name", "") or "",
    )


def _notification_to_model(note: Any) -> GitHubNotification:
    subject = getattr(note, "subject", None)
    repository = getattr(note, "repository", None)
    return GitHubNotification(
        id=str(getattr(note, "id", "") or ""),
        repo=(getattr(repository, "full_name", "") or "") if repository is not None else "",
        title=(getattr(subject, "title", "") or "") if subject is not None else "",
        state="unread" if getattr(note, "unread", True) else "read",
        url=(getattr(subject, "url", "") or "") if subject is not None else "",
        updated=_to_ms(getattr(note, "updated_at", None)),
        reason=getattr(note, "reason", "") or "",
    )


def _github_error(exc: Exception) -> AdapterError:
    """Normalize a PyGithub exception into an :class:`AdapterError`."""
    if isinstance(exc, AdapterError):
        return exc
    name = type(exc).__name__
    status = getattr(exc, "status", None)
    msg = str(exc) or "github error"
    if name == "RateLimitExceededException" or status == 429:
        headers = getattr(exc, "headers", None) or {}
        retry = None
        reset = headers.get("retry-after") or headers.get("Retry-After")
        if reset is not None:
            try:
                retry = int(reset) * 1000
            except (TypeError, ValueError):
                retry = None
        return AdapterError(msg, kind="transient", retry_after_ms=retry or 60_000)
    if name == "BadCredentialsException" or status in (401, 403):
        return AdapterError(msg, kind="permission")
    if name in ("UnknownObjectException", "BadRequestException") or status in (400, 404, 422):
        return AdapterError(msg, kind="validation")
    return AdapterError(msg, kind="unknown")


# -- the surface interface ----------------------------------------------------


class GitHubSurface(ABC):
    """The read/act contract every GitHub backend implements (PRD 24.1, 24.2)."""

    #: stable network id, matching quill_social.model.NETWORKS
    name: str = "github"

    @abstractmethod
    def notifications(self) -> list[GitHubNotification]:
        """Unread and subscribed notifications, newest first."""

    @abstractmethod
    def issues(self, repo: str) -> list[GitHubIssue]:
        """Open issues for ``repo`` (``owner/name``)."""

    @abstractmethod
    def pull_requests(self, repo: str) -> list[GitHubPullRequest]:
        """Pull requests for ``repo``."""

    @abstractmethod
    def discussions(self, repo: str) -> list[GitHubDiscussion]:
        """Discussions for ``repo``."""

    @abstractmethod
    def releases(self, repo: str) -> list[GitHubRelease]:
        """Releases for ``repo``, newest first."""

    @abstractmethod
    def create_issue(
        self, repo: str, title: str, body: str = "", labels: list[str] | None = None
    ) -> GitHubIssue:
        """Create an issue where permission allows (PRD 24.2)."""

    @abstractmethod
    def comment(self, repo: str, number: int, body: str) -> GitHubIssue:
        """Comment on an issue/PR/discussion; returns the refreshed target."""

    @classmethod
    def available(cls) -> bool:
        """Whether a GitHub client library is importable in this build."""
        try:
            import github  # noqa: F401  (PyGithub, installed via the 'github' extra)
        except ImportError:
            return False
        return True


class GitHubAdapter(GitHubSurface):
    """The live surface boundary.

    Every network method raises an :class:`AdapterError` (``kind="permission"``)
    until the live client is wired and an account is connected with the required
    scopes. The token is resolved from the OS credential store (PRD 31.1) and is
    never logged or stored raw.
    """

    name = "github"

    def __init__(
        self,
        *,
        token_ref: str = "",
        api_base: str = "https://api.github.com",
        client: Any = None,
    ) -> None:
        self.token_ref = token_ref  # a reference/handle, never the raw token (PRD 31.1)
        self.api_base = api_base
        self._client = client  # a live github.Github or an injected fake

    def _require_client(self) -> Any:
        if self._client is None:
            raise AdapterError(_NOT_ENABLED, kind="permission")
        return self._client

    def notifications(self) -> list[GitHubNotification]:
        client = self._require_client()
        try:
            notes = client.get_user().get_notifications()
            return [_notification_to_model(n) for n in notes]
        except Exception as exc:  # noqa: BLE001 -- normalized below
            raise _github_error(exc) from exc

    def issues(self, repo: str) -> list[GitHubIssue]:
        client = self._require_client()
        try:
            repo_obj = client.get_repo(repo)
            return [
                _issue_to_model(i, repo)
                for i in repo_obj.get_issues(state="open")
                if getattr(i, "pull_request", None) is None
            ]
        except Exception as exc:  # noqa: BLE001
            raise _github_error(exc) from exc

    def pull_requests(self, repo: str) -> list[GitHubPullRequest]:
        client = self._require_client()
        try:
            repo_obj = client.get_repo(repo)
            return [_pr_to_model(p, repo) for p in repo_obj.get_pulls(state="all")]
        except Exception as exc:  # noqa: BLE001
            raise _github_error(exc) from exc

    def discussions(self, repo: str) -> list[GitHubDiscussion]:
        client = self._require_client()
        try:
            repo_obj = client.get_repo(repo)
            return [_discussion_to_model(d, repo) for d in repo_obj.get_discussions()]
        except Exception as exc:  # noqa: BLE001
            raise _github_error(exc) from exc

    def releases(self, repo: str) -> list[GitHubRelease]:
        client = self._require_client()
        try:
            repo_obj = client.get_repo(repo)
            return [_release_to_model(r, repo) for r in repo_obj.get_releases()]
        except Exception as exc:  # noqa: BLE001
            raise _github_error(exc) from exc

    def create_issue(
        self, repo: str, title: str, body: str = "", labels: list[str] | None = None
    ) -> GitHubIssue:
        client = self._require_client()
        try:
            repo_obj = client.get_repo(repo)
            issue = repo_obj.create_issue(title=title, body=body, labels=labels or [])
            return _issue_to_model(issue, repo)
        except Exception as exc:  # noqa: BLE001
            raise _github_error(exc) from exc

    def comment(self, repo: str, number: int, body: str) -> GitHubIssue:
        client = self._require_client()
        try:
            repo_obj = client.get_repo(repo)
            issue = repo_obj.get_issue(number)
            issue.create_comment(body)
            return _issue_to_model(repo_obj.get_issue(number), repo)
        except Exception as exc:  # noqa: BLE001
            raise _github_error(exc) from exc


class MockGitHub(GitHubAdapter):
    """A deterministic, credential-free GitHub surface for the P0 experience.

    Seeded from a fixed base timestamp so tests can assert on exact records and
    the app has real content (notifications, issues, PRs, discussions, releases)
    before a single token is entered. Overrides the live methods with in-memory
    reads and appends created issues/comments to a local log.
    """

    name = "github"

    def __init__(self, *, repo: str = "quill/quill-social", base_ms: int = 1_700_000_000_000):
        super().__init__(token_ref="mock")
        self.repo = repo
        self.base_ms = base_ms
        self._seq = 0
        self._issues = self._seed_issues()
        self._prs = self._seed_prs()
        self._discussions = self._seed_discussions()
        self._releases = self._seed_releases()
        self._notifications = self._seed_notifications()

    # -- reads ----------------------------------------------------------------

    def notifications(self) -> list[GitHubNotification]:
        return list(self._notifications)

    def issues(self, repo: str = "") -> list[GitHubIssue]:
        want = repo or self.repo
        return [i for i in self._issues if i.repo == want]

    def pull_requests(self, repo: str = "") -> list[GitHubPullRequest]:
        want = repo or self.repo
        return [p for p in self._prs if p.repo == want]

    def discussions(self, repo: str = "") -> list[GitHubDiscussion]:
        want = repo or self.repo
        return [d for d in self._discussions if d.repo == want]

    def releases(self, repo: str = "") -> list[GitHubRelease]:
        want = repo or self.repo
        return [r for r in self._releases if r.repo == want]

    # -- acts -----------------------------------------------------------------

    def create_issue(
        self, repo: str, title: str, body: str = "", labels: list[str] | None = None
    ) -> GitHubIssue:
        self._seq += 1
        number = 100 + self._seq
        issue = GitHubIssue(
            id=f"mock-issue-{number}",
            repo=repo or self.repo,
            number=number,
            title=title,
            body=body,
            state="open",
            labels=list(labels or []),
            author="@you",
            url=f"https://github.com/{repo or self.repo}/issues/{number}",
            updated=self.base_ms + self._seq * 60_000,
        )
        self._issues.append(issue)
        return issue

    def comment(self, repo: str, number: int, body: str) -> GitHubIssue:
        want = repo or self.repo
        for issue in self._issues:
            if issue.repo == want and issue.number == number:
                issue.body = f"{issue.body}\n\n> comment: {body}".strip()
                issue.updated = self.base_ms + (self._seq + 1) * 60_000
                return issue
        raise AdapterError(
            f"no such issue {want}#{number}", kind="validation"
        )

    # -- seed data ------------------------------------------------------------

    def _seed_issues(self) -> list[GitHubIssue]:
        return [
            GitHubIssue(
                id="mock-issue-1", repo=self.repo, number=1,
                title="Timeline focus jumps to top on refresh",
                body="Screen reader focus is lost when the timeline refreshes.",
                state="open", labels=["accessibility", "bug"], author="@ada",
                url=f"https://github.com/{self.repo}/issues/1",
                updated=self.base_ms - 3 * 60_000,
            ),
            GitHubIssue(
                id="mock-issue-2", repo=self.repo, number=2,
                title="Add keyboard shortcut to jump to unread",
                body="Requesting a single-key jump to the next unread item.",
                state="open", labels=["enhancement"], author="@grace",
                url=f"https://github.com/{self.repo}/issues/2",
                updated=self.base_ms - 9 * 60_000,
            ),
        ]

    def _seed_prs(self) -> list[GitHubPullRequest]:
        return [
            GitHubPullRequest(
                id="mock-pr-10", repo=self.repo, number=10,
                title="Preserve reading position across refresh",
                body="Keeps focus where the user was after a background refresh.",
                state="merged", labels=["accessibility"], author="@alan",
                url=f"https://github.com/{self.repo}/pull/10",
                updated=self.base_ms - 2 * 60_000,
            ),
            GitHubPullRequest(
                id="mock-pr-11", repo=self.repo, number=11,
                title="Spoken thread splitter progress",
                body="Announces segment counts while composing a thread.",
                state="merged", labels=["accessibility", "composer"], author="@katherine",
                url=f"https://github.com/{self.repo}/pull/11",
                updated=self.base_ms - 5 * 60_000,
            ),
            GitHubPullRequest(
                id="mock-pr-12", repo=self.repo, number=12,
                title="Draft outbox persistence",
                body="Work in progress; not yet merged.",
                state="open", labels=["offline"], author="@bits",
                url=f"https://github.com/{self.repo}/pull/12",
                updated=self.base_ms - 8 * 60_000,
            ),
        ]

    def _seed_discussions(self) -> list[GitHubDiscussion]:
        return [
            GitHubDiscussion(
                id="mock-disc-1", repo=self.repo, number=20,
                title="How should catch-up grouping work?",
                body="Looking for feedback on grouping unread items by conversation.",
                state="open", labels=["question"], author="@bits",
                url=f"https://github.com/{self.repo}/discussions/20",
                updated=self.base_ms - 12 * 60_000,
            ),
        ]

    def _seed_releases(self) -> list[GitHubRelease]:
        return [
            GitHubRelease(
                id="mock-rel-1", repo=self.repo, number=0,
                title="QUILL Social 0.1.0",
                body="First accessible slice: read, draft, split, and schedule.",
                state="published", labels=[], author="@bits",
                url=f"https://github.com/{self.repo}/releases/tag/v0.1.0",
                updated=self.base_ms - 60 * 60_000, tag="v0.1.0",
            ),
        ]

    def _seed_notifications(self) -> list[GitHubNotification]:
        return [
            GitHubNotification(
                id="mock-note-1", repo=self.repo, number=1,
                title="Timeline focus jumps to top on refresh",
                body="@you were mentioned.", state="unread",
                labels=["accessibility"], author="@ada",
                url=f"https://github.com/{self.repo}/issues/1",
                updated=self.base_ms - 3 * 60_000, reason="mention",
            ),
            GitHubNotification(
                id="mock-note-2", repo=self.repo, number=10,
                title="Preserve reading position across refresh",
                body="Review requested from @you.", state="unread",
                labels=[], author="@alan",
                url=f"https://github.com/{self.repo}/pull/10",
                updated=self.base_ms - 2 * 60_000, reason="review_requested",
            ),
        ]
