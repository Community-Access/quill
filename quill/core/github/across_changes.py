"""Changing a named thing across repositories: plan, preview, run (PRD 22.11).

:mod:`quill.core.github.across_by_name` gathers labels and milestones by name;
this module changes them. Writes are planned first and run second. A
:class:`Plan` holds one :class:`Step` per repository -- update, create,
rename, delete, relabel or close, or a skip with its reason -- and its preview
says, repository by repository, what will change and what is blocked: no
permission to change it there, or a conflict such as a label of the new name
already existing. :func:`apply` re-reads each target just before writing, so
a copy somebody changed on GitHub since the survey is skipped with a sentence
rather than overwritten, and returns one :class:`Result` per repository,
blocked and skipped ones included, so no repository leaves the outcome.

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from quill.core.github.across import why_failed
from quill.core.github.across_by_name import (
    KINDS,
    WRITABLE_KINDS,
    ByNameRow,
    Copy,
    Survey,
    describe_props,
    seg,
)

__all__ = [
    "MERGE_ITEM_LIMIT",
    "LogEntry",
    "Plan",
    "Result",
    "Step",
    "apply",
    "blocked_for",
    "plan_close",
    "plan_copy_missing",
    "plan_delete",
    "plan_make_same",
    "plan_merge",
    "plan_move_open",
    "plan_rename",
    "results_summary",
]

#: Merge relabels at most this many items per repository; past it the old
#: label is kept, so nothing is lost, and the result says so.
MERGE_ITEM_LIMIT = 300


def _list(api: Any, path: str, query: Mapping[str, str]) -> list[Any]:
    answer = api.rest("GET", path, query=dict(query))
    return answer.data if isinstance(answer.data, list) else []


@dataclass(frozen=True, slots=True)
class Step:
    repository: str
    action: str
    before: str = ""
    after: str = ""
    #: Why this step will not run ("" when it will).
    blocked: str = ""
    copy: Copy | None = None
    body: tuple[tuple[str, str], ...] = ()

    def preview(self) -> str:
        if self.blocked:
            return f"{self.repository}: will not change, {self.blocked}"
        if self.action == "skip":
            return f"{self.repository}: no change, {self.after or 'already the same'}"
        change = f"{self.before} becomes {self.after}" if self.before else self.after
        return f"{self.repository}: {self.action}, {change}"


@dataclass(frozen=True, slots=True)
class Plan:
    kind: str
    name: str
    operation: str
    steps: tuple[Step, ...]
    #: For a merge: the label the items move to; for a move, the milestone.
    into: str = ""

    @property
    def runnable(self) -> tuple[Step, ...]:
        return tuple(s for s in self.steps if not s.blocked and s.action != "skip")

    def preview(self) -> str:
        noun = KINDS[self.kind][0]
        head = (
            f"{self.operation} the {noun} {self.name}: {len(self.runnable)} of "
            f"{len(self.steps)} repositories will change."
        )
        return "\n".join([head, *(s.preview() for s in self.steps)])


def blocked_for(survey: Survey, repo: str, *, admin: bool = False) -> str:
    """Why the account may not change *repo*'s copy ("" when it may, or nobody knows)."""
    noun = KINDS[survey.kind][0]
    if admin:
        if survey.can_admin.get(repo) is False:
            return f"you may not change a {noun} there (it needs admin access)"
        return ""
    if survey.can_write.get(repo) is False:
        return f"you may not change a {noun} there (it needs write access)"
    return ""


_blocked = blocked_for


def _props_body(kind: str, props: Sequence[tuple[str, str]]) -> tuple[tuple[str, str], ...]:
    allowed = {"labels": ("color", "description"), "milestones": ("due_on", "description")}
    return tuple((k, v) for k, v in props if k in allowed.get(kind, ()))


