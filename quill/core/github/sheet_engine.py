"""The GitHub Properties engine: load, check, save, verify and undo a sheet (PRD 15 and 16).

A :class:`SheetDef` is everything the Workbench knows about one kind of
object: its :class:`~quill.core.workbench.properties.SheetSpec` (pages and
fields), how to read it (:class:`Read`), how each editable field is written
(:class:`Write`, with the requirement and tier GATE-GITHUB-PERM checks), and
where its picker choices come from (:class:`Options`). Every function here is
plain data in and data out over a :class:`~quill.core.github.workbench_api.GitHubApi`,
so the whole cycle is tested against recorded answers:

- :func:`load` reads the object fresh (and its viewer fields), with the
  ``updated_at`` or ETag the conflict check compares later;
- :func:`plan` turns the changed fields into requests, one per endpoint, only
  the changed fields in each (section 15.2: only changed fields are sent);
- :func:`save` checks for conflicts first (section 15.3), sends the plan,
  reads the object again and reports, field by field, only what the re-read
  proves (GitHub ignores some writes and still says 200);
- :func:`sentence` is the one sentence said afterwards;
- :func:`inverse` is the undo of a saved change, where GitHub allows one.

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from quill.core.error_codes import CodedError
from quill.core.github.permissions import ViewerContext, WriteTier, check
from quill.core.github.workbench_api import GitHubApi, fill_path
from quill.core.workbench.properties import (
    MIXED,
    FieldChange,
    ListDelta,
    SheetSpec,
    Value,
    apply_delta,
    conflicts,
)

__all__ = [
    "Ident",
    "Loaded",
    "Options",
    "Read",
    "SaveOutcome",
    "SheetDef",
    "SheetSaveError",
    "adopted",
    "Write",
    "inverse",
    "load",
    "load_options",
    "locked_fields",
    "plan",
    "save",
    "sentence",
]

Ident = Mapping[str, str]
"""What names one object: ``{"repo": "owner/name", "number": "42"}``."""

Extract = Callable[[Mapping[str, Any]], dict[str, Value]]
Encode = Callable[[Value, Mapping[str, object], Ident], dict[str, object]]


class SheetSaveError(CodedError):
    """A save could not be planned or sent; the message says why in a sentence."""

    code = "QUILL-GITHUB-SHEET-SAVE-FAILED"


@dataclass(frozen=True)
class Read:
    """One request a sheet's values come from: REST *path*, or a GraphQL *graphql* query."""

    path: str = ""
    extract: Extract | None = None
    graphql: str = ""
    variables: Callable[[Ident], dict[str, object]] | None = None
    optional: bool = False
    """A read whose failure leaves its fields empty (a 404 on a page you cannot see)."""
    fallback: Mapping[str, Value] = field(default_factory=dict)
    """What an optional read stands for when it fails (404 on a subscription: not watching)."""
    query: Callable[[Ident], dict[str, str]] | None = None
    pick: Callable[[Mapping[str, Any], Ident], dict[str, Value]] | None = None
    """Like *extract*, for a read that needs the ident (one asset out of a release's list)."""


@dataclass(frozen=True)
class Write:
    """How one field is saved, and what it needs.

    *kind* is ``"patch"`` (the field goes into a JSON body that may carry other
    fields for the same endpoint), ``"toggle"`` (PUT when true, DELETE when
    false: star, follow, lock), ``"put"`` or ``"post"`` (a request of its own),
    ``"graphql"`` (*path* is the mutation, *encode* builds its variables; a
    false value runs *off_path* instead when there is one), ``"set"`` (a list
    whose additions are POSTed to *path* and removals DELETEd at *off_path*
    or *path*, under *body_key*: reviewers) or ``"set_graphql"`` (one mutation
    per added item and one per removed, with ``$id`` and ``$content``:
    reactions).
    *encode* turns the field's value into the body fragment; the default sends
    ``{body_key or the field key: value}``. *requirement* and *tier* are what
    GATE-GITHUB-PERM checks; *undo* is False for a change GitHub cannot
    reverse, which the sheet says before it happens (section 16.5).
    """

    path: str
    requirement: str
    tier: WriteTier
    method: str = "PATCH"
    kind: str = "patch"
    body_key: str = ""
    encode: Encode | None = None
    undo: bool = True
    off_path: str = ""
    """For a toggle whose off request goes elsewhere (unlock is DELETE .../lock)."""
    off_method: str = "DELETE"
    """For a toggle whose off request is not a DELETE (a workflow's PUT .../disable)."""


