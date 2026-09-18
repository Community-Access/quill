"""Menu-structure gate (GATE-12).

Four invariants checked statically against source:

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

4. **Binding/label consistency**: every menu item routed through the
   ``_menu_label`` builder has a non-empty title literal when its command
   has a binding, and every hand-written ``<name>\\t<binding>`` literal
   agrees with the binding the matching command (or wx stock id) would
   resolve.  Catches the regression where ``self._menu_label("",
   "format.bold")`` silently produces a menu slot with no readable
   name.  See :mod:`quill.tools._check_binding_label_consistency`.

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
    "view.send_to_tray",  # legacy Ctrl+Alt+T allowance; now a QUILL-key chord
    # The guided tutorials (2026-08-28). Ctrl+Alt+F1 is the family key: the same
    # chord opens the lessons in Quill Radio, QUILL Cast and Quill Weather, and
    # keeping it identical across the four apps is worth more than avoiding the
    # Ctrl+Alt class here. It is also outside what the policy is actually about:
    # the hostility of Ctrl+Alt is AltGr on European layouts (a *character* key
    # problem) and the screen readers' Ctrl+Alt+letter/arrow commands. F1 is
    # neither -- no default JAWS or NVDA command uses Ctrl+Alt+F1, and AltGr
    # cannot produce a function key.
    "help.tutorials",  # Ctrl+Alt+F1
    # Get Help from Support (2026-09-11), one key along from Tutorials and
    # the family key for the same reason: every app answers it with the same
    # door to a person who can reply, and a support key that differs per app
    # is one nobody remembers on the day they need it. Same exemption as
    # above -- a function key is neither an AltGr character nor a default
    # JAWS or NVDA command.
    "help.report_bug",  # Ctrl+Alt+F2
    "view.toggle_tab_control",  # legacy Ctrl+Alt+Shift+T allowance; now a QUILL-key chord
    # EdSharp port: heading shortcuts override NVDA switch-to-synth-N (Ctrl+Alt+1..6).
    "format.heading_1",
    "format.heading_2",
    "format.heading_3",
    "format.heading_4",
    "format.heading_5",
    "format.heading_6",
    # Ctrl+Alt+0, the seventh row of the same ladder: the way back to body text.
    # Same justification as the six above it -- it overrides NVDA's
    # switch-to-synth-N, deliberately, and a heading ladder with a hole where
    # "not a heading" belongs is a ladder you cannot come down (bad.md P1.4).
    "format.body_text",
    # Format-aware structured inserts / authoring chords
    # (x.md "Authoring"), user-authorized as in-app Ctrl+Alt chords. None
    # collides with a default NVDA/JAWS command.
    "format.toggle_bullet_list",  # Ctrl+Alt+B
    "file.new_plain_text_document",  # Ctrl+Alt+N, QuillLite's chord (bad.md P1.13)
    "format.insert_table",  # Ctrl+Alt+T
    "format.blockquote",  # Ctrl+Alt+Q
    "format.horizontal_rule",  # Ctrl+Alt+H
    "edit.insert_link",  # Ctrl+Alt+K
    "format.insert_markdown_tag",  # Ctrl+Alt+I, QuillLite's chord (bad.md P1.1)
    # Table cell navigation: Ctrl+Alt+arrow/Home/End move
    # cell by cell; context-sensitive and harmless outside a table.
    "table.next_cell",  # Ctrl+Alt+Right
    "table.previous_cell",  # Ctrl+Alt+Left
    "table.cell_below",  # Ctrl+Alt+Down
    "table.cell_above",  # Ctrl+Alt+Up
    "table.first_cell",  # Ctrl+Alt+Home
    "table.last_cell",  # Ctrl+Alt+End
    # #357 keymap consolidation: AI commands use Ctrl+Alt+Shift+<letter> as
    # their chord class. Inline accelerators were stripped from main_frame_menu
    # because they collided with the F7/F8 selection bindings. The chord class
    # is reserved for AI commands so power users can find them by feel.
    "tools.ai_spell_check",  # Ctrl+Alt+Shift+S
    "tools.ai_spell_check_interactive",  # Ctrl+Alt+Shift+I
    "tools.ai_grammar_style",  # Ctrl+Alt+Shift+G
    "tools.ai_translate_selection",  # Ctrl+Alt+Shift+T
    "tools.ai_thesaurus",  # Ctrl+Alt+Shift+H
    # #357 keymap consolidation: compare commands share the Ctrl+Alt+Shift+
    # chord class. The previous inline F8/Shift+F8/Ctrl+F8 accelerators
    # collided with edit.start_selection / edit.complete_selection /
    # edit.reselect.
    "tools.compare_next_difference",  # Ctrl+Alt+Shift+.
    "tools.compare_previous_difference",  # Ctrl+Alt+Shift+,
    "tools.compare_announce_difference",  # Ctrl+Alt+Shift+D
    # ------------------------------------------------------------------ #
    # The 2026-09 keyless-command sweep (bad.md P1.1, 4452595 and after).
    #
    # Eighteen chords arrived in one round, and they are listed here rather
    # than carrying eighteen inline "# §edsharp-ok" comments because the
    # reasoning divides cleanly into two cases and is worth writing once.
    #
    # **Ctrl+Alt+<function key> is outside what the policy is about.** The
    # policy has two real grounds: Ctrl+Alt is AltGr on European layouts, so
    # the chord *types a character* instead of firing; and JAWS and NVDA both
    # own a spread of Ctrl+Alt+<letter> and Ctrl+Alt+<arrow> commands. Neither
    # ground reaches a function key -- AltGr cannot produce F6, and no default
    # JAWS or NVDA command uses Ctrl+Alt+F6 through F12. This is the same
    # exemption already granted above to help.tutorials (Ctrl+Alt+F1) and
    # help.report_bug (Ctrl+Alt+F2), and it is the whole justification for:
    "navigate.set_language",  # Ctrl+Alt+F6
    "view.toggle_spellcheck_as_you_type",  # Ctrl+Alt+F7
    "tools.add_word_to_dictionary",  # Ctrl+Alt+F9
    "tools.individual_feature_toggles",  # Ctrl+Alt+F10
    "tools.share_export",  # Ctrl+Alt+F11
    "tools.share_import",  # Ctrl+Alt+F12
    #
    # **Ctrl+Alt+<letter> is a real cost, and these twelve are worth it.**
    # Each overrides nothing in a default JAWS or NVDA layer: both readers
    # reserve Insert+<key> for their own commands and use Ctrl+Alt only for
    # NVDA's table navigation (Ctrl+Alt+<arrow>, already allowed above for
    # QUILL's own table cells) and NVDA's Ctrl+Alt+<digit> synthesiser switch
    # (already allowed above for the heading chords, which deliberately take
    # it). No letter below collides with either.
    #
    # The AltGr cost is real and is accepted knowingly: on a European layout
    # these chords may type a character instead of firing, which is exactly
    # what the Keyboard Manager exists to let somebody rebind. The trade is
    # that the alternative was **no key at all** -- every one of these twelve
    # was reachable only by walking the menu bar, which is a cost a
    # screen-reader user pays on every single visit, not once per layout.
    # bad.md 3.9 decided that trade; this table records it.
    "navigate.clear_numbered_bookmarks",  # Ctrl+Alt+B (Ctrl+Shift+B sets)
    "edit.remove_duplicate_lines",  # Ctrl+Alt+D
    "format.editor_font",  # Ctrl+Alt+F -- the editor's own face and size
    "navigate.next_heading",  # Ctrl+Alt+H (Ctrl+Alt+Shift+H goes back)
    "navigate.set_temp_bookmark",  # Ctrl+Alt+J (Ctrl+J is Word's Justify)
    "power.remove_blank_lines",  # Ctrl+Alt+K
    "file.page_setup",  # Ctrl+Alt+P, one modifier off Ctrl+P
    "edit.trim_trailing_whitespace",  # Ctrl+Alt+R
    "edit.sort_lines_ascending",  # Ctrl+Alt+S
    "tools.check_updates",  # Ctrl+Alt+U
    "edit.open_copy_tray",  # Ctrl+Alt+V, one modifier off Ctrl+V
    "edit.copy_to_next_slot",  # Ctrl+Alt+Y
    # 2026-09-17, all three on QuillLite's chords (bad.md 3.7, P1.12).
    "power.compute_line_statistics",  # Ctrl+Alt+W
    "power.toggle_clipboard_collector",  # Ctrl+Alt+G
    "edit.keep_selection_in_clip_library",  # Ctrl+Alt+M
    "power.describe_character_detail",  # Ctrl+Alt+C, QuillLite's chord (bad.md P1.13)
    # Ctrl+Alt+= and Ctrl+Alt+E, 2026-09-17 (bad.md 3.3, 3.7, P1.8): File Format
    # takes QuillLite's Ctrl+Alt+E, Select Line takes Word-shaped Ctrl+Shift+E,
    # and Insert Equation moves to the sign it draws. Neither new chord is a
    # letter any screen reader claims with Ctrl+Alt.
    "edit.insert_equation",  # Ctrl+Alt+=
    "file.file_format",  # Ctrl+Alt+E
    # 2026-09-18, the structural six converging on QuillLite's chords (bad.md
    # 3.3, P1.2, P2.5): Duplicate Selection took Ctrl+Alt+Q from the retired
    # Block Quote, and Exchange Cursor and Mark took Ctrl+Alt+X so Expand
    # Selection could have QuillLite's Ctrl+Shift+X. Neither letter is one a
    # default JAWS or NVDA command claims with Ctrl+Alt.
    "edit.duplicate_selection",  # Ctrl+Alt+Q
    "edit.exchange_point_mark",  # Ctrl+Alt+X
    # Ctrl+Alt+Space, 2026-09-17: Select Token gave up Ctrl+Space to Select
    # Sentence, which is what that chord means in QuillLite and now means in
    # both (bad.md P1.2b, 5.3a). Ctrl+Alt+Space is the nearest free
    # neighbour, and Space is not a letter any screen reader claims with
    # Ctrl+Alt -- the §10.8 concern is the letter rows.
    "edit.select_chunk",
})

# §10.3 binding-spec cluster labels that must appear as the label argument
# of an AppendSubMenu(...) call in main_frame_menu.py.  Checks walk the AST
# (see _check_required_clusters) so a comment mentioning a cluster name
# cannot satisfy the gate.
_REQUIRED_CLUSTER_LABELS: tuple[tuple[str, str], ...] = (
    ("Reading & Dictation", "R&eading and Dictation"),
    ("Comparison", "C&omparison"),
    ("Watch Folder", "&Watch Folder"),
    # AI was promoted from a Tools cluster to a top-level "&AI" menu (2026-06-27;
    # see PRD section 5.84a), so it is no longer a required Tools-menu cluster.
    ("Advanced", "&Advanced"),
    ("Quillins", "&Quillins"),
    ("Customize & Support", "&Customize and Support"),
    ("Writing & Language", "&Writing and Language"),
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


def _check_no_literal_double_ampersand(menu_source: str) -> list[str]:
    """Return error strings for AppendSubMenu labels containing a literal "&&".

    #876: NVDA read submenu headers such as "Writing & Language" as literal
    "Writing && Language" -- wx's usual "&&" -> "&" escape did not collapse
    for these submenu-header labels the way it does for leaf menu items with
    a single "&" mnemonic. Rather than depend on an escape sequence whose
    behavior isn't reliable for this call site, submenu headers must spell a
    literal ampersand out as "and" instead of "&&".
    """
    errors: list[str] = []
    try:
        tree = ast.parse(menu_source, filename=str(_MENU_PATH))
    except SyntaxError as exc:
        return [f"  SyntaxError parsing main_frame_menu.py: {exc}"]

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Attribute) and func.attr == "AppendSubMenu"):
            continue
        if len(node.args) < 2:
            continue
        label = _label_text(node.args[1])
        if label is not None and "&&" in label:
            errors.append(
                f"  AppendSubMenu label {label!r} contains a literal '&&' "
                "(#876) -- spell it as 'and' instead."
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

    double_ampersand = _check_no_literal_double_ampersand(menu_source)
    if double_ampersand:
        errors.append("Submenu labels with a literal '&&' (#876):")
        errors.extend(double_ampersand)

    # Delegate the binding/label consistency check (4th invariant) so the
    # gate catches label/binding drift between main_frame_menu.py and
    # DEFAULT_KEYMAP. The runtime gap-check in MainFrame._menu_label is the
    # safety net for runtime customization drift.
    from quill.tools._check_binding_label_consistency import run_checks as _bl_checks

    bl_drift = _bl_checks()
    if bl_drift:
        errors.append("Binding/label consistency violations:")
        errors.extend(bl_drift)

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
