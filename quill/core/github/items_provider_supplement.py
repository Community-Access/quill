"""Issue-template and repository-security extensions for GitHub Items."""

from __future__ import annotations

from itertools import islice
from typing import TYPE_CHECKING, Any, Protocol
from urllib.parse import quote, urlsplit

from quill.core.github.issue_templates import GitHubIssueTemplate, list_issue_templates
from quill.core.github.items_errors import GitHubItemsError
from quill.core.github.items_provider_constants import DEFAULT_PAGE_LIMIT
from quill.core.github.notifications import GitHubSecurityAlert, list_security_alerts
from quill.core.github.release_notes import GitHubReleaseNotesDraft
from quill.core.github.workflow_models import GitHubWorkflowRun, map_workflow_run
from quill.core.github.workflows import map_workflow

if TYPE_CHECKING:
    from quill.core.github.items_provider import GitHubCommit, GitHubRelease
    from quill.core.github.workflows import GitHubWorkflow


class _RepositoryAccess(Protocol):
    def _repo(self, full_name: str) -> Any: ...

    def _map_branch(self, row: Any, repo: Any) -> Any: ...

    def _map_commit(self, row: Any, repo: Any) -> GitHubCommit: ...

    @staticmethod
    def _release_asset_rows(row: Any) -> list[Any]: ...


def _take(iterable: Any, limit: int) -> list[Any]:
    return list(islice(iter(iterable), max(0, limit)))