def plan_make_same(survey: Survey, row: ByNameRow, winner: Sequence[tuple[str, str]]) -> Plan:
    """Every copy takes *winner*'s properties (one of the row's variants)."""
    body = _props_body(survey.kind, winner)
    steps = []
    for copy in row.copies:
        current = _props_body(survey.kind, copy.props)
        if current == body:
            steps.append(Step(copy.repository, "skip", after="already the same", copy=copy))
            continue
        steps.append(
            Step(
                copy.repository,
                "update",
                describe_props(current),
                describe_props(body),
                _blocked(survey, copy.repository),
                copy,
                body,
            )
        )
    return Plan(survey.kind, row.name, "Make the same", tuple(steps))


def plan_copy_missing(
    survey: Survey, row: ByNameRow, winner: Sequence[tuple[str, str]], targets: Sequence[str] = ()
) -> Plan:
    """Create the row's thing, with *winner*'s properties, where it is missing."""
    body = _props_body(survey.kind, winner)
    steps = []
    for repo in targets or row.missing:
        if survey.has(repo, row.name) is not None:
            steps.append(Step(repo, "skip", after="it already has one"))
            continue
        steps.append(
            Step(
                repo,
                "create",
                "",
                f"{row.name}, {describe_props(body)}",
                _blocked(survey, repo),
                None,
                body,
            )
        )
    return Plan(survey.kind, row.name, "Add to the missing", tuple(steps))


def plan_rename(survey: Survey, row: ByNameRow, new_name: str) -> Plan:
    steps = []
    for copy in row.copies:
        clash = survey.has(copy.repository, new_name)
        blocked = _blocked(survey, copy.repository)
        if not blocked and clash is not None and clash.name.casefold() != row.name.casefold():
            blocked = f"it already has {new_name}; Merge Into joins the two instead"
        steps.append(Step(copy.repository, "rename", copy.name, new_name, blocked, copy))
    return Plan(survey.kind, row.name, "Rename", tuple(steps))


def plan_delete(survey: Survey, row: ByNameRow) -> Plan:
    steps = tuple(
        Step(c.repository, "delete", c.name, "deleted", _blocked(survey, c.repository), c)
        for c in row.copies
    )
    return Plan(survey.kind, row.name, "Delete", steps)


def plan_merge(survey: Survey, row: ByNameRow, into: str) -> Plan:
    """Labels: move every item from *row* to *into*, then delete *row*'s label.

    Where a repository has no *into* label, renaming does the same in one
    request and keeps the items, so that is the step there.
    """
    steps = []
    for copy in row.copies:
        blocked = _blocked(survey, copy.repository)
        target = survey.has(copy.repository, into)
        if target is None:
            steps.append(Step(copy.repository, "rename", copy.name, into, blocked, copy))
        else:
            after = f"items move to {target.name}, then {copy.name} is deleted"
            steps.append(Step(copy.repository, "relabel", copy.name, after, blocked, copy))
    return Plan(survey.kind, row.name, "Merge", tuple(steps), into=into)


def plan_close(survey: Survey, row: ByNameRow) -> Plan:
    """Milestones: close every open copy."""
    steps = []
    for copy in row.copies:
        if copy.prop("state") == "closed":
            steps.append(Step(copy.repository, "skip", after="already closed", copy=copy))
        else:
            blocked = _blocked(survey, copy.repository)
            steps.append(Step(copy.repository, "close", "open", "closed", blocked, copy))
    return Plan(survey.kind, row.name, "Close", tuple(steps))


def plan_move_open(survey: Survey, row: ByNameRow, into: str) -> Plan:
    """Milestones: move each copy's open items to *into* in the same repository.

    A repository without an *into* milestone is blocked with the reason (Add
    to Missing makes one first), so no item is ever left without a milestone.
    """
    steps = []
    for copy in row.copies:
        target = survey.has(copy.repository, into)
        opened = dict(copy.extra).get("open", "0")
        blocked = _blocked(survey, copy.repository)
        if not blocked and target is None:
            blocked = f"it has no milestone {into}; Add to Missing makes one first"
        if opened == "0" and not blocked:
            steps.append(Step(copy.repository, "skip", after="no open items", copy=copy))
            continue
        body = (("into_number", target.ident if target is not None else ""),)
        after = f"{opened} open items move to {into}"
        steps.append(Step(copy.repository, "move", copy.name, after, blocked, copy, body))
    return Plan(survey.kind, row.name, "Move open work", tuple(steps), into=into)


