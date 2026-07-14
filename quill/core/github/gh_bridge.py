"""The narrow `gh`-CLI bridge (`docs/planning/github.md` section 1's Tier 3):
GitHub Codespaces lifecycle management and `gh copilot suggest`/`explain`.

Deliberately not a general `gh api` passthrough or an extension-ecosystem
bridge -- those stay out of scope per the PRD. This module covers exactly
the two things PyGithub has no clean path to: Codespaces (no stable REST
wrapper for the interesting lifecycle operations) and Copilot's CLI-native
suggest/explain (a genuinely different feature from QUILL's own AI
assistant, scoped to git/gh command help).

**Needs live-device verification.** Every function here is unit-tested with
a fake subprocess runner (mirroring `quill.core.local_git`'s convention),
which proves the argument-building and JSON-parsing logic is correct, but
none of it has been exercised against a real `gh` installation, a real
GitHub Codespaces-enabled repository, or a real Copilot CLI entitlement --
none of which are available in this environment. `gh copilot suggest` in
particular is a TUI-first command in its upstream design; whether it
degrades cleanly to captured, non-interactive stdout the way this module
assumes needs confirming on a real machine before this is promoted out of
"needs verification." Matches QUILL's own established pattern for
hardware/account-dependent features (e.g. the macOS `say` Read Aloud engine
shipping "needs on-device confirmation").
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from quill.core.vault.sync import Runner

_DEFAULT_TIMEOUT = 30.0


class GhBridgeError(RuntimeError):
    """A `gh`-CLI operation failed, or `gh` itself is not available."""


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


# ---------------------------------------------------------------------------
# Copilot CLI: suggest / explain
# ---------------------------------------------------------------------------


def copilot_suggest(
    query: str, *, gh_path: str, runner: Runner, timeout_seconds: float = 60.0
) -> str:
    """Ask `gh copilot suggest` for a shell command matching *query*, in
    plain natural language (e.g. "undo my last commit but keep the
    changes"). Returns whatever `gh` prints; the caller decides whether to
    show it as-is or offer to run it (this function never executes a
    suggested command).
    """
    return _run_ok(
        gh_path,
        runner,
        "copilot",
        "suggest",
        "-t",
        "shell",
        query,
        timeout_seconds=timeout_seconds,
    )


def copilot_explain(
    command: str, *, gh_path: str, runner: Runner, timeout_seconds: float = 60.0
) -> str:
    """Ask `gh copilot explain` what *command* does, in plain language."""
    return _run_ok(gh_path, runner, "copilot", "explain", command, timeout_seconds=timeout_seconds)


__all__ = [
    "CodespaceInfo",
    "GhBridgeError",
    "codespace_ssh_config",
    "copilot_explain",
    "copilot_suggest",
    "create_codespace",
    "delete_codespace",
    "list_codespaces",
    "stop_codespace",
]
