"""GitHub remote provider backed by PyGithub.

PyGithub is imported lazily so that QUILL starts even when the package is not
installed.  Call :func:`require_pygithub` to get a user-facing error message
when the optional dep is absent.
"""

from __future__ import annotations

from typing import Any

from quill.core.error_codes import CodedError
from quill.core.github.models import (
    RemoteAccount,
    RemoteFile,
    RemoteNode,
    RemoteRef,
    RemoteRepository,
)
from quill.core.github.provider import RemoteProvider

_GITHUB_FILE_SIZE_LIMIT = 1_000_000  # bytes; GitHub's file-contents API limit


class GitHubDependencyError(CodedError):
    """Raised when PyGithub is not installed."""

    code = "QUILL-GITHUB-DEPENDENCY-MISSING"


def require_pygithub() -> None:
    """Raise :class:`GitHubDependencyError` if PyGithub is not installed."""
    try:
        import github  # noqa: F401
    except ImportError as exc:
        raise GitHubDependencyError(
            "PyGithub is required for GitHub integration.\n"
            'Install it with:  pip install "quill[github]"'
        ) from exc


def _get_gh_module() -> Any:
    try:
        import github

        return github
    except ImportError as exc:
        raise GitHubDependencyError(
            'PyGithub is not installed. Run: pip install "quill[github]"'
        ) from exc


def _looks_binary(data: bytes, *, sample: int = 8000) -> bool:
    """Return True if *data* contains a NUL byte within the first *sample* bytes.

    Used to refuse non-text files at the GitHub provider boundary (finding
    #25).  The previous latin-1 fallback silently turned images and other
    binaries into a "text" view that round-tripped through save-back as
    mangled UTF-8.
    """
    return b"\x00" in data[:sample]