# -- running ----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LogEntry:
    """What Change History keeps for one repository's write (PRD 16.5, 18.5).

    *kind* and *ident* name a Properties sheet (``label``, ``milestone``,
    ``repository``) and *changes* its fields, so the history's Undo reverses
    the write through the sheet engine where *can_undo*; a write no sheet can
    reverse (a delete, a merge, a new ruleset) is logged with can_undo False.
    """

    kind: str
    ident: tuple[tuple[str, str], ...]
    target: str
    summary: str
    changes: tuple[tuple[str, str, object, object], ...] = ()
    can_undo: bool = False
    confirmed: bool = False


@dataclass(frozen=True, slots=True)
class Result:
    repository: str
    ok: bool
    said: str
    log: LogEntry | None = None


Outcome = tuple[str, "LogEntry | None"]
Runner = Callable[[Any, Plan, Step], Outcome]
Check = Callable[[Any, Plan, Step], str]


def results_summary(results: Sequence[Result]) -> str:
    same = sum(1 for r in results if r.ok and r.said.startswith("no change"))
    done = sum(1 for r in results if r.ok) - same
    head = f"{done} of {len(results)} repositories changed."
    if same:
        head += f" {same} already right."
    failed = [f"{r.repository}: {r.said}" for r in results if not r.ok]
    return head + (" Not changed: " + "; ".join(failed) + "." if failed else "")


def _label_path(repo: str, name: str) -> str:
    return f"/repos/{repo}/labels/{seg(name)}"


def _current_label(api: Any, repo: str, name: str) -> tuple[tuple[str, str], ...] | None:
    try:
        answer = api.rest("GET", _label_path(repo, name))
    except Exception as exc:  # noqa: BLE001
        if "not found" in why_failed(exc):
            return None
        raise
    data = answer.data if isinstance(answer.data, Mapping) else {}
    return (
        ("color", str(data.get("color") or "").lower()),
        ("description", str(data.get("description") or "")),
    )


def _current_milestone(api: Any, repo: str, number: str) -> tuple[tuple[str, str], ...] | None:
    try:
        answer = api.rest("GET", f"/repos/{repo}/milestones/{seg(number)}")
    except Exception as exc:  # noqa: BLE001
        if "not found" in why_failed(exc):
            return None
        raise
    data = answer.data if isinstance(answer.data, Mapping) else {}
    return (
        ("due_on", str(data.get("due_on") or "")[:10]),
        ("description", str(data.get("description") or "")),
        ("state", str(data.get("state") or "")),
    )


def _changed_since(api: Any, plan: Plan, step: Step) -> str:
    """Why *step* must not run because GitHub changed under it ("" when it may)."""
    kind, copy = plan.kind, step.copy
    if step.action == "create":
        if kind == "labels" and _current_label(api, step.repository, plan.name) is not None:
            return "it was created on GitHub since you looked"
        return ""
    if copy is None:
        return ""
    if kind == "labels":
        now = _current_label(api, step.repository, copy.ident)
        if now is None:
            return "it was deleted or renamed on GitHub since you looked"
        if now != _props_body(kind, copy.props):
            return "it was changed on GitHub since you looked"
    else:
        now = _current_milestone(api, step.repository, copy.ident)
        if now is None:
            return "it was deleted on GitHub since you looked"
        if now != copy.props:
            return "it was changed on GitHub since you looked"
    return ""


def _body(step: Step) -> dict[str, object]:
    out: dict[str, object] = {}
    for key, value in step.body:
        if key == "into_number":
            continue
        if key == "due_on":
            out[key] = f"{value}T00:00:00Z" if value else None
        else:
            out[key] = value
    return out


