"""Banned-pattern gate (GATE-4).

Fails the build on a small set of high-value patterns that have previously
caused real bugs in Quill:

1. Bare ``wx.`` usage in ``quill/ui/main_frame.py``. The module never imports
   ``wx`` at module scope; every method that needs wx must bind it locally with
   ``wx = self._wx``. A bare ``wx.X`` where ``wx`` is not bound in the current or
   any enclosing function scope is a ``NameError`` waiting to happen (this is
   exactly the BUG-2 class).

2. Unhardened XML parsing: a direct ``ET.fromstring`` / ``etree.fromstring`` /
   ``ElementTree.fromstring`` call anywhere except ``quill/core/safe_xml.py``.
   All untrusted XML must go through ``quill.core.safe_xml.fromstring`` so
   entity-expansion attacks stay disabled (the SEC-10 class).

3. Configuration guard: ruff's undefined-name (F) and redefinition (F811)
   rules must stay enabled in ``pyproject.toml`` so undefined names and
   duplicate imports (the BUG-1 / BUG-4 classes) keep failing lint.

4. Dialog-contract guard (A11Y-4). Every ``wx.Dialog`` in ``quill/ui`` must
   follow the construction contract that the find-in-files trap (#84) and the
   status-bar / misspelling layout bugs all shared:

   * A button sizer is never added with ``wx.ALIGN_RIGHT`` (the banned
     alignment that pushed OK/Cancel off-screen and broke focus order); the
     approved pattern adds it with ``wx.EXPAND``. ``wx.ALIGN_RIGHT`` is banned
     outright in ``quill/ui`` source.
   * A module that constructs a raw ``wx.Dialog(...)`` (anything other than the
     auto-destroying ``with wx.Dialog(...)`` form) must also ``Destroy()`` it,
     so no modal dialog leaks (the crash-recovery leak class).

   This makes the bug class un-regressable and steers new dialogs to the
   approved helpers (``quill/ui/dialog_contract.py``, the stock
   ``wx.MessageDialog`` / ``SingleChoiceDialog`` / ``TextEntryDialog``, or the
   web ``show_web_form``).

5. Dialog registry cross-check (A11Y-4 / DLG-3). Every dialog surface found in
   source must be present, with a matching classification, in the committed
   dialog registry snapshot (``quill.tools.dialog_inventory``). A new or moved
   dialog that has not been registered with
   ``python -m quill.tools.dialog_inventory --write`` fails the gate, so no
   dialog can ship unregistered or unclassified (the "magical" gating from
   ``zfix.md``).

6. ``self._enter_region`` and ``self._exit_region`` are banned in ``quill/ui``
   (BUG-REGION / issue #165). These attributes do not exist on ``MainFrame``; the
   correct form is ``self._region_tracker.enter`` / ``self._region_tracker.exit``.
   The nonexistent attributes caused ``main_frame_image.py`` to raise
   ``AttributeError`` silently (wxPython swallows event-handler exceptions),
   making the image-description feature silently non-functional for all users.

7. ``wx.CheckListBox`` is banned in ``quill/ui`` (A11Y-SR-1 / issue #161).
   CheckListBox does not reliably announce checked/unchecked state to NVDA or
   JAWS when the user navigates with arrow keys — the screen reader hears only
   the item label, not its toggle state. Use individual ``wx.CheckBox`` controls
   inside a ``wx.ScrolledWindow`` instead; each checkbox announces its state
   natively on focus.

Run directly (``python -m quill.tools.check_banned_patterns``) or via pytest
(``tests/unit/tools/test_check_banned_patterns.py``). Exit code is non-zero when
any violation is found.
"""

from __future__ import annotations

import ast
import sys
import tomllib
from collections.abc import Iterable
from pathlib import Path

