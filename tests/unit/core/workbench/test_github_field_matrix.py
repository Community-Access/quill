"""Every editable field of every GitHub Properties sheet, proved over a fake (complete.md 1.3).

The row: "Verify every editable field, mixed value, field removal, batch
operation, conflict resolution, verify-after-save, history and supported
undo/redo." The sheets are enumerated from the registry
(:data:`quill.core.github.sheet_catalog.SHEETS`), so a field added to any
sheet joins every test here without anybody listing it.

Each field is saved through the real engine over a sheet whose reads are
replaced by one scripted read of a fake GitHub's state, so what is proved is
the engine's own work for that field's write: the request it sends, the
re-read that decides what is claimed, the history row, the undo. The request
each field sends is pinned in ``fixtures/github_field_requests.json``, a
reviewed table; set ``QUILL_WRITE_FIELD_REQUESTS=1`` to rewrite it after a
deliberate change, and review the diff.
"""

from __future__ import annotations

import base64
import json
import os
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from quill.core.github.batch import BatchItem, results_text, run
from quill.core.github.change_log import ChangeLog
from quill.core.github.sheet_catalog import SHEETS
from quill.core.github.sheet_engine import (
    Read,
    SheetDef,
    adopted,
    inverse,
    is_set,
    plan,
    save,
    sentence,
)
from quill.core.github.sheet_replay import redo, undo, undo_notes, undo_refusal
from quill.core.github.sheet_values import (
    NEVER_EMPTY,
    EmptyValueError,
    NotANumberError,
    emptied_refusal,
)
from quill.core.workbench.properties import (
    MIXED,
    FieldChange,
    FieldKind,
    ListDelta,
    SheetState,
    Value,
    merge_values,
)
from tests.github_api_fake import FakeGitHubApi

FIXTURE = Path(__file__).parent / "fixtures" / "github_field_requests.json"
STATE_PATH = "/__state__"

IDENT: dict[str, str] = {
    "repo": "owner/repo",
    "number": "7",
    "name": "thing",
    "org": "acme",
    "team": "docs-team",
    "login": "kellylford",
    "id": "9",
    "tag": "v1",
    "branch": "main",
    "owner": "owner",
    "path": "a.txt",
    "sha": "abc123",
    "alert_path": "dependabot/alerts",
    "me": "me",
    "title": "Roadmap",
}

#: Loaded values a save adopts into its ident (a node id, the whole object as JSON).
ADOPTED: dict[str, Value] = {
    "node_id": "N_1",
    "raw_json": "{}",
    "project_items": "",
    "key_id": "k1",
    "public_key": base64.b64encode(bytes(range(32))).decode(),
    "asset_id": "6",
}

#: What else an object of a kind has loaded, where its whole-object save reads it.
LOADED: dict[str, dict[str, Value]] = {
    "security_alert": {"state": "dismissed", "reason": "tolerable_risk", "comment": ""},
}

#: Values a field's own write checks (a label's colour must be a colour).
SAMPLES: dict[tuple[str, str], tuple[Value, Value]] = {
    ("label", "colour"): ("ededed", "00ff00"),
    ("issue_type", "colour"): ("gray", "blue"),
}

FIELDS = sorted((kind, key) for kind, sheet in SHEETS.items() for key in sheet.editable_keys())
IDS = [f"{kind}.{key}" for kind, key in FIELDS]


# -- the scripted object -------------------------------------------------------------


def _choices(sheet: SheetDef, key: str) -> list[str]:
    spec = sheet.sheet.field(key)
    if spec.choices:
        return list(spec.choices)
    if key in sheet.fixed:
        return list(sheet.fixed[key])
    return ["first", "second"]


def _picks(sheet: SheetDef) -> dict[str, dict[str, object]]:
    """What load_options would give: each picker's name to the value the API wants."""
    return {key: {"first": "ID_first", "second": "ID_second"} for key in sheet.options}


def sample(sheet: SheetDef, key: str) -> tuple[Value, Value]:
    """(before, after) for one edit, of the field's own kind, as the sheet's controls give it."""
    if (sheet.kind, key) in SAMPLES:
        return SAMPLES[(sheet.kind, key)]
    kind = sheet.sheet.field(key).kind
    if kind is FieldKind.CHECK:
        return False, True
    if kind is FieldKind.CHOICE:
        first, second = (_choices(sheet, key) + ["second"])[:2]
        return first, second
    if kind is FieldKind.CHECKLIST:
        first, second = (_choices(sheet, key) + ["second"])[:2]
        return (first,), (first, second)
    if kind is FieldKind.LIST:
        return ("one",), ("one", "two")
    if kind is FieldKind.NUMBER:
        return 1, "2"  # a number box hands back text
    if kind is FieldKind.DATE:
        return "2026-01-01", "2026-02-02"
    if kind is FieldKind.SECRET:
        return None, "s3cret-value"
    return "old words", "new words"


