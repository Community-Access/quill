"""Sheets for Actions: workflows, runs, jobs, artifacts, caches and runners (Appendix C).

A workflow turns on and off; a run, a job, an artifact and a cache are read in
full (their jobs, steps and sizes each a row); a runner's custom labels are
editable. Environments, deployments, secrets and variables are in
:mod:`quill.core.github.sheets_deploy`; releases and packages in
:mod:`quill.core.github.sheets_releases`.

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quill.core.github.permissions import WriteTier
from quill.core.github.sheet_engine import Ident, Read, SheetDef, Write
from quill.core.github.sheet_fields import dig, ed, lst, page, ro, when
from quill.core.workbench.properties import FieldKind, SheetSpec, Value

__all__ = ["ARTIFACT", "CACHE", "JOB", "RUN", "WORKFLOW"]

_O, _V, _A, _D = (
    WriteTier.ORGANIZING,
    WriteTier.VISIBLE,
    WriteTier.ACCESS,
    WriteTier.DESTRUCTIVE,
)
_K = FieldKind
_ACT = "/repos/{repo}/actions"


def _rows(key: str, render: Any) -> Any:
    def extract(data: Mapping[str, Any]) -> dict[str, Value]:
        return {key: tuple(render(row) for row in lst(data, key) if isinstance(row, Mapping))}

    return extract


# -- workflows, runs, jobs ------------------------------------------------------


def _workflow(data: Mapping[str, Any]) -> dict[str, Value]:
    return {
        "name": str(data.get("name") or ""),
        "path": str(data.get("path") or ""),
        "state": str(data.get("state") or ""),
        "enabled": data.get("state") == "active",
        "created": when(data.get("created_at")),
        "updated": str(data.get("updated_at") or ""),
        "url": str(data.get("html_url") or ""),
        "badge": str(data.get("badge_url") or ""),
    }


WORKFLOW = SheetDef(
    "workflow",
    SheetSpec(
        "workflow",
        "Workflow",
        (
            page(
                "general",
                "General",
                ro("name", "Name"),
                ro("path", "File"),
                ed(
                    "enabled",
                    "Enabled",
                    _K.CHECK,
                    "A disabled workflow does not run on any event until it is turned on again.",
                ),
                ro("state", "State"),
                ro("created", "Created", _K.DATE),
                ro("url", "Address", _K.LINK),
            ),
            page(
                "runs",
                "Runs",
                ro("runs_note", "Runs", help="Enter on the workflow lists its runs."),
            ),
            page(
                "triggers",
                "Triggers",
                ro(
                    "triggers_note",
                    "Triggers",
                    help="Its on: section; Open in Editor shows the file.",
                ),
            ),
            page(
                "usage",
                "Usage",
                ro("badge", "Status badge", _K.LINK, "A badge address to put in a README."),
            ),
        ),
    ),
    (Read(_ACT + "/workflows/{id}", _workflow),),
    {
        "enabled": Write(
            _ACT + "/workflows/{id}/enable",
            "repo:write",
            _V,
            "PUT",
            "toggle",
            off_path=_ACT + "/workflows/{id}/disable",
            off_method="PUT",
        ),
    },
    title=lambda ident: f"Workflow {ident.get('name') or ident['id']}",
    url=lambda ident: f"https://github.com/{ident['repo']}/actions",
)


def _run(data: Mapping[str, Any]) -> dict[str, Value]:
    return {
        "name": str(data.get("name") or data.get("display_title") or ""),
        "number": int(data.get("run_number") or 0),
        "attempt": int(data.get("run_attempt") or 0),
        "status": str(data.get("status") or ""),
        "conclusion": str(data.get("conclusion") or ""),
        "event": str(data.get("event") or ""),
        "branch": str(data.get("head_branch") or ""),
        "sha": str(data.get("head_sha") or ""),
        "actor": str(dig(data, "actor", "login") or ""),
        "created": when(data.get("created_at")),
        "updated": str(data.get("updated_at") or ""),
        "url": str(data.get("html_url") or ""),
    }


def _job_row(row: Mapping[str, Any]) -> str:
    return f"{row.get('name', '')}, {row.get('conclusion') or row.get('status') or ''}"


def _artifact_row(row: Mapping[str, Any]) -> str:
    return f"{row.get('name', '')}, {int(row.get('size_in_bytes') or 0) // 1024} KB"


def _timing(data: Mapping[str, Any]) -> dict[str, Value]:
    seconds = int(data.get("run_duration_ms") or 0) // 1000
    return {"duration": f"{seconds // 60} minutes {seconds % 60} seconds"}


RUN = SheetDef(
    "run",
    SheetSpec(
        "run",
        "Workflow Run",
        (
            page(
                "general",
                "General",
                ro("name", "Workflow"),
                ro("number", "Run", _K.NUMBER),
                ro("attempt", "Attempt", _K.NUMBER),
                ro("status", "Status"),
                ro("conclusion", "Conclusion"),
                ro("event", "Event"),
                ro("branch", "Branch"),
                ro("sha", "Commit"),
                ro("actor", "Started by"),
                ro("created", "Started", _K.DATE),
                ro("url", "Address", _K.LINK),
            ),
            page(
                "jobs",
                "Jobs",
                ro(
                    "jobs",
                    "Jobs",
                    _K.TABLE,
                    "Each job and how it ended; What Failed reads the failing steps.",
                ),
            ),
            page("artifacts", "Artifacts", ro("artifacts", "Artifacts", _K.TABLE)),
            page("usage", "Usage", ro("duration", "Duration")),
        ),
    ),
    (
        Read(_ACT + "/runs/{id}", _run),
        Read(_ACT + "/runs/{id}/jobs", _rows("jobs", _job_row), optional=True),
        Read(_ACT + "/runs/{id}/artifacts", _rows("artifacts", _artifact_row), optional=True),
        Read(_ACT + "/runs/{id}/timing", _timing, optional=True),
    ),
    title=lambda ident: f"Run {ident.get('number') or ident['id']}",
    url=lambda ident: f"https://github.com/{ident['repo']}/actions/runs/{ident['id']}",
)


def _job(data: Mapping[str, Any]) -> dict[str, Value]:
    return {
        "name": str(data.get("name") or ""),
        "status": str(data.get("status") or ""),
        "conclusion": str(data.get("conclusion") or ""),
        "runner": str(data.get("runner_name") or ""),
        "started": when(data.get("started_at")),
        "steps": tuple(
            f"{step.get('number', '')}. {step.get('name', '')}, "
            f"{step.get('conclusion') or step.get('status') or ''}"
            for step in lst(data, "steps")
            if isinstance(step, Mapping)
        ),
        "url": str(data.get("html_url") or ""),
    }


JOB = SheetDef(
    "job",
    SheetSpec(
        "job",
        "Job",
        (
            page(
                "general",
                "General",
                ro("name", "Name"),
                ro("status", "Status"),
                ro("conclusion", "Conclusion"),
                ro("runner", "Runner"),
                ro("started", "Started", _K.DATE),
                ro("url", "Address", _K.LINK),
            ),
            page("steps", "Steps", ro("steps", "Steps", _K.TABLE)),
            page("log", "Log", ro("log_note", "Log", help="Open in Editor opens its log.")),
        ),
    ),
    (Read(_ACT + "/jobs/{id}", _job),),
    title=lambda ident: f"Job {ident.get('name') or ident['id']}",
    url=lambda ident: f"https://github.com/{ident['repo']}/actions",
)


def _artifact(data: Mapping[str, Any]) -> dict[str, Value]:
    return {
        "name": str(data.get("name") or ""),
        "size": f"{int(data.get('size_in_bytes') or 0) // 1024} KB",
        "created": when(data.get("created_at")),
        "expires": when(data.get("expires_at")),
        "expired": bool(data.get("expired")),
    }


ARTIFACT = SheetDef(
    "artifact",
    SheetSpec(
        "artifact",
        "Artifact",
        (
            page(
                "general",
                "General",
                ro("name", "Name"),
                ro("size", "Size"),
                ro("created", "Created", _K.DATE),
                ro("expires", "Expires", _K.DATE),
                ro("expired", "Expired", _K.CHECK),
            ),
        ),
    ),
    (Read(_ACT + "/artifacts/{id}", _artifact),),
    title=lambda ident: f"Artifact {ident.get('name') or ident['id']}",
)


def _cache(data: Mapping[str, Any], ident: Ident) -> dict[str, Value]:
    for row in lst(data, "actions_caches"):
        if isinstance(row, Mapping) and str(row.get("id")) == ident.get("id"):
            return {
                "key": str(row.get("key") or ""),
                "ref": str(row.get("ref") or ""),
                "size": f"{int(row.get('size_in_bytes') or 0) // 1024} KB",
                "last_used": when(row.get("last_accessed_at")),
                "created": when(row.get("created_at")),
            }
    return {}


CACHE = SheetDef(
    "cache",
    SheetSpec(
        "cache",
        "Actions Cache",
        (
            page(
                "general",
                "General",
                ro("key", "Key"),
                ro("ref", "Branch or ref"),
                ro("size", "Size"),
                ro("last_used", "Last used", _K.DATE),
                ro("created", "Created", _K.DATE),
            ),
        ),
    ),
    (Read(_ACT + "/caches", pick=_cache),),
    title=lambda ident: f"Cache {ident['id']}",
)