from quill.tools.dialog_inventory import (
    SURFACES,
    load_snapshot,
    scan_dialog_surfaces,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MAIN_FRAME = _REPO_ROOT / "quill" / "ui" / "main_frame.py"
_SAFE_XML = _REPO_ROOT / "quill" / "core" / "safe_xml.py"
_PACKAGE_ROOT = _REPO_ROOT / "quill"
_UI_ROOT = _REPO_ROOT / "quill" / "ui"

# Names that, when called as ``<name>.fromstring(...)``, indicate a raw stdlib
# ElementTree parse instead of the hardened wrapper.
_RAW_XML_MODULE_NAMES = frozenset({"ET", "etree", "ElementTree"})


class Violation:
    __slots__ = ("path", "line", "message")

    def __init__(self, path: Path, line: int, message: str) -> None:
        self.path = path
        self.line = line
        self.message = message

    def __str__(self) -> str:
        rel = self.path.relative_to(_REPO_ROOT)
        return f"{rel}:{self.line}: {self.message}"


class _BareWxVisitor(ast.NodeVisitor):
    """Flag ``wx.<attr>`` where ``wx`` is not bound in any enclosing scope."""

    def __init__(self) -> None:
        self.violations: list[tuple[int, str]] = []
        # Each stack frame is the set of names bound in that function scope.
        self._scopes: list[set[str]] = [set()]

    def _bound(self, name: str) -> bool:
        return any(name in scope for scope in self._scopes)

    def _collect_bindings(self, node: ast.AST, scope: set[str]) -> None:
        """Record names assigned, imported, or declared in this function body.

        Walks the function body but does NOT descend into nested function or
        class definitions (those get their own scope), so a name bound only in a
        sibling nested function does not leak here.
        """
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                scope.add(child.name)
                continue
            if isinstance(child, ast.Assign):
                for target in child.targets:
                    self._add_target(target, scope)
            elif isinstance(child, (ast.AnnAssign, ast.AugAssign, ast.NamedExpr)):
                self._add_target(child.target, scope)
            elif isinstance(child, (ast.Import, ast.ImportFrom)):
                for alias in child.names:
                    scope.add((alias.asname or alias.name).split(".")[0])
            elif isinstance(child, (ast.For, ast.AsyncFor)):
                self._add_target(child.target, scope)
            elif isinstance(child, (ast.With, ast.AsyncWith)):
                for item in child.items:
                    if item.optional_vars is not None:
                        self._add_target(item.optional_vars, scope)
            elif isinstance(child, (ast.Global, ast.Nonlocal)):
                scope.update(child.names)
            self._collect_bindings(child, scope)

    def _add_target(self, target: ast.AST, scope: set[str]) -> None:
        if isinstance(target, ast.Name):
            scope.add(target.id)
        elif isinstance(target, (ast.Tuple, ast.List)):
            for element in target.elts:
                self._add_target(element, scope)

    def _enter_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        scope: set[str] = set()
        args = node.args
        for arg in (*args.posonlyargs, *args.args, *args.kwonlyargs):
            scope.add(arg.arg)
        if args.vararg:
            scope.add(args.vararg.arg)
        if args.kwarg:
            scope.add(args.kwarg.arg)
        self._collect_bindings(node, scope)
        self._scopes.append(scope)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._enter_function(node)
        for child in node.body:
            self.visit(child)
        self._scopes.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._enter_function(node)
        for child in node.body:
            self.visit(child)
        self._scopes.pop()

    def visit_Attribute(self, node: ast.Attribute) -> None:
        value = node.value
        if isinstance(value, ast.Name) and value.id == "wx" and not self._bound("wx"):
            self.violations.append((
                node.lineno,
                "bare 'wx.' usage; bind 'wx = self._wx' in this scope first",
            ))
        self.generic_visit(node)


def _check_bare_wx(path: Path) -> list[Violation]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    visitor = _BareWxVisitor()
    visitor.visit(tree)
    return [Violation(path, line, message) for line, message in visitor.violations]


def _check_raw_xml(paths: Iterable[Path]) -> list[Violation]:
    violations: list[Violation] = []
    for path in paths:
        if path == _SAFE_XML:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Attribute)
                and node.attr == "fromstring"
                and isinstance(node.value, ast.Name)
                and node.value.id in _RAW_XML_MODULE_NAMES
            ):
                violations.append(
                    Violation(
                        path,
                        node.lineno,
                        f"raw '{node.value.id}.fromstring'; use quill.core.safe_xml.fromstring",
                    )
                )
    return violations