def cleared(sheet: SheetDef, key: str) -> Value | None:
    """What the field holds when emptied, or None when it cannot be emptied."""
    spec = sheet.sheet.field(key)
    write = sheet.writes[key]
    if spec.kind is FieldKind.CHECK:
        return False if write.kind == "toggle" else None
    if spec.kind is FieldKind.CHOICE:
        return "" if not spec.choices and key not in sheet.fixed else None
    if spec.kind in (FieldKind.LIST, FieldKind.CHECKLIST):
        return ()
    if spec.kind is FieldKind.SECRET:
        return None  # a secret is replaced, never emptied
    if spec.kind is FieldKind.NUMBER:
        return ""
    return ""


def _number(value: Value) -> Value:
    return int(value) if isinstance(value, str) and value.strip().isdigit() else value


class World:
    """A fake GitHub holding one object; a write sets the field the test is changing."""

    def __init__(self, sheet: SheetDef, key: str, before: Value, *, takes: bool = True) -> None:
        self.real = sheet
        self.key = key
        self.state: dict[str, Value] = {**ADOPTED, **LOADED.get(sheet.kind, {}), key: before}
        self.takes = takes
        self.target: Value = None
        self.api = FakeGitHubApi()
        self.api.answer("GET", STATE_PATH, lambda: dict(self.state))
        self.api.on_write = self._write
        self.api.answer_graphql("mutation", self._mutation)
        self.sheet = replace(
            sheet,
            reads=(Read(STATE_PATH, lambda data: dict(data)),),
            options={},
        )

    def _write(self, _method: str, _path: str, _body: Any) -> None:
        if self.takes:
            self.state[self.key] = self.target

    def _mutation(self) -> dict[str, Any]:
        self._write("POST", "/graphql", None)
        return {}

    def save(self, before: Value, after: Value, **kw: Any) -> Any:
        self.target = _number(after)
        label = self.real.sheet.field(self.key).label
        return save(
            self.api,
            self.sheet,
            IDENT,
            [FieldChange(self.key, label, before, after)],
            loaded=dict(self.state),
            choices=_picks(self.real),
            **kw,
        )

    def sent(self, start: int = 0) -> list[list[Any]]:
        """The writes sent since *start*, REST and GraphQL in order, secrets masked."""
        found: list[list[Any]] = []
        mutations = iter(q for q, _v in self.api.graphql_calls if q.lstrip().startswith("mut"))
        variables = iter(v for q, v in self.api.graphql_calls if q.lstrip().startswith("mut"))
        for method, path, body in self.api.calls[start:]:
            if method == "GET":
                continue
            found.append([method, path, _masked(self.real, body)])
        for query, values in zip(mutations, variables, strict=True):
            found.append(["GRAPHQL", query.split("(", 1)[0] + "(" + query.split("{", 2)[1], values])
        return found


def _masked(sheet: SheetDef, body: Any) -> Any:
    if isinstance(body, dict) and sheet.secret_fields and "encrypted_value" in body:
        return {**body, "encrypted_value": "<sealed>"}
    return body


# -- the reviewed table of requests --------------------------------------------------


def _requests_for(kind: str, key: str) -> dict[str, Any]:
    sheet = SHEETS[kind]
    before, after = sample(sheet, key)
    world = World(sheet, key, before)
    world.save(before, after)
    found: dict[str, Any] = {"set": world.sent()}
    assert (kind, key) not in NEVER_EMPTY or cleared(sheet, key) is not None
    empty = cleared(sheet, key)
    if empty is not None:
        start = len(world.api.calls)
        calls = len(world.api.graphql_calls)
        try:
            world.save(world.state[key], empty)
        except (ValueError, EmptyValueError) as exc:  # GitHub needs a value: the sentence says so
            said = str(exc.args[0] if exc.args else exc)
            found["refused"] = said.split("] ", 1)[1] if said.startswith("[QUILL-") else said
        else:
            found["clear"] = _since(world, start, calls)
    return found


def _since(world: World, start: int, calls: int) -> list[list[Any]]:
    graphql = world.api.graphql_calls
    world.api.graphql_calls = graphql[calls:]
    try:
        return world.sent(start)
    finally:
        world.api.graphql_calls = graphql


def _table() -> dict[str, Any]:
    return {f"{kind}.{key}": _requests_for(kind, key) for kind, key in FIELDS}


@pytest.fixture(scope="module")
def recorded() -> dict[str, Any]:
    if os.environ.get("QUILL_WRITE_FIELD_REQUESTS"):
        FIXTURE.parent.mkdir(parents=True, exist_ok=True)
        FIXTURE.write_text(json.dumps(_table(), indent=1, sort_keys=True) + "\n", "utf-8")
    return dict(json.loads(FIXTURE.read_text("utf-8")))