@dataclass(frozen=True)
class Options:
    """Where a picker's choices come from: a list endpoint and how to name each entry.

    *value* gives what the API wants for an entry (a milestone's number for
    its title); without it the name itself is sent.
    """

    path: str
    name: Callable[[Mapping[str, Any]], str]
    value: Callable[[Mapping[str, Any]], object] | None = None
    query: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class SheetDef:
    """One kind of object: its sheet, reads, writes and pickers."""

    kind: str
    sheet: SheetSpec
    reads: tuple[Read, ...]
    writes: Mapping[str, Write] = field(default_factory=dict)
    options: Mapping[str, Options] = field(default_factory=dict)
    title: Callable[[Ident], str] = lambda ident: ""
    url: Callable[[Ident], str] = lambda ident: ""
    stamp: str = "updated"
    """The field whose value says when GitHub last changed it, for the conflict check."""
    fixed: Mapping[str, Mapping[str, object]] = field(default_factory=dict)
    """Pickers whose choices never change (reactions, states): word to API value."""
    compose: (
        Callable[[Ident, Mapping[str, Value]], list[tuple[str, str, dict[str, object]]]] | None
    ) = None
    """For an object GitHub replaces whole (a ruleset, an environment): the changed
    fields in, the requests out, as (method, path, body)."""
    secret_fields: tuple[str, ...] = ()
    """Write-only fields (a secret's value): never re-read, never said, never logged."""
    adopt: tuple[str, ...] = ("node_id",)
    """Loaded values a save needs in its ident too (a GraphQL node id, a release's id)."""
    renames: tuple[str, str] = ("", "")
    """(field, ident key): changing that field moves the object (a label's name)."""

    def ident_after(self, ident: Ident, done: Sequence[FieldChange]) -> dict[str, str]:
        """*ident* after a save that may have renamed the object."""
        moved = dict(ident)
        field_key, ident_key = self.renames
        for change in done:
            if field_key and change.key == field_key and isinstance(change.after, str):
                if ident_key == "team":
                    slug = "".join(ch if ch.isalnum() else "-" for ch in change.after.lower())
                    moved["team"] = "-".join(part for part in slug.split("-") if part)
                elif ident_key == "repo" and "/" in moved.get("repo", ""):
                    owner = moved["repo"].split("/", 1)[0]
                    moved["repo"] = f"{owner}/{change.after}"
                else:
                    moved[ident_key] = change.after
        return moved

    def editable_keys(self) -> tuple[str, ...]:
        return tuple(spec.key for spec in self.sheet.fields() if not spec.readonly)


@dataclass
class Loaded:
    """A sheet's values as GitHub answered them, and the pickers' choices."""

    values: dict[str, Value]
    viewer: dict[str, bool] = field(default_factory=dict)
    choices: dict[str, dict[str, object]] = field(default_factory=dict)
    missing: tuple[str, ...] = ()
    """Reads that failed and were optional, by path, so the sheet can say so."""