class GitHubItemsSupplementMixin:
    """Add bounded direct references, issue templates, and security reads."""

    def fetch_branch_by_name(self: _RepositoryAccess, full_name: str, name: str) -> Any:
        if not name or len(name) > 256 or "\x00" in name:
            raise GitHubItemsError("Enter a valid branch name.")
        repo = self._repo(full_name)
        try:
            row = repo.get_branch(name)
        except Exception as exc:  # noqa: BLE001 - direct lookup context
            raise GitHubItemsError(f"Could not open branch {name!r}: {exc}") from exc
        return self._map_branch(row, repo)

    def fetch_commit_by_sha(self: _RepositoryAccess, full_name: str, sha: str) -> GitHubCommit:
        if (
            len(sha) < 6
            or len(sha) > 64
            or any(char not in "0123456789abcdefABCDEF" for char in sha)
        ):
            raise GitHubItemsError("Enter a commit SHA using hexadecimal characters.")
        repo = self._repo(full_name)
        try:
            row = repo.get_commit(sha)
        except Exception as exc:  # noqa: BLE001 - preserve direct lookup context
            raise GitHubItemsError(f"Could not open commit {sha[:12]}: {exc}") from exc
        return self._map_commit(row, repo)

    def fetch_release_by_tag(self: _RepositoryAccess, full_name: str, tag: str) -> GitHubRelease:
        """Fetch one release by encoded tag, even when it is beyond recent pages."""
        if not tag or len(tag) > 256 or any(ord(char) < 32 for char in tag):
            raise GitHubItemsError("Enter a valid release tag.")
        repo = self._repo(full_name)
        requester = getattr(repo, "_requester", None)
        repo_url = str(getattr(repo, "url", "") or "").rstrip("/")
        request = getattr(requester, "requestJsonAndCheck", None)
        parsed = urlsplit(repo_url)
        if parsed.scheme != "https" or not parsed.hostname or not callable(request):
            raise GitHubItemsError("Direct release lookup is unavailable for this repository.")
        try:
            _headers, data = request("GET", f"{repo_url}/releases/tags/{quote(tag, safe='')}")
        except Exception as exc:  # noqa: BLE001 - retain the tag and repo in the error
            raise GitHubItemsError(f"Could not open release tag {tag!r}: {exc}") from exc
        if not isinstance(data, dict):
            raise GitHubItemsError("GitHub returned invalid release details for this tag.")
        from quill.core.github.items_provider import GitHubRelease, parse_release_assets

        raw_assets = data.get("assets", [])
        assets = parse_release_assets(raw_assets if isinstance(raw_assets, list) else [])
        created = data.get("created_at", "")
        return GitHubRelease(
            tag=str(data.get("tag_name", "") or tag),
            name=str(data.get("name", "") or ""),
            draft=bool(data.get("draft", False)),
            prerelease=bool(data.get("prerelease", False)),
            created_at=str(created or ""),
            url=str(data.get("html_url", "") or ""),
            body=str(data.get("body", "") or ""),
            assets=assets,
        )

    def fetch_workflow_run_by_id(
        self: _RepositoryAccess, full_name: str, run_id: int
    ) -> GitHubWorkflowRun:
        if run_id <= 0:
            raise GitHubItemsError("Workflow-run IDs must be positive.")
        repo = self._repo(full_name)
        try:
            row = repo.get_workflow_run(run_id)
        except Exception as exc:  # noqa: BLE001 - preserve direct lookup context
            raise GitHubItemsError(f"Could not open workflow run {run_id}: {exc}") from exc
        return map_workflow_run(row)

    def fetch_workflow_by_reference(
        self: _RepositoryAccess, full_name: str, reference: str
    ) -> GitHubWorkflow:
        repo = self._repo(full_name)
        if reference.isdecimal():
            try:
                row = repo.get_workflow(int(reference))
            except Exception as exc:  # noqa: BLE001 - direct lookup context
                raise GitHubItemsError(f"Could not open workflow {reference!r}: {exc}") from exc
            return map_workflow(row)
        if not reference or len(reference) > 256 or ".." in reference.split("/"):
            raise GitHubItemsError("Enter a valid workflow file name.")
        try:
            rows = _take(repo.get_workflows(), 100)
        except Exception as exc:  # noqa: BLE001 - direct lookup context
            raise GitHubItemsError(f"Could not list workflows: {exc}") from exc
        suffix = "/" + reference.casefold().lstrip("/")
        row = next(
            (
                item
                for item in rows
                if str(getattr(item, "path", "") or "").casefold() == reference.casefold()
                or str(getattr(item, "path", "") or "").casefold().endswith(suffix)
            ),
            None,
        )
        if row is None:
            raise GitHubItemsError(
                f"Workflow {reference!r} was not found in the first 100 repository workflows."
            )
        return map_workflow(row)

    def generate_release_notes(
        self: _RepositoryAccess,
        full_name: str,
        *,
        target_tag: str,
        previous_tag: str,
        target_commitish: str = "",
    ) -> GitHubReleaseNotesDraft:
        """Generate an editable preview for an explicit tag range; never publish it."""
        for label, value in (
            ("target", target_tag),
            ("previous", previous_tag),
            ("target branch", target_commitish),
        ):
            if len(value) > 256 or any(ord(char) < 32 for char in value):
                raise GitHubItemsError(f"The release {label} contains invalid characters.")
        if not target_tag.strip() or not previous_tag.strip():
            raise GitHubItemsError("Choose both a target tag and a previous tag for the range.")
        if target_tag.strip() == previous_tag.strip():
            raise GitHubItemsError("The target tag and previous tag must be different.")
        repo = self._repo(full_name)
        generate = getattr(repo, "generate_release_notes", None)
        if not callable(generate):
            raise GitHubItemsError("This GitHub client cannot generate release-note previews.")
        kwargs: dict[str, str] = {
            "tag_name": target_tag.strip(),
            "previous_tag_name": previous_tag.strip(),
        }
        if target_commitish.strip():
            kwargs["target_commitish"] = target_commitish.strip()
        try:
            result = generate(**kwargs)
        except Exception as exc:  # noqa: BLE001 - surface permission and range errors
            raise GitHubItemsError(f"Could not generate release-note draft: {exc}") from exc
        return GitHubReleaseNotesDraft(
            target_tag=target_tag.strip(),
            previous_tag=previous_tag.strip(),
            target_commitish=target_commitish.strip(),
            name=str(getattr(result, "name", "") or "")[:512],
            body=str(getattr(result, "body", "") or "")[:50_000],
        )

    def fetch_issue_templates(
        self: _RepositoryAccess, full_name: str, *, limit: int = 20
    ) -> tuple[GitHubIssueTemplate, ...]:
        try:
            return list_issue_templates(self._repo(full_name), limit=limit)
        except Exception as exc:  # noqa: BLE001 - template errors stay visible
            raise GitHubItemsError(f"Could not load issue templates: {exc}") from exc

    def fetch_security_alerts(
        self: _RepositoryAccess,
        full_name: str,
        *,
        limit: int = DEFAULT_PAGE_LIMIT,
    ) -> list[GitHubSecurityAlert]:
        try:
            return list_security_alerts(self._repo(full_name), limit=limit, take=_take)
        except Exception as exc:  # noqa: BLE001 - security read failures are surfaced
            raise GitHubItemsError(f"Could not list security alerts: {exc}") from exc


__all__ = ["GitHubItemsSupplementMixin"]
