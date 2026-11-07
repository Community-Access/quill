""" "What failed" for one workflow run, as one plain-text read.

A failed run on GitHub is a page of collapsed groups, coloured logs and
annotations in a side panel. This module turns the same evidence into text
that reads top to bottom: each failed job, then the steps in it that failed,
then the annotations with ``file:line``, then the last meaningful log lines of
each failed step, with GitHub's timestamps and colour codes taken out.

The job log GitHub returns is one stream for the whole job. Every line starts
with a timestamp, and each step reports when it started and finished, so a
step's lines are the ones stamped inside its window. When the steps carry no
times, or nothing falls inside the window, the digest says so and uses the
end of the job's log instead -- that is where a failure almost always is.

No ``wx``; the fetch side takes its log reader as a parameter so tests never
reach GitHub.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from quill.core.github.workflow_models import (
    GitHubWorkflowAnnotation,
    GitHubWorkflowJob,
    GitHubWorkflowStep,
)

FAILED_CONCLUSIONS = frozenset({"failure", "timed_out", "startup_failure"})
TAIL_LINES = 40
MAX_FAILED_JOBS = 10

_ANSI = re.compile(
    r"\x1b\[[0-9;:?]*[ -/]*[@-~]"  # CSI: colours, cursor moves, line clears
    r"|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)"  # OSC: hyperlinks, titles
    r"|\x1b[()][A-Za-z0-9]"  # character-set switches
    r"|\^\[\[[0-9;:?]*[A-Za-z]"  # the same, written out as ^[[
)
_STAMP = re.compile(r"^\ufeff?(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(?:\.\d+)?Z ?")
_MARKERS = (
    ("##[error]", "ERROR: "),
    ("##[warning]", "WARNING: "),
    ("##[notice]", "NOTE: "),
    ("##[command]", "Command: "),
    ("[command]", "Command: "),
    ("##[debug]", "Debug: "),
    ("##[group]", ""),
    ("##[endgroup]", ""),
)


def clean_log_line(line: str) -> str:
    """A log line as a person reads it: no colour codes, no timestamp, markers in words."""
    line = _STAMP.sub("", _ANSI.sub("", line.rstrip("\r")))
    for marker, word in _MARKERS:
        if line.startswith(marker):
            return word + line[len(marker) :]
    return line


def is_meaningful(raw: str, cleaned: str) -> bool:
    """Blank lines, group brackets and debug chatter carry nothing for a listener."""
    if not cleaned.strip():
        return False
    stripped = _STAMP.sub("", _ANSI.sub("", raw)).strip()
    return not stripped.startswith(("##[endgroup]", "##[debug]"))


def _second(value: str) -> str:
    """``2026-01-02T03:04:05`` from either a log stamp or an API timestamp."""
    match = re.match(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d", value or "")
    if match:
        return match.group(0)
    try:
        return datetime.fromisoformat(value).strftime("%Y-%m-%dT%H:%M:%S")
    except (TypeError, ValueError):
        return ""


def step_tail(
    log_text: str, step: GitHubWorkflowStep | None, *, lines: int = TAIL_LINES
) -> tuple[list[str], bool]:
    """The last *lines* meaningful lines of *step*, and whether the step window matched.

    Lines are stamped to the sub-second and steps to the second, so the window
    is compared at second resolution, inclusive at both ends.
    """
    start = _second(step.started_at) if step else ""
    end = _second(step.completed_at) if step else ""
    windowed: list[str] = []
    everything: list[str] = []
    current = ""
    for raw in log_text.split("\n"):
        match = _STAMP.match(raw)
        if match:
            current = match.group(1)
        cleaned = clean_log_line(raw)
        if not is_meaningful(raw, cleaned):
            continue
        everything.append(cleaned)
        if start and end and current and start <= current <= end:
            windowed.append(cleaned)
    if windowed:
        return windowed[-lines:], True
    return everything[-lines:], False


@dataclass(frozen=True, slots=True)
class FailedJobEvidence:
    """What was fetched for one failed job (each part may have failed on its own)."""

    job: GitHubWorkflowJob
    annotations: tuple[GitHubWorkflowAnnotation, ...] = ()
    annotations_error: str = ""
    log_text: str = ""
    log_error: str = ""


def failed_jobs(jobs: list[GitHubWorkflowJob]) -> list[GitHubWorkflowJob]:
    return [job for job in jobs if job.conclusion in FAILED_CONCLUSIONS]


def _failed_steps(job: GitHubWorkflowJob) -> list[GitHubWorkflowStep]:
    return [step for step in job.steps if step.conclusion in FAILED_CONCLUSIONS]


def build_failure_digest(
    run_label: str,
    evidence: list[FailedJobEvidence],
    *,
    total_jobs: int,
    skipped_jobs: int = 0,
) -> str:
    """Render the digest. Pure: everything it says comes from *evidence*."""
    lines = [f"What failed in {run_label}"]
    if not evidence:
        lines.append(
            "No jobs failed in this run."
            if total_jobs
            else "GitHub returned no jobs for this run yet."
        )
        return "\n".join(lines)
    count = len(evidence) + skipped_jobs
    lines.append(f"{count} of {total_jobs} jobs failed.")
    if skipped_jobs:
        lines.append(
            f"Showing the first {len(evidence)}; open the run on GitHub for the other "
            f"{skipped_jobs}."
        )
    for number, item in enumerate(evidence, start=1):
        job = item.job
        lines.extend(("", f"Job {number} of {len(evidence)}: {job.name} ({job.conclusion})"))
        steps = _failed_steps(job)
        if steps:
            lines.append(
                "Failed steps: "
                + "; ".join(f"step {step.number}, {step.name}" for step in steps)
                + "."
            )
        else:
            lines.append("GitHub named no failed step in this job.")
        if item.annotations_error:
            lines.append(f"Annotations unavailable: {item.annotations_error}")
        elif item.annotations:
            lines.append(f"Annotations ({len(item.annotations)}):")
            for note in item.annotations:
                where = f"{note.path}:{note.start_line}" if note.path else "no file"
                title = f"{note.title}: " if note.title else ""
                lines.append(f"  {where}: {note.level or 'notice'}: {title}{note.message}")
        else:
            lines.append("No annotations.")
        if item.log_error:
            lines.append(f"Log unavailable: {item.log_error}")
            continue
        targets: list[GitHubWorkflowStep | None] = list(steps) if steps else [None]
        for step in targets:
            tail, matched = step_tail(item.log_text, step)
            name = f"step {step.number}, {step.name}" if step else "the job"
            if not tail:
                lines.append(f"The log for {name} is empty.")
                continue
            if step is not None and not matched:
                lines.append(
                    f"Could not find {name} in the log by its times; "
                    "these are the last lines of the whole job."
                )
            lines.append(f"Last {len(tail)} log lines of {name}:")
            lines.extend(f"  {text}" for text in tail)
    return "\n".join(lines)


def collect_failure_digest(
    provider: Any,
    repo: str,
    run_id: int,
    run_label: str,
    *,
    attempt_number: int | None = None,
    fetch_log: Callable[[str | None, str, int], str],
) -> str:
    """Fetch jobs, then annotations and logs for the failed ones, and build the digest.

    One job's missing log or annotations become a line in the digest rather
    than an empty result; only failing to list the jobs at all is raised.
    """
    if attempt_number is None:
        jobs = provider.fetch_workflow_jobs(repo, run_id)
    else:
        jobs = provider.fetch_workflow_jobs(repo, run_id, attempt_number=attempt_number)
    failed = failed_jobs(jobs)
    shown, skipped = failed[:MAX_FAILED_JOBS], max(0, len(failed) - MAX_FAILED_JOBS)
    evidence: list[FailedJobEvidence] = []
    for job in shown:
        annotations: tuple[GitHubWorkflowAnnotation, ...] = ()
        annotations_error = log_text = log_error = ""
        check_run_id = job.check_run_id or job.id
        if check_run_id > 0:
            try:
                annotations, _truncated = provider.fetch_workflow_job_annotations(
                    repo, check_run_id
                )
            except Exception as exc:  # noqa: BLE001 - one job's gap stays visible
                annotations_error = str(exc)
        try:
            log_text = fetch_log(getattr(provider, "token", None), repo, job.id)
        except Exception as exc:  # noqa: BLE001 - one job's gap stays visible
            log_error = str(exc)
        evidence.append(FailedJobEvidence(job, annotations, annotations_error, log_text, log_error))
    return build_failure_digest(run_label, evidence, total_jobs=len(jobs), skipped_jobs=skipped)


__all__ = [
    "FAILED_CONCLUSIONS",
    "TAIL_LINES",
    "FailedJobEvidence",
    "build_failure_digest",
    "clean_log_line",
    "collect_failure_digest",
    "failed_jobs",
    "is_meaningful",
    "step_tail",
]