def load(api: GitHubApi, sheet: SheetDef, ident: Ident) -> Loaded:
    """Read every request of *sheet* for *ident*, freshly."""
    values: dict[str, Value] = {}
    viewer: dict[str, bool] = {}
    missing: list[str] = []
    for read in sheet.reads:
        try:
            if read.graphql:
                variables = read.variables(ident) if read.variables else dict(ident)
                data: Mapping[str, Any] = api.graphql(read.graphql, variables)
            else:
                query = read.query(ident) if read.query else None
                answer = api.rest("GET", fill_path(read.path, ident), query=query)
                data = answer.data if isinstance(answer.data, Mapping) else {"items": answer.data}
        except Exception:
            if not read.optional:
                raise
            missing.append(read.path or "graphql")
            values.update(read.fallback)
            continue
        found: dict[str, Value] = {}
        if read.extract is not None:
            found = read.extract(data)
        elif read.pick is not None:
            found = read.pick(data, ident)
        if found:
            for key, value in found.items():
                if key.startswith("viewer"):
                    viewer[key] = bool(value)
                else:
                    values[key] = value
    return Loaded(values, viewer, {}, tuple(missing))


def load_options(api: GitHubApi, sheet: SheetDef, ident: Ident) -> dict[str, dict[str, object]]:
    """Each picker's choices: display name to the value the API wants."""
    found: dict[str, dict[str, object]] = {}
    for key, source in sheet.options.items():
        try:
            answer = api.rest(
                "GET", fill_path(source.path, ident), query={"per_page": "100", **source.query}
            )
        except Exception:  # noqa: BLE001 - a picker that cannot load keeps the typed value
            continue
        rows = answer.data if isinstance(answer.data, list) else []
        choices: dict[str, object] = {}
        for row in rows:
            if isinstance(row, Mapping):
                name = source.name(row)
                choices[name] = source.value(row) if source.value else name
        found[key] = choices
    return found


def locked_fields(sheet: SheetDef, ctx: ViewerContext) -> dict[str, str]:
    """Each editable field the person may not change, with the reason (GH-R-032)."""
    locked: dict[str, str] = {}
    for key, write in sheet.writes.items():
        reason = check(write.requirement, ctx, write.tier)
        if reason:
            locked[key] = reason
    return locked


# ---------------------------------------------------------------------------
# Planning and sending
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Request:
    method: str
    path: str
    body: dict[str, object] | None
    keys: tuple[str, ...]
    graphql: str = ""


def _encoded(
    key: str, write: Write, value: Value, choices: Mapping[str, object], ident: Ident
) -> dict[str, object]:
    if write.encode is not None:
        return write.encode(value, choices, ident)
    if isinstance(value, tuple):
        sent: object = [choices.get(item, item) for item in value]
    elif isinstance(value, str) and value in choices:
        sent = choices[value]
    else:
        sent = value
    return {write.body_key or key: sent}


def plan(
    sheet: SheetDef,
    ident: Ident,
    changed: Sequence[FieldChange],
    choices: Mapping[str, Mapping[str, object]] | None = None,
) -> list[Request]:
    """The requests that send *changed*: patches grouped per endpoint, the rest one each."""
    picks = {**sheet.fixed, **(choices or {})}
    if sheet.compose is not None:
        whole = sheet.compose(ident, {change.key: change.after for change in changed})
        sent = tuple(change.key for change in changed)
        return [
            Request("POST", "/graphql", body, sent, path)
            if method == "GRAPHQL"
            else Request(method, path, body, sent)
            for method, path, body in whole
        ]
    grouped: dict[tuple[str, str], tuple[dict[str, object], list[str]]] = {}
    requests: list[Request] = []
    for change in changed:
        write = sheet.writes.get(change.key)
        if write is None:
            raise SheetSaveError(f"{change.label} cannot be changed from this sheet.")
        value = change.after
        if isinstance(value, ListDelta):
            before = change.before if isinstance(change.before, tuple) else ()
            value = apply_delta(before, value)
        picked = picks.get(change.key, {})
        if write.kind in ("set", "set_graphql"):
            requests.extend(_set_requests(change, write, value, picked, ident))
            continue
        fragment = _encoded(change.key, write, value, picked, ident)
        override = fragment.pop("__method", None)
        if isinstance(override, str):
            # One choice of several is a different request: "participating" is a
            # DELETE of the subscription, "none" a DELETE of the interaction limit.
            path = fill_path(write.path, ident)
            requests.append(Request(override, path, fragment or None, (change.key,)))
            continue
        if write.kind == "patch":
            path = fill_path(write.path, ident)
            body, keys = grouped.setdefault((write.method, path), ({}, []))
            body.update(fragment)
            keys.append(change.key)
        elif write.kind == "toggle":
            on = bool(value)
            path = fill_path(write.path if on or not write.off_path else write.off_path, ident)
            method = write.method if on else write.off_method
            requests.append(
                Request(method, path, fragment if on and write.body_key else None, (change.key,))
            )
        elif write.kind == "graphql":
            off = value is False or value == "" or value is None
            mutation = write.off_path if off and write.off_path else write.path
            requests.append(Request("POST", "/graphql", fragment, (change.key,), mutation))
        else:
            requests.append(
                Request(write.method, fill_path(write.path, ident), fragment, (change.key,))
            )
    for (method, path), (body, keys) in grouped.items():
        requests.insert(0, Request(method, path, body, tuple(keys)))
    return requests


