"""The shared Workbench engine: tree, sheets, filters, help, history and coverage."""

from __future__ import annotations

import pytest

from quill.core.workbench import WorkbenchSpecError
from quill.core.workbench.coverage import CoverageRow, CoverageStatus, CoverageTable
from quill.core.workbench.filters import (
    Condition,
    Operator,
    describe,
    matches_words,
    parse,
    render,
)
from quill.core.workbench.help import HelpCatalogue, HelpRecord
from quill.core.workbench.history import Change, ChangeHistory
from quill.core.workbench.properties import (
    MIXED,
    FieldKind,
    FieldSpec,
    PageSpec,
    SheetSpec,
    SheetState,
    as_text,
    changes,
    conflicts,
    merge_values,
)
from quill.core.workbench.tree import NodeSpec, TreeSpec

# -- tree ---------------------------------------------------------------------


def _tree(**kwargs: object) -> TreeSpec:
    return TreeSpec(
        [
            NodeSpec("sites", "Sites", template="site"),
            NodeSpec("search", "Search", loader="p:search"),
        ],
        {
            "site": [
                NodeSpec("site", "a site"),
                NodeSpec("content", "Content", parent="site"),
                NodeSpec("posts", "Posts", parent="content", loader="p:posts"),
            ]
        },
        **kwargs,  # type: ignore[arg-type]
    )


def test_a_tree_lists_roots_children_and_paths() -> None:
    tree = _tree()
    assert [node.key for node in tree.roots()] == ["sites", "search"]
    assert [n.key for n in tree.children("content", template="site")] == ["posts"]
    assert tree.path("search") == ("Search",)
    assert tree.depth("sites") == 4


def test_a_tree_counts_its_template_toward_the_depth_limit() -> None:
    with pytest.raises(WorkbenchSpecError):
        _tree(max_depth=3)


def test_a_tree_refuses_bad_keys_parents_and_templates() -> None:
    with pytest.raises(WorkbenchSpecError):
        TreeSpec([NodeSpec("a", "A"), NodeSpec("a", "Again")])
    with pytest.raises(WorkbenchSpecError):
        TreeSpec([NodeSpec("child", "Child", parent="later"), NodeSpec("later", "Later")])
    with pytest.raises(WorkbenchSpecError):
        TreeSpec([NodeSpec("a", "A", template="nowhere")])


def test_loaders_and_homes_cover_templates() -> None:
    tree = _tree()
    assert tree.loaders() == {"p:search": [("", "search")], "p:posts": [("site", "posts")]}
    assert tree.homes() == tree.loaders()


# -- properties -----------------------------------------------------------------

SHEET = SheetSpec(
    "issue",
    "Issue",
    (
        PageSpec(
            "general",
            "General",
            (
                FieldSpec("number", "Number", FieldKind.NUMBER, readonly=True),
                FieldSpec("title", "Title"),
                FieldSpec("labels", "Labels", FieldKind.LIST, requirement="triage"),
            ),
        ),
        PageSpec("you", "You", (FieldSpec("subscribed", "Subscribed", FieldKind.CHECK),)),
    ),
)


def test_a_sheet_opens_on_general_and_names_fields_once() -> None:
    with pytest.raises(WorkbenchSpecError):
        SheetSpec("x", "X", (PageSpec("other", "Other", ()),))
    with pytest.raises(WorkbenchSpecError):
        SheetSpec(
            "x",
            "X",
            (PageSpec("general", "General", (FieldSpec("a", "A"), FieldSpec("a", "Again"))),),
        )
    assert SHEET.heading("Issue #42", "o/r") == "Issue #42 Properties - o/r"


def test_several_objects_show_mixed_where_they_differ() -> None:
    merged = merge_values([{"title": "A", "labels": ("bug",)}, {"title": "B", "labels": ("bug",)}])
    assert merged["title"] is MIXED
    assert merged["labels"] == ("bug",)
    assert str(MIXED) == "Mixed"


def test_only_changed_editable_fields_are_sent() -> None:
    loaded = {"number": 42, "title": "Old", "labels": ("bug",), "subscribed": False}
    edited = {**loaded, "number": 43, "title": "New", "labels": MIXED}
    sent = changes(SHEET, loaded, edited)
    assert [change.key for change in sent] == ["title"]
    state = SheetState(SHEET, dict(loaded))
    state.set("subscribed", True)
    assert [change.key for change in state.pending()] == ["subscribed"]
    with pytest.raises(WorkbenchSpecError):
        state.set("number", 1)


def test_conflicts_name_only_fields_someone_else_changed() -> None:
    loaded = {"title": "Old", "labels": ("bug",)}
    pending = changes(SHEET, loaded, {"title": "Mine", "labels": ("docs",)})
    found = conflicts(pending, loaded, {"title": "Theirs", "labels": ("bug",)})
    assert [(c.key, c.before, c.after) for c in found] == [("title", "Theirs", "Mine")]


