"""A workflow file as linear pieces: triggers, jobs, steps, inputs, permissions (PRD 22.1).

GitHub's own workflow editor is a code editor with a sidebar of actions; the
dependency graph between jobs is a drawing. Here a workflow is read and
changed as lists a screen reader walks in order:

* **Triggers**, one row each: "On a push, branches main", "Run by hand, 2
  inputs", "On a schedule: 30 5 * * 1".
* **Jobs**, one row each, with the graph said in words: "Build, runs on
  ubuntu-latest, runs after Test and Lint, 4 steps". :func:`order_sentence`
  reads the whole graph as stages ("First Test and Lint, together. Then
  Build.").
* **Steps** of a job, one row each: "2. Run tests: runs pytest -q".
* **Permissions**, one level per scope.

A :class:`WorkflowDraft` keeps the file as plain dictionaries, so whatever
the form does not show (``concurrency``, ``strategy``, a key GitHub adds next
year) survives the round trip; the form only changes what it was asked to.
The checks GitHub would reject a file for are in
:mod:`quill.core.github.workflow_checks`. YAML goes through
:mod:`quill.core.github.actions_yaml`, so ``on:`` stays ``on:``.

wx-free and strict-typed.
"""

from __future__ import annotations

import copy
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from quill.core.github.actions_yaml import (
    dump_mapping,
    header_comments,
    load_mapping,
    same_data,
    scalar,
    scalar_text,
)

__all__ = [
    "EVENT_WORDS",
    "FILTER_KEYS",
    "INPUT_TYPES",
    "PERMISSION_LEVELS",
    "PERMISSION_SCOPES",
    "WorkflowDraft",
    "add_job",
    "dispatch_inputs",
    "dump_workflow",
    "input_summary",
    "job",
    "job_ids",
    "job_name",
    "job_summary",
    "load_workflow",
    "make_job_id",
    "move_job",
    "needs_of",
    "needs_sentence",
    "new_workflow",
    "order_sentence",
    "pairs_text",
    "parse_pairs",
    "permissions_summary",
    "remove_job",
    "remove_trigger",
    "replace_job",
    "run_order",
    "schedule_crons",
    "set_trigger",
    "step_summary",
    "trigger_summary",
    "triggers",
]

#: How a trigger row names its event; any other event is named by its key.
EVENT_WORDS: dict[str, str] = {
    "push": "On a push",
    "pull_request": "On a pull request",
    "pull_request_target": "On a pull request, with the base branch's rights",
    "workflow_dispatch": "Run by hand",
    "schedule": "On a schedule",
    "workflow_call": "Called by another workflow",
    "workflow_run": "After another workflow runs",
    "release": "On a release",
    "issues": "On an issue",
    "issue_comment": "On an issue or pull request comment",
    "merge_group": "In the merge queue",
    "repository_dispatch": "When sent an event through the API",
}

#: The filters a push or pull request trigger takes, in the order they are shown.
FILTER_KEYS: tuple[str, ...] = (
    "branches",
    "branches-ignore",
    "tags",
    "tags-ignore",
    "paths",
    "paths-ignore",
    "types",
)

#: ``workflow_dispatch`` input types GitHub accepts.
INPUT_TYPES: tuple[str, ...] = ("string", "boolean", "choice", "number", "environment")

#: The GITHUB_TOKEN permission scopes, in GitHub's documented order.
PERMISSION_SCOPES: tuple[str, ...] = (
    "actions",
    "attestations",
    "checks",
    "contents",
    "deployments",
    "discussions",
    "id-token",
    "issues",
    "models",
    "packages",
    "pages",
    "pull-requests",
    "repository-projects",
    "security-events",
    "statuses",
)
PERMISSION_LEVELS: tuple[str, ...] = ("read", "write", "none")

_JOB_ID = re.compile(r"[^A-Za-z0-9_-]+")


@dataclass
class WorkflowDraft:
    """One workflow file as dictionaries, with what it was opened from."""

    data: dict[str, Any]
    header: str = ""
    original_text: str = ""
    original_data: dict[str, Any] = field(default_factory=dict)

    def changed(self) -> bool:
        return not same_data(self.data, self.original_data)