def _each_item(api: Any, repo: str, query: Mapping[str, str]) -> tuple[list[int], bool]:
    """Issue numbers matching *query*, up to the limit; (numbers, all of them)."""
    numbers: list[int] = []
    page = 1
    while len(numbers) < MERGE_ITEM_LIMIT:
        found = _list(api, f"/repos/{repo}/issues", {**query, "per_page": "100", "page": str(page)})
        numbers += [
            e["number"]
            for e in found
            if isinstance(e, Mapping) and isinstance(e.get("number"), int)
        ]
        if len(found) < 100:
            return numbers[:MERGE_ITEM_LIMIT], len(numbers) <= MERGE_ITEM_LIMIT
        page += 1
    return numbers[:MERGE_ITEM_LIMIT], False


def _relabel(api: Any, repo: str, old: str, into: str) -> tuple[int, bool]:
    """Move items from *old* to *into*; (moved, all of them)."""
    numbers, complete = _each_item(api, repo, {"labels": old, "state": "all"})
    for number in numbers:
        api.rest("POST", f"/repos/{repo}/issues/{number}/labels", body={"labels": [into]})
        api.rest("DELETE", f"/repos/{repo}/issues/{number}/labels/{seg(old)}")
    return len(numbers), complete


def _label_fields(
    copy: Copy, body: Mapping[str, object]
) -> tuple[tuple[str, str, object, object], ...]:
    labels = {"color": ("colour", "Colour"), "description": ("description", "Description")}
    return tuple(
        (labels[k][0], labels[k][1], copy.prop(k), v) for k, v in body.items() if k in labels
    )


def _milestone_fields(
    copy: Copy, body: Mapping[str, object]
) -> tuple[tuple[str, str, object, object], ...]:
    names = {
        "due_on": ("due", "Due"),
        "description": ("description", "Description"),
        "state": ("state", "State"),
    }
    return tuple(
        (names[k][0], names[k][1], copy.prop(k), str(v)[:10] if k == "due_on" and v else (v or ""))
        for k, v in body.items()
        if k in names
    )


def _run_labels(api: Any, plan: Plan, step: Step) -> Outcome:
    repo, copy = step.repository, step.copy
    target = f"{repo} label {plan.name}"
    if step.action == "update" and copy is not None:
        body = _body(step)
        api.rest("PATCH", _label_path(repo, copy.ident), body=body)
        proven = _current_label(api, repo, copy.ident) == _props_body(
            "labels", tuple((k, str(v)) for k, v in body.items())
        )
        ident = (("repo", repo), ("name", copy.ident))
        log = LogEntry(
            "label", ident, target, "made the same", _label_fields(copy, body), True, proven
        )
        return "made the same", log
    if step.action == "create":
        api.rest("POST", f"/repos/{repo}/labels", body={"name": plan.name, **_body(step)})
        log = LogEntry("label", (("repo", repo), ("name", plan.name)), target, "added")
        return "added", log
    if step.action == "rename" and copy is not None:
        api.rest("PATCH", _label_path(repo, copy.ident), body={"new_name": step.after})
        proven = _current_label(api, repo, step.after) is not None
        ident = (("repo", repo), ("name", copy.ident))
        changes = (("name", "Name", copy.ident, step.after),)
        log = LogEntry("label", ident, target, f"renamed to {step.after}", changes, True, proven)
        return f"renamed to {step.after}", log
    if step.action == "delete" and copy is not None:
        api.rest("DELETE", _label_path(repo, copy.ident))
        return "deleted", LogEntry(
            "label", (("repo", repo), ("name", copy.ident)), target, "deleted"
        )
    if step.action == "relabel" and copy is not None:
        moved, complete = _relabel(api, repo, copy.ident, plan.into)
        if not complete:
            raise RuntimeError(
                f"moved {moved} items and stopped at {MERGE_ITEM_LIMIT}; "
                f"{copy.name} was kept so nothing is lost. Merge again to move the rest"
            )
        api.rest("DELETE", _label_path(repo, copy.ident))
        said = f"moved {moved} items to {plan.into} and deleted {copy.name}"
        return said, LogEntry("label", (("repo", repo), ("name", copy.ident)), target, said)
    raise ValueError(f"labels cannot {step.action}.")


