"""Menu-structure gate (GATE-12).

Three invariants checked statically against source:

1. **Ctrl+Alt policy (§10.8)**: ``DEFAULT_KEYMAP`` in ``quill/core/keymap.py``
   may contain a ``Ctrl+Alt+`` binding only when (a) the command id is in the
   :data:`_CTRL_ALT_DOCUMENTED` allowlist, or (b) the binding line ends with
   the ``# §edsharp-ok`` per-binding justification comment.  The rationale
   for the relaxation is in ``docs/keybinding-standard.md``; the policy
   remains that ``Ctrl+Alt+`` is screen-reader-hostile and must be earned
   with a documented justification.

2. **Required §10.3 clusters**: every Tools-menu cluster name mandated by
   §10.3 must appear in ``main_frame_menu.py``.  A missing name means the
   menu reorganisation was partially reverted or mis-named.

3. **Two-level cap (§10.4)**: no ``wx.Menu()`` variable may be *both* a child
   submenu (passed to ``AppendSubMenu``) *and* itself have ``AppendSubMenu``
   called on it — that would create three-level nesting.

The gate also delegates to :mod:`quill.tools.check_copy_tray_binding` so a
single ``python -m quill.tools.menu_lint`` invocation enforces that the
12 Copy Tray paste slots keep their default ``Ctrl+Shift+`` chords.

Run directly (``python -m quill.tools.menu_lint``) or via pytest
(``tests/unit/tools/test_menu_lint.py``).  Exit code is non-zero when any
violation is found.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_KEYMAP_PATH = _REPO_ROOT / "quill" / "core" / "keymap.py"
_MENU_PATH = _REPO_ROOT / "quill" / "ui" / "main_frame_menu.py"

# Ctrl+Alt+ bindings that have been earned with a screen-reader-binding
# justification and are therefore permitted in DEFAULT_KEYMAP.  Each entry
# must be paired with a justification comment in keymap.py naming the
# screen-reader chord the binding overrides; see docs/keybinding-standard.md
# for the full audit.  Entries added in the EdSharp port (PR2/3) come with
# the per-binding "# §edsharp-ok" comment on the line itself; entries
# carried from earlier work (view.send_to_tray / view.toggle_tab_control)
# predate the escape-hatch mechanism but have equivalent justification.
_CTRL_ALT_DOCUMENTED: frozenset[str] = frozenset({
    "view.send_to_tray",  # Ctrl+Alt+T — Windows-shell registration
    "view.toggle_tab_control",  # Ctrl+Alt+Shift+T — Windows-shell registration
    # EdSharp port: heading shortcuts override NVDA switch-to-synth-N (Ctrl+Alt+1..6).
    "format.heading_1",
    "format.heading_2",
    "format.heading_3",
    "format.heading_4",
    "format.heading_5",
    "format.heading_6",
    # EdSharp port: list-toggle shortcuts override NVDA review-cursor.
    "format.toggle_bullet_list",  # Ctrl+Alt+7
    "format.toggle_numbered_list",  # Ctrl+Alt+8
})

# §10.3 binding-spec cluster labels that must appear as the label argument
# of an AppendSubMenu(...) call in main_frame_menu.py.  Checks walk the AST
# (see _check_required_clusters) so a comment mentioning a cluster name
# cannot satisfy the gate.
_REQUIRED_CLUSTER_LABELS: tuple[tuple[str, str], ...] = (
    ("Reading & Dictation", "R&eading && Dictation"),
    ("Comparison", "C&omparison"),
    ("Watch Folder", "&Watch Folder"),
    ("AI Assistant", "AI &Assistant"),
    ("Advanced", "&Advanced"),
    ("Quillins", "&Quillins"),
    ("Accessibility", "A&ccessibility"),
    ("Customize & Support", "&Customize && Support"),
    ("Writing & Language", "&Writing && Language"),
)


def _check_ctrl_alt(source: str) -> list[str]:
    """Return error strings for DEFAULT_KEYMAP entries bound to Ctrl+Alt+.

    A ``Ctrl+Alt+`` binding passes the gate when EITHER:

    * the command id is in :data:`_CTRL_ALT_DOCUMENTED` (the binding is
      historically permitted and has a documented screen-reader-binding
      justification in :mod:`docs.keybinding-standard`), OR
    * the line in ``keymap.py`` ends with the inline justification comment
      ``# §edsharp-ok`` (the per-binding escape hatch introduced with the
      EdSharp port; each occurrence must be paired with a justification
      naming which screen-reader chord the binding overrides).

    The escape-hatch check is line-level so a single DEFAULT_KEYMAP line can
    be permitted without growing the global allowlist for one-off bindings.
    """
    errors: list[str] = []
    try:
        tree = ast.parse(source, filename=str(_KEYMAP_PATH))
    except SyntaxError as exc:
        return [f"  SyntaxError parsing keymap.py: {exc}"]

    # Pre-compute line-number -> text lookup so we can verify the per-binding
    # escape-hatch comment lives on the same line as the binding entry.
    lines = source.splitlines()

    for node in ast.walk(tree):
        # DEFAULT_KEYMAP uses an annotated assignment (dict[str, str] type hint).
        if isinstance(node, ast.AnnAssign):
            if not (isinstance(node.target, ast.Name) and node.target.id == "DEFAULT_KEYMAP"):
                continue
            dict_node = node.value
        elif isinstance(node, ast.Assign):
            if not any(isinstance(t, ast.Name) and t.id == "DEFAULT_KEYMAP" for t in node.targets):
                continue
            dict_node = node.value
        else:
            continue
        if not isinstance(dict_node, ast.Dict):
            continue
        for key_node, val_node in zip(dict_node.keys, dict_node.values, strict=True):
            if not (isinstance(key_node, ast.Constant) and isinstance(val_node, ast.Constant)):
                continue
            command_id = str(key_node.value)
            binding = str(val_node.value)
            # Match Ctrl+Alt+ exactly, but not Ctrl+Alt+Shift+... The
            # §10.8 policy is about Ctrl+Alt+ by itself; Ctrl+Alt+Shift+ is a
            # different chord whose screen-reader collision profile is much
            # narrower and is governed by §10.4 (modifier-stacking) rather
            # than this gate.
            if not re.match(r"(?i)ctrl\+alt\+(?!shift\+)", binding):
                continue
            if command_id in _CTRL_ALT_DOCUMENTED:
                continue
            line_text = lines[val_node.lineno - 1] if 0 < val_node.lineno <= len(lines) else ""
            if "§edsharp-ok" in line_text:
                continue
            errors.append(
                f"  {command_id!r}: {binding!r} — "
                "Ctrl+Alt+ is screen-reader-hostile (§10.8). "
                "Add the binding id to _CTRL_ALT_DOCUMENTED in menu_lint.py, "
                "or append a '# §edsharp-ok' justification comment naming the "
                "screen-reader binding it overrides."
            )
    return errors


def _label_text(node: ast.expr) -> str | None:
    """Resolve an AppendSubMenu label argument to its literal text.

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