def test_every_editable_field_of_every_sheet_is_in_the_table(recorded) -> None:
    """192 fields when this was written; a new one fails here until the table is rewritten."""
    assert len(FIELDS) >= 192
    assert sorted(recorded) == sorted(IDS)
    for kind, sheet in SHEETS.items():
        for key in sheet.editable_keys():
            assert key in sheet.writes, f"{kind}.{key} is editable with no write"


@pytest.mark.parametrize(("kind", "key"), FIELDS, ids=IDS)
def test_an_edit_sends_exactly_the_reviewed_request(recorded, kind: str, key: str) -> None:
    sheet = SHEETS[kind]
    before, after = sample(sheet, key)
    world = World(sheet, key, before)
    world.save(before, after)
    sent = world.sent()
    assert json.loads(json.dumps(sent)) == recorded[f"{kind}.{key}"]["set"]
    assert sent, "an edit sends something"
    text = json.dumps(sent)
    assert "{" + "repo}" not in text and "Mixed" not in text and "MIXED" not in text
    for _method, path, _body in sent:
        assert path.startswith("/") or path.startswith("mutation"), path
        assert "{" not in path.split("(", 1)[0], f"{path} has an unfilled placeholder"
    if key in sheet.secret_fields:
        assert "s3cret-value" not in text, "a secret is sealed, never sent as typed"


# -- verify after save ---------------------------------------------------------------


@pytest.mark.parametrize(("kind", "key"), FIELDS, ids=IDS)
def test_verify_after_save_claims_only_what_the_re_read_proves(kind: str, key: str) -> None:
    sheet = SHEETS[kind]
    before, after = sample(sheet, key)
    label = sheet.sheet.field(key).label
    took = World(sheet, key, before).save(before, after)
    ignored = World(sheet, key, before, takes=False).save(before, after)
    if key in sheet.secret_fields:
        # Write-only: GitHub never gives it back, so the save says "(set)" and never the value.
        assert [(c.key, c.after) for c in took.done] == [(key, "(set)")]
        assert "s3cret-value" not in sentence("It", took)
        return
    assert took.ok and [(c.key, c.after) for c in took.done] == [(key, _number(after))]
    assert not ignored.done and [c.key for c in ignored.not_taken] == [key]
    said = sentence("It", ignored)
    assert f"did not change {label.lower()}" in said


# -- history -------------------------------------------------------------------------


@pytest.mark.parametrize(("kind", "key"), FIELDS, ids=IDS)
def test_change_history_records_the_change_and_reads_it_back(
    tmp_path: Path, kind: str, key: str
) -> None:
    sheet = SHEETS[kind]
    before, after = sample(sheet, key)
    outcome = World(sheet, key, before).save(before, after)
    back, cannot = inverse(sheet, outcome.done)
    log = ChangeLog(tmp_path / "history.json")
    log.record(
        account="me",
        kind=kind,
        ident=sheet.ident_after(IDENT, outcome.done),
        target=sheet.title(IDENT) or kind,
        summary=sentence("It", outcome),
        changes=outcome.done,
        tier=int(sheet.writes[key].tier),
        confirmed=outcome.ok,
        can_undo=bool(back) and not cannot,
    )
    (entry,) = ChangeLog.load(tmp_path / "history.json").entries
    assert entry.as_changes() == outcome.done
    assert entry.kind == kind and entry.confirmed
    assert entry.can_undo is sheet.writes[key].undo
    if key in sheet.secret_fields:
        assert "s3cret-value" not in (tmp_path / "history.json").read_text("utf-8")


# -- undo and redo -------------------------------------------------------------------


@pytest.mark.parametrize(("kind", "key"), FIELDS, ids=IDS)
def test_undo_sends_the_inverse_or_says_plainly_why_not(monkeypatch, kind: str, key: str) -> None:
    sheet = SHEETS[kind]
    # Undo loads the pickers' choices itself, as the open sheet did (a milestone by number).
    monkeypatch.setattr(
        "quill.core.github.sheet_replay.load_options", lambda _a, _s, _i: _picks(sheet)
    )
    before, after = sample(sheet, key)
    world = World(sheet, key, before)
    done = world.save(before, after).done
    where = sheet.ident_after(IDENT, done)
    why = undo_refusal(sheet, done)
    if not sheet.writes[key].undo:
        assert why.startswith(f"{sheet.sheet.field(key).label} cannot be undone: ")
        assert len(why) > 40, "the reason is a sentence, not a bare refusal"
        assert undo_notes(sheet, done) == [why], "said in the preview before it happens too"
        return
    assert why == ""
    start, calls = len(world.api.calls), len(world.api.graphql_calls)
    world.target = before
    outcome = undo(world.api, world.sheet, where, done)
    assert outcome.ok and outcome.done, sentence("It", outcome)
    assert world.state[key] == before
    back, _ = inverse(sheet, done)
    expected = plan(
        world.sheet, adopted(world.sheet, where, world.state | {key: after}), back, _picks(sheet)
    )
    sent = _since(world, start, calls)
    assert len(sent) == len(expected)
    for request, (method, path, _body) in zip(expected, sent, strict=True):
        if request.graphql:
            assert method == "GRAPHQL"
        else:
            assert (request.method, request.path) == (method, path)
    # Redo makes it again, from where the undo left the object.
    world.target = _number(after)
    again = redo(world.api, world.sheet, where, done)
    assert again.ok and world.state[key] == _number(after)


