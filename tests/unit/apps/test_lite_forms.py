"""Forms in both editors: every row runs the shared command, and only that (17a.10).

QUILL Lite may never be ahead of QUILL, and the cheapest way to break that is
a second implementation. So each ``cmd_forms_*`` is checked to hand straight
to the shared :class:`~quill.ui.forms_commands.FormsCommands` method its row
names, neither adapter may define a ``cmd_*`` beyond those hand-offs, and the
two editors' menus are both read from ``quill/core/forms/menu.py``.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pytest

from quill.apps.lite_window_forms import DocumentFormsMixin
from quill.core.forms.menu import DOCUMENT_ONLY, PLACES, all_rows, is_form_path, lite_handler
from quill.core.lite.commands import COMMANDS


class _Recorder:
    def __init__(self) -> None:
        self.ran: list[str] = []

    def __getattr__(self, name: str):
        if not name.startswith("cmd_"):
            raise AttributeError(name)
        return lambda: self.ran.append(name)


class _Window(DocumentFormsMixin):
    def __init__(self) -> None:
        self._forms_commands = _Recorder()


@pytest.mark.parametrize(
    ("run", "shared"),
    [
        (lambda w: w.cmd_forms_new_form(), "cmd_new_form"),
        (lambda w: w.cmd_forms_insert_field(), "cmd_insert_field"),
        (lambda w: w.cmd_forms_outline(), "cmd_outline"),
        (lambda w: w.cmd_forms_rules(), "cmd_rules"),
        (lambda w: w.cmd_forms_check(), "cmd_check"),
        (lambda w: w.cmd_forms_fill_in(), "cmd_fill_in"),
        (lambda w: w.cmd_forms_properties(), "cmd_properties"),
        (lambda w: w.cmd_forms_responses(), "cmd_responses"),
    ],
)
def test_each_lite_row_runs_the_shared_command(run, shared) -> None:
    window = _Window()
    run(window)
    assert window._forms_commands.ran == [shared]


def test_every_row_has_a_lite_handler_test_above() -> None:
    names = {lite_handler(cid) for _p, (cid, _t, _h) in all_rows()}
    source = Path(__file__).read_text(encoding="utf-8")
    assert all(f"w.{name}()" in source for name in names)


def test_the_lite_table_and_the_shared_table_match() -> None:
    handlers = {lite_handler(cid) for _p, (cid, _t, _h) in all_rows()}
    lite = [
        (menu, label, handler) for menu, label, _k, handler, kind in COMMANDS if handler in handlers
    ]
    shared = [(path, title, lite_handler(cid)) for path, (cid, title, _h) in all_rows()]
    assert sorted(lite) == sorted(shared)


def test_new_form_sits_with_the_other_new_rows() -> None:
    file_rows = [row[3] for row in COMMANDS if row[0] == "&File" and row[4] not in {"sep", "sub"}]
    at = file_rows.index("cmd_new_plain")
    assert file_rows[at + 1] == "cmd_forms_new_form"


def test_switching_the_area_off_takes_every_row_and_the_submenu() -> None:
    from quill.core.lite.command_areas import visible_commands

    off = visible_commands(lambda area: area != "forms")
    handlers = {lite_handler(cid) for _p, (cid, _t, _h) in all_rows()}
    assert not [row for row in off if row[3] in handlers]
    assert not [row for row in off if row[0].endswith("|Forms") or row[1] == "Forms"]
    on = visible_commands(lambda _area: True)
    assert handlers <= {row[3] for row in on}


def test_the_area_is_on_in_recommended_and_everything_and_off_in_the_small_two() -> None:
    from quill.core.lite.features import PROFILES

    off = {p.id: "forms" in p.disabled for p in PROFILES}
    assert off == {"recommended": False, "everything": False, "wordpad": True, "notepad": True}


def test_every_shared_handler_exists() -> None:
    from quill.ui.forms_commands import FormsCommands

    assert [h for _p, (_c, _t, h) in all_rows() if not hasattr(FormsCommands, h)] == []
    assert DOCUMENT_ONLY <= {h for _p, (_c, _t, h) in all_rows()}


def test_a_form_document_is_a_bfl_file() -> None:
    assert is_form_path("C:/forms/fair.BFL") and is_form_path(Path("x.bfl"))
    assert not is_form_path("notes.md") and not is_form_path(None) and not is_form_path("")


@pytest.mark.parametrize(
    "module", ["quill/apps/lite_window_forms.py", "quill/ui/main_frame_forms.py"]
)
def test_the_adapters_have_no_second_implementation(module) -> None:
    """Only one-line hand-offs, and QUILL's adapter has no commands at all."""
    tree = ast.parse(Path(module).read_text(encoding="utf-8"))
    commands = [
        n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name.startswith("cmd_")
    ]
    if module.startswith("quill/ui"):
        assert commands == []
    for node in commands:
        body = [
            n
            for n in node.body
            if not isinstance(n, ast.Expr) or not isinstance(n.value, ast.Constant)
        ]
        assert len(body) == 1 and isinstance(body[0], ast.Expr), (
            f"{node.name} does more than hand off"
        )
        assert isinstance(body[0].value, ast.Call)


