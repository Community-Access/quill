"""What GitHub would reject a workflow file for, said before it is saved (PRD 22.1).

GitHub only reports a broken workflow after the file is pushed: the run fails
at once with "Invalid workflow file", and nothing ran. :func:`check_workflow`
finds the same problems first, each naming where it is ("Job build, step 3")
and what to do:

* a top-level key, job key or step key GitHub does not know;
* no ``on:``, an event GitHub does not have, filters it cannot combine
  (``branches`` with ``branches-ignore``), a schedule that is not five fields;
* a ``workflow_dispatch`` input with an unknown type, or a choice with no
  options;
* no jobs, a job id GitHub refuses, a job with no ``runs-on`` (and no
  reusable workflow), or a reusable-workflow job that also has steps;
* ``needs`` naming a job that does not exist, the job itself, or a loop;
* a step with both ``uses`` and ``run`` or neither, an action with no
  version (``actions/checkout`` without ``@v4``), and step ids used twice;
* a permission scope or level GitHub does not have.

Expressions (``${{ }}``) are not evaluated; GitHub checks those as it runs.
wx-free and strict-typed.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from quill.core.github.workflow_authoring import (
    FILTER_KEYS,
    INPUT_TYPES,
    PERMISSION_LEVELS,
    PERMISSION_SCOPES,
    WorkflowDraft,
    dispatch_inputs,
    job_ids,
    needs_of,
    schedule_crons,
    triggers,
)

__all__ = ["EVENTS", "JOB_KEYS", "STEP_KEYS", "TOP_KEYS", "WorkflowProblem", "check_workflow"]

TOP_KEYS = frozenset({
    "name",
    "run-name",
    "on",
    "permissions",
    "env",
    "defaults",
    "concurrency",
    "jobs",
})
JOB_KEYS = frozenset({
    "name",
    "permissions",
    "needs",
    "if",
    "runs-on",
    "snapshot",
    "environment",
    "concurrency",
    "outputs",
    "env",
    "defaults",
    "steps",
    "timeout-minutes",
    "strategy",
    "continue-on-error",
    "container",
    "services",
    "uses",
    "with",
    "secrets",
})
STEP_KEYS = frozenset({
    "id",
    "if",
    "name",
    "uses",
    "run",
    "shell",
    "with",
    "env",
    "continue-on-error",
    "timeout-minutes",
    "working-directory",
})
#: Every event a workflow can be triggered by (GitHub's "Events that trigger workflows").
EVENTS = frozenset({
    "branch_protection_rule",
    "check_run",
    "check_suite",
    "create",
    "delete",
    "deployment",
    "deployment_status",
    "discussion",
    "discussion_comment",
    "fork",
    "gollum",
    "image_version",
    "issue_comment",
    "issues",
    "label",
    "merge_group",
    "milestone",
    "page_build",
    "project",
    "project_card",
    "project_column",
    "public",
    "pull_request",
    "pull_request_review",
    "pull_request_review_comment",
    "pull_request_target",
    "push",
    "registry_package",
    "release",
    "repository_dispatch",
    "schedule",
    "status",
    "watch",
    "workflow_call",
    "workflow_dispatch",
    "workflow_run",
})
_FILTERED = frozenset({"push", "pull_request", "pull_request_target"})
_INPUT_KEYS = frozenset({"description", "required", "default", "type", "options"})
_JOB_ID = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")
_ONLY = {"id-token": ("write", "none"), "models": ("read", "none")}


@dataclass(frozen=True, slots=True)
class WorkflowProblem:
    """One reason GitHub would refuse the file: where it is, and what to do."""

    where: str
    sentence: str

    def text(self) -> str:
        return f"{self.where}: {self.sentence}"


def _check_permissions(value: Any, where: str, out: list[WorkflowProblem]) -> None:
    if value is None:
        return
    if isinstance(value, str):
        if value not in ("read-all", "write-all"):
            out.append(
                WorkflowProblem(where, f"permissions {value!r} is not read-all or write-all.")
            )
        return
    if not isinstance(value, dict):
        out.append(WorkflowProblem(where, "permissions must be scopes with levels."))
        return
    for scope, level in value.items():
        if scope not in PERMISSION_SCOPES:
            out.append(
                WorkflowProblem(where, f"{scope} is not a permission GitHub has; remove it.")
            )
            continue
        allowed = _ONLY.get(str(scope), PERMISSION_LEVELS)
        if level not in allowed:
            out.append(
                WorkflowProblem(
                    where, f"{scope} cannot be {level}; it can be {' or '.join(allowed)}."
                )
            )


def _check_triggers(draft: WorkflowDraft, out: list[WorkflowProblem]) -> None:
    raw = draft.data.get("on")
    if raw is None or raw == {} or raw == []:
        out.append(WorkflowProblem("Triggers", "there are none, so nothing would ever start it."))
        return
    for event, settings in triggers(draft).items():
        where = f"Trigger {event}"
        if event not in EVENTS:
            out.append(WorkflowProblem(where, f"{event} is not an event GitHub has."))
            continue
        if event in _FILTERED and isinstance(settings, dict):
            for key in settings:
                if key not in FILTER_KEYS:
                    out.append(WorkflowProblem(where, f"{key} is not a filter it takes."))
            for kept, ignored in (
                ("branches", "branches-ignore"),
                ("tags", "tags-ignore"),
                ("paths", "paths-ignore"),
            ):
                if kept in settings and ignored in settings:
                    out.append(
                        WorkflowProblem(
                            where, f"{kept} and {ignored} cannot both be used; use ! in {kept}."
                        )
                    )
        if event == "schedule":
            crons = schedule_crons(settings)
            if not crons:
                out.append(WorkflowProblem(where, "a schedule needs at least one cron time."))
            for cron in crons:
                if len(cron.split()) != 5:
                    out.append(
                        WorkflowProblem(
                            where, f"{cron!r} is not five fields (minute hour day month weekday)."
                        )
                    )
        if event in ("workflow_dispatch", "workflow_call"):
            _check_inputs(event, settings, where, out)


def _check_inputs(event: str, settings: Any, where: str, out: list[WorkflowProblem]) -> None:
    allowed = set(INPUT_TYPES) if event == "workflow_dispatch" else {"string", "boolean", "number"}
    for name, spec in dispatch_inputs(settings).items():
        here = f"{where}, input {name}"
        for key in spec:
            if key not in _INPUT_KEYS:
                out.append(WorkflowProblem(here, f"{key} is not something an input has."))
        kind = str(spec.get("type", "string"))
        if event == "workflow_call" and "type" not in spec:
            out.append(WorkflowProblem(here, "an input of a called workflow needs a type."))
        elif kind not in allowed:
            out.append(
                WorkflowProblem(here, f"{kind} is not an input type; use {', '.join(allowed)}.")
            )
        if kind == "choice":
            options = spec.get("options")
            if not isinstance(options, list) or not options:
                out.append(WorkflowProblem(here, "a choice needs at least one option."))
            elif spec.get("default") not in (None, "") and spec.get("default") not in options:
                out.append(WorkflowProblem(here, "its default is not one of its options."))


def _check_step(step: Any, where: str, out: list[WorkflowProblem]) -> None:
    if not isinstance(step, dict):
        out.append(WorkflowProblem(where, "a step must be a set of keys."))
        return
    for key in step:
        if key not in STEP_KEYS:
            out.append(WorkflowProblem(where, f"{key} is not something a step has."))
    uses, run = step.get("uses"), step.get("run")
    if uses and run:
        out.append(
            WorkflowProblem(where, "a step either uses an action or runs commands, not both.")
        )
    elif not uses and not run:
        out.append(WorkflowProblem(where, "it neither uses an action nor runs anything."))
    if isinstance(uses, str) and uses and not uses.startswith(("./", "docker://")):
        if "@" not in uses:
            out.append(
                WorkflowProblem(
                    where, f"{uses} has no version; add one, such as {uses}@v4 or a commit."
                )
            )


def _check_job(job_id: str, spec: Any, known: set[str], out: list[WorkflowProblem]) -> None:
    where = f"Job {job_id}"
    if not _JOB_ID.match(job_id):
        out.append(
            WorkflowProblem(
                where,
                "a job id starts with a letter or _ and has only letters, digits, - and _.",
            )
        )
    if not isinstance(spec, dict):
        out.append(WorkflowProblem(where, "a job must be a set of keys."))
        return
    for key in spec:
        if key not in JOB_KEYS:
            out.append(WorkflowProblem(where, f"{key} is not something a job has."))
    calls = bool(spec.get("uses"))
    if calls and "steps" in spec:
        out.append(
            WorkflowProblem(where, "a job that calls a reusable workflow cannot have steps.")
        )
    if not calls and not spec.get("runs-on"):
        out.append(WorkflowProblem(where, "it has no runs-on, so no runner would take it."))
    if not calls:
        steps = spec.get("steps")
        if not isinstance(steps, list) or not steps:
            out.append(WorkflowProblem(where, "it has no steps."))
        else:
            seen: set[str] = set()
            for index, step in enumerate(steps, 1):
                _check_step(step, f"{where}, step {index}", out)
                step_id = step.get("id") if isinstance(step, dict) else None
                if isinstance(step_id, str) and step_id:
                    if step_id in seen:
                        out.append(
                            WorkflowProblem(
                                f"{where}, step {index}", f"the id {step_id} is used twice."
                            )
                        )
                    seen.add(step_id)
    for need in needs_of(spec):
        if need == job_id:
            out.append(WorkflowProblem(where, "it needs itself, so it could never start."))
        elif need not in known:
            out.append(
                WorkflowProblem(
                    where, f"it needs {need}, and there is no job {need}. Fix or remove it."
                )
            )
    _check_permissions(spec.get("permissions"), where, out)


def check_workflow(draft: WorkflowDraft) -> list[WorkflowProblem]:
    """Every reason GitHub would refuse the file; empty when it would take it."""
    out: list[WorkflowProblem] = []
    for key in draft.data:
        if key not in TOP_KEYS:
            out.append(WorkflowProblem("The file", f"{key} is not something a workflow has."))
    _check_triggers(draft, out)
    _check_permissions(draft.data.get("permissions"), "Workflow permissions", out)
    jobs = draft.data.get("jobs")
    if not isinstance(jobs, Mapping) or not jobs:
        out.append(WorkflowProblem("Jobs", "there are none; a workflow needs at least one."))
        return out
    known = set(job_ids(draft))
    for job_id, spec in jobs.items():
        _check_job(str(job_id), spec, known, out)
    looped = _in_a_loop(draft, known)
    if looped:
        out.append(
            WorkflowProblem(
                "Jobs",
                f"{', '.join(looped)} wait for each other in a loop, so none of them "
                "could ever start.",
            )
        )
    return out


def _in_a_loop(draft: WorkflowDraft, known: set[str]) -> list[str]:
    """Jobs on a loop of two or more needs (a job needing itself is said on its own)."""
    edges = {
        j: [n for n in needs_of(draft.data["jobs"].get(j) or {}) if n in known and n != j]
        for j in job_ids(draft)
    }
    found: list[str] = []
    for start in job_ids(draft):
        seen: set[str] = set()
        todo = list(edges.get(start, []))
        while todo:
            current = todo.pop()
            if current == start:
                found.append(start)
                break
            if current in seen:
                continue
            seen.add(current)
            todo.extend(edges.get(current, []))
    return found