def _set_requests(
    change: FieldChange,
    write: Write,
    value: Value,
    choices: Mapping[str, object],
    ident: Ident,
) -> list[Request]:
    before = change.before if isinstance(change.before, tuple) else ()
    after = value if isinstance(value, tuple) else ()
    added = [item for item in after if item not in before]
    removed = [item for item in before if item not in after]
    key = (change.key,)
    if write.kind == "set_graphql":
        node = ident.get("node_id", "")
        found = [
            Request("POST", "/graphql", {"id": node, "content": choices.get(i, i)}, key, write.path)
            for i in added
        ]
        found += [
            Request(
                "POST", "/graphql", {"id": node, "content": choices.get(i, i)}, key, write.off_path
            )
            for i in removed
        ]
        return found
    list_key = write.body_key or change.key
    path = fill_path(write.path, ident)
    found = []
    if added:
        found.append(
            Request(write.method, path, {list_key: [choices.get(i, i) for i in added]}, key)
        )
    if removed:
        off = fill_path(write.off_path, ident) if write.off_path else path
        found.append(Request("DELETE", off, {list_key: [choices.get(i, i) for i in removed]}, key))
    return found


def _send(api: GitHubApi, request: Request) -> None:
    if request.graphql:
        api.graphql(request.graphql, request.body or {})
        return
    api.rest(request.method, request.path, body=request.body)


@dataclass
class SaveOutcome:
    """What a save did, field by field, as the re-read proved it."""

    done: list[FieldChange] = field(default_factory=list)
    not_taken: list[FieldChange] = field(default_factory=list)
    failed: list[tuple[FieldChange, str]] = field(default_factory=list)
    conflicts: tuple[FieldChange, ...] = ()
    after: dict[str, Value] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.not_taken and not self.failed and not self.conflicts


def _same(intended: Value, found: Value) -> bool:
    if isinstance(intended, tuple) and isinstance(found, tuple):
        return sorted(intended) == sorted(found)
    if intended in (None, "") and found in (None, ""):
        return True
    return intended == found


def adopted(sheet: SheetDef, ident: Ident, loaded: Mapping[str, Value]) -> dict[str, str]:
    """*ident* with the loaded values a save needs (``node_id``, a release's ``id``)."""
    found = dict(ident)
    for key in sheet.adopt:
        value = loaded.get(key)
        if isinstance(value, (str, int, bool)) and str(value):
            found.setdefault(key, str(value))
    return found


