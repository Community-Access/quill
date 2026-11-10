"""The shared engine's additions for GitHub Phases 7 to 10: submenus, check lists, deltas."""

from __future__ import annotations

from quill.core.workbench.menus import MenuRow, MenuSpec, MenuSub, all_rows, problems, rows
from quill.core.workbench.properties import (
    FieldKind,
    FieldSpec,
    ListDelta,
    PageSpec,
    SheetSpec,
    apply_delta,
    as_text,
    changes,
    list_states,
)


def _bar(*subs: MenuSub) -> tuple[MenuSpec, ...]:
    return (MenuSpec("&View", (MenuRow("v.refresh", "R&efresh", "F5", "Load again."), *subs)),)


def test_a_submenu_row_may_go_keyless_when_it_has_an_access_letter() -> None:
    bar = _bar(MenuSub("&Show", (MenuRow("v.issues", "&Issues", radio="show"),)))
    assert problems(bar) == []
    assert [row.command_id for _m, row in rows(bar)] == ["v.refresh"]
    assert [row.command_id for _m, row in all_rows(bar)] == ["v.refresh", "v.issues"]


def test_a_submenu_row_with_neither_key_nor_letter_breaks_the_rule() -> None:
    bar = _bar(MenuSub("&Show", (MenuRow("v.issues", "Issues"),)))
    assert any("no key route" in found for found in problems(bar))


def test_submenu_letters_and_titles_are_checked() -> None:
    bar = _bar(
        MenuSub("Show", (MenuRow("v.a", "&Alpha"), MenuRow("v.b", "&Also"))),
        MenuSub("&Pinned", dynamic="pinned"),
    )
    found = problems(bar)
    assert any("Show has no access key" in f for f in found)
    assert any("two rows on the access key 'a'" in f for f in found)


def test_a_dynamic_submenu_has_no_static_rows() -> None:
    bar = _bar(MenuSub("&Pinned", (MenuRow("v.x", "&X"),), dynamic="pinned"))
    assert any("dynamic and also has rows" in f for f in problems(bar))


def test_list_states_count_each_value_across_objects() -> None:
    objects = [{"labels": ("bug", "ui")}, {"labels": ("bug",)}, {"labels": ()}]
    assert list_states(objects, "labels") == {"bug": 2, "ui": 1}


def test_apply_delta_removes_then_adds_and_keeps_order() -> None:
    delta = ListDelta(added=("docs", "bug"), removed=("ui",))
    assert apply_delta(("bug", "ui", "triage"), delta) == ("bug", "triage", "docs")
    assert not ListDelta()


def test_an_empty_delta_is_not_a_change_and_a_real_one_is() -> None:
    sheet = SheetSpec(
        "issue",
        "Issue",
        (PageSpec("general", "General", (FieldSpec("labels", "Labels", FieldKind.CHECKLIST),)),),
    )
    assert changes(sheet, {}, {"labels": ListDelta()}) == ()
    found = changes(sheet, {}, {"labels": ListDelta(added=("bug",))})
    assert [c.key for c in found] == ["labels"]
    assert "add bug" in as_text(sheet, {"labels": ListDelta(added=("bug",))})


def test_a_field_can_name_its_new_button() -> None:
    spec = FieldSpec("milestone", "Milestone", FieldKind.CHOICE, create="New Milestone...")
    assert spec.create == "New Milestone..."
