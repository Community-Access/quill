"""The shared action table and the context-menu rules every provider inherits."""

from __future__ import annotations

import pytest

from quill.core.workbench import WorkbenchSpecError
from quill.core.workbench.actions import (
    PROPERTIES_COMMAND,
    ActionRow,
    ActionScope,
    ActionTable,
    Tier,
    split_for_menu,
)


def _row(
    command: str, *, default: bool = False, scope: ActionScope = ActionScope.ITEM
) -> ActionRow:
    return ActionRow(command, command.title(), default=default, scope=scope)


def _properties() -> ActionRow:
    return ActionRow(PROPERTIES_COMMAND, "Properties...\tAlt+Enter")


def test_split_keeps_short_menus_whole() -> None:
    assert split_for_menu(list(range(8))) == (list(range(8)), [])


def test_split_leaves_room_for_more_among_eight() -> None:
    top, more = split_for_menu(list(range(12)))
    assert top == list(range(7))
    assert more == list(range(7, 12))


def test_split_refuses_a_menu_with_no_room() -> None:
    with pytest.raises(WorkbenchSpecError):
        split_for_menu([1, 2], 1)


def test_a_table_needs_its_default_first_and_properties_last() -> None:
    with pytest.raises(WorkbenchSpecError):
        ActionTable({"thing": [_row("b"), _row("a", default=True), _properties()]})
    with pytest.raises(WorkbenchSpecError):
        ActionTable({"thing": [_row("a", default=True), _row("b")]})
    table = ActionTable({"thing": [_row("a", default=True), _row("b"), _properties()]})
    assert table.default_for("thing").command_id == "a"


def test_a_table_refuses_rows_that_are_not_about_the_item() -> None:
    with pytest.raises(WorkbenchSpecError):
        ActionTable({
            "thing": [
                _row("a", default=True),
                _row("rate", scope=ActionScope.ACCOUNT),
                _properties(),
            ]
        })


def test_a_command_appears_once_per_row_type() -> None:
    with pytest.raises(WorkbenchSpecError):
        ActionTable({"thing": [_row("a", default=True), _row("b"), _row("b"), _properties()]})


def test_menu_for_keeps_properties_last_when_more_is_needed() -> None:
    rows = [_row("a", default=True), *(_row(f"r{n}") for n in range(10)), _properties()]
    table = ActionTable({"thing": rows})
    top, more = table.menu_for("thing")
    assert len(top) + 1 == 8  # More is the eighth entry
    assert top[0].command_id == "a"
    assert top[-1].command_id == PROPERTIES_COMMAND
    assert [row.command_id for row in more] == [f"r{n}" for n in range(5, 10)]


def test_tiers_order_by_how_much_they_change() -> None:
    assert Tier.READ < Tier.ORGANIZE < Tier.WRITE < Tier.DESTRUCTIVE
