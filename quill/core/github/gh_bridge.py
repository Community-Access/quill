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
import re
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
    last_used_at: str = ""
    machine_display_name: str = ""
    location: str = ""


_CODESPACE_JSON_FIELDS = (
    "name,displayName,repository,state,gitStatus,createdAt,lastUsedAt,machineDisplayName,location"
)
_CODESPACE_NAME_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,78}[a-z0-9])?$")
_LOGIN_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")


def _codespace_name(value: str) -> str:
    name = value.strip().casefold()
    if not _CODESPACE_NAME_RE.fullmatch(name):
        raise GhBridgeError("GitHub returned an invalid codespace name.")
    return name


def _codespace_info(row: object) -> CodespaceInfo:
    if not isinstance(row, dict):
        raise GhBridgeError("GitHub returned an invalid codespace record.")
    git_status = row.get("gitStatus")
    if not isinstance(git_status, dict):
        git_status = {}
    try:
        ahead = max(0, int(git_status.get("ahead", 0) or 0))
        behind = max(0, int(git_status.get("behind", 0) or 0))
    except (TypeError, ValueError) as exc:
        raise GhBridgeError("GitHub returned invalid codespace Git status.") from exc
    return CodespaceInfo(
        name=_codespace_name(str(row.get("name", ""))),
        display_name=str(row.get("displayName", ""))[:128],
        repository=str(row.get("repository", ""))[:256],
        state=str(row.get("state", ""))[:64],
        git_status_ahead=ahead,
        git_status_behind=behind,
        created_at=str(row.get("createdAt", ""))[:64],
        last_used_at=str(row.get("lastUsedAt", ""))[:64],
        machine_display_name=str(row.get("machineDisplayName", ""))[:128],
        location=str(row.get("location", ""))[:64],
    )


def list_codespaces(*, gh_path: str, runner: Runner) -> list[CodespaceInfo]:
    """List the authenticated account's codespaces, across every repository."""
    output = _run_ok(
        gh_path,
        runner,
        "codespace",
        "list",
        "--limit",
        "50",
        "--json",
        _CODESPACE_JSON_FIELDS,
    )
    try:
        rows = json.loads(output) if output.strip() else []
    except json.JSONDecodeError as exc:
        raise GhBridgeError(f"Could not parse codespace list: {exc}") from exc
    if not isinstance(rows, list):
        raise GhBridgeError("GitHub returned an invalid codespace list.")
    return [_codespace_info(row) for row in rows[:50]]


def authenticated_login(*, gh_path: str, runner: Runner) -> str:
    """Return the account selected in ``gh`` without exposing its token."""
    login = _run_ok(gh_path, runner, "api", "user", "--jq", ".login").strip()
    if not _LOGIN_RE.fullmatch(login):
        raise GhBridgeError("GitHub CLI did not report a valid signed-in account.")
    return login


def view_codespace(name: str, *, gh_path: str, runner: Runner) -> CodespaceInfo:
    """Refresh health and repository status for one existing codespace."""
    target = _codespace_name(name)
    output = _run_ok(
        gh_path,
        runner,
        "codespace",
        "view",
        "--codespace",
        target,
        "--json",
        _CODESPACE_JSON_FIELDS,
    )
    try:
        row = json.loads(output)
    except json.JSONDecodeError as exc:
        raise GhBridgeError(f"Could not parse codespace details: {exc}") from exc
    return _codespace_info(row)


def open_codespace(name: str, *, gh_path: str, runner: Runner, web: bool = True) -> None:
    """Open a named codespace in VS Code Web or desktop VS Code."""
    args = ["codespace", "code", "--codespace", _codespace_name(name)]
    if web:
        args.append("--web")
    _run_ok(gh_path, runner, *args, timeout_seconds=60.0)


def create_codespace(
    repo: str, *, branch: str = "", gh_path: str, runner: Runner, timeout_seconds: float = 120.0
) -> CodespaceInfo:
    """Create a codespace for *repo* (optionally on *branch*).

    Costs real money/quota on GitHub's side -- callers must confirm this
    explicitly before calling, the same as any other high-consequence
    action in this codebase; this function itself does not gate on
    anything beyond the `gh` call succeeding.
    """
    if not repo or len(repo) > 256 or "/" not in repo or any(ch.isspace() for ch in repo):
        raise GhBridgeError("Enter a repository as owner/repo for the codespace.")
    args = ["codespace", "create", "--repo", repo, "--json", "name"]
    if branch:
        args.extend(["--branch", branch])
    output = _run_ok(gh_path, runner, *args, timeout_seconds=timeout_seconds)
    try:
        parsed = json.loads(output) if output.strip() else {}
    except json.JSONDecodeError as exc:
        raise GhBridgeError(f"Could not parse codespace create result: {exc}") from exc
    raw_name = str(parsed.get("name", "")).strip() if isinstance(parsed, dict) else ""
    if not raw_name:
        raise GhBridgeError("gh codespace create did not report a codespace name.")
    name = _codespace_name(raw_name)
    matches = [c for c in list_codespaces(gh_path=gh_path, runner=runner) if c.name == name]
    if matches:
        return matches[0]
    return CodespaceInfo(name=name, display_name=name, repository=repo, state="Unknown")


def stop_codespace(name: str, *, gh_path: str, runner: Runner) -> None:
    _run_ok(gh_path, runner, "codespace", "stop", "--codespace", _codespace_name(name))


def delete_codespace(name: str, *, gh_path: str, runner: Runner) -> None:
    _run_ok(
        gh_path,
        runner,
        "codespace",
        "delete",
        "--codespace",
        _codespace_name(name),
        "--force",
    )


def codespace_ssh_config(name: str, *, gh_path: str, runner: Runner) -> str:
    """The SSH connection config `gh codespace ssh --config` prints for
    *name* -- host, proxy command, identity file -- so a caller can hand it
    to an SSH client (e.g. QUILL's own `quill.core.ssh.client`) instead of
    needing `gh` itself to hold the connection open.

    Returned verbatim; parsing it into a structured connection descriptor is
    a follow-up, not yet needed by anything in this codebase.
    """
    return _run_ok(
        gh_path,
        runner,
        "codespace",
        "ssh",
        "--codespace",
        _codespace_name(name),
        "--config",
    )


__all__ = [
    "CodespaceInfo",
    "GhBridgeError",
    "authenticated_login",
    "codespace_ssh_config",
    "create_codespace",
    "delete_codespace",
    "list_codespaces",
    "open_codespace",
    "stop_codespace",
    "view_codespace",
]