class GitHubRemoteProvider(RemoteProvider):
    """Read-only GitHub provider using the PyGithub library."""

    provider_id = "github"

    def __init__(self, token: str | None = None) -> None:
        gh = _get_gh_module()
        if token:
            auth = gh.Auth.Token(token)
            self._gh: Any = gh.Github(auth=auth)
        else:
            self._gh = gh.Github()
        self._token = token

    def get_identity(self) -> RemoteAccount | None:
        if not self._token:
            return None
        try:
            user = self._gh.get_user()
            return RemoteAccount(
                provider="github",
                account_id=f"github:{user.login}",
                display_name=user.name or user.login,
                login=user.login,
            )
        except Exception:  # noqa: BLE001 - authentication errors are non-fatal
            return None

    def get_repository(self, full_name: str) -> RemoteRepository:
        gh = _get_gh_module()
        try:
            repo = self._gh.get_repo(full_name)
        except gh.GithubException as exc:
            status = getattr(exc, "status", None)
            msg = exc.data.get("message", str(exc)) if hasattr(exc, "data") else str(exc)
            if status == 404:
                raise KeyError(
                    f"Repository not found: {full_name!r}. "
                    "Check the owner/repo name and that you have access."
                ) from exc
            if status == 401:
                raise PermissionError("GitHub token is invalid or has expired.") from exc
            if status == 403:
                raise PermissionError(
                    "Access denied. Your token may need 'repo' scope for private repositories."
                ) from exc
            raise RuntimeError(f"GitHub error {status}: {msg}") from exc
        return RemoteRepository(
            provider="github",
            full_name=repo.full_name,
            description=repo.description or "",
            is_private=repo.private,
            default_branch=repo.default_branch,
            html_url=repo.html_url,
        )

    def list_refs(
        self,
        repository: RemoteRepository,
        *,
        limit: int = 100,
    ) -> list[RemoteRef]:
        """Return up to *limit* branches and tags for *repository*.

        ``limit`` is the per-kind cap.  A repo with thousands of refs (e.g.
        ``kubernetes/kubernetes`` has 2000+ branches) used to burn an entire
        anonymous GitHub rate-limit window before the dialog became
        responsive (finding #34).  Callers that genuinely need the full
        list should pass a larger ``limit`` explicitly; the dialog uses a
        cap of 100 by default and a "Show all refs" affordance.
        """
        gh = _get_gh_module()
        try:
            repo = self._gh.get_repo(repository.full_name)
        except gh.GithubException as exc:
            raise RuntimeError(f"Could not list refs: {exc}") from exc
        refs: list[RemoteRef] = []
        branch_count = 0
        for b in repo.get_branches():
            refs.append(RemoteRef(name=b.name, kind="branch"))
            branch_count += 1
            if branch_count >= limit:
                break
        tag_count = 0
        for t in repo.get_tags():
            refs.append(RemoteRef(name=t.name, kind="tag"))
            tag_count += 1
            if tag_count >= limit:
                break
        return refs

    def list_directory(
        self,
        repository: RemoteRepository,
        path: str,
        ref: str,
    ) -> list[RemoteNode]:
        gh = _get_gh_module()
        try:
            repo = self._gh.get_repo(repository.full_name)
            raw = repo.get_contents(path or "", ref=ref)
        except gh.GithubException as exc:
            status = getattr(exc, "status", None)
            if status == 404:
                raise KeyError(f"Path not found: {path!r} on {ref!r}") from exc
            raise RuntimeError(f"Could not list directory: {exc}") from exc
        items = raw if isinstance(raw, list) else [raw]
        nodes: list[RemoteNode] = []
        for item in sorted(items, key=lambda x: (x.type != "dir", x.name.lower())):
            nodes.append(
                RemoteNode(
                    name=item.name,
                    path=item.path,
                    kind="dir" if item.type == "dir" else "file",
                    size=item.size or 0,
                    sha=item.sha or "",
                )
            )
        return nodes

    def get_file(
        self,
        repository: RemoteRepository,
        path: str,
        ref: str,
    ) -> RemoteFile:
        gh = _get_gh_module()
        try:
            repo = self._gh.get_repo(repository.full_name)
            content = repo.get_contents(path, ref=ref)
        except gh.GithubException as exc:
            status = getattr(exc, "status", None)
            if status == 404:
                raise KeyError(f"File not found: {path!r} on {ref!r}") from exc
            raise RuntimeError(f"Could not fetch file: {exc}") from exc
        if isinstance(content, list):
            raise ValueError(f"{path!r} is a directory, not a file.")
        size = content.size or 0
        if size > _GITHUB_FILE_SIZE_LIMIT:
            raise ValueError(
                f"File is {size:,} bytes. GitHub's file API is limited to "
                f"{_GITHUB_FILE_SIZE_LIMIT:,} bytes. Download it manually."
            )
        raw: bytes = content.decoded_content
        if _looks_binary(raw):
            # #25: refuse to silently coerce binary content into a text editor
            # and a save-back round-trip (the old latin-1 fallback corrupted
            # bytes, and the resulting UTF-8 file was useless for the user).
            raise ValueError(
                f"{path!r} on {ref!r} looks like a binary file "
                f"(NUL byte detected in the first {len(raw)} bytes). "
                "Download it manually instead of opening it in the editor."
            )
        html_url: str = content.html_url or (
            f"https://github.com/{repository.full_name}/blob/{ref}/{path}"
        )
        return RemoteFile(
            repository=repository,
            path=path,
            ref=ref,
            sha=content.sha or "",
            content=raw,
            html_url=html_url,
        )

    def write_file(
        self,
        full_name: str,
        path: str,
        ref: str,
        content: bytes,
        sha: str,
        message: str,
    ) -> str:
        """Commit updated *content* to *path* on *ref* and return the new SHA."""
        gh = _get_gh_module()
        try:
            repo = self._gh.get_repo(full_name)
            result = repo.update_file(
                path=path,
                message=message,
                content=content,
                sha=sha,
                branch=ref,
            )
            new_sha: str = result["content"].sha
            return new_sha
        except gh.GithubException as exc:
            status = getattr(exc, "status", None)
            msg = exc.data.get("message", str(exc)) if hasattr(exc, "data") else str(exc)
            if status == 401:
                raise PermissionError("GitHub token is invalid or has expired.") from exc
            if status == 403:
                raise PermissionError(
                    "Write access denied. Ensure your token has 'repo' scope "
                    "and that you have push permission on this repository."
                ) from exc
            if status == 409:
                raise RuntimeError(
                    "File has been modified on GitHub since you opened it. "
                    "Refresh from GitHub and try again."
                ) from exc
            raise RuntimeError(f"GitHub error {status}: {msg}") from exc

    def close(self) -> None:
        """Release the underlying GitHub session."""
        try:
            self._gh.close()
        except Exception:  # noqa: BLE001
            pass