# -- field removal -------------------------------------------------------------------


def _form(sheet: SheetDef, key: str, set_sent: list[Any], clear_sent: list[Any]) -> str:
    if clear_sent and all(row[0] == "DELETE" for row in clear_sent):
        return "DELETE"
    if clear_sent and all(
        row[0] == "GRAPHQL" and ("remove" in row[1] or "delete" in row[1]) for row in clear_sent
    ):
        return "remove mutation"
    if sheet.writes[key].kind == "toggle":
        return f"{sheet.writes[key].off_method} off"
    leaves = _changed_leaves(set_sent[0][2] if set_sent else None, clear_sent[0][2])
    if not leaves and len(clear_sent) == 1:
        leaves = _changed_leaves(None, clear_sent[0][2])
    kinds = {_leaf_kind(value) for value in leaves}
    return " and ".join(sorted(kinds)) or "unchanged"


def _changed_leaves(old: Any, new: Any) -> list[Any]:
    if isinstance(new, list) and isinstance(old, list) and new and len(new) == len(old):
        return [
            leaf for was, now in zip(old, new, strict=True) for leaf in _changed_leaves(was, now)
        ]
    if isinstance(new, dict):
        found: list[Any] = []
        for name, value in new.items():
            was = old.get(name) if isinstance(old, dict) else None
            if value != was:
                found.extend(_changed_leaves(was, value))
        return found
    return [new]


def _leaf_kind(value: Any) -> str:
    if value is None:
        return "null"
    if value == []:
        return "empty list"
    if value == "":
        return "empty text"
    if isinstance(value, bool):
        return "false" if not value else "true"
    if value == 0:
        return "zero"
    return "value"


def _clearable() -> list[tuple[str, str]]:
    return [(k, f) for k, f in FIELDS if cleared(SHEETS[k], f) is not None]


@pytest.mark.parametrize(("kind", "key"), _clearable(), ids=[f"{k}.{f}" for k, f in _clearable()])
def test_clearing_a_field_sends_the_remove_form_for_its_kind(recorded, kind: str, key: str) -> None:
    sheet = SHEETS[kind]
    row = recorded[f"{kind}.{key}"]
    label = sheet.sheet.field(key).label
    required = REQUIRED.get(f"{kind}.{key}") or emptied_refusal(
        kind, FieldChange(key, label, None, "")
    )
    if "refused" in row:
        # GitHub needs a value here, so emptying it is refused before anything is sent.
        assert required and row["refused"] == required
        return
    assert not required
    form = _form(sheet, key, row["set"], row["clear"])
    allowed = REMOVE_FORMS_BY_KIND[sheet.sheet.field(key).kind]
    assert form in allowed, f"{kind}.{key} is emptied as {form!r}, not one of {sorted(allowed)}"
    if f"{kind}.{key}" in REMOVE_EXACT:
        assert form == REMOVE_EXACT[f"{kind}.{key}"]


#: The remove form each kind of field may use.
REMOVE_FORMS_BY_KIND: dict[FieldKind, set[str]] = {
    # GitHub empties a string with "" (or null where it wants one: a due date).
    FieldKind.TEXT: {"empty text", "null"},
    FieldKind.MULTILINE: {"empty text", "null"},
    FieldKind.DATE: {"null"},
    # An emptied count is 0, which GitHub reads as off (or null for a section that goes).
    FieldKind.NUMBER: {"zero", "null"},
    # A picker emptied is null: no milestone, no type.
    FieldKind.CHOICE: {"null"},
    # A list emptied is an empty list, one DELETE per item, or null for a section that goes.
    FieldKind.LIST: {"empty list", "null", "DELETE"},
    FieldKind.CHECKLIST: {"empty list", "DELETE", "remove mutation"},
    # A toggle off is its DELETE (or the workflow's PUT .../disable).
    FieldKind.CHECK: {"DELETE", "PUT off"},
}

#: Fields whose own write refuses an empty value (beyond sheet_values.NEVER_EMPTY).
REQUIRED: dict[str, str] = {
    "label.colour": "A colour is needed: type a name such as green, or six hex digits.",
}