def _is_wx_dialog_call(node: ast.AST) -> bool:
    """True for a ``wx.Dialog(...)`` construction (base dialog only)."""
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "Dialog"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "wx"
    )


def _check_dialog_contract(paths: Iterable[Path]) -> list[Violation]:
    """Enforce the A11Y-4 dialog construction contract in ``quill/ui``.

    * ``wx.ALIGN_RIGHT`` is banned outright (button sizers use ``wx.EXPAND``).
    * A module that builds a raw ``wx.Dialog(...)`` (not the auto-destroying
      ``with wx.Dialog(...)`` form) must also ``Destroy()`` a dialog somewhere
      in the module, so modal dialogs never leak.
    """
    violations: list[Violation] = []
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

        # Collect the wx.Dialog calls that are the context expression of a
        # ``with`` statement; those auto-destroy and are exempt from the
        # explicit-Destroy requirement.
        managed_dialog_calls: set[int] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.With):
                for item in node.items:
                    if _is_wx_dialog_call(item.context_expr):
                        managed_dialog_calls.add(id(item.context_expr))

        has_raw_dialog = False
        has_destroy = False
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Attribute)
                and node.attr == "ALIGN_RIGHT"
                and isinstance(node.value, ast.Name)
                and node.value.id == "wx"
            ):
                violations.append(
                    Violation(
                        path,
                        node.lineno,
                        "wx.ALIGN_RIGHT is banned in quill/ui; add button "
                        "sizers with wx.EXPAND (A11Y-4 dialog contract)",
                    )
                )
            if _is_wx_dialog_call(node) and id(node) not in managed_dialog_calls:
                has_raw_dialog = True
            if isinstance(node, ast.Attribute) and node.attr == "Destroy":
                has_destroy = True

        if has_raw_dialog and not has_destroy:
            violations.append(
                Violation(
                    path,
                    0,
                    "constructs a raw wx.Dialog but never calls .Destroy(); "
                    "Destroy the dialog or use 'with wx.Dialog(...)' "
                    "(A11Y-4 dialog contract)",
                )
            )
    return violations


def _check_checklistbox(paths: Iterable[Path]) -> list[Violation]:
    """Ban wx.CheckListBox in quill/ui (A11Y-SR-1 / issue #161).

    CheckListBox does not announce checked state to screen readers on
    navigation. Use individual wx.CheckBox controls instead.

    Existing call sites that cannot be converted immediately may be exempted
    with an inline comment on the same source line:

        chooser = wx.CheckListBox(...)  # A11Y-SR-1-OK: <reason>

    The reason is required and must explain why conversion is deferred.
    """
    violations: list[Violation] = []
    for path in paths:
        source_lines = path.read_text(encoding="utf-8").splitlines()
        tree = ast.parse("\n".join(source_lines), filename=str(path))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Attribute)
                and node.attr == "CheckListBox"
                and isinstance(node.value, ast.Name)
                and node.value.id == "wx"
            ):
                # Check the opening line and up to 4 continuation lines for
                # the exemption comment (ruff may place it on the closing paren).
                window = source_lines[node.lineno - 1 : node.lineno + 4]
                if any("# A11Y-SR-1-OK:" in ln for ln in window):
                    continue
                violations.append(
                    Violation(
                        path,
                        node.lineno,
                        "wx.CheckListBox is banned (A11Y-SR-1): screen readers do not "
                        "announce checked state on navigation. Use individual "
                        "wx.CheckBox controls inside a wx.ScrolledWindow instead. "
                        "Add '# A11Y-SR-1-OK: <reason>' to exempt an existing site.",
                    )
                )
    return violations


# Finding #40: per CLAUDE.md the UI thread owns widgets and background work
# must run on QuillTaskManager.  Direct threading.Thread calls in quill/ui
# bypass cancellation and shutdown-draining semantics.  This gate holds the
# line: existing offenders are allowed through with an explicit comment so
# migration is gradual and audited.
#
#     threading.Thread(  # GATE-40-OK: <reason>, target migrated in <ticket>
#         ...
#     ).start()
#
# The reason must be specific (ticket id, or "ad-hoc one-shot, no
# cancellation needed because <observable reason>").  Generic "legacy" /
# "TODO" reasons are rejected at code review.
_GATE_40_OK_MARKER = "# GATE-40-OK:"
# The wx heartbeat watchdog is a long-lived daemon that runs outside the
# task manager on purpose (it survives app shutdown so it can raise
# diagnostics).  It is the only legitimate threading.Thread under
# quill/stability and is exempt from the gate.
_GATE_40_EXEMPT_PATHS = frozenset({
    _REPO_ROOT / "quill" / "stability" / "wx_heartbeat.py",
})


