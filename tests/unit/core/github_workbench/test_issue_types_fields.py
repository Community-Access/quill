"""Issue types and organization issue fields as typed values (complete.md 1.3).

On the Workbench's issue rows (a column), in details, as filters and on the
Properties sheet; and the six states -- a value, empty, not set, hidden,
unsupported (read only) and unreadable -- never read alike anywhere.
"""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from quill.core.github.across_issue_fields import FieldValue, IssueExtras, read_issue_extras
from quill.core.github.issue_fields_rows import (
    FIELD_PAGE,
    STATE_KEY,
    cell,
    detail_lines,
    field_choices,
    issue_type_of,
    read_row_fields,
    sheet_values,
    with_field_page,
)
from quill.core.github.items_provider import GitHubItem
from quill.core.github.rest_transport import GitHubRestError
from quill.core.github.sheet_engine import load
from quill.core.github.sheets_items import ISSUE
from quill.core.workbench.properties import FieldKind
from tests.github_api_fake import FakeGitHubApi

REPO = "acme/site"
DEFS = [
    {"id": 1, "name": "Priority", "data_type": "single_select", "options": [{"name": "High"}]},
    {"id": 2, "name": "Due", "data_type": "date"},
    {"id": 3, "name": "Points", "data_type": "number"},
    {"id": 4, "name": "Notes", "data_type": "text"},
    {"id": 5, "name": "Areas", "data_type": "multi_select"},
    {"id": 6, "name": "Odd", "data_type": "hologram"},
    {"id": 7, "name": "Owner", "data_type": "text"},
]
VALUES = [
    {"issue_field_id": 1, "single_select_option": {"name": "High"}},
    {"issue_field_id": 2, "value": "2026-12-31"},
    {"issue_field_id": 3, "value": 3.0},
    {"issue_field_id": 4, "value": ""},
    {"issue_field_id": 5, "values": [{"name": "Docs"}, {"name": "UI"}]},
    {"issue_field_id": 6, "value": "shimmer"},
]


def _issue(number: int, issue_type: str = "", **kw: object) -> GitHubItem:
    url = f"https://github.com/{REPO}/issues/{number}"
    return GitHubItem(number, f"Issue {number}", "open", url, False, issue_type=issue_type, **kw)  # type: ignore[arg-type]


def _api() -> FakeGitHubApi:
    api = FakeGitHubApi()
    api.answer("GET", "/orgs/acme/issue-fields", DEFS)
    api.answer("GET", f"/repos/{REPO}/issues/1/issue-field-values", VALUES)
    return api


def _states() -> dict[str, FieldValue]:
    return {
        "value": FieldValue("1", "Priority", "single_select", "value", ("High",)),
        "empty": FieldValue("4", "Priority", "text", "empty", ()),
        "unset": FieldValue("7", "Priority", "text", "unset"),
        "hidden": FieldValue("1", "Priority", "single_select", "hidden"),
        "unsupported": FieldValue("6", "Priority", "hologram", "unsupported", ("x",)),
        "unavailable": FieldValue("1", "Priority", "text", "unavailable", reason="no answer"),
    }


# -- typed values -------------------------------------------------------------------------


def test_each_kind_reads_as_its_type() -> None:
    assert FieldValue("2", "Due", "date", "value", ("2026-12-31",)).typed() == date(2026, 12, 31)
    assert FieldValue("3", "Points", "number", "value", ("3.0",)).typed() == 3
    assert FieldValue("3", "Points", "number", "value", ("2.5",)).typed() == 2.5
    assert FieldValue("1", "Priority", "single_select", "value", ("High",)).typed() == "High"
    many = FieldValue("5", "Areas", "multi_select", "value", ("Docs", "UI"))
    assert many.typed() == ("Docs", "UI")
    assert FieldValue("4", "Notes", "text", "value", ("hi",)).typed() == "hi"
    # A value that is not its declared type stays the text GitHub sent, never a guess.
    assert FieldValue("2", "Due", "date", "value", ("soon",)).typed() == "soon"
    for state, field in _states().items():
        if state != "value":
            assert field.typed() is None, state


