"""The Fleet view: every repository in a Repository Set, one line each (PRD 22.12).

"quill: main at 3f2a9c1 from 2026-11-12, checks passing, 4 open pull
requests, latest release 3.2.0, no open Dependabot alerts." Each line names
the **exact revision** it describes (the default branch's head commit) and
when it was read, so a listener knows what the words are true of and how
fresh they are. A repository that could not be read keeps its line, with the
reason; a part that could not be read (alerts need more access than the rest)
says so inside the line instead of hiding the whole repository.

Reads, per repository, through the Workbench's one
:class:`~quill.core.github.workbench_api.GitHubApi`: ``GET /repos/{r}``, the
default branch's head (``GET /repos/{r}/commits/{branch}``), its combined
status (``.../commits/{sha}/status``), open pull requests
(``GET /repos/{r}/pulls``), the latest release (``.../releases/latest``) and
open Dependabot alerts (``.../dependabot/alerts``). All are rows the
Workbench already covers; nothing new leaves the machine.

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

from quill.core.github.across import why_failed

__all__ = ["FleetRow", "read_fleet"]

_WORKERS = 6
_PAGE = 100


@dataclass(frozen=True, slots=True)
class FleetRow:
    repository: str
    read_at: str
    error: str = ""
    default_branch: str = ""
    revision: str = ""
    revision_date: str = ""
    checks: str = ""
    open_pulls: str = ""
    latest_release: str = ""
    alerts: str = ""
    archived: bool = False

    @property
    def failed(self) -> bool:
        return bool(self.error)

    def sentence(self) -> str:
        if self.error:
            return f"{self.repository}: could not be read, {self.error}; read at {self.read_at}"
        head = f"{self.repository}: {self.default_branch} at {self.revision[:7]}"
        if self.revision_date:
            head += f" from {self.revision_date[:10]}"
        parts = [head, self.checks, self.open_pulls, self.latest_release, self.alerts]
        if self.archived:
            parts.insert(1, "archived")
        return ", ".join(p for p in parts if p) + f"; read at {self.read_at}"

    def detail(self) -> str:
        if self.error:
            return (
                f"{self.sentence()}.\n\nThe repository stays in the Fleet so it is not forgotten."
            )
        return "\n".join([
            f"Repository: {self.repository}",
            f"Default branch: {self.default_branch}",
            f"Revision: {self.revision}",
            f"Committed: {self.revision_date or 'unknown'}",
            f"Checks: {self.checks}",
            f"Pull requests: {self.open_pulls}",
            f"Latest release: {self.latest_release}",
            f"Alerts: {self.alerts}",
            f"Read at: {self.read_at}",
        ])


def _data(api: Any, path: str, query: Mapping[str, str] | None = None) -> Any:
    return api.rest("GET", path, query=dict(query) if query is not None else None).data


def _checks(api: Any, repo: str, sha: str) -> str:
    try:
        data = _data(api, f"/repos/{repo}/commits/{sha}/status")
    except Exception as exc:  # noqa: BLE001 - a part, not the repository
        return f"checks could not be read, {why_failed(exc)}"
    state = str(data.get("state") or "") if isinstance(data, Mapping) else ""
    total = int(data.get("total_count") or 0) if isinstance(data, Mapping) else 0
    if not total:
        return "no status checks reported"
    return {
        "success": "checks passing",
        "failure": "checks failing",
        "error": "checks erroring",
        "pending": "checks pending",
    }.get(state, f"checks {state or 'unknown'}")


def _pulls(api: Any, repo: str) -> str:
    try:
        data = _data(api, f"/repos/{repo}/pulls", {"state": "open", "per_page": str(_PAGE)})
    except Exception as exc:  # noqa: BLE001
        return f"pull requests could not be read, {why_failed(exc)}"
    count = len(data) if isinstance(data, list) else 0
    if count >= _PAGE:
        return f"{_PAGE} or more open pull requests"
    return f"{count} open pull request{'' if count == 1 else 's'}"


def _release(api: Any, repo: str) -> str:
    try:
        data = _data(api, f"/repos/{repo}/releases/latest")
    except Exception as exc:  # noqa: BLE001
        reason = why_failed(exc)
        return "no releases" if "not found" in reason else f"releases could not be read, {reason}"
    name = str(data.get("tag_name") or data.get("name") or "") if isinstance(data, Mapping) else ""
    return f"latest release {name}" if name else "no releases"


def _alerts(api: Any, repo: str) -> str:
    try:
        data = _data(api, f"/repos/{repo}/dependabot/alerts", {"state": "open", "per_page": "100"})
    except Exception as exc:  # noqa: BLE001
        reason = why_failed(exc)
        if reason.endswith(" are off"):
            return "Dependabot alerts are off"
        return f"alerts could not be read, {reason}"
    count = len(data) if isinstance(data, list) else 0
    if count >= _PAGE:
        return f"{_PAGE} or more open Dependabot alerts"
    if not count:
        return "no open Dependabot alerts"
    return f"{count} open Dependabot alert{'' if count == 1 else 's'}"


def _one(api: Any, repo: str, read_at: str) -> FleetRow:
    try:
        info = _data(api, f"/repos/{repo}")
        info = info if isinstance(info, Mapping) else {}
        branch = str(info.get("default_branch") or "")
        head = _data(api, f"/repos/{repo}/commits/{branch}") if branch else {}
        head = head if isinstance(head, Mapping) else {}
    except Exception as exc:  # noqa: BLE001 - the repository keeps its row
        return FleetRow(repo, read_at, error=why_failed(exc))
    sha = str(head.get("sha") or "")
    commit = head.get("commit")
    committer = commit.get("committer") if isinstance(commit, Mapping) else None
    date = str(committer.get("date") or "") if isinstance(committer, Mapping) else ""
    if not sha:
        return FleetRow(repo, read_at, error="it has no commits on its default branch")
    return FleetRow(
        repo,
        read_at,
        default_branch=branch,
        revision=sha,
        revision_date=date,
        checks=_checks(api, repo, sha),
        open_pulls=_pulls(api, repo),
        latest_release=_release(api, repo),
        alerts=_alerts(api, repo),
        archived=bool(info.get("archived")),
    )


def read_fleet(api: Any, repositories: Sequence[str], *, read_at: str) -> list[FleetRow]:
    """One row per repository, in the set's order. Runs off the UI thread."""
    chosen = list(dict.fromkeys(r.strip() for r in repositories if r.strip()))
    with ThreadPoolExecutor(max_workers=min(_WORKERS, max(1, len(chosen)))) as pool:
        return list(pool.map(lambda repo: _one(api, repo, read_at), chosen))
