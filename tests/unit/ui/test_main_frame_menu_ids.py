"""Guard against use-before-assignment of menu id-refs in ``_build_menu``.

``MenuBuilderMixin._build_menu`` creates a large batch of ``self._id_*``
``wx.NewIdRef()`` handles and then appends menu items that reference them. If an
id is created *after* the menu item that uses it (as happened in b28416b for
``_id_convert_file`` -> launch-time ``AttributeError`` building the File menu),
the app crashes on startup. No unit test constructs the real menu, so this
static check parses the method and asserts every ``self._id_*`` that is both
assigned and used inside ``_build_menu`` is assigned before its first use.
"""

from __future__ import annotations

import ast
from collections import defaultdict
from pathlib import Path

_MENU_MODULE = Path(__file__).resolve().parents[3] / "quill" / "ui" / "main_frame_menu.py"


def _build_menu_node() -> ast.FunctionDef:
    tree = ast.parse(_MENU_MODULE.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_build_menu":
            return node
    raise AssertionError("_build_menu not found in main_frame_menu.py")


def test_build_menu_id_refs_assigned_before_first_use() -> None:
    build = _build_menu_node()
    stores: dict[str, list[int]] = defaultdict(list)
    loads: dict[str, list[int]] = defaultdict(list)
    for node in ast.walk(build):
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "self"
            and node.attr.startswith("_id_")
        ):
            if isinstance(node.ctx, ast.Store):
                stores[node.attr].append(node.lineno)
            elif isinstance(node.ctx, ast.Load):
                loads[node.attr].append(node.lineno)

    # Only ids both created and used inside _build_menu are checkable here; ids
    # created in other methods (run earlier) are out of scope for this guard.
    offenders = {
        attr: {"first_use": min(loads[attr]), "first_assign": min(stores[attr])}
        for attr in loads
        if attr in stores and min(stores[attr]) > min(loads[attr])
    }
    assert not offenders, (
        "menu id-refs used before they are assigned in _build_menu "
        f"(create them earlier): {offenders}"
    )
