"""Saved find-and-replace jobs: a named list of steps, run in order, as one edit.

Both editors run the same jobs through the same code (``quill/ui/replace_jobs.py``
shows them; this module decides what they do). A job is for the clean-up somebody
does every week -- the same six replacements on every exported transcript, the
same quote marks straightened in every pasted email -- where retyping six Find
and Replace pairs is the whole cost and a typo in one of them is the risk.

Rules that a listener depends on and cannot check by eye:

* **Steps run in order, each on the result of the one before**, which is the
  only order a person can reason about: "first turn tabs into spaces, then
  squeeze the spaces".
* **A plain step replaces exactly what was typed.** Only a regular-expression
  step reads its replacement as a template (``\\1``, ``\\g<name>``), so
  ``C:\\new`` in a plain step stays ``C:\\new`` -- the same rule Replace All
  follows in both editors.
* **A bad pattern stops the whole job before anything changes.** Every step
  runs on a copy, and the document is written once, after the last step -- half
  a job is worse than none, a state no saved job describes.
* **The count is of replacements, per step**, so "Tidy spaces: 14 replacements"
  is something you can trust, and a step that matched nothing is named.

Stored with :func:`quill.core.storage.write_json_atomic` (classified ``content``
in the persistence audit): user-created data whose shape only ever grows.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from quill.core.error_codes import CodedError
from quill.core.storage import write_json_atomic

__all__ = [
    "JOBS_FILE_NAME",
    "SAMPLE_JOBS",
    "ReplaceJob",
    "ReplaceJobError",
    "ReplaceStep",
    "describe_run",
    "describe_step",
    "load_replace_jobs",
    "run_job",
    "save_replace_jobs",
    "step_error",
    "unique_job_name",
]

#: The file, in each editor's own data folder.
JOBS_FILE_NAME = "replace_jobs.json"

_SCHEMA = 1


class ReplaceJobError(CodedError):
    """A step's pattern cannot be used; the message names the step and why."""

    code = "QUILL-EDIT-REPLACEJOB-PATTERN"


@dataclass(slots=True)
class ReplaceStep:
    """One find-and-replace pair and its two options."""

    find: str
    replace: str = ""
    regex: bool = False
    match_case: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "find": self.find,
            "replace": self.replace,
            "regex": self.regex,
            "match_case": self.match_case,
        }


@dataclass(slots=True)
class ReplaceJob:
    """A named list of steps."""

    name: str
    steps: list[ReplaceStep] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {"name": self.name, "steps": [step.to_dict() for step in self.steps]}


def _samples() -> list[ReplaceJob]:
    """Three jobs to start from, each one a real chore and a worked example.

    Deliberately small: they show the shape (a regular expression, a plain
    step, several steps in order) and are worth keeping as they are.
    """
    return [
        ReplaceJob(
            "Tidy spaces",
            [
                ReplaceStep("\t", " "),
                ReplaceStep(r"[ ]{2,}", " ", regex=True),
                ReplaceStep(r"[ ]+$", "", regex=True),
            ],
        ),
        ReplaceJob(
            "Straighten quote marks",
            [
                ReplaceStep("\u201c", '"'),
                ReplaceStep("\u201d", '"'),
                ReplaceStep("\u2018", "'"),
                ReplaceStep("\u2019", "'"),
            ],
        ),
        ReplaceJob(
            "Close up blank lines",
            [ReplaceStep(r"\n{3,}", r"\n\n", regex=True)],
        ),
    ]


#: What a person sees the first time, before they have saved anything.
SAMPLE_JOBS: tuple[ReplaceJob, ...] = tuple(_samples())


def _step_from(payload: object) -> ReplaceStep | None:
    if not isinstance(payload, dict):
        return None
    find = payload.get("find")
    if not isinstance(find, str) or not find:
        return None
    replace = payload.get("replace", "")
    return ReplaceStep(
        find=find,
        replace=replace if isinstance(replace, str) else "",
        regex=bool(payload.get("regex", False)),
        match_case=bool(payload.get("match_case", False)),
    )


def _job_from(payload: object) -> ReplaceJob | None:
    if not isinstance(payload, dict):
        return None
    name = payload.get("name")
    if not isinstance(name, str) or not name.strip():
        return None
    raw_steps = payload.get("steps", [])
    steps = [s for s in (_step_from(one) for one in raw_steps or []) if s is not None]
    return ReplaceJob(name=name.strip(), steps=steps)