#: Where the form is not only allowed but required.
REMOVE_EXACT: dict[str, str] = {
    "issue.milestone": "null",
    "issue.issue_type": "null",
    "pull_request.milestone": "null",
    "milestone.due": "null",
    "issue.labels": "DELETE",
    "pull_request.reviewers": "DELETE",
    "pull_request.team_reviewers": "DELETE",
    "issue.assignees": "empty list",
    "repository.topics": "empty list",
    "branch_protection.approvals": "null",
    "branch_protection.status_checks": "null",
    "workflow.enabled": "PUT off",
}


# -- mixed values --------------------------------------------------------------------


@pytest.mark.parametrize(("kind", "key"), FIELDS, ids=IDS)
def test_a_field_that_differs_shows_mixed_and_left_alone_sends_nothing(kind: str, key: str) -> None:
    sheet = SHEETS[kind]
    before, after = sample(sheet, key)
    one = {**ADOPTED, key: before}
    two = {**ADOPTED, key: _number(after)}
    merged = merge_values([one, two])
    assert merged[key] is MIXED
    state = SheetState(sheet.sheet, loaded=dict(merged))
    assert state.pending() == ()
    api = FakeGitHubApi()
    items = [BatchItem("one", IDENT, one), BatchItem("two", IDENT, two)]
    results = run(api, sheet, items, state.pending(), pace=0)
    assert [r.status for r in results] == ["Skipped", "Skipped"]
    assert api.writes() == [] and api.graphql_calls == []


def test_a_mixed_field_left_alone_is_not_sent_while_another_field_is() -> None:
    sheet = SHEETS["issue"]
    first = {**ADOPTED, "milestone": "2027.1", "title": "A", "labels": ("docs",)}
    second = {**ADOPTED, "milestone": "2027.2", "title": "B", "labels": ()}
    merged = merge_values([first, second])
    assert merged["milestone"] is MIXED and merged["title"] is MIXED
    changes = [FieldChange("labels", "Labels", MIXED, ListDelta(added=("bug",)))]
    api = FakeGitHubApi()
    api.answer("GET", "/repos/owner/repo/issues/7", {"labels": [{"name": "bug"}]})
    api.answer("GET", "/repos/owner/repo/issues/8", {"labels": [{"name": "docs"}, {"name": "bug"}]})
    items = [
        BatchItem("#7", {"repo": "owner/repo", "number": "7"}, first),
        BatchItem("#8", {"repo": "owner/repo", "number": "8"}, second),
    ]
    run(api, sheet, items, changes, pace=0)
    assert api.writes() == [
        ("POST", "/repos/owner/repo/issues/7/labels", {"labels": ["bug"]}),
        ("POST", "/repos/owner/repo/issues/8/labels", {"labels": ["bug"]}),
    ]


# -- conflict resolution -------------------------------------------------------------

_WHOLE = [(k, f) for k, f in FIELDS if not is_set(SHEETS[k].writes[f])]


@pytest.mark.parametrize(("kind", "key"), _WHOLE, ids=[f"{k}.{f}" for k, f in _WHOLE])
def test_a_field_changed_on_github_since_it_was_read_stops_the_save(kind: str, key: str) -> None:
    sheet = SHEETS[kind]
    before, after = sample(sheet, key)
    if key in sheet.secret_fields:
        pytest.skip("a secret is never read, so there is nothing of theirs to compare")
    world = World(sheet, key, before)
    loaded = dict(world.state)
    theirs: Value = (
        "theirs"
        if isinstance(before, str) or before is None
        else (not before if isinstance(before, bool) else ("theirs",))
    )
    if isinstance(before, int) and not isinstance(before, bool):
        theirs = 5
    world.state[key] = theirs
    label = sheet.sheet.field(key).label
    outcome = save(
        world.api,
        world.sheet,
        IDENT,
        [FieldChange(key, label, before, after)],
        loaded=loaded,
        choices=_picks(sheet),
    )
    assert [(c.key, c.before) for c in outcome.conflicts] == [(key, theirs)]
    assert world.api.writes() == [] and not any(
        q.lstrip().startswith("mut") for q, _v in world.api.graphql_calls
    )
    assert "Changed on GitHub since you opened this" in sentence("It", outcome)
    assert "Nothing was saved." in sentence("It", outcome)
    # Keep Theirs drops the field; Use Mine sends it without asking again.
    kept = save(
        world.api,
        world.sheet,
        IDENT,
        [FieldChange(key, label, before, after)],
        loaded=loaded,
        keep_theirs=frozenset({key}),
        check_conflicts=False,
    )
    assert kept.done == [] and world.state[key] == theirs
    world.target = _number(after)
    mine = save(
        world.api,
        world.sheet,
        IDENT,
        [FieldChange(key, label, before, after)],
        loaded=loaded,
        choices=_picks(sheet),
        check_conflicts=False,
    )
    assert mine.ok and world.state[key] == _number(after)


