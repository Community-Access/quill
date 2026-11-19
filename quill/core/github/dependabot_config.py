"""``.github/dependabot.yml`` as a sheet, and Dependabot's pull request commands (PRD 22.1).

**The configuration.** Each entry under ``updates:`` is one row: "pip in /,
weekly on Monday, up to 5 pull requests, labels dependencies". An entry's
sheet has its ecosystem, its directories, the schedule (interval, day, time,
time zone), the pull request limit, the target branch and labels; what the
sheet does not show (groups, ignore rules, registries, cooldown) stays in
the file untouched and is counted on the row. :func:`check_config` finds
what Dependabot would refuse: a version other than 2, an unknown key or
ecosystem, no directory or both ``directory`` and ``directories``, a
schedule it does not have, a negative limit, and two entries for the same
ecosystem, directory and branch.

**The commands.** Dependabot reads ``@dependabot ...`` comments on its own
pull requests. :data:`COMMANDS` is the list a Dependabot pull request's
"Dependabot Commands..." row offers, each with what it does; posting one is
an ordinary comment through the Workbench's comment path. Dependabot answers
in the thread when it acts.

YAML goes through :mod:`quill.core.github.actions_yaml`. wx-free and
strict-typed.
"""

from __future__ import annotations

import copy
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from quill.core.github.actions_yaml import dump_mapping, header_comments, load_mapping, same_data

__all__ = [
    "COMMANDS",
    "DAYS",
    "ECOSYSTEMS",
    "INTERVALS",
    "DependabotCommand",
    "DependabotDraft",
    "check_config",
    "dump_config",
    "entry_summary",
    "is_dependabot",
    "load_config",
    "new_entry",
]

#: Every ``package-ecosystem`` value GitHub documents.
ECOSYSTEMS: tuple[str, ...] = (
    "bun",
    "bundler",
    "cargo",
    "composer",
    "conda",
    "devcontainers",
    "docker",
    "docker-compose",
    "dotnet-sdk",
    "elm",
    "github-actions",
    "gitsubmodule",
    "gomod",
    "gradle",
    "helm",
    "julia",
    "maven",
    "mix",
    "npm",
    "nuget",
    "opentofu",
    "pip",
    "pub",
    "rust-toolchain",
    "swift",
    "terraform",
    "uv",
    "vcpkg",
)
INTERVALS: tuple[str, ...] = (
    "daily",
    "weekly",
    "monthly",
    "quarterly",
    "semiannually",
    "yearly",
    "cron",
)
DAYS: tuple[str, ...] = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)
_TOP_KEYS = frozenset({
    "version",
    "updates",
    "registries",
    "enable-beta-ecosystems",
    "multi-ecosystem-groups",
})
_ENTRY_KEYS = frozenset({
    "package-ecosystem",
    "directory",
    "directories",
    "schedule",
    "allow",
    "assignees",
    "commit-message",
    "cooldown",
    "exclude-paths",
    "groups",
    "ignore",
    "insecure-external-code-execution",
    "labels",
    "milestone",
    "multi-ecosystem-group",
    "open-pull-requests-limit",
    "patterns",
    "pull-request-branch-name",
    "rebase-strategy",
    "registries",
    "reviewers",
    "target-branch",
    "vendor",
    "versioning-strategy",
})
_SCHEDULE_KEYS = frozenset({"interval", "day", "time", "timezone", "cronjob"})
_TIME = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")
_BOTS = frozenset({"dependabot[bot]", "dependabot-preview[bot]", "app/dependabot", "dependabot"})


@dataclass
class DependabotDraft:
    data: dict[str, Any]
    header: str = ""
    original_text: str = ""
    original_data: dict[str, Any] = field(default_factory=dict)

    @property
    def entries(self) -> list[dict[str, Any]]:
        updates = self.data.get("updates")
        if not isinstance(updates, list):
            updates = []
            self.data["updates"] = updates
        return updates

    def changed(self) -> bool:
        return not same_data(self.data, self.original_data)


def load_config(text: str) -> DependabotDraft:
    """Read dependabot.yml; a missing file starts as version 2 with no entries."""
    data = load_mapping(text, "Dependabot configuration")
    if not data:
        data = {"version": 2, "updates": []}
    return DependabotDraft(data, header_comments(text), text, copy.deepcopy(data))


def dump_config(draft: DependabotDraft) -> str:
    if draft.original_text and not draft.changed():
        return draft.original_text
    return dump_mapping(draft.data, draft.header)


def new_entry(ecosystem: str = "github-actions", directory: str = "/") -> dict[str, Any]:
    return {
        "package-ecosystem": ecosystem,
        "directory": directory,
        "schedule": {"interval": "weekly"},
    }


def _list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(v) for v in value]
    return []


def entry_summary(entry: Mapping[str, Any]) -> str:
    """ "pip in / and /docs, weekly on Monday at 09:00, up to 5 pull requests, labels x"."""
    ecosystem = str(entry.get("package-ecosystem") or "no ecosystem")
    places = _list(entry.get("directories")) or _list(entry.get("directory"))
    parts = [f"{ecosystem} in {' and '.join(places) if places else 'no directory'}"]
    schedule = entry.get("schedule")
    if isinstance(schedule, dict):
        interval = str(schedule.get("interval") or "no interval")
        when = interval if interval != "cron" else f"on cron {schedule.get('cronjob', '')}"
        if schedule.get("day"):
            when += f" on {str(schedule['day']).title()}"
        if schedule.get("time"):
            when += f" at {schedule['time']}"
        if schedule.get("timezone"):
            when += f" {schedule['timezone']}"
        parts.append(when)
    if "open-pull-requests-limit" in entry:
        limit = entry["open-pull-requests-limit"]
        parts.append(
            "version updates off (limit 0)" if limit == 0 else f"up to {limit} pull requests"
        )
    if entry.get("target-branch"):
        parts.append(f"into {entry['target-branch']}")
    labels = _list(entry.get("labels"))
    if labels:
        parts.append("labels " + ", ".join(labels))
    for key, word in (("groups", "group"), ("ignore", "ignore rule")):
        count = len(entry.get(key) or ())
        if count:
            parts.append(f"{count} {word}{'s' if count != 1 else ''}")
    return ", ".join(parts)