def _check_threading_thread(paths: Iterable[Path]) -> list[Violation]:
    """Ban direct ``threading.Thread(...)`` construction in quill/ui.

    Finding #40 / CLAUDE.md invariant: background work in the UI layer must
    go through :class:`quill.stability.task_manager.TaskManager` so the
    runtime can drain, cancel, and report results.  Each existing call site
    is given an explicit exemption marker so the migration is auditable.
    """
    violations: list[Violation] = []
    for path in paths:
        if path in _GATE_40_EXEMPT_PATHS:
            continue
        # Use the relative path string so the marker is portable across
        # developer machines and CI clones.
        try:
            rel = path.relative_to(_REPO_ROOT).as_posix()
        except ValueError:
            rel = str(path)
        if rel.startswith("tests/"):
            # Tests are free to spin up threads to exercise the code under
            # test; the invariant targets production UI code only.
            continue
        source_lines = path.read_text(encoding="utf-8").splitlines()
        tree = ast.parse("\n".join(source_lines), filename=str(path))
        for node in ast.walk(tree):
            if not _is_threading_thread_call(node):
                continue
            lineno = _node_lineno(node)
            # The line of the Call node usually contains the marker; ruff
            # may move it to the next line, so check a 4-line window.
            window = source_lines[lineno - 1 : lineno + 4]
            if any(_GATE_40_OK_MARKER in ln for ln in window):
                continue
            violations.append(
                Violation(
                    path,
                    lineno,
                    "threading.Thread(...) in quill/ui bypasses "
                    "QuillTaskManager; use TaskManager.submit() instead. "
                    "Add '# GATE-40-OK: <reason>' to exempt an existing site "
                    "while it is migrated.",
                )
            )
    return violations


def _is_threading_thread_call(node: ast.AST) -> bool:
    """True for a ``threading.Thread(...)`` construction call."""
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "Thread"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "threading"
    )


# Finding #41: announce-dialog gate.  Raw wx.MessageBox calls bypass
# ``MainFrame._show_message_box`` (which handles z-order, region tracking,
# and screen-reader announcement) and are not consistently announced.  Each
# new call site should go through the wrapper; existing sites get an
# explicit exemption marker:
#
#     wx.MessageBox(  # GATE-41-OK: <reason>
#         "..."
#     )
#
# Note: ``quill/ui/dialog_contract.py`` exposes the sanctioned
# ``show_message_box`` helper that wraps ``wx.MessageBox`` with announce +
# region hooks.
# Finding #42: show-modal wrapper gate.  Every ``dialog.ShowModal()`` call in
# the main-frame entry-point files must go through ``_show_modal_dialog`` (or
# the module-level ``show_modal_dialog`` from ``dialog_contract.py``) so the
# screen reader hears "Entered <label> dialog" and focus is managed correctly.
# The same violation caused the silent Report a Bug dialog and silent F1 help.
# Exempt an existing site with the marker on the same or next source line:
#
#     dlg.ShowModal()  # GATE-42-OK: <reason>
_GATE_42_OK_MARKER = "# GATE-42-OK:"
# Files where all ShowModal calls must be routed through _show_modal_dialog.
# dialog_contract.py is the wrapper itself and is excluded.
_GATE_42_TARGET_STEMS = frozenset({
    "main_frame",
    "main_frame_menu",
    "main_frame_ai",
    "main_frame_commands",
    "main_frame_copy_tray",
    "main_frame_feedback",
    "main_frame_github",
    "main_frame_notebook",
    "main_frame_quillins",
    "main_frame_quillins_host",
    "main_frame_ssh",
    "context_help",
})