def load_workflow(text: str) -> WorkflowDraft:
    """Read a workflow; raises :class:`~quill.core.github.actions_yaml.ActionsYamlError`."""
    data = load_mapping(text, "workflow")
    return WorkflowDraft(data, header_comments(text), text, copy.deepcopy(data))


def dump_workflow(draft: WorkflowDraft) -> str:
    """The draft as YAML; a draft nobody changed is the text it was opened from."""
    if draft.original_text and not draft.changed():
        return draft.original_text
    return dump_mapping(draft.data, draft.header)


def new_workflow(name: str) -> WorkflowDraft:
    """A starter: on a push to main and by hand, one job that checks out the code."""
    data: dict[str, Any] = {
        "name": name or "CI",
        "on": {"push": {"branches": ["main"]}, "workflow_dispatch": None},
        "permissions": {"contents": "read"},
        "jobs": {
            "build": {
                "runs-on": "ubuntu-latest",
                "steps": [
                    {"name": "Check out the code", "uses": "actions/checkout@v4"},
                    {"name": "Build", "run": "echo Replace this with your build command."},
                ],
            }
        },
    }
    return WorkflowDraft(data)


# -- triggers --------------------------------------------------------------------------


def triggers(draft: WorkflowDraft) -> dict[str, Any]:
    """``event -> its settings`` whichever way ``on:`` was written (a word, a list, keys)."""
    raw = draft.data.get("on")
    if isinstance(raw, str):
        return {raw: None}
    if isinstance(raw, list):
        return {str(event): None for event in raw}
    if isinstance(raw, dict):
        return {str(event): value for event, value in raw.items()}
    return {}


def set_trigger(draft: WorkflowDraft, event: str, settings: Any) -> None:
    """Add or replace one trigger; ``on:`` becomes keys, and the order is kept."""
    found = triggers(draft)
    found[event] = settings
    draft.data["on"] = found


def remove_trigger(draft: WorkflowDraft, event: str) -> None:
    found = triggers(draft)
    found.pop(event, None)
    draft.data["on"] = found


def _words(values: Iterable[Any]) -> str:
    items = [str(v) for v in values]
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def schedule_crons(settings: Any) -> list[str]:
    if not isinstance(settings, list):
        return []
    return [str(entry.get("cron", "")) for entry in settings if isinstance(entry, dict)]


def dispatch_inputs(settings: Any) -> dict[str, dict[str, Any]]:
    """A ``workflow_dispatch`` (or ``workflow_call``) trigger's inputs, by name."""
    if not isinstance(settings, dict) or not isinstance(settings.get("inputs"), dict):
        return {}
    return {
        str(name): dict(spec) if isinstance(spec, dict) else {}
        for name, spec in settings["inputs"].items()
    }


def input_summary(name: str, spec: Mapping[str, Any]) -> str:
    """ "environment, a choice of staging or production, required, default staging"."""
    kind = str(spec.get("type", "string"))
    parts = [name]
    options = spec.get("options")
    if kind == "choice" and isinstance(options, list):
        parts.append(f"a choice of {_words(options) or 'nothing yet'}")
    else:
        parts.append({"boolean": "yes or no", "number": "a number"}.get(kind, f"a {kind}"))
    if spec.get("required") is True:
        parts.append("required")
    if spec.get("default") not in (None, ""):
        parts.append(f"default {spec.get('default')}")
    if spec.get("description"):
        parts.append(str(spec["description"]))
    return ", ".join(parts)


def trigger_summary(event: str, settings: Any) -> str:
    """One trigger as a row: "On a push, branches main, paths docs/**"."""
    said = EVENT_WORDS.get(event, event)
    if event == "schedule":
        crons = schedule_crons(settings)
        return f"{said}: {_words(crons)}" if crons else f"{said}, with no times yet"
    if event in ("workflow_dispatch", "workflow_call"):
        count = len(dispatch_inputs(settings))
        if count:
            return f"{said}, {count} input{'s' if count != 1 else ''}"
        return said
    parts = [said]
    if isinstance(settings, dict):
        for key in FILTER_KEYS:
            values = settings.get(key)
            if isinstance(values, str):
                values = [values]
            if isinstance(values, list) and values:
                parts.append(f"{key.replace('-', ' ')} {_words(values)}")
    return ", ".join(parts)


# -- permissions ------------------------------------------------------------------------