def test_a_newer_updated_at_alone_is_no_conflict_fields_nobody_touched_save() -> None:
    sheet = SHEETS["issue"]
    world = World(sheet, "title", "old words")
    loaded = {**world.state, "updated": "9 November 2026, 14:05"}
    world.state["updated"] = "9 November 2026, 15:00"
    world.state["body"] = "somebody else's edit"
    world.target = "new words"
    outcome = save(
        world.api,
        world.sheet,
        IDENT,
        [FieldChange("title", "Title", "old words", "new words")],
        loaded=loaded,
    )
    assert outcome.ok and not outcome.conflicts
    assert world.state["body"] == "somebody else's edit"


def _ruleset_api(raw: dict[str, Any]) -> tuple[FakeGitHubApi, dict[str, Any]]:
    holder = {"raw": raw}
    api = FakeGitHubApi()
    api.answer("GET", "/repos/owner/repo/rulesets/9", lambda: holder["raw"])

    def on_write(method: str, _path: str, body: Any) -> None:
        if method == "PUT":
            holder["raw"] = {**holder["raw"], **body}

    api.on_write = on_write
    return api, holder


def test_a_whole_object_is_rebuilt_from_what_github_has_now_not_when_it_opened() -> None:
    """A ruleset is PUT whole: somebody's change to another field is kept, not put back."""
    sheet = SHEETS["ruleset"]
    opened = {"id": 9, "name": "Main", "enforcement": "active", "target": "branch", "rules": []}
    api, holder = _ruleset_api(opened)
    from quill.core.github.sheet_engine import load

    loaded = load(api, sheet, {"repo": "owner/repo", "id": "9"}).values
    holder["raw"] = {**opened, "enforcement": "evaluate"}  # somebody else, meanwhile
    outcome = save(
        api,
        sheet,
        {"repo": "owner/repo", "id": "9"},
        [FieldChange("name", "Name", "Main", "Main branch")],
        loaded=loaded,
    )
    assert outcome.ok, sentence("It", outcome)
    ((_method, _path, body),) = api.writes()
    assert body["name"] == "Main branch"
    assert body.get("enforcement", "evaluate") == "evaluate"
    assert holder["raw"]["enforcement"] == "evaluate"


def test_keep_theirs_on_a_whole_object_keeps_their_value_in_the_put() -> None:
    sheet = SHEETS["ruleset"]
    opened = {"id": 9, "name": "Main", "enforcement": "active", "target": "branch", "rules": []}
    api, holder = _ruleset_api(opened)
    from quill.core.github.sheet_engine import load

    ident = {"repo": "owner/repo", "id": "9"}
    loaded = load(api, sheet, ident).values
    holder["raw"] = {**opened, "enforcement": "evaluate"}
    changes = [
        FieldChange("name", "Name", "Main", "Main branch"),
        FieldChange("enforcement", "Enforcement", "active", "disabled"),
    ]
    stopped = save(api, sheet, ident, changes, loaded=loaded)
    assert [c.key for c in stopped.conflicts] == ["enforcement"]
    assert api.writes() == []
    kept = save(
        api, sheet, ident, changes, loaded=loaded, keep_theirs=frozenset({"enforcement"}),
        check_conflicts=False,
    )  # fmt: skip
    assert kept.ok
    assert holder["raw"]["enforcement"] == "evaluate" and holder["raw"]["name"] == "Main branch"


# -- numbers -------------------------------------------------------------------------


def test_a_number_box_that_is_not_a_number_stops_before_anything_is_sent() -> None:
    sheet = SHEETS["environment"]
    world = World(sheet, "wait_timer", 0)
    with pytest.raises(NotANumberError, match="Wait timer .*whole number"):
        world.save(0, "ten")
    assert world.api.writes() == []


# -- batches -------------------------------------------------------------------------


def _issue_world() -> tuple[FakeGitHubApi, dict[int, dict[str, Any]], set[int]]:
    issues = {
        n: {"number": n, "title": f"Issue {n}", "labels": [], "state": "open"} for n in (1, 2, 3)
    }
    failing: set[int] = set()
    api = FakeGitHubApi()
    for n in issues:
        api.answer("GET", f"/repos/owner/repo/issues/{n}", lambda n=n: issues[n])

    def on_write(method: str, path: str, body: Any) -> None:
        number = int(path.split("/")[5])
        if number in failing and path.endswith("/labels"):
            from quill.core.github.rest_transport import GitHubRestError

            raise GitHubRestError("Server Error", status=502)
        if method == "PATCH" and body and "title" in body:
            issues[number] = {**issues[number], "title": body["title"]}
        if method == "POST" and path.endswith("/labels"):
            names = [label["name"] for label in issues[number]["labels"]]
            names += [n for n in body["labels"] if n not in names]
            issues[number] = {**issues[number], "labels": [{"name": n} for n in names]}

    api.on_write = on_write
    return api, issues, failing


