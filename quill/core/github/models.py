"""Data models for the GitHub remote-file abstraction."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RemoteAccount:
    """An authenticated (or anonymous) GitHub identity."""

    provider: str  # always "github"
    account_id: str  # "github:<login>" or "github:anonymous"
    display_name: str
    login: str  # GitHub username, or "" for anonymous


@dataclass(frozen=True, slots=True)
class RemoteRepository:
    """A GitHub repository."""

    provider: str
    full_name: str  # "owner/repo"
    description: str = ""
    is_private: bool = False
    default_branch: str = "main"
    html_url: str = ""


@dataclass(frozen=True, slots=True)
class RemoteRef:
    """A branch or tag."""

    name: str
    kind: str  # "branch" or "tag"


@dataclass(frozen=True, slots=True)
class RemoteNode:
    """A file or directory entry inside a repository."""

    name: str
    path: str  # full path from the repo root
    kind: str  # "file" or "dir"
    size: int = 0
    sha: str = ""


@dataclass(frozen=True, slots=True)
class RemoteFile:
    """A fetched file's content and metadata."""

    repository: RemoteRepository
    path: str
    ref: str
    sha: str
    content: bytes
    html_url: str = ""


@dataclass(frozen=True, slots=True)
class RemoteOrigin:
    """Metadata attached to a document opened from GitHub."""

    provider: str  # "github"
    account_id: str  # "github:<login>" or "github:anonymous"
    repository: str  # "owner/repo"
    ref: str  # branch / tag / commit
    path: str  # "docs/example.md"
    sha: str
    url: str  # canonical HTML URL on github.com
    opened_at: str  # ISO-8601


@dataclass(frozen=True, slots=True)
class BrowseResult:
    """Returned by the browser dialog; the mixin downloads the file."""

    repository: RemoteRepository
    path: str
    ref: str
    sha: str
    html_url: str
    line: int = 0
    line_end: int = 0