def test_the_six_states_never_read_alike() -> None:
    fields = _states()
    for say in (FieldValue.short, FieldValue.words):
        said = {state: say(field).split(": ", 1)[1] for state, field in fields.items()}
        assert len(set(said.values())) == len(fields), said
    assert fields["unsupported"].short() == "Priority: x (read only)"
    assert fields["hidden"].short() == "Priority: hidden"
    assert fields["unavailable"].short() == "Priority: unreadable"
    assert "does not edit yet" in fields["unsupported"].words()


# -- rows: the type for free, the fields when asked ------------------------------------------


def test_the_issue_type_comes_from_the_list_row_without_a_request() -> None:
    assert issue_type_of(SimpleNamespace(raw_data={"type": {"name": "Bug"}})) == "Bug"
    assert issue_type_of(SimpleNamespace(raw_data={"type": None})) == ""
    assert issue_type_of(SimpleNamespace(type=SimpleNamespace(name="Task"))) == "Task"
    assert issue_type_of(SimpleNamespace()) == ""


def test_rows_gain_typed_fields_and_pull_requests_are_left_alone() -> None:
    api = _api()
    api.answer(
        "GET",
        f"/repos/{REPO}/issues/2/issue-field-values",
        GitHubRestError("Server Error", status=500),
    )
    pull = GitHubItem(9, "PR", "open", "u", True)
    rows = read_row_fields(api, REPO, [_issue(1, "Bug"), _issue(2), pull])
    one, two, pr = rows
    assert isinstance(one, GitHubItem) and isinstance(two, GitHubItem)
    assert pr is pull and pull.issue_fields is None
    # The type came with the row, so the issue list was not read again.
    assert ("GET", f"/repos/{REPO}/issues", None) not in api.calls
    assert one.issue_fields is not None and one.issue_fields.issue_type == "Bug"
    states = {f.name: f.state for f in one.issue_fields.fields}
    assert states == {
        "Priority": "value",
        "Due": "value",
        "Points": "value",
        "Notes": "empty",
        "Areas": "value",
        "Odd": "unsupported",
        "Owner": "unset",
    }
    typed = {f.name: f.typed() for f in one.issue_fields.fields}
    assert typed["Due"] == date(2026, 12, 31) and typed["Points"] == 3
    assert two.issue_fields is not None and two.issue_fields.fields_state == "unavailable"
    assert cell(one, "issue_type") == "Bug" and cell(two, "issue_type") == "no type"
    assert cell(one, "issue_fields") == (
        "Priority: High; Due: 2026-12-31; Points: 3; Notes: empty; Areas: Docs, UI; "
        "Odd: shimmer (read only); Owner: not set"
    )
    assert str(cell(two, "issue_fields")).startswith("unreadable: ")
    assert "Server Error" in str(cell(two, "issue_fields"))
    assert cell(pull, "issue_fields") == "" and cell(one, "title") is None


def test_hidden_unreadable_unread_and_none_defined_cells_differ() -> None:
    cells = {
        "not read": cell(_issue(1), "issue_fields"),
        "hidden": cell(_issue(1, issue_fields=IssueExtras(fields_state="hidden")), "issue_fields"),
        "unreadable": cell(
            _issue(1, issue_fields=IssueExtras(fields_state="unavailable", reason="timed out")),
            "issue_fields",
        ),
        "past the bound": cell(
            _issue(1, issue_fields=IssueExtras(fields_state="not_read")), "issue_fields"
        ),
        "none": cell(_issue(1, issue_fields=IssueExtras(fields_state="read")), "issue_fields"),
    }
    assert len(set(cells.values())) == len(cells), cells
    assert cells["hidden"] == "hidden from you"
    assert cells["none"] == "none defined"


def test_a_forbidden_definitions_read_is_hidden_and_a_person_falls_back_to_their_own() -> None:
    api = FakeGitHubApi()
    api.answer(
        "GET", "/orgs/acme/issue-fields", GitHubRestError("Must have admin rights", status=403)
    )
    found = read_row_fields(api, REPO, [_issue(1)])[0]
    assert isinstance(found, GitHubItem) and found.issue_fields is not None
    assert found.issue_fields.fields_state == "hidden"
    # A person's repository: the organization read is a 404, so their own fields are used.
    mine = FakeGitHubApi()
    mine.answer("GET", "/user/issue-fields", DEFS[:1])
    mine.answer("GET", "/repos/jeff/notes/issues/1/issue-field-values", [])
    got = read_issue_extras(mine, "jeff/notes", [1], organization="jeff", types={1: ""})[1]
    assert got.fields_state == "read" and got.fields[0].state == "unset"