def _items(issues: Mapping[int, Mapping[str, Any]]) -> list[BatchItem]:
    """Each issue as the combined sheet loaded it."""
    from quill.core.github.sheet_engine import load

    found = []
    for n in issues:
        ident = {"repo": "owner/repo", "number": str(n)}
        values = load(_static(issues[n], n), SHEETS["issue"], ident).values
        found.append(BatchItem(f"#{n}", ident, values))
    return found


def _static(issue: Mapping[str, Any], n: int) -> FakeGitHubApi:
    api = FakeGitHubApi()
    api.answer("GET", f"/repos/owner/repo/issues/{n}", dict(issue))
    return api


def test_a_batch_says_per_row_done_skipped_or_failed_and_why() -> None:
    api, issues, failing = _issue_world()
    issues[2] = {**issues[2], "labels": [{"name": "bug"}]}
    items = _items(issues)
    failing.add(3)
    changes = [FieldChange("labels", "Labels", MIXED, ListDelta(added=("bug",)))]
    results = run(api, SHEETS["issue"], items, changes, pace=0)
    assert [(r.name, r.status) for r in results] == [
        ("#1", "Done"),
        ("#2", "Skipped"),
        ("#3", "Failed"),
    ]
    assert results[1].detail == "already so"
    assert "Server Error" in results[2].detail
    assert results_text(results).splitlines()[-1] == "1 done, 1 skipped, 1 failed"


def test_retry_failed_reads_again_so_what_took_the_first_time_is_not_a_conflict() -> None:
    """Title took and labels failed on #3; the retry sends only the labels."""
    api, issues, failing = _issue_world()
    items = _items(issues)
    failing.add(3)
    changes = [
        FieldChange("title", "Title", MIXED, "Same title"),
        FieldChange("labels", "Labels", MIXED, ListDelta(added=("bug",))),
    ]
    first = run(api, SHEETS["issue"], items, changes, pace=0)
    assert [r.status for r in first] == ["Done", "Done", "Failed"]
    assert issues[3]["title"] == "Same title"
    failing.clear()
    again = [item for item in items if item.name == "#3"]
    before = len(api.writes())
    retried = run(api, SHEETS["issue"], again, changes, pace=0, reload=True)
    assert [(r.name, r.status) for r in retried] == [("#3", "Done")]
    assert api.writes()[before:] == [
        ("POST", "/repos/owner/repo/issues/3/labels", {"labels": ["bug"]})
    ]


def test_without_a_fresh_read_a_retry_would_see_its_own_change_as_a_conflict() -> None:
    """Why Retry Failed reloads: the stale values make the first run's title look like theirs."""
    api, issues, failing = _issue_world()
    items = _items(issues)
    failing.add(3)
    changes = [
        FieldChange("title", "Title", MIXED, "Same title"),
        FieldChange("labels", "Labels", MIXED, ListDelta(added=("bug",))),
    ]
    run(api, SHEETS["issue"], items, changes, pace=0)
    failing.clear()
    stale = run(api, SHEETS["issue"], [items[2]], changes, pace=0)
    assert stale[0].status == "Failed" and "changed on GitHub meanwhile" in stale[0].detail


# -- the defects these tests found, each over a sheet's real reads -------------------


def test_a_number_saved_through_the_real_read_is_proved_not_reported_as_ignored() -> None:
    """A number box gives text; it is sent and compared as a number (it used to "not take")."""
    sheet = SHEETS["environment"]
    env: dict[str, Any] = {"name": "prod", "protection_rules": [], "can_admins_bypass": True}
    api = FakeGitHubApi()
    api.answer("GET", "/repos/owner/repo/environments/prod", lambda: env)

    def on_write(method: str, _path: str, body: Any) -> None:
        if method == "PUT":
            env["protection_rules"] = [{"type": "wait_timer", "wait_timer": body["wait_timer"]}]

    api.on_write = on_write
    from quill.core.github.sheet_engine import load

    ident = {"repo": "owner/repo", "name": "prod"}
    loaded = load(api, sheet, ident).values
    outcome = save(
        api, sheet, ident, [FieldChange("wait_timer", "Wait timer", 0, "10")], loaded=loaded
    )
    assert outcome.ok, sentence("prod", outcome)
    assert api.writes()[-1][2]["wait_timer"] == 10
    assert outcome.done[0].after == 10