def _check_required_clusters(menu_source: str) -> list[str]:
    """Return error strings for §10.3 clusters absent from the menu source.

    Walks the AST for ``AppendSubMenu(menu, label)`` calls the way
    ``_check_depth`` does, so a comment or docstring mentioning a cluster's
    label text cannot satisfy the gate (#286).
    """
    errors: list[str] = []
    try:
        tree = ast.parse(menu_source, filename=str(_MENU_PATH))
    except SyntaxError as exc:
        return [f"  SyntaxError parsing main_frame_menu.py: {exc}"]

    found_labels: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Attribute) and func.attr == "AppendSubMenu"):
            continue
        if len(node.args) < 2:
            continue
        label = _label_text(node.args[1])
        if label is not None:
            found_labels.add(label)

    for friendly_name, label_fragment in _REQUIRED_CLUSTER_LABELS:
        if label_fragment not in found_labels:
            errors.append(
                f'  "{friendly_name}" cluster ({label_fragment!r}) not found in an '
                "AppendSubMenu(...) call in main_frame_menu.py"
            )
    return errors


def _check_depth(menu_source: str) -> list[str]:
    """Return error strings for menus that create three or more submenu levels.

    The §10.4 two-level cap allows:
      TopMenu > SubMenu (depth 1) > SubSubMenu (depth 2) > items
    but prohibits a depth-2 submenu from having further submenus (that would
    make items reachable only through three submenu levels).
    """
    errors: list[str] = []
    try:
        tree = ast.parse(menu_source, filename=str(_MENU_PATH))
    except SyntaxError as exc:
        return [f"  SyntaxError parsing main_frame_menu.py: {exc}"]

    menu_vars: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if not isinstance(target, ast.Name):
                continue
            val = node.value
            if (
                isinstance(val, ast.Call)
                and isinstance(val.func, ast.Attribute)
                and val.func.attr == "Menu"
            ):
                menu_vars.add(target.id)

    # parent_to_children: parent_name -> list of child_name
    parent_to_children: dict[str, list[str]] = {}
    is_child: set[str] = set()
    has_children: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Expr):
            continue
        call = node.value
        if not isinstance(call, ast.Call):
            continue
        func = call.func
        if not (isinstance(func, ast.Attribute) and func.attr == "AppendSubMenu"):
            continue
        parent: str | None = None
        child: str | None = None
        if isinstance(func.value, ast.Name):
            parent = func.value.id
            has_children.add(parent)
        if call.args and isinstance(call.args[0], ast.Name):
            child = call.args[0].id
            is_child.add(child)
        if parent and child:
            parent_to_children.setdefault(parent, []).append(child)

    # BFS from root menus (never a child) to compute depth of each menu var.
    roots = menu_vars - is_child
    depth: dict[str, int] = {r: 0 for r in roots}
    queue = list(roots)
    while queue:
        current = queue.pop(0)
        for child in parent_to_children.get(current, []):
            if child not in depth:
                depth[child] = depth[current] + 1
                queue.append(child)

    # Violation: a menu at depth >= 2 that itself has AppendSubMenu children
    # would place items at depth 3+ below the top-level menu.
    for var in sorted(has_children):
        if depth.get(var, 0) >= 2:
            errors.append(
                f"  {var!r} (depth {depth[var]}) calls AppendSubMenu — "
                "creates three or more submenu levels, violating the §10.4 two-level cap."
            )
    return errors