def check_config(draft: DependabotDraft) -> list[str]:
    """Every reason Dependabot would refuse the file, as sentences; empty when fine."""
    out: list[str] = []
    data = draft.data
    if data.get("version") != 2:
        out.append("The file: version must be 2.")
    for key in data:
        if key not in _TOP_KEYS:
            out.append(f"The file: {key} is not something dependabot.yml has.")
    updates = data.get("updates")
    if not isinstance(updates, list) or not updates:
        out.append("Updates: there are none, so Dependabot checks nothing.")
        return out
    seen: dict[tuple[str, str, str], int] = {}
    for number, entry in enumerate(updates, 1):
        where = f"Entry {number}"
        if not isinstance(entry, dict):
            out.append(f"{where}: an entry must be a set of keys.")
            continue
        for key in entry:
            if key not in _ENTRY_KEYS:
                out.append(f"{where}: {key} is not something an entry has.")
        ecosystem = str(entry.get("package-ecosystem") or "")
        if not ecosystem:
            out.append(f"{where}: it has no package ecosystem.")
        elif ecosystem not in ECOSYSTEMS:
            out.append(f"{where}: {ecosystem} is not a package ecosystem Dependabot has.")
        has_one, has_many = "directory" in entry, "directories" in entry
        if has_one and has_many:
            out.append(f"{where}: use directory or directories, not both.")
        elif not has_one and not has_many:
            out.append(f"{where}: it has no directory; / is the repository's root.")
        _check_schedule(entry.get("schedule"), where, out)
        limit = entry.get("open-pull-requests-limit")
        if limit is not None and (
            not isinstance(limit, int) or isinstance(limit, bool) or limit < 0
        ):
            out.append(f"{where}: the pull request limit must be a whole number, 0 or more.")
        for place in _list(entry.get("directories")) or _list(entry.get("directory")):
            slot = (ecosystem, place, str(entry.get("target-branch") or ""))
            if slot in seen:
                out.append(
                    f"{where}: entry {seen[slot]} already updates {ecosystem} in {place}"
                    + (f" into {slot[2]}" if slot[2] else "")
                    + "; Dependabot refuses the file with both."
                )
            seen.setdefault(slot, number)
    return out


def _check_schedule(schedule: Any, where: str, out: list[str]) -> None:
    if not isinstance(schedule, dict) or not schedule.get("interval"):
        out.append(f"{where}: it has no schedule interval.")
        return
    for key in schedule:
        if key not in _SCHEDULE_KEYS:
            out.append(f"{where}: {key} is not something a schedule has.")
    interval = schedule.get("interval")
    if interval not in INTERVALS:
        out.append(f"{where}: {interval} is not an interval; use {', '.join(INTERVALS)}.")
    if interval == "cron" and not schedule.get("cronjob"):
        out.append(f"{where}: a cron interval needs a cronjob.")
    day = schedule.get("day")
    if day is not None and str(day).casefold() not in DAYS:
        out.append(f"{where}: {day} is not a day of the week.")
    time = schedule.get("time")
    if time is not None and not _TIME.match(str(time)):
        out.append(f"{where}: the time {time} is not hh:mm in 24 hours, such as 09:00.")


# -- pull request commands -----------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DependabotCommand:
    key: str
    label: str
    comment: str
    help: str


COMMANDS: tuple[DependabotCommand, ...] = (
    DependabotCommand(
        "rebase",
        "Rebase",
        "@dependabot rebase",
        "Rebase the pull request onto its base branch.",
    ),
    DependabotCommand(
        "recreate",
        "Recreate",
        "@dependabot recreate",
        "Make the pull request again from scratch, dropping any edits made to it.",
    ),
    DependabotCommand(
        "merge",
        "Merge When Checks Pass",
        "@dependabot merge",
        "Merge it once its checks pass.",
    ),
    DependabotCommand(
        "squash",
        "Squash and Merge When Checks Pass",
        "@dependabot squash and merge",
        "Squash and merge it once its checks pass.",
    ),
    DependabotCommand(
        "cancel_merge",
        "Cancel Merge",
        "@dependabot cancel merge",
        "Cancel a merge asked for earlier.",
    ),
    DependabotCommand(
        "reopen",
        "Reopen",
        "@dependabot reopen",
        "Reopen it if it was closed.",
    ),
    DependabotCommand(
        "close",
        "Close and Stop",
        "@dependabot close",
        "Close it, and stop Dependabot making it again.",
    ),
    DependabotCommand(
        "ignore_dependency",
        "Ignore This Dependency",
        "@dependabot ignore this dependency",
        "Close it, and never update this dependency again.",
    ),
    DependabotCommand(
        "ignore_major",
        "Ignore This Major Version",
        "@dependabot ignore this major version",
        "Close it, and skip this major version.",
    ),
    DependabotCommand(
        "ignore_minor",
        "Ignore This Minor Version",
        "@dependabot ignore this minor version",
        "Close it, and skip this minor version.",
    ),
    DependabotCommand(
        "ignore_patch",
        "Ignore This Patch Version",
        "@dependabot ignore this patch version",
        "Close it, and skip this patch version.",
    ),
)


def is_dependabot(author: str) -> bool:
    """Whether a pull request's author is Dependabot (the commands work only there)."""
    return author.strip().casefold() in _BOTS