def _milestone_api() -> tuple[FakeGitHubApi, dict[str, Any]]:
    milestones = [{"title": "2027.1", "number": 7}, {"title": "2027.2", "number": 8}]
    issue: dict[str, Any] = {
        "number": 42,
        "title": "Crash",
        "state": "open",
        "labels": [],
        "assignees": [],
        "milestone": milestones[0],
    }
    api = FakeGitHubApi()
    api.answer("GET", "/repos/owner/repo/issues/42", lambda: issue)
    api.answer("GET", "/repos/owner/repo/milestones", milestones)
    api.answer("GET", "/repos/owner/repo/labels", [])
    api.answer("GET", "/repos/owner/repo/assignees", [])

    def on_write(method: str, _path: str, body: Any) -> None:
        if method == "PATCH" and body and "milestone" in body:
            found = [m for m in milestones if m["number"] == body["milestone"]]
            issue["milestone"] = found[0] if found else None

    api.on_write = on_write
    return api, issue


def test_undo_puts_a_milestone_back_by_its_number_not_by_its_title() -> None:
    """Undo had no picker choices, so it sent the title, which GitHub read as no milestone."""
    from quill.core.github.sheet_engine import load, load_options

    sheet = SHEETS["issue"]
    api, issue = _milestone_api()
    ident = {"repo": "owner/repo", "number": "42"}
    loaded = load(api, sheet, ident).values
    change = FieldChange("milestone", "Milestone", "2027.1", "2027.2")
    done = save(
        api, sheet, ident, [change], loaded=loaded, choices=load_options(api, sheet, ident)
    ).done
    assert issue["milestone"]["number"] == 8
    outcome = undo(api, sheet, ident, done)
    assert outcome.ok, sentence("#42", outcome)
    assert api.writes()[-1] == ("PATCH", "/repos/owner/repo/issues/42", {"milestone": 7})
    assert issue["milestone"]["title"] == "2027.1"


def test_undo_of_a_ruleset_field_keeps_every_other_rule() -> None:
    """Undo rebuilt the ruleset from nothing, so it would have PUT it back with no rules."""
    sheet = SHEETS["ruleset"]
    raw = {
        "id": 9,
        "name": "Main",
        "enforcement": "active",
        "target": "branch",
        "rules": [{"type": "deletion"}, {"type": "non_fast_forward"}],
    }
    api, holder = _ruleset_api(raw)
    from quill.core.github.sheet_engine import load

    ident = {"repo": "owner/repo", "id": "9"}
    loaded = load(api, sheet, ident).values
    done = save(
        api, sheet, ident, [FieldChange("name", "Name", "Main", "Main branch")], loaded=loaded
    ).done
    outcome = undo(api, sheet, ident, done)
    assert outcome.ok, sentence("Main", outcome)
    put = api.writes()[-1][2]
    assert put["name"] == "Main"
    assert [rule["type"] for rule in put["rules"]] == ["deletion", "non_fast_forward"]
    assert holder["raw"]["name"] == "Main"


def test_a_renamed_label_is_undone_at_its_new_name_and_redone_at_its_old_one() -> None:
    """History named the label by its old name, so Undo asked GitHub for a label that was gone."""
    sheet = SHEETS["label"]
    labels: dict[str, dict[str, Any]] = {"bug": {"name": "bug", "color": "d73a4a"}}
    api = FakeGitHubApi()
    for name in ("bug", "defect"):
        api.answer(
            "GET",
            f"/repos/owner/repo/labels/{name}",
            lambda name=name: labels.get(name) or GitHubRestErrorFor404(),
        )

    def on_write(method: str, path: str, body: Any) -> None:
        old = path.rsplit("/", 1)[-1]
        if method == "PATCH" and old in labels and body and "new_name" in body:
            labels[body["new_name"]] = {**labels.pop(old), "name": body["new_name"]}

    api.on_write = on_write
    from quill.core.github.sheet_engine import load

    ident = {"repo": "owner/repo", "name": "bug"}
    loaded = load(api, sheet, ident).values
    done = save(
        api, sheet, ident, [FieldChange("name", "Name", "bug", "defect")], loaded=loaded
    ).done
    where = sheet.ident_after(ident, done)  # what Change History now keeps
    assert where["name"] == "defect"
    assert undo(api, sheet, where, done).ok
    assert api.writes()[-1] == ("PATCH", "/repos/owner/repo/labels/defect", {"new_name": "bug"})
    assert redo(api, sheet, where, done).ok
    assert api.writes()[-1] == ("PATCH", "/repos/owner/repo/labels/bug", {"new_name": "defect"})
    assert list(labels) == ["defect"]


def GitHubRestErrorFor404() -> Any:  # noqa: N802 - reads as the answer it stands for
    from quill.core.github.rest_transport import GitHubRestError

    raise GitHubRestError("Not Found", status=404)


def test_undo_stops_when_somebody_changed_the_field_since() -> None:
    sheet = SHEETS["issue"]
    world = World(sheet, "title", "old words")
    done = world.save("old words", "new words").done
    world.state["title"] = "their words"
    before = len(world.api.writes())
    outcome = undo(world.api, world.sheet, IDENT, done)
    assert [(c.key, c.before) for c in outcome.conflicts] == [("title", "their words")]
    assert len(world.api.writes()) == before
