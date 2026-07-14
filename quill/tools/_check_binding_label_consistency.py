"""Binding/label consistency check (4th menu_lint invariant).

Walks the AST of ``quill/ui/main_frame_menu.py`` and reports items where
a label and a binding disagree in ways that surface as user-visible gaps:

1. **Empty label through ``_menu_label``**: an item routed through the
   label builder whose title literal is the empty string AND whose
   command id has a non-empty entry in ``DEFAULT_KEYMAP``. The runtime
   label would render the accelerator alone with no menu name. Source
   of the regression that motivates this gate: ``self._menu_label("",
   "format.bold")`` silently produces a blank-named menu slot.

2. **Manual-tab literal drift**: a hand-written label literal of the
   form ``<name>\\t<binding>`` whose binding portion does not match
   the binding the matching command (or wx stock id) actually exposes
   to the user. Catches drift between the inline literal and the
   underlying accelerator the runtime would resolve.

3. **Tab-without-binding**: any ``Append(...)`` call whose label literal
   contains ``\\t`` but the segment after the tab is empty. The user
   would see a menu name with a trailing tab and no accelerator at all.

The check is structural; it cannot catch runtime customization changes
to ``MenuCustomization.item_label`` or the user keymap. The runtime
gap-check in :func:`MainFrame._menu_label` is the safety net for those.
"""

from __future__ import annotations

import ast
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MENU_PATH = _REPO_ROOT / "quill" / "ui" / "main_frame_menu.py"
_KEYMAP_PATH = _REPO_ROOT / "quill" / "core" / "keymap.py"

# wx stock-item labels that predate the ``_menu_label`` builder. Each
# tuple is ``(wx stock id, expected binding)``; the check verifies the
# literal's tab portion matches. The literal ``&Name`` is what
# ``main_frame_menu.py`` writes verbatim; the binding is what wx / the
# ``quill_key_binding`` would resolve.
#
# Note: these are the runtime stock bindings used by the
# platform-specific accelerator tables. We verify the literal matches.
_WX_STOCK_BINDINGS: dict[str, str] = {
    "Cu&t": "Ctrl+X",
    "&Copy": "Ctrl+C",
    "&Paste": "Ctrl+V",
    "Select &All": "Ctrl+A",
}


def _load_keymap_bindings() -> dict[str, str]:
    """Return ``{command_id: binding_str}`` parsed from ``DEFAULT_KEYMAP``."""
    source = _KEYMAP_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(_KEYMAP_PATH))
    for node in ast.walk(tree):
        target: ast.expr | None = None
        value: ast.expr | None = None
        if isinstance(node, ast.AnnAssign):
            target = node.target
            value = node.value
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "DEFAULT_KEYMAP":
                    target = t
                    value = node.value
                    break
        if target is None or value is None:
            continue
        if not (isinstance(target, ast.Name) and target.id == "DEFAULT_KEYMAP"):
            continue
        if not isinstance(value, ast.Dict):
            continue
        out: dict[str, str] = {}
        for k, v in zip(value.keys, value.values, strict=True):
            if isinstance(k, ast.Constant) and isinstance(v, ast.Constant):
                out[str(k.value)] = str(v.value)
        return out
    return {}