def permissions_summary(value: Any) -> str:
    """ "contents read, pull-requests write", or what GitHub's default means."""
    if value is None:
        return "not set, so the repository's default for GITHUB_TOKEN applies"
    if isinstance(value, str):
        return {"read-all": "read everything", "write-all": "write everything"}.get(value, value)
    if isinstance(value, dict):
        if not value:
            return "none at all"
        return ", ".join(f"{scope} {level}" for scope, level in value.items())
    return str(value)


# -- jobs -------------------------------------------------------------------------------


def _jobs(draft: WorkflowDraft) -> dict[str, Any]:
    jobs = draft.data.get("jobs")
    if not isinstance(jobs, dict):
        jobs = {}
        draft.data["jobs"] = jobs
    return jobs


def job_ids(draft: WorkflowDraft) -> list[str]:
    jobs = draft.data.get("jobs")
    return [str(key) for key in jobs] if isinstance(jobs, dict) else []


def job(draft: WorkflowDraft, job_id: str) -> dict[str, Any]:
    found = _jobs(draft).get(job_id)
    return found if isinstance(found, dict) else {}


def job_name(draft: WorkflowDraft, job_id: str) -> str:
    """What a person calls the job: its ``name:``, or its id."""
    name = job(draft, job_id).get("name")
    return str(name) if isinstance(name, str) and name.strip() else job_id


def needs_of(spec: Mapping[str, Any]) -> list[str]:
    needs = spec.get("needs")
    if isinstance(needs, str):
        return [needs]
    if isinstance(needs, list):
        return [str(n) for n in needs]
    return []


def needs_sentence(draft: WorkflowDraft, job_id: str) -> str:
    """ "Build runs after Test and Lint." or "Test starts first; it needs no other job." """
    name = job_name(draft, job_id)
    needs = needs_of(job(draft, job_id))
    if not needs:
        return f"{name} starts first; it needs no other job."
    known = set(job_ids(draft))
    named = [job_name(draft, n) if n in known else f"{n} (no such job)" for n in needs]
    return f"{name} runs after {_words(named)}."


def run_order(draft: WorkflowDraft) -> list[list[str]]:
    """Jobs in stages: each stage starts when every job it needs has finished.

    A job caught in a loop of needs, or needing a job that does not exist,
    can never start; those are the last stage, which the checks report.
    """
    ids = job_ids(draft)
    waiting = {i: set(needs_of(job(draft, i))) for i in ids}
    done: set[str] = set()
    stages: list[list[str]] = []
    while waiting:
        ready = [i for i in ids if i in waiting and waiting[i] <= done]
        if not ready:
            stages.append([i for i in ids if i in waiting])
            break
        stages.append(ready)
        for i in ready:
            done.add(i)
            del waiting[i]
    return stages


def order_sentence(draft: WorkflowDraft) -> str:
    """The whole graph: "First Test and Lint, together. Then Build. Then Deploy." """
    stages = run_order(draft)
    if not stages:
        return "No jobs yet."
    said: list[str] = []
    blocked = bool(stages) and any(
        not set(needs_of(job(draft, i))) <= {j for stage in stages[:-1] for j in stage}
        for i in stages[-1]
    )
    for index, stage in enumerate(stages):
        names = _words(job_name(draft, i) for i in stage)
        together = ", together" if len(stage) > 1 else ""
        if blocked and index == len(stages) - 1:
            said.append(f"Never: {names}, which wait for a job that never finishes.")
        else:
            said.append(f"{'First' if index == 0 else 'Then'} {names}{together}.")
    return " ".join(said)


def job_summary(draft: WorkflowDraft, job_id: str) -> str:
    """ "Build, runs on ubuntu-latest, runs after Test and Lint, 4 steps"."""
    spec = job(draft, job_id)
    parts = [job_name(draft, job_id)]
    if job_name(draft, job_id) != job_id:
        parts[0] += f" ({job_id})"
    if spec.get("uses"):
        parts.append(f"calls {spec['uses']}")
    runs_on = spec.get("runs-on")
    if isinstance(runs_on, list):
        parts.append(f"runs on {_words(runs_on)}")
    elif runs_on:
        parts.append(f"runs on {runs_on}")
    needs = needs_of(spec)
    if needs:
        parts.append("runs after " + _words(job_name(draft, n) for n in needs))
    steps = spec.get("steps")
    if isinstance(steps, list):
        parts.append(f"{len(steps)} step{'s' if len(steps) != 1 else ''}")
    if "permissions" in spec:
        parts.append("permissions " + permissions_summary(spec.get("permissions")))
    return ", ".join(parts)