def load_replace_jobs(path: Path) -> list[ReplaceJob]:
    """The saved jobs, or the samples when nothing has been saved yet.

    Tolerant on purpose: an unreadable or hand-damaged file gives the samples
    rather than an error at the moment somebody wanted to run a job, and an
    entry that cannot be read is skipped rather than costing the others.
    """
    try:
        payload: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return _samples()
    raw_jobs = payload.get("jobs", []) if isinstance(payload, dict) else []
    return [job for job in (_job_from(one) for one in raw_jobs or []) if job is not None]


def save_replace_jobs(path: Path, jobs: list[ReplaceJob]) -> None:
    """Write every job, atomically, so a power cut cannot leave half a file."""
    write_json_atomic(path, {"schema": _SCHEMA, "jobs": [job.to_dict() for job in jobs]})


def unique_job_name(wanted: str, jobs: list[ReplaceJob], *, ignore: int = -1) -> bool:
    """Whether *wanted* is free (case ignored), not counting the job at *ignore*."""
    needle = wanted.strip().casefold()
    return bool(needle) and not any(
        index != ignore and job.name.casefold() == needle for index, job in enumerate(jobs)
    )


def _compile(step: ReplaceStep) -> re.Pattern[str]:
    flags = re.MULTILINE if step.regex else 0
    if not step.match_case:
        flags |= re.IGNORECASE
    return re.compile(step.find if step.regex else re.escape(step.find), flags)


def step_error(step: ReplaceStep) -> str:
    """Why *step* cannot run, in a sentence, or "" when it can."""
    if not step.find:
        return "Find what is empty."
    try:
        _compile(step)
    except re.error as error:
        return f"The regular expression is not valid: {error}."
    return ""


def _replacement(step: ReplaceStep) -> Any:
    if step.regex:
        return step.replace
    literal = step.replace
    return lambda _match: literal


def run_job(text: str, job: ReplaceJob) -> tuple[str, list[int]]:
    """Run every step in order; return the new text and each step's count.

    Raises :class:`ReplaceJobError` before changing anything when a step
    cannot run, naming the step by its number.
    """
    compiled = []
    for number, step in enumerate(job.steps, start=1):
        problem = step_error(step)
        if problem:
            raise ReplaceJobError(f"Step {number} of {job.name}: {problem}")
        compiled.append((_compile(step), _replacement(step)))
    counts: list[int] = []
    for number, (pattern, replacement) in enumerate(compiled, start=1):
        try:
            text, count = pattern.subn(replacement, text)
        except (re.error, IndexError) as error:
            raise ReplaceJobError(f"Step {number} of {job.name}: {error}.") from error
        counts.append(count)
    return text, counts


def describe_step(step: ReplaceStep) -> str:
    """One row of the step list, readable by ear."""
    options = []
    if step.regex:
        options.append("regular expression")
    if step.match_case:
        options.append("match case")
    suffix = f" ({', '.join(options)})" if options else ""
    replace = _visible(step.replace) if step.replace else "nothing"
    return f"Find {_visible(step.find)}, replace with {replace}{suffix}"


def _visible(value: str) -> str:
    """Make tabs, line breaks and bare spaces say themselves in a list row."""
    if value.strip() == "":
        names = {" ": "space", "\t": "tab", "\n": "line break"}
        spoken = [names.get(ch, repr(ch)) for ch in value]
        return " ".join(spoken) if len(spoken) < 4 else f"{len(spoken)} blank characters"
    shown = value.replace("\t", "\\t").replace("\n", "\\n")
    return f'"{shown}"'


def describe_run(job: ReplaceJob, counts: list[int], *, in_selection: bool) -> str:
    """What one run did, in one sentence: the total, and any step that found nothing."""
    total = sum(counts)
    where = " in the selection" if in_selection else ""
    if total == 0:
        return f"{job.name}: nothing to replace{where}"
    noun = "replacement" if total == 1 else "replacements"
    idle = [str(number) for number, count in enumerate(counts, start=1) if count == 0]
    tail = ""
    if idle and len(counts) > 1:
        steps = "step" if len(idle) == 1 else "steps"
        tail = f". {steps.capitalize()} {', '.join(idle)} found nothing"
    return f"{job.name}: {total} {noun}{where}{tail}"