def _literal_text(node: ast.expr) -> str | None:
    """Resolve a string-typed argument to its literal text.

    Handles a bare string constant or the ``_("...")`` i18n wrapper used
    throughout main_frame_menu.py.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "_"
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
    ):
        return node.args[0].value
    return None


def _check_empty_label_with_binding(menu_source: str, keymap: dict[str, str]) -> list[str]:
    """Flag ``self._menu_label("", "command.with.binding")`` patterns.

    An empty title literal routed through the label builder is a gap:
    the user sees the accelerator but no menu name. (The label
    builder itself will log a warning at runtime; this gate prevents
    the regression from landing in the first place.)
    """
    errors: list[str] = []
    tree = ast.parse(menu_source, filename=str(_MENU_PATH))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Attribute) and func.attr == "_menu_label"):
            continue
        if len(node.args) < 2:
            continue
        title = _literal_text(node.args[0])
        cmd_id = _literal_text(node.args[1])
        if title is None or cmd_id is None:
            continue
        if title.strip() != "":
            continue
        binding = keymap.get(cmd_id)
        if not binding:
            continue
        errors.append(
            f'  _menu_label("", {cmd_id!r}) at line {node.lineno}: '
            f"command has binding {binding!r} but the title literal is empty; "
            "the user would see a menu item with no readable name."
        )
    return errors


def _check_manual_tab_literals(menu_source: str) -> list[str]:
    """Flag ``<name>\\t<binding>`` literals where the binding portion drifted.

    Covers two patterns:

    * ``self._menu_label(_("<name>\\t<binding>"), "<command_id>")`` where
      the literal binding is non-empty but does not match what
      ``DEFAULT_KEYMAP[<command_id>]`` says.
    * Stock-wx items (e.g. ``edit_menu.Append(wx.ID_CUT, _("Cu&t\\tCtrl+X"))``)
      whose literal binding does not match the documented wx stock
      accelerator. We pin the known set of wx stock items to their
      stock bindings; an unknown literal containing a tab is allowed
      through (no command to compare against) but still must satisfy
      the tab-without-binding check.
    """
    errors: list[str] = []
    tree = ast.parse(menu_source, filename=str(_MENU_PATH))
    keymap = _load_keymap_bindings()

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        # Resolve the label argument position based on call shape.
        label_arg: ast.expr | None = None
        cmd_id: str | None = None
        is_menu_label = isinstance(func, ast.Attribute) and func.attr == "_menu_label"
        is_append = isinstance(func, ast.Attribute) and func.attr == "Append"
        if not (is_menu_label or is_append):
            continue
        if is_menu_label and len(node.args) >= 2:
            label_arg = node.args[0]
            cmd_text = _literal_text(node.args[1])
            if cmd_text is not None:
                cmd_id = cmd_text
        elif is_append and len(node.args) >= 2:
            label_arg = node.args[1]
        if label_arg is None:
            continue
        text = _literal_text(label_arg)
        if text is None or "\t" not in text:
            continue
        # Skip the help-menu stock items that we pin in the table below
        # — they're checked via the stock table to keep this function
        # focused on _menu_label/Append-with-command-id cases.
        name_part, _, tab_part = text.partition("\t")
        if not tab_part:
            errors.append(
                f"  Append call at line {node.lineno}: label {text!r} contains "
                "'\\t' but no binding portion follows — the user would see a "
                "trailing tab with no accelerator."
            )
            continue
        # _menu_label calls: compare tab_part to the DEFAULT_KEYMAP binding.
        if is_menu_label and cmd_id is not None:
            expected = keymap.get(cmd_id, "")
            if expected and tab_part != expected:
                errors.append(
                    f"  _menu_label at line {node.lineno}: command {cmd_id!r} "
                    f"has DEFAULT_KEYMAP binding {expected!r} but the label "
                    f"literal {text!r} shows {tab_part!r}. Update the literal "
                    "or DEFAULT_KEYMAP so they agree."
                )
        # Append calls: compare tab_part to the wx stock binding table.
        if is_append:
            for name, stock in _WX_STOCK_BINDINGS.items():
                if name_part == name and tab_part != stock:
                    errors.append(
                        f"  Append at line {node.lineno}: stock item {name!r} "
                        f"literals binding {tab_part!r} but wx stock binding is "
                        f"{stock!r}. Update the literal so the user sees the "
                        "correct accelerator."
                    )
    return errors


def _check_tab_without_binding(menu_source: str) -> list[str]:
    """Flag any label literal of the form ``<name>\\t`` (tab, no binding)."""
    errors: list[str] = []
    tree = ast.parse(menu_source, filename=str(_MENU_PATH))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Attribute) and func.attr in {"Append", "_menu_label"}):
            continue
        # Find the label argument
        label_arg: ast.expr | None = None
        if (
            isinstance(func, ast.Name) is False
            and func.attr == "_menu_label"
            and len(node.args) >= 1
        ):
            label_arg = node.args[0]
        elif isinstance(func, ast.Attribute) and func.attr == "Append" and len(node.args) >= 2:
            label_arg = node.args[1]
        if label_arg is None:
            continue
        text = _literal_text(label_arg)
        if text is None or not text.endswith("\t"):
            continue
        errors.append(
            f"  label literal {text!r} at line {node.lineno} ends with '\\t' "
            "but the binding portion is empty. Either remove the '\\t' or "
            "add the binding after it."
        )
    return errors


def run_checks() -> list[str]:
    """Return a flat list of error strings (empty = clean)."""
    try:
        menu_source = _MENU_PATH.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"Cannot read main_frame_menu.py: {exc}"]

    try:
        keymap = _load_keymap_bindings()
    except (OSError, SyntaxError) as exc:
        return [f"Cannot load DEFAULT_KEYMAP: {exc}"]

    errors: list[str] = []
    empty = _check_empty_label_with_binding(menu_source, keymap)
    if empty:
        errors.append("Binding/label consistency: empty label routed through _menu_label:")
        errors.extend(empty)

    manual = _check_manual_tab_literals(menu_source)
    if manual:
        errors.append("Binding/label consistency: manual-tab literal drift:")
        errors.extend(manual)

    tabless = _check_tab_without_binding(menu_source)
    if tabless:
        errors.append("Binding/label consistency: '\\t' literal with empty binding portion:")
        errors.extend(tabless)

    return errors
