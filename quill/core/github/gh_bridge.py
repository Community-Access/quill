"""The narrow `gh`-CLI bridge (`docs/planning/github.md` section 1's Tier 3):
GitHub Codespaces lifecycle management.

Deliberately not a general `gh api` passthrough or an extension-ecosystem
bridge -- those stay out of scope per the PRD. This module covers the one
thing PyGithub has no clean path to: Codespaces (no stable REST wrapper for
the interesting lifecycle operations). The `gh copilot suggest`/`explain`
pair it once wrapped was removed on 2026-10-31: GitHub retired that
extension on 2025-10-25, so both commands could only fail.

**Needs live-device verification.** Every function here is unit-tested with
a fake subprocess runner (mirroring `quill.core.local_git`'s convention),
which proves the argument-building and JSON-parsing logic is correct, but
none of it has been exercised against a real `gh` installation, a real
GitHub Codespaces-enabled repository -- neither of which is available in
this environment. Matches QUILL's own established pattern for
hardware/account-dependent features (e.g. the macOS `say` Read Aloud engine
shipping "needs on-device confirmation").
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from quill.core.error_codes import CodedError
from quill.core.vault.sync import Runner

_DEFAULT_TIMEOUT = 30.0


class GhBridgeError(CodedError):
    """A `gh`-CLI operation failed, or `gh` itself is not available."""

    code = "QUILL-GITHUB-GHBRIDGE-FAILED"


def _run_ok(
    gh_path: str, runner: Runner, *args: str, timeout_seconds: float = _DEFAULT_TIMEOUT
) -> str:
    result = runner([gh_path, *args], timeout_seconds=timeout_seconds)
    returncode = int(getattr(result, "returncode", 1))
    stdout = str(getattr(result, "stdout", "") or "")
    stderr = str(getattr(result, "stderr", "") or "")
    if returncode != 0:
        raise GhBridgeError((stderr or stdout or "gh command failed").strip())
    return stdout


# ---------------------------------------------------------------------------
# Codespaces
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CodespaceInfo:
    name: str
    display_name: str
    repository: str
    state: str
    git_status_ahead: int = 0
    git_status_behind: int = 0
    created_at: str = ""


_CODESPACE_JSON_FIELDS = "name,displayName,repository,state,gitStatus,createdAt"


def list_codespaces(*, gh_path: str, runner: Runner) -> list[CodespaceInfo]:
    """List the authenticated account's codespaces, across every repository."""
    output = _run_ok(gh_path, runner, "codespace", "list", "--json", _CODESPACE_JSON_FIELDS)
    try:
        rows = json.loads(output) if output.strip() else []
    except json.JSONDecodeError as exc:
        raise GhBridgeError(f"Could not parse codespace list: {exc}") from exc
    out: list[CodespaceInfo] = []
    for row in rows:
        git_status = row.get("gitStatus") or {}
        out.append(
            CodespaceInfo(
                name=str(row.get("name", "")),
                display_name=str(row.get("displayName", "")),
                repository=str(row.get("repository", "")),
                state=str(row.get("state", "")),
                git_status_ahead=int(git_status.get("ahead", 0) or 0),
                git_status_behind=int(git_status.get("behind", 0) or 0),
                created_at=str(row.get("createdAt", "")),
            )
        )
    return out


def create_codespace(
    repo: str, *, branch: str = "", gh_path: str, runner: Runner, timeout_seconds: float = 120.0
) -> CodespaceInfo:
    """Create a codespace for *repo* (optionally on *branch*).

    Costs real money/quota on GitHub's side -- callers must confirm this
    explicitly before calling, the same as any other high-consequence
    action in this codebase; this function itself does not gate on
    anything beyond the `gh` call succeeding.
    """
    args = ["codespace", "create", "--repo", repo, "--json", "name"]
    if branch:
        args.extend(["--branch", branch])
    output = _run_ok(gh_path, runner, *args, timeout_seconds=timeout_seconds)
    try:
        parsed = json.loads(output) if output.strip() else {}
    except json.JSONDecodeError as exc:
        raise GhBridgeError(f"Could not parse codespace create result: {exc}") from exc
    name = str(parsed.get("name", "")) if isinstance(parsed, dict) else str(output).strip()
    if not name:
        raise GhBridgeError("gh codespace create did not report a codespace name.")
    matches = [c for c in list_codespaces(gh_path=gh_path, runner=runner) if c.name == name]
    if matches:
        return matches[0]
    return CodespaceInfo(name=name, display_name=name, repository=repo, state="Unknown")


def stop_codespace(name: str, *, gh_path: str, runner: Runner) -> None:
    _run_ok(gh_path, runner, "codespace", "stop", "--codespace", name)


def delete_codespace(name: str, *, gh_path: str, runner: Runner) -> None:
    _run_ok(gh_path, runner, "codespace", "delete", "--codespace", name, "--force")


def codespace_ssh_config(name: str, *, gh_path: str, runner: Runner) -> str:
    """The SSH connection config `gh codespace ssh --config` prints for
    *name* -- host, proxy command, identity file -- so a caller can hand it
    to an SSH client (e.g. QUILL's own `quill.core.ssh.client`) instead of
    needing `gh` itself to hold the connection open.

    Returned verbatim; parsing it into a structured connection descriptor is
    a follow-up, not yet needed by anything in this codebase.
    """
    return _run_ok(gh_path, runner, "codespace", "ssh", "--codespace", name, "--config")


__all__ = [
    "CodespaceInfo",
    "GhBridgeError",
    "codespace_ssh_config",
    "create_codespace",
    "delete_codespace",
    "list_codespaces",
    "stop_codespace",
]