def make_job_id(name: str, taken: Iterable[str] = ()) -> str:
    """A job id from a name: letters, digits, ``-`` and ``_``, starting with a letter."""
    base = _JOB_ID.sub("-", name.strip().casefold()).strip("-_") or "job"
    if not (base[0].isalpha() or base[0] == "_"):
        base = f"job-{base}"
    used = set(taken)
    candidate, number = base, 2
    while candidate in used:
        candidate = f"{base}-{number}"
        number += 1
    return candidate


def add_job(draft: WorkflowDraft, job_id: str, spec: dict[str, Any]) -> None:
    _jobs(draft)[job_id] = spec


def replace_job(draft: WorkflowDraft, old_id: str, new_id: str, spec: dict[str, Any]) -> None:
    """Put *spec* where *old_id* was, under *new_id*; other jobs' needs follow a rename."""
    jobs = _jobs(draft)
    rebuilt: dict[str, Any] = {}
    for key, value in jobs.items():
        rebuilt[new_id if key == old_id else key] = spec if key == old_id else value
    if old_id not in jobs:
        rebuilt[new_id] = spec
    if new_id != old_id:
        for key, value in rebuilt.items():
            if key != new_id and isinstance(value, dict) and old_id in needs_of(value):
                _set_needs(value, [new_id if n == old_id else n for n in needs_of(value)])
    draft.data["jobs"] = rebuilt


def _set_needs(spec: dict[str, Any], needs: list[str]) -> None:
    if not needs:
        spec.pop("needs", None)
    elif len(needs) == 1 and isinstance(spec.get("needs"), str):
        spec["needs"] = needs[0]
    else:
        spec["needs"] = needs


def remove_job(draft: WorkflowDraft, job_id: str) -> list[str]:
    """Remove a job; returns the jobs that needed it, which now no longer do."""
    jobs = _jobs(draft)
    jobs.pop(job_id, None)
    freed: list[str] = []
    for key, value in jobs.items():
        if isinstance(value, dict) and job_id in needs_of(value):
            _set_needs(value, [n for n in needs_of(value) if n != job_id])
            freed.append(key)
    return freed


def move_job(draft: WorkflowDraft, job_id: str, delta: int) -> bool:
    """Move a job up (-1) or down (+1) in the file; the graph is unchanged by order."""
    ids = job_ids(draft)
    if job_id not in ids:
        return False
    index = ids.index(job_id)
    target = index + delta
    if not 0 <= target < len(ids):
        return False
    ids[index], ids[target] = ids[target], ids[index]
    jobs = _jobs(draft)
    draft.data["jobs"] = {key: jobs[key] for key in ids}
    return True


# -- steps ------------------------------------------------------------------------------


def step_summary(step: Mapping[str, Any], number: int) -> str:
    """ "2. Run tests: runs pytest -q" or "1. Check out: uses actions/checkout@v4"."""
    name = str(step.get("name") or step.get("id") or "").strip()
    if step.get("uses"):
        what = f"uses {step['uses']}"
    elif step.get("run"):
        first = str(step["run"]).strip().splitlines()[0] if str(step["run"]).strip() else ""
        more = len(str(step["run"]).strip().splitlines()) - 1
        what = f"runs {first}" + (
            f" and {more} more line{'s' if more != 1 else ''}" if more else ""
        )
    else:
        what = "does nothing yet"
    head = f"{number}. {name}: " if name else f"{number}. "
    extra = f", only if {step['if']}" if step.get("if") else ""
    return head + what + extra


def parse_pairs(text: str) -> dict[str, Any]:
    """ "key: value" lines (``with:`` and ``env:``) as a dictionary; blank lines skipped."""
    found: dict[str, Any] = {}
    for line in text.replace("\r\n", "\n").split("\n"):
        if not line.strip():
            continue
        key, _sep, value = line.partition(":")
        if key.strip():
            found[key.strip()] = scalar(value)
    return found


def pairs_text(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    return "\n".join(f"{key}: {scalar_text(inner)}" for key, inner in value.items())