def run_checks() -> list[str]:
    """Run all checks; return a flat list of error strings (empty = clean)."""
    errors: list[str] = []
    try:
        keymap_source = _KEYMAP_PATH.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"Cannot read keymap.py: {exc}"]
    try:
        menu_source = _MENU_PATH.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"Cannot read main_frame_menu.py: {exc}"]

    ctrl_alt = _check_ctrl_alt(keymap_source)
    if ctrl_alt:
        errors.append("Ctrl+Alt+ policy violations (§10.8):")
        errors.extend(ctrl_alt)

    clusters = _check_required_clusters(menu_source)
    if clusters:
        errors.append("Missing §10.3 Tools-menu clusters:")
        errors.extend(clusters)

    depth = _check_depth(menu_source)
    if depth:
        errors.append("Three-level nesting violations (§10.4 two-level cap):")
        errors.extend(depth)

    # Delegate the Copy Tray binding guard so menu_lint remains a single
    # one-shot gate for keymap + menu structural issues.
    from quill.tools.check_copy_tray_binding import run_checks as _copy_tray_checks

    copy_tray = _copy_tray_checks()
    if copy_tray:
        errors.append("Copy Tray binding drift:")
        errors.extend(copy_tray)

    return errors


def main(argv: list[str] | None = None) -> int:
    errors = run_checks()
    if errors:
        print("menu_lint: FAIL", file=sys.stderr)
        for line in errors:
            print(line, file=sys.stderr)
        return 1
    print("menu_lint: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
