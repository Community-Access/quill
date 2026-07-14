"""DLG-3 Phase 3 guard: every hardened_custom dialog wires the shared contract.

This is the machine-enforced anti-regression control for the dialog estate
governance plan in PRD section 9.13. Every dialog surface classified as
``hardened_custom`` in the committed inventory snapshot must, within its
enclosing scope, both:

* apply the shared modal id contract (``apply_modal_ids``), and
* show through an accessible path -- the announcing modal helper
  (``_show_modal_dialog`` / ``show_modal_dialog``), a raw ``ShowModal`` call,
  or a modeless ``Show()`` for persistent monitor windows.

Bespoke dialogs that drift off the contract are caught here long before a
manual screen-reader pass, keeping NVDA/JAWS/Narrator parity intact.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
INVENTORY = REPO_ROOT / "tests" / "unit" / "ui" / "fixtures" / "dialog_inventory.json"

_SHOW_TOKENS = (
    "_show_modal_dialog",
    "show_modal_dialog",
    ".ShowModal(",
    ".Show()",
)


def _scope_source(tree: ast.AST, source: str, qualname: str) -> str:
    """Return the source of the function/class scope named by ``qualname``."""
    parts = qualname.split(".")
    target = parts[-1]
    matches: list[ast.AST] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == parts[0] and target == "__init__":
            return ast.get_source_segment(source, node) or ""
        if isinstance(node, ast.ClassDef) and node.name == target:
            # A wx.Dialog subclass surface: the class body is the scope.
            return ast.get_source_segment(source, node) or ""
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == target:
            matches.append(node)
    if matches:
        return ast.get_source_segment(source, matches[0]) or ""
    return ""


def _hardened_surfaces() -> list[str]:
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    return sorted(key for key, kind in inventory.items() if kind == "hardened_custom")


def test_every_hardened_dialog_wires_the_shared_contract() -> None:
    failures: list[str] = []
    cache: dict[str, tuple[str, ast.AST]] = {}
    for key in _hardened_surfaces():
        module, qualname, _kind = key.split("::")
        path = REPO_ROOT / module
        if not path.exists():
            failures.append(f"{key}: source module missing")
            continue
        if module not in cache:
            source = path.read_text(encoding="utf-8")
            cache[module] = (source, ast.parse(source))
        source, tree = cache[module]
        scope = _scope_source(tree, source, qualname)
        if not scope:
            failures.append(f"{key}: could not locate enclosing scope")
            continue
        if "apply_modal_ids" not in scope:
            failures.append(f"{key}: missing apply_modal_ids() wiring")
        # A `class X(wx.Dialog)` subclass surface owns its keyboard contract,
        # but the accessible show path lives at its construction sites (which
        # are themselves inventoried), so the show-token rule applies only to
        # call-site surfaces.
        if "subclass:" not in key and not any(token in scope for token in _SHOW_TOKENS):
            failures.append(f"{key}: missing an accessible show/ShowModal path")

    assert not failures, "Hardened dialogs drifted off the shared contract:\n" + "\n".join(failures)


def test_hardened_surface_set_is_non_empty() -> None:
    # Guards against a corrupted inventory silently passing the contract check.
    assert _hardened_surfaces(), "No hardened_custom dialogs found in the inventory snapshot"
