"""Repository lifecycle operations: create, rename, visibility, default
branch, branch protection, fork, and multi-file commits.

A sibling of :mod:`quill.core.github.github_provider` (single-file browse/
write) and :mod:`quill.core.github.items_provider` (issues/PRs/branches/
commits/etc.). This module is the third leg: operations on the *repository
itself* rather than its files or its issue tracker.

Transport is PyGithub, same as every other GitHub module in this package --
no ``gh`` subprocess, no new dependency. See ``docs/planning/github.md`` for
the design rationale (extend the existing PyGithub provider rather than
shell out to the ``gh`` CLI).

wx-free and strict-typed (in ``mypy quill/core`` scope). Every mutating call
here is a genuine write against GitHub -- the UI mixin
(:mod:`quill.ui.main_frame_github_admin`) gates every one of them behind
consent, a Safe Mode refusal, and an explicit confirmation dialog naming the
exact repository/branch/action, exactly like the existing
``GitHubItemsProvider.update_items`` batch-write precedent.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from quill.core.github.github_provider import _get_gh_module, require_pygithub
from quill.core.github.models import RemoteRepository


@dataclass(frozen=True, slots=True)
class ReleaseInfo:
    """A created (or draft) GitHub release."""

    tag: str
    name: str
    html_url: str
    draft: bool = False
    prerelease: bool = False


class GitHubRepoAdminError(RuntimeError):
    """A repository admin operation failed (auth, API, or not-found)."""


def _translate(exc: Exception, *, context: str) -> GitHubRepoAdminError:
    """Map a PyGithub ``GithubException`` (or anything else) to one error type.

    Mirrors the status-code translation already used in
    ``github_provider.py`` and ``items_provider.py``, collapsed into a single
    helper here since every method in this module needs the same mapping.
    """
    gh = _get_gh_module()
    if isinstance(exc, gh.GithubException):
        status = getattr(exc, "status", None)
        msg = exc.data.get("message", str(exc)) if hasattr(exc, "data") else str(exc)
        if status == 404:
            return GitHubRepoAdminError(f"{context}: not found or no access.")
        if status == 401:
            return GitHubRepoAdminError(f"{context}: GitHub token is invalid or has expired.")
        if status == 403:
            return GitHubRepoAdminError(
                f"{context}: access denied. Your token may need 'repo' or "
                "'delete_repo' scope for this action."
            )
        if status == 422:
            return GitHubRepoAdminError(f"{context}: {msg} (name may already be taken).")
        return GitHubRepoAdminError(f"{context}: GitHub error {status}: {msg}")
    return GitHubRepoAdminError(f"{context}: {exc}")


def _to_repository(repo: Any) -> RemoteRepository:
    return RemoteRepository(
        provider="github",
        full_name=repo.full_name,
        description=repo.description or "",
        is_private=repo.private,
        default_branch=repo.default_branch,
        html_url=repo.html_url,
    )


class GitHubRepoAdminProvider:
    """Repository-lifecycle operations backed by PyGithub.

    Requires an authenticated token for every method -- there is no
    anonymous path, unlike the read-only browsers. Construct with the same
    token used elsewhere in the GitHub integration.
    """

    def __init__(self, token: str) -> None:
        if not token:
            raise GitHubRepoAdminError("Repository admin actions need a signed-in GitHub account.")
        gh = _get_gh_module()
        self._gh: Any = gh.Github(auth=gh.Auth.Token(token))
        self._token = token

    def _repo(self, full_name: str) -> Any:
        try:
            return self._gh.get_repo(full_name)
        except Exception as exc:  # noqa: BLE001
            raise _translate(exc, context=f"Could not open {full_name}") from exc

    # ------------------------------------------------------------------
    # Create / fork

    def create_repository(
        self,
        name: str,
        *,
        private: bool = True,
        description: str = "",
        org: str = "",
    ) -> RemoteRepository:
        """Create a new repository, optionally under an organization.

        Raises :class:`GitHubRepoAdminError` if the name is taken, invalid,
        or the token lacks the ``repo`` scope.
        """
        try:
            if org:
                owner = self._gh.get_organization(org)
                repo = owner.create_repo(name, private=private, description=description)
            else:
                user = self._gh.get_user()
                repo = user.create_repo(name, private=private, description=description)
        except Exception as exc:  # noqa: BLE001
            raise _translate(exc, context=f"Could not create repository {name!r}") from exc
        return _to_repository(repo)

    def fork_repository(self, full_name: str, *, org: str = "") -> RemoteRepository:
        """Fork *full_name* into the authenticated account (or *org*)."""
        repo = self._repo(full_name)
        try:
            if org:
                owner = self._gh.get_organization(org)
                fork = repo.create_fork(organization=owner)
            else:
                fork = repo.create_fork()
        except Exception as exc:  # noqa: BLE001
            raise _translate(exc, context=f"Could not fork {full_name}") from exc
        return _to_repository(fork)

    # ------------------------------------------------------------------
    # Rename / visibility / default branch

    def rename_repository(self, full_name: str, new_name: str) -> RemoteRepository:
        """Rename a repository. GitHub redirects the old URL automatically."""
        repo = self._repo(full_name)
        try:
            repo.edit(name=new_name)
            renamed = self._gh.get_repo(f"{repo.owner.login}/{new_name}")
        except Exception as exc:  # noqa: BLE001
            raise _translate(exc, context=f"Could not rename {full_name}") from exc
        return _to_repository(renamed)

    def set_visibility(self, full_name: str, *, private: bool) -> RemoteRepository:
        """Flip a repository between private and public."""
        repo = self._repo(full_name)
        try:
            repo.edit(private=private)
            repo = self._gh.get_repo(full_name)
        except Exception as exc:  # noqa: BLE001
            raise _translate(exc, context=f"Could not change visibility of {full_name}") from exc
        return _to_repository(repo)

    def set_default_branch(self, full_name: str, branch: str) -> RemoteRepository:
        """Change the repository's default branch."""
        repo = self._repo(full_name)
        try:
            repo.edit(default_branch=branch)
            repo = self._gh.get_repo(full_name)
        except Exception as exc:  # noqa: BLE001
            raise _translate(
                exc, context=f"Could not set default branch to {branch!r} on {full_name}"
            ) from exc
        return _to_repository(repo)

    # ------------------------------------------------------------------
    # Branch protection

    def set_branch_protection(
        self,
        full_name: str,
        branch: str,
        *,
        required_approving_review_count: int | None = None,
        required_status_checks: Sequence[str] = (),
        enforce_admins: bool = False,
    ) -> None:
        """Apply branch protection to *branch*.

        ``required_approving_review_count`` of ``None`` skips the required-
        reviews rule entirely; a value of 0 is rejected by GitHub's API (use
        :meth:`remove_branch_protection` to clear protection instead).
        """
        repo = self._repo(full_name)
        try:
            ref = repo.get_branch(branch)
            ref.edit_protection(
                strict=bool(required_status_checks),
                contexts=list(required_status_checks),
                enforce_admins=enforce_admins,
                required_approving_review_count=required_approving_review_count,
            )
        except Exception as exc:  # noqa: BLE001
            raise _translate(exc, context=f"Could not protect {branch!r} on {full_name}") from exc

    def remove_branch_protection(self, full_name: str, branch: str) -> None:
        """Remove all branch protection rules from *branch*."""
        repo = self._repo(full_name)
        try:
            ref = repo.get_branch(branch)
            ref.remove_protection()
        except Exception as exc:  # noqa: BLE001
            raise _translate(
                exc, context=f"Could not remove protection from {branch!r} on {full_name}"
            ) from exc

    # ------------------------------------------------------------------
    # Branch deletion

    def delete_branch(self, full_name: str, branch: str) -> None:
        """Delete *branch*. Irreversible on GitHub's side beyond its reflog."""
        repo = self._repo(full_name)
        try:
            ref = repo.get_git_ref(f"heads/{branch}")
            ref.delete()
        except Exception as exc:  # noqa: BLE001
            raise _translate(exc, context=f"Could not delete branch {branch!r}") from exc

    # ------------------------------------------------------------------
    # Multi-file commit (atomic tree commit, unlike write_file's single-file PUT)

    def commit_files(
        self,
        full_name: str,
        branch: str,
        files: Sequence[tuple[str, bytes]],
        message: str,
    ) -> str:
        """Commit multiple files to *branch* in a single atomic commit.

        Builds a git tree from the current branch tip plus the given
        ``(path, content)`` pairs, creates one commit, and fast-forwards
        *branch* to it. Returns the new commit SHA.

        Raises :class:`GitHubRepoAdminError` if *branch* has moved since it
        was read (a concurrent push) -- the ref update uses a plain
        fast-forward, so a diverged branch is refused rather than force-
        pushed over.
        """
        if not files:
            raise GitHubRepoAdminError("commit_files: no files given.")
        repo = self._repo(full_name)
        try:
            ref = repo.get_git_ref(f"heads/{branch}")
            base_commit = repo.get_git_commit(ref.object.sha)
            base_tree = base_commit.tree
            elements = [
                {
                    "path": path,
                    "mode": "100644",
                    "type": "blob",
                    "content": content.decode("utf-8"),
                }
                for path, content in files
            ]
            new_tree = repo.create_git_tree(elements, base_tree)
            new_commit = repo.create_git_commit(message, new_tree, [base_commit])
            ref.edit(new_commit.sha)
        except UnicodeDecodeError as exc:
            raise GitHubRepoAdminError(
                "commit_files: all file content must be UTF-8 text "
                "(binary files are not supported by this call)."
            ) from exc
        except Exception as exc:  # noqa: BLE001
            raise _translate(exc, context=f"Could not commit files to {full_name}") from exc
        return str(new_commit.sha)

    # ------------------------------------------------------------------
    # Organizations (Teams are explicitly out of scope -- see
    # docs/planning/github.md section 1: "Organizations in, Teams out")

    def list_organizations(self) -> list[str]:
        """Organization logins the authenticated account belongs to."""
        try:
            return [org.login for org in self._gh.get_user().get_orgs()]
        except Exception as exc:  # noqa: BLE001
            raise _translate(exc, context="Could not list organizations") from exc

    def list_org_repositories(self, org: str, *, limit: int = 100) -> list[RemoteRepository]:
        """Repositories visible to the authenticated account within *org*."""
        try:
            organization = self._gh.get_organization(org)
            repos = []
            for i, repo in enumerate(organization.get_repos()):
                if i >= limit:
                    break
                repos.append(_to_repository(repo))
            return repos
        except Exception as exc:  # noqa: BLE001
            raise _translate(exc, context=f"Could not list repositories for {org}") from exc

    # ------------------------------------------------------------------
    # Releases, authored

    def generate_release_notes(
        self, full_name: str, tag_name: str, *, previous_tag_name: str = ""
    ) -> str:
        """Draft release notes from merged PRs since *previous_tag_name*
        (or since the last release, when blank) -- GitHub's own
        auto-generated notes, the same text the web UI's "Generate release
        notes" button produces."""
        repo = self._repo(full_name)
        try:
            gh = _get_gh_module()
            result = repo.generate_release_notes(
                tag_name,
                previous_tag_name=previous_tag_name or gh.GithubObject.NotSet,
            )
        except Exception as exc:  # noqa: BLE001
            raise _translate(
                exc, context=f"Could not generate release notes for {tag_name}"
            ) from exc
        return str(getattr(result, "body", "") or "")

    def create_release(
        self,
        full_name: str,
        tag: str,
        *,
        name: str = "",
        body: str = "",
        draft: bool = False,
        prerelease: bool = False,
        generate_notes: bool = False,
        target_commitish: str = "",
    ) -> ReleaseInfo:
        repo = self._repo(full_name)
        try:
            gh = _get_gh_module()
            release = repo.create_git_release(
                tag,
                name or gh.GithubObject.NotSet,
                body or gh.GithubObject.NotSet,
                draft=draft,
                prerelease=prerelease,
                generate_release_notes=generate_notes,
                target_commitish=target_commitish or gh.GithubObject.NotSet,
            )
        except Exception as exc:  # noqa: BLE001
            raise _translate(exc, context=f"Could not create release {tag}") from exc
        return ReleaseInfo(
            tag=str(getattr(release, "tag_name", tag)),
            name=str(getattr(release, "title", "") or getattr(release, "name", "") or ""),
            html_url=str(getattr(release, "html_url", "") or ""),
            draft=bool(getattr(release, "draft", draft)),
            prerelease=bool(getattr(release, "prerelease", prerelease)),
        )

    def close(self) -> None:
        """Release the underlying GitHub session."""
        try:
            self._gh.close()
        except Exception:  # noqa: BLE001
            pass


__all__ = [
    "GitHubRepoAdminError",
    "GitHubRepoAdminProvider",
    "ReleaseInfo",
    "require_pygithub",
]