def test_details_name_the_type_and_each_field_in_its_state() -> None:
    assert detail_lines(_issue(1, "Bug")) == ["Issue type: Bug"]
    assert detail_lines(_issue(1)) == ["Issue type: none"]
    assert detail_lines(GitHubItem(9, "PR", "open", "u", True)) == []
    row = read_row_fields(_api(), REPO, [_issue(1, "Bug")])[0]
    lines = detail_lines(row)
    assert lines[0] == "Issue type: Bug"
    assert "Field Due (date, field 2): 2026-12-31" in lines
    assert "Field Points (number, field 3): 3" in lines
    assert "Field Notes (text, field 4): set to nothing" in lines
    assert "Field Owner (text, field 7): not set" in lines


def test_show_only_writes_the_qualifiers_github_search_answers() -> None:
    row = read_row_fields(_api(), REPO, [_issue(1, "Bug")])[0]
    tokens = [token for token, _words in field_choices(row)]
    assert tokens == [
        "field.priority:High",
        "field.due:2026-12-31",
        "field.points:3",
        "field.areas:Docs",
        "field.areas:UI",
    ]
    spaced = _issue(
        2,
        issue_fields=IssueExtras(
            fields=(FieldValue("8", "Story points", "number", "value", ("5",)),),
            fields_state="read",
        ),
    )
    assert field_choices(spaced) == []  # GitHub wants a quoted name the box cannot carry


# -- Properties --------------------------------------------------------------------------


def test_the_sheet_gains_one_typed_read_only_field_per_issue_field() -> None:
    api = _api()
    api.answer("GET", f"/repos/{REPO}/issues/1", {"number": 1, "type": {"name": "Bug"}})
    loaded = load(api, ISSUE, {"repo": REPO, "number": "1"})
    values = loaded.values
    assert values["issue_type"] == "Bug"
    assert values[STATE_KEY] == "7 fields"
    sheet = with_field_page(ISSUE.sheet, values)
    keys = [page.key for page in sheet.pages]
    assert keys.index(FIELD_PAGE) == keys.index("organize") + 1
    page = next(page for page in sheet.pages if page.key == FIELD_PAGE)
    kinds = {spec.label: spec.kind for spec in page.fields}
    assert kinds["Priority"] is FieldKind.CHOICE
    assert kinds["Due"] is FieldKind.DATE
    assert kinds["Points"] is FieldKind.NUMBER
    assert kinds["Areas"] is FieldKind.LIST
    assert kinds["Odd"] is FieldKind.TEXT
    assert all(spec.readonly for spec in page.fields)
    odd = next(spec for spec in page.fields if spec.label == "Odd")
    assert "does not edit yet" in odd.help
    by_label = {spec.label: values.get(spec.key) for spec in page.fields}
    assert by_label["Points"] == 3 and by_label["Due"] == "2026-12-31"
    assert by_label["Areas"] == ("Docs", "UI")
    assert by_label["Notes"] == "set to nothing" and by_label["Owner"] == "not set"
    assert by_label["Odd"] == "shimmer (read only)"
    # A pull request's values carry no fields, so its sheet is unchanged.
    assert with_field_page(ISSUE.sheet, {"title": "x"}) is ISSUE.sheet


def test_the_sheet_says_hidden_and_unreadable_apart() -> None:
    hidden = FakeGitHubApi()
    hidden.answer(
        "GET", "/orgs/acme/issue-fields", GitHubRestError("Must have admin rights", status=403)
    )
    broken = FakeGitHubApi()
    broken.answer("GET", "/orgs/acme/issue-fields", GitHubRestError("Bad gateway", status=502))
    ident = {"repo": REPO, "number": "1"}
    said_hidden = sheet_values(hidden, ident)[STATE_KEY]
    said_broken = sheet_values(broken, ident)[STATE_KEY]
    assert said_hidden == "hidden from you in this repository"
    assert str(said_broken).startswith("could not be read")
    none = FakeGitHubApi()
    none.answer("GET", "/orgs/acme/issue-fields", [])
    none.answer("GET", f"/repos/{REPO}/issues/1/issue-field-values", [])
    assert sheet_values(none, ident)[STATE_KEY] == "the owner defines none"