def _check_show_modal_wrapper(paths: Iterable[Path]) -> list[Violation]:
    """Ban direct ``.ShowModal()`` calls in main-frame and mixin files.

    GATE-42: these entry-point modules must route every modal through
    ``_show_modal_dialog`` so screen-reader announcements fire reliably.
    Add ``# GATE-42-OK: <reason>`` on the same line to exempt a site.
    """
    violations: list[Violation] = []
    for path in paths:
        if path.stem not in _GATE_42_TARGET_STEMS:
            continue
        source_lines = path.read_text(encoding="utf-8").splitlines()
        tree = ast.parse("\n".join(source_lines), filename=str(path))
        for node in ast.walk(tree):
            if not (
                isinstance(node, ast.Attribute)
                and node.attr == "ShowModal"
                and isinstance(node, ast.Attribute)
            ):
                continue
            # Must be a Call node parent (ShowModal() not ShowModal reference)
            lineno = _node_lineno(node)
            window = source_lines[lineno - 1 : lineno + 4]
            if any(_GATE_42_OK_MARKER in ln for ln in window):
                continue
            violations.append(
                Violation(
                    path,
                    lineno,
                    "direct .ShowModal() call bypasses _show_modal_dialog "
                    "(GATE-42); route through self._show_modal_dialog(dlg, label) "
                    "so screen readers hear the dialog open. "
                    "Add '# GATE-42-OK: <reason>' to exempt an existing site.",
                )
            )
    return violations


_GATE_41_OK_MARKER = "# GATE-41-OK:"
_GATE_41_EXEMPT_PATHS = frozenset({
    # The sanctioned wrapper itself legitimately calls wx.MessageBox.
    _REPO_ROOT / "quill" / "ui" / "dialog_contract.py",
    # MainFrame's _show_message_box wrapper delegates to wx.MessageBox.
    _REPO_ROOT / "quill" / "ui" / "main_frame.py",
})
_GATE_41_DIRECTORIES = (
    _REPO_ROOT / "quill" / "ui",
    _REPO_ROOT / "quill" / "devtools",
)


def _check_wx_message_box(paths: Iterable[Path]) -> list[Violation]:
    """Ban raw ``wx.MessageBox(...)`` in quill/ui and quill/devtools.

    Finding #41: those surfaces must route through the region-track /
    announce wrapper (``MainFrame._show_message_box`` or
    :func:`quill.ui.dialog_contract.show_message_box`) so every dialog is
    heard by NVDA/JAWS/Narrator.  Exempt an existing site with the
    ``GATE-41-OK`` marker.
    """
    violations: list[Violation] = []
    for path in paths:
        if path in _GATE_41_EXEMPT_PATHS:
            continue
        try:
            rel = path.relative_to(_REPO_ROOT).as_posix()
        except ValueError:
            rel = str(path)
        if rel.startswith("tests/"):
            continue
        # Only enforce on the governed directories (quill/ui, quill/devtools).
        if not any(_is_under(path, root) for root in _GATE_41_DIRECTORIES):
            continue
        source_lines = path.read_text(encoding="utf-8").splitlines()
        tree = ast.parse("\n".join(source_lines), filename=str(path))
        for node in ast.walk(tree):
            if not _is_wx_message_box_call(node):
                continue
            lineno = _node_lineno(node)
            window = source_lines[lineno - 1 : lineno + 4]
            if any(_GATE_41_OK_MARKER in ln for ln in window):
                continue
            violations.append(
                Violation(
                    path,
                    lineno,
                    "wx.MessageBox(...) in quill/ui/devtools bypasses the "
                    "announce-dialog wrapper; call "
                    "MainFrame._show_message_box or "
                    "quill.ui.dialog_contract.show_message_box instead. "
                    "Add '# GATE-41-OK: <reason>' to exempt an existing site.",
                )
            )
    return violations


def _is_wx_message_box_call(node: ast.AST) -> bool:
    """True for a ``wx.MessageBox(...)`` call (not a definition)."""
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "MessageBox"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "wx"
    )


def _node_lineno(node: ast.AST) -> int:
    """Return a usable 1-based line number for an AST node (always positive)."""
    lineno = getattr(node, "lineno", 0) or 0
    return lineno if lineno > 0 else 1


