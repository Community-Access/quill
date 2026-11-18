"""A repository's self-hosted runners, and its software bill of materials (PRD 14.2).

* **Runners** (Repository > Actions > Runners) lists the machines a
  repository runs its own jobs on: whether each is online, busy or idle, its
  system and its labels (``GET .../actions/runners``). GitHub shows them only
  to administrators, and says so.
* **Export Software Bill of Materials...** saves the repository's dependency
  graph as an SPDX file (``GET .../dependency-graph/sbom``), the list of every
  package it depends on that security reviews and procurement ask for.

Takes the Workbench's :class:`~quill.core.github.workbench_api.GitHubApi`.
wx-free and strict-typed.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from quill.core.error_codes import CodedError
from quill.core.github.explore_models import ExploreRow
from quill.core.github.rest_transport import GitHubRestError
from quill.core.github.workbench_api import GitHubApi

__all__ = ["RunnersError", "fetch_runners", "runner_row", "save_sbom", "sbom_name"]


class RunnersError(CodedError):
    """Runners or the bill of materials could not be read or saved; the message is said."""

    code = "QUILL-GITHUB-RUNNERS-SBOM"


def runner_row(repository: str, raw: Mapping[str, Any]) -> ExploreRow:
    name = str(raw.get("name") or "a runner")
    online = str(raw.get("status") or "") == "online"
    busy = bool(raw.get("busy"))
    state = ("online, busy" if busy else "online, idle") if online else "offline"
    system = str(raw.get("os") or "")
    labels = [
        str(label.get("name") or "")
        for label in raw.get("labels") or ()
        if isinstance(label, Mapping) and label.get("name")
    ]
    label = f"{name}: {state}" + (f", {system}" if system else "")
    detail = (
        f"Runner {name}, {state}"
        + (f", on {system}" if system else "")
        + "."
        + (f" Labels: {', '.join(labels)}." if labels else "")
    )
    url = f"https://github.com/{repository}/settings/actions/runners"
    return ExploreRow(label, detail, url, repository, "runner", str(raw.get("id") or ""), "", name)


def fetch_runners(api: GitHubApi, repository: str, *, limit: int = 100) -> list[ExploreRow]:
    try:
        data = api.rest(
            "GET",
            f"/repos/{repository}/actions/runners",
            query={"per_page": str(max(1, min(limit, 100)))},
        ).data
    except GitHubRestError as exc:
        if exc.status in (403, 404):
            raise RunnersError(
                f"GitHub shows {repository}'s runners only to its administrators."
            ) from exc
        raise
    rows = (data or {}).get("runners") if isinstance(data, Mapping) else None
    return [runner_row(repository, row) for row in rows or () if isinstance(row, Mapping)]


def sbom_name(repository: str) -> str:
    return repository.replace("/", "-") + ".spdx.json"


def save_sbom(api: GitHubApi, repository: str, target: Path) -> str:
    """Save the repository's SPDX bill of materials to *target*; returns the sentence to say."""
    try:
        data = api.rest("GET", f"/repos/{repository}/dependency-graph/sbom").data
    except GitHubRestError as exc:
        if exc.status in (403, 404):
            raise RunnersError(
                f"GitHub has no dependency graph for {repository}. It is turned on in the "
                "repository's settings, under Code security."
            ) from exc
        raise
    sbom = (data or {}).get("sbom") if isinstance(data, Mapping) else None
    if not isinstance(sbom, Mapping):
        raise RunnersError(f"GitHub sent no bill of materials for {repository}.")
    try:
        target.write_text(json.dumps(sbom, indent=2), encoding="utf-8")
    except OSError as exc:
        raise RunnersError(f"Could not save {target.name}: {exc}") from exc
    packages = len(sbom.get("packages") or ())
    return f"Saved {target.name}: {packages} packages, in SPDX format."
