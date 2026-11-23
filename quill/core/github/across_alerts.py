"""Dismiss Everywhere: one security alert's copies across repositories (PRD 22.11; GH-R-151).

On a row of Across Repositories > Security Alerts, **Dismiss Everywhere...**
finds every open alert in the set for the same thing and dismisses them with
one of GitHub's reasons and one comment:

- a **Dependabot** alert by its advisory (the GHSA id), whatever manifest it is in;
- a **code scanning** alert by its rule and tool, wherever in the code it is.

A **secret scanning** alert is never matched by type: each leaked secret is its
own, so each is resolved in its own repository (Dismiss or Reopen Alert).

The preview names each repository and the alert numbers it will dismiss; one
whose alerts cannot be read (the feature is off, or no access) says so, and one
with none open says that. Just before writing, each repository's open alerts
are read again, so one somebody closed meanwhile is left out and named. Each
dismissed alert is its own Change History entry, through the Security Alert
sheet's State, Reason and Comment, so Undo reopens it, as Reopen does in one
repository. The result is one sentence per repository.

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from quill.core.error_codes import CodedError
from quill.core.github.across import why_failed
from quill.core.github.across_changes import LogEntry, Plan, Result, Step
from quill.core.github.alert_triage import DISMISS_REASONS, AlertKind, alert_kind_for

__all__ = [
    "COMMENT_LIMIT",
    "DISMISSABLE",
    "AlertMatch",
    "AlertNotFound",
    "apply_dismiss",
    "match_for",
    "plan_dismiss",
]

#: The alert kinds whose copies are matched across repositories.
DISMISSABLE = frozenset({"Dependabot", "Code scanning"})
#: GitHub keeps at most this many characters of a dismissal comment.
COMMENT_LIMIT = 280


class AlertNotFound(CodedError):
    code = "QUILL-GITHUB-ALERT-NOT-OPEN"


@dataclass(frozen=True, slots=True)
class AlertMatch:
    """What makes two alerts the same: an advisory, or a rule of one tool."""

    kind: AlertKind
    key: str  # GHSA id, or rule id
    tool: str = ""
    words: str = ""  # the advisory's summary or the rule's description

    @property
    def name(self) -> str:
        return f"{self.key} ({self.words})" if self.words else self.key


def _open(api: Any, repo: str, kind: AlertKind) -> list[Mapping[str, Any]]:
    data = api.rest(
        "GET", f"/repos/{repo}/{kind.key}/alerts", query={"state": "open", "per_page": "100"}
    ).data
    return [e for e in data if isinstance(e, Mapping)] if isinstance(data, list) else []


def _key(kind: AlertKind, alert: Mapping[str, Any]) -> tuple[str, str, str]:
    """(key, tool, words) of one alert from GitHub's answer."""
    if kind.key == "dependabot":
        advisory = alert.get("security_advisory")
        advisory = advisory if isinstance(advisory, Mapping) else {}
        return str(advisory.get("ghsa_id") or ""), "", str(advisory.get("summary") or "")
    rule = alert.get("rule")
    rule = rule if isinstance(rule, Mapping) else {}
    tool = alert.get("tool")
    tool_name = str(tool.get("name") or "") if isinstance(tool, Mapping) else ""
    return str(rule.get("id") or ""), tool_name, str(rule.get("description") or "")


def _where(kind: AlertKind, alert: Mapping[str, Any]) -> str:
    if kind.key == "dependabot":
        dependency = alert.get("dependency")
        dependency = dependency if isinstance(dependency, Mapping) else {}
        package = dependency.get("package")
        name = str(package.get("name") or "") if isinstance(package, Mapping) else ""
        return " in ".join(p for p in (name, str(dependency.get("manifest_path") or "")) if p)
    instance = alert.get("most_recent_instance")
    location = instance.get("location") if isinstance(instance, Mapping) else None
    return str(location.get("path") or "") if isinstance(location, Mapping) else ""


def match_for(api: Any, repo: str, alert_type: str, number: int) -> AlertMatch:
    """What alert *number* in *repo* is about, read from its repository's open alerts."""
    if alert_type not in DISMISSABLE:
        raise AlertNotFound(
            f"{alert_type} alerts are dismissed one at a time: each is its own finding."
        )
    kind = alert_kind_for(alert_type)
    for alert in _open(api, repo, kind):
        if alert.get("number") == number:
            key, tool, words = _key(kind, alert)
            if key:
                return AlertMatch(kind, key, tool, words)
    raise AlertNotFound(
        f"{kind.label} alert #{number} in {repo} is not open now; F5 reads the list again."
    )


def _matching(api: Any, repo: str, match: AlertMatch) -> list[tuple[int, str]]:
    """(number, where) of each open alert in *repo* that is *match*."""
    found = []
    for alert in _open(api, repo, match.kind):
        key, tool, _words = _key(match.kind, alert)
        if key == match.key and tool == match.tool and isinstance(alert.get("number"), int):
            found.append((int(alert["number"]), _where(match.kind, alert)))
    return found