def _is_under(path: Path, root: Path) -> bool:
    """Return True when *path* lives under *root* (or is *root* itself)."""
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _check_dialog_registry() -> list[Violation]:
    """Every source dialog surface must be registered and classified.

    Cross-checks the live source scan against the committed dialog registry
    snapshot (``quill.tools.dialog_inventory``). A dialog surface that is new,
    moved to a different scope, or reclassified -- and therefore absent from the
    snapshot -- fails the gate until the author runs
    ``python -m quill.tools.dialog_inventory --write`` and reviews the diff.
    """
    snapshot = load_snapshot()
    violations: list[Violation] = []
    for surface in scan_dialog_surfaces():
        path = _REPO_ROOT / surface.module
        registered = snapshot.get(surface.key)
        if registered is None:
            violations.append(
                Violation(
                    path,
                    surface.line,
                    f"unregistered dialog surface '{surface.key}'; run "
                    "'python -m quill.tools.dialog_inventory --write' to "
                    "register and classify it (A11Y-4 dialog registry). "
                    "If this is a stock wx dialog, add it to "
                    "_NATIVE_WX_DIALOGS in quill/tools/dialog_inventory.py first.",
                )
            )
        elif registered != surface.surface:
            violations.append(
                Violation(
                    path,
                    surface.line,
                    f"dialog '{surface.key}' is classified '{registered}' in the "
                    f"registry but scans as '{surface.surface}'; regenerate the "
                    "snapshot (A11Y-4 dialog registry)",
                )
            )
        elif surface.surface not in SURFACES:
            violations.append(
                Violation(
                    path,
                    surface.line,
                    f"dialog '{surface.key}' has unsanctioned surface "
                    f"'{surface.surface}' (A11Y-4 dialog registry)",
                )
            )
    return violations


def _check_ruff_config() -> list[Violation]:
    pyproject = _REPO_ROOT / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    select = data.get("tool", {}).get("ruff", {}).get("lint", {}).get("select", [])
    if "F" not in select:
        return [
            Violation(
                pyproject,
                0,
                "ruff lint.select must include 'F' (undefined names F821, "
                "redefinition F811) so banned name patterns keep failing lint",
            )
        ]
    return []


def _check_dead_region_attrs(paths: Iterable[Path]) -> list[Violation]:
    """Ban ``self._enter_region`` / ``self._exit_region`` in quill/ui.

    These attributes do not exist on MainFrame.  The correct form is
    ``self._region_tracker.enter`` / ``self._region_tracker.exit``.
    The nonexistent attributes caused the image-description feature to fail
    silently (#165) because wxPython swallows AttributeErrors raised in event
    handlers.
    """
    violations: list[Violation] = []
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not (
                isinstance(node, ast.Attribute)
                and node.attr in ("_enter_region", "_exit_region")
                and isinstance(node.value, ast.Name)
                and node.value.id == "self"
            ):
                continue
            violations.append(
                Violation(
                    path,
                    node.lineno,
                    f"self.{node.attr} does not exist on MainFrame; "
                    "use self._region_tracker.enter / self._region_tracker.exit "
                    "(BUG-REGION / #165)",
                )
            )
    return violations


def find_violations() -> list[Violation]:
    ui_files = sorted(_UI_ROOT.rglob("*.py"))
    violations: list[Violation] = []
    violations.extend(_check_bare_wx(_MAIN_FRAME))
    violations.extend(_check_raw_xml(sorted(_PACKAGE_ROOT.rglob("*.py"))))
    violations.extend(_check_dialog_contract(ui_files))
    violations.extend(_check_checklistbox(ui_files))
    violations.extend(_check_dead_region_attrs(ui_files))
    violations.extend(_check_threading_thread(ui_files))
    violations.extend(_check_wx_message_box(sorted(_PACKAGE_ROOT.rglob("*.py"))))
    violations.extend(_check_show_modal_wrapper(ui_files))
    violations.extend(_check_dialog_registry())
    violations.extend(_check_ruff_config())
    return violations


def main() -> int:
    violations = find_violations()
    if not violations:
        print("Banned-pattern gate: no violations.")
        return 0
    print("Banned-pattern gate found violations:")
    for violation in violations:
        print(f"  {violation}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