# -- dimming outside a form document, in both editors ------------------------- #


class _Item:
    def __init__(self) -> None:
        self.enabled: bool | None = None

    def Enable(self, value: bool) -> None:  # noqa: N802 - wx's name
        self.enabled = value


def test_lite_dims_the_form_rows_outside_a_form() -> None:
    window = _Window()
    window._menu_items = {lite_handler(cid): _Item() for _p, (cid, _t, _h) in all_rows()}
    window.path = "notes.md"
    window._sync_forms_items()
    dims = {h: i.enabled for h, i in window._menu_items.items()}
    assert dims["cmd_forms_check"] is False and dims["cmd_forms_new_form"] is None
    window.path = "fair.bfl"
    window._sync_forms_items()
    assert window._menu_items["cmd_forms_check"].enabled is True


class _Doc:
    path: Any = None


class _MenuBar:
    def __init__(self, ids: dict[str, int]) -> None:
        self.items = {number: _Item() for number in ids.values()}

    def FindItemById(self, number: int) -> _Item | None:  # noqa: N802 - wx's name
        return self.items.get(number)


def _quill_frame(enabled: bool = True) -> Any:
    from quill.ui.main_frame_forms import FormsMenuMixin

    class Frame(FormsMenuMixin):
        def __init__(self) -> None:
            self.document = _Doc()
            self._forms_ids = {cid: n for n, (_p, (cid, _t, _h)) in enumerate(all_rows(), 1)}
            self.filled: list[tuple[Any, tuple]] = []

        def _feature_enabled(self, feature: str) -> bool:
            assert feature == "core.forms"
            return enabled

        def _fill_forms_menu(self, menu: Any, rows: tuple) -> Any:
            self.filled.append((menu, rows))
            return menu

    return Frame()


def test_quill_dims_the_form_rows_outside_a_form() -> None:
    frame = _quill_frame()
    bar = _MenuBar(frame._forms_ids)
    frame._refresh_forms_menu_items(bar)
    check = bar.items[frame._forms_ids["forms.check"]]
    new = bar.items[frame._forms_ids["forms.new_form"]]
    assert check.enabled is False and new.enabled is None
    frame.document.path = "C:/forms/fair.bfl"
    frame._refresh_forms_menu_items(bar)
    assert check.enabled is True


def test_quill_places_each_menu_once_and_only_with_forms_on() -> None:
    frame = _quill_frame()
    frame._append_forms_new_row("file menu")
    frame._place_forms_rows({"edit": "e", "view": "v", "insert": "i", "format": "o", "tools": "t"})
    assert [menu for menu, _rows in frame.filled] == ["file menu", "v", "i", "o", "t"]
    assert frame.filled[0][1] == PLACES["file"][1]
    off = _quill_frame(enabled=False)
    off._append_forms_new_row("file menu")
    off._place_forms_rows({"view": "v"})
    assert off.filled == []


def test_quill_builds_its_command_on_the_shared_class() -> None:
    from quill.ui.forms_commands import FormsCommands

    frame = _quill_frame()
    assert isinstance(frame._forms(), FormsCommands)
    assert frame._forms() is frame._forms()