def save(
    api: GitHubApi,
    sheet: SheetDef,
    ident: Ident,
    changed: Sequence[FieldChange],
    *,
    loaded: Mapping[str, Value],
    choices: Mapping[str, Mapping[str, object]] | None = None,
    keep_theirs: frozenset[str] = frozenset(),
    check_conflicts: bool = True,
) -> SaveOutcome:
    """Send *changed* safely: conflict check, send, read again, report what is proven.

    When somebody changed a pending field on GitHub since *loaded*, nothing is
    sent and the outcome lists the conflicts; the window asks Keep Theirs or
    Use Mine per field and calls again with *keep_theirs* (those fields are
    dropped) and ``check_conflicts=False``.
    """
    outcome = SaveOutcome()
    ident = adopted(sheet, ident, loaded)
    pending = [change for change in changed if change.key not in keep_theirs]
    if check_conflicts and pending:
        current = load(api, sheet, ident).values
        found = conflicts(pending, dict(loaded), current)
        if found:
            outcome.conflicts = found
            return outcome
    for request in plan(sheet, ident, pending, choices):
        try:
            _send(api, request)
        except Exception as exc:  # noqa: BLE001 - a failure is reported per field
            for change in pending:
                if change.key in request.keys:
                    outcome.failed.append((change, str(exc)))
    failed_keys = {change.key for change, _reason in outcome.failed}
    after = load(api, sheet, sheet.ident_after(ident, pending)).values
    outcome.after = after
    for change in pending:
        if change.key in failed_keys:
            continue
        intended = change.after
        if isinstance(intended, ListDelta):
            before = change.before if isinstance(change.before, tuple) else ()
            intended = apply_delta(before, intended)
        if change.key in sheet.secret_fields:
            outcome.done.append(FieldChange(change.key, change.label, None, "(set)"))
        elif _same(intended, after.get(change.key)):
            outcome.done.append(FieldChange(change.key, change.label, change.before, intended))
        else:
            outcome.not_taken.append(change)
    return outcome


def _value_words(value: object) -> str:
    if isinstance(value, tuple):
        return ", ".join(value) if value else "none"
    if isinstance(value, bool):
        return "on" if value else "off"
    if value is None or value == "" or value is MIXED:
        return "none"
    return str(value)


def _change_words(change: FieldChange) -> str:
    label = change.label.lower()
    before, after = change.before, change.after
    if isinstance(after, tuple):
        old = before if isinstance(before, tuple) else ()
        added = [item for item in after if item not in old]
        removed = [item for item in old if item not in after]
        if label.startswith("assignee"):
            parts = [f"assigned to {', '.join(added)}"] if added else []
            parts += [f"unassigned {', '.join(removed)}"] if removed else []
        else:
            parts = [f"added {', '.join(added)}"] if added else []
            parts += [f"removed {', '.join(removed)}"] if removed else []
        return ", ".join(parts) or f"{label} unchanged"
    if label in {"body", "description"} and isinstance(after, str) and len(after) > 40:
        return f"{label} changed"
    return f"{label} {_value_words(after)}"


def sentence(name: str, outcome: SaveOutcome) -> str:
    """The one sentence after a save: "#42: added bug, removed docs; milestone 2027.1."

    Only what the re-read proved is claimed; a field that did not take, or
    failed, is named after it.
    """
    parts: list[str] = []
    if outcome.done:
        parts.append(f"{name}: " + "; ".join(_change_words(c) for c in outcome.done) + ".")
    if outcome.not_taken:
        names = ", ".join(c.label.lower() for c in outcome.not_taken)
        parts.append(
            f"GitHub accepted but did not change {names}; you may not have access to set it."
        )
    for change, reason in outcome.failed:
        parts.append(f"Could not change {change.label.lower()}: {reason}")
    if outcome.conflicts:
        names = ", ".join(c.label.lower() for c in outcome.conflicts)
        parts.append(f"Changed on GitHub since you opened this: {names}. Nothing was saved.")
    return " ".join(parts) or f"{name}: nothing changed."


def inverse(sheet: SheetDef, done: Sequence[FieldChange]) -> tuple[list[FieldChange], list[str]]:
    """The changes that put *done* back, and the labels GitHub cannot reverse."""
    back: list[FieldChange] = []
    cannot: list[str] = []
    for change in done:
        write = sheet.writes.get(change.key)
        if write is None or not write.undo:
            cannot.append(change.label)
            continue
        before = change.before
        if before is MIXED or isinstance(before, ListDelta):
            cannot.append(change.label)
            continue
        restored: Value = before if isinstance(before, (str, int, bool, tuple)) else None
        back.append(FieldChange(change.key, change.label, change.after, restored))
    return back, cannot