def _run_milestones(api: Any, plan: Plan, step: Step) -> Outcome:
    repo, copy = step.repository, step.copy
    target = f"{repo} milestone {plan.name}"
    if copy is not None and step.action in ("update", "close"):
        body = _body(step) if step.action == "update" else {"state": "closed"}
        api.rest("PATCH", f"/repos/{repo}/milestones/{seg(copy.ident)}", body=body)
        now = _current_milestone(api, repo, copy.ident)
        said = "made the same" if step.action == "update" else "closed"
        proven = now is not None and all(
            dict(now).get(k) == (str(v)[:10] if k == "due_on" and v else (v or ""))
            for k, v in body.items()
        )
        ident = (("repo", repo), ("number", copy.ident))
        return said, LogEntry(
            "milestone", ident, target, said, _milestone_fields(copy, body), True, proven
        )
    if step.action == "create":
        body = {"title": plan.name, **{k: v for k, v in _body(step).items() if v is not None}}
        api.rest("POST", f"/repos/{repo}/milestones", body=body)
        return "added", LogEntry(
            "milestone", (("repo", repo), ("title", plan.name)), target, "added"
        )
    if step.action == "move" and copy is not None:
        into = dict(step.body).get("into_number", "")
        numbers, complete = _each_item(api, repo, {"milestone": copy.ident, "state": "open"})
        for number in numbers:
            api.rest("PATCH", f"/repos/{repo}/issues/{number}", body={"milestone": int(into)})
        listed = ", ".join(f"#{n}" for n in numbers) or "none"
        said = f"moved {len(numbers)} open items to {plan.into} ({listed})"
        if not complete:
            said += f"; stopped at {MERGE_ITEM_LIMIT}, move again for the rest"
        log = LogEntry("milestone", (("repo", repo), ("number", copy.ident)), target, said)
        if not complete:
            raise RuntimeError(said)
        return said, log
    raise ValueError(f"milestones cannot {step.action}.")


def _run(api: Any, plan: Plan, step: Step) -> Outcome:
    """Do one label or milestone step; the result's words and its history entry."""
    if plan.kind == "labels":
        return _run_labels(api, plan, step)
    if plan.kind == "milestones":
        return _run_milestones(api, plan, step)
    raise ValueError(f"{plan.kind} cannot {step.action} here.")


def apply(
    api: Any,
    plan: Plan,
    *,
    on_step: Callable[[Result], None] | None = None,
    runner: Runner | None = None,
    check: Check | None = None,
) -> list[Result]:
    """Run the plan's runnable steps, one repository at a time. Runs off the UI thread.

    Blocked and skipped steps come back as results too, so every repository in
    the preview has a line in the outcome. *runner* and *check* do and guard
    the steps of kinds this module does not know (topics, rules: see
    :mod:`quill.core.github.across_admin_changes`).
    """
    if plan.kind not in WRITABLE_KINDS:
        raise ValueError(f"{plan.kind} are read only here.")
    run = runner or _run
    guard = check or _changed_since
    results: list[Result] = []
    for step in plan.steps:
        if step.blocked:
            result = Result(step.repository, False, step.blocked)
        elif step.action == "skip":
            result = Result(step.repository, True, f"no change, {step.after}")
        else:
            try:
                conflict = guard(api, plan, step)
                if conflict:
                    result = Result(step.repository, False, conflict)
                else:
                    said, log = run(api, plan, step)
                    result = Result(step.repository, True, said, log)
            except Exception as exc:  # noqa: BLE001 - one repository never sinks the rest
                result = Result(step.repository, False, why_failed(exc))
        results.append(result)
        if on_step is not None:
            on_step(result)
    return results