def _numbers(found: Sequence[tuple[int, str]]) -> str:
    said = [f"#{n}" + (f" ({where})" if where else "") for n, where in found]
    if len(said) == 1:
        return f"alert {said[0]}"
    return "alerts " + ", ".join(said[:-1]) + " and " + said[-1]


def plan_dismiss(
    api: Any, match: AlertMatch, repositories: Sequence[str], reason: str, comment: str = ""
) -> Plan:
    """A step per repository: its open copies, dismissed with *reason*. Off the UI thread."""
    reasons = dict(DISMISS_REASONS[match.kind.key])
    if reason not in reasons:
        raise ValueError(f"{reason!r} is not a reason for a {match.kind.label} alert.")
    if len(comment) > COMMENT_LIMIT:
        raise ValueError(f"A dismissal comment is at most {COMMENT_LIMIT} characters.")
    steps = []
    for repo in dict.fromkeys(repositories):
        try:
            found = _matching(api, repo, match)
        except Exception as exc:  # noqa: BLE001 - one repository never sinks the rest
            steps.append(
                Step(repo, "dismiss", blocked=f"its alerts could not be read ({why_failed(exc)})")
            )
            continue
        if not found:
            steps.append(Step(repo, "skip", after="no open alert for it"))
            continue
        body = (
            ("numbers", ",".join(str(n) for n, _w in found)),
            ("reason", reason),
            ("comment", comment),
        )
        after = f"{_numbers(found)}, reason: {reasons[reason]}"
        steps.append(Step(repo, "dismiss", "", after, "", None, body))
    return Plan("alerts", match.name, "Dismiss", tuple(steps))


def _dismiss(api: Any, match: AlertMatch, repo: str, step: Step) -> Result:
    body = dict(step.body)
    wanted = [int(n) for n in body.get("numbers", "").split(",") if n.isdigit()]
    still = {n for n, _w in _matching(api, repo, match)}
    gone = [n for n in wanted if n not in still]
    if not [n for n in wanted if n in still]:
        return Result(repo, False, "they were closed on GitHub since you looked")
    kind, reason, comment = match.kind, body.get("reason", ""), body.get("comment", "")
    sent: dict[str, object] = {"state": kind.closed_state, kind.reason_field: reason}
    if comment:
        sent[kind.comment_field] = comment
    logs, done, failed = [], [], []
    for number in (n for n in wanted if n in still):
        try:
            answer = api.rest(
                "PATCH", f"/repos/{repo}/{kind.key}/alerts/{number}", body=dict(sent)
            ).data
        except Exception as exc:  # noqa: BLE001 - say which alert, keep going
            failed.append(f"#{number} not dismissed, {why_failed(exc)}")
            continue
        proven = isinstance(answer, Mapping) and answer.get("state") == kind.closed_state
        if not proven:  # FUX-04: only what GitHub's answer shows counts as dismissed
            failed.append(f"#{number} sent, but GitHub still shows it open")
            continue
        done.append(number)
        changes: list[tuple[str, str, object, object]] = [
            ("state", "State", "open", kind.closed_state),
            ("reason", "Reason", "", reason),
        ]
        if comment:
            changes.append(("comment", "Comment", "", comment))
        ident = (("repo", repo), ("number", str(number)), ("alert_path", f"{kind.key}/alerts"))
        target = f"{repo} {kind.label} alert #{number}"
        logs.append(
            LogEntry("security_alert", ident, target, "dismissed", tuple(changes), True, proven)
        )
    parts = []
    if done:
        parts.append("dismissed " + _numbers([(n, "") for n in done]))
    parts += failed
    if gone:
        parts.append(", ".join(f"#{n}" for n in gone) + " closed on GitHub since you looked")
    said = "; ".join(parts)
    if not done:
        return Result(repo, False, said)
    return Result(repo, True, said, logs[0], tuple(logs[1:]))


def apply_dismiss(
    api: Any,
    match: AlertMatch,
    plan: Plan,
    *,
    on_step: Callable[[Result], None] | None = None,
) -> list[Result]:
    """Dismiss each step's alerts, one repository at a time; a result per repository."""
    results = []
    for step in plan.steps:
        if step.blocked:
            result = Result(step.repository, False, step.blocked)
        elif step.action == "skip":
            result = Result(step.repository, True, f"no change, {step.after}")
        else:
            try:
                result = _dismiss(api, match, step.repository, step)
            except Exception as exc:  # noqa: BLE001 - one repository never sinks the rest
                result = Result(step.repository, False, why_failed(exc))
        results.append(result)
        if on_step is not None:
            on_step(result)
    return results