def test_copy_as_text_reads_every_page() -> None:
    text = as_text(SHEET, {"number": 42, "title": "Fix", "labels": (), "subscribed": True})
    assert text.splitlines() == [
        "Issue",
        "",
        "General",
        "Number: 42",
        "Title: Fix",
        "Labels: none",
        "",
        "You",
        "Subscribed: yes",
    ]


# -- filters --------------------------------------------------------------------


def test_a_query_splits_into_qualifiers_and_words() -> None:
    query = parse('is:open -label:docs created:>2026-01-01 "screen reader" crash')
    assert query.conditions == (
        Condition("is", Operator.IS, "open"),
        Condition("label", Operator.IS_NOT, "docs"),
        Condition("created", Operator.AFTER, "2026-01-01"),
    )
    assert query.words == ("screen reader", "crash")
    assert render(query) == 'is:open -label:docs created:>2026-01-01 "screen reader" crash'


def test_a_query_round_trips_through_the_builder() -> None:
    query = parse("").with_condition(Condition("label", Operator.IS, "good first issue"))
    assert render(query) == 'label:"good first issue"'
    assert parse(render(query)) == query
    assert render(query.without("label")) == ""


def test_a_filter_is_said_in_words() -> None:
    assert describe(parse("")) == "No filter"
    assert describe(parse("label:bug fix")) == "label is bug, containing fix"


def test_local_words_match_ignoring_case() -> None:
    assert matches_words("Fix the Crash on start", ["crash", "FIX"])
    assert not matches_words("Fix it", ["crash"])
    assert parse("https://github.com/o/r").words == ("https://github.com/o/r",)


# -- help -----------------------------------------------------------------------


def test_help_links_must_resolve_and_ids_are_unique() -> None:
    with pytest.raises(WorkbenchSpecError):
        HelpCatalogue([HelpRecord("a", "A", "", related=("b",))])
    with pytest.raises(WorkbenchSpecError):
        HelpCatalogue([HelpRecord("a", "A", ""), HelpRecord("a", "A2", "")])


def test_help_finds_records_by_command_and_words() -> None:
    catalogue = HelpCatalogue([
        HelpRecord("node.inbox", "Inbox", "What needs you.", commands=("go.inbox",)),
        HelpRecord("go.refresh", "Refresh", "Load this view again."),
    ])
    assert catalogue.for_command("go.inbox") is catalogue.get("node.inbox")
    assert catalogue.for_command("go.refresh") is catalogue.get("go.refresh")
    assert catalogue.missing(["node.inbox", "node.other"]) == ("node.other",)
    assert [r.id for r in catalogue.search("view again")] == ["go.refresh"]
    assert catalogue.get("go.refresh").spoken() == "Refresh. Load this view again."  # type: ignore[union-attr]


# -- history --------------------------------------------------------------------


def test_history_undoes_and_redoes_in_order() -> None:
    labels: list[str] = ["bug"]
    history = ChangeHistory()
    assert history.undo() == "Nothing to undo."
    labels.append("docs")
    history.record(
        Change(
            "#42",
            "#42: added docs",
            undo=lambda: labels.remove("docs") or "#42: removed docs",  # type: ignore[func-returns-value]
            redo=lambda: labels.append("docs") or "#42: added docs",  # type: ignore[func-returns-value]
        )
    )
    assert history.can_undo()
    assert history.undo() == "#42: removed docs"
    assert labels == ["bug"]
    assert history.redo() == "#42: added docs"
    assert labels == ["bug", "docs"]


def test_a_change_that_cannot_be_undone_says_so() -> None:
    history = ChangeHistory()
    history.record(Change("main", "Deleted branch old"))
    assert not history.can_undo()
    assert history.undo() == "Deleted branch old cannot be undone."
    assert len(history.entries) == 1


# -- coverage -------------------------------------------------------------------


def test_coverage_counts_and_finds_what_has_no_row() -> None:
    table = CoverageTable([
        CoverageRow("GET /issues", CoverageStatus.BUILT, "issues"),
        CoverageRow("GET /wiki", CoverageStatus.PLANNED, "wiki", reference="GX12"),
        CoverageRow("POST /token", CoverageStatus.SITE_ONLY, "GitHub offers no API"),
    ])
    assert table.summary() == "1 built, 1 planned, 1 on the site only"
    assert table.missing(["GET /issues", "GET /packages"]) == ("GET /packages",)
    with pytest.raises(WorkbenchSpecError):
        CoverageTable([CoverageRow("x", CoverageStatus.BUILT, "")])
