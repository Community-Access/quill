"""The scanner behind GATE-CTLLABEL: who labels whom, in creation order.

``SetName`` is not an accessible name on Windows. wxWidgets stores it as
``wxWindow``'s own name, and the MSAA/UIA bridge that NVDA and JAWS read never
looks at it for a plain edit field, combo box or list: the name is taken from
the **wx.StaticText constructed immediately before the control in z-order**, and
z-order is creation order -- not sizer position, and not anything ``SetName``
touches.

Two edit fields in ``quill/ui/podcasts/add_podcast_dialog.py`` shipped
announcing as bare "edit" for exactly this reason (fixed in ``ba69898``). Both
carried a careful, well-written ``SetName``. The ``wx.Choice`` directly above
them announced correctly, and the only difference was that the choice had a
label created before it. So the author had written the name, the reviewer had
read the name, the existing name gate had counted the name, and the listener
heard "edit".

That last part is why this is separate from
:mod:`quill.tools.accessible_name_audit`. That gate asks "does this site name
its control?" and answers yes for a bare ``SetName`` -- which is precisely the
shape that is silent on the platform every QUILL user runs. It is not wrong (it
was written for macOS VoiceOver, issue #1012, where the window name *is* the
name and the neighbouring static text is never linked); it simply cannot see
this failure. A name written and never heard is worse than none written, because
it closes the bug in everybody's head.

This module answers only "what is where, and what labels it". The snapshot, the
ratchet and the command line live in :mod:`quill.tools.check_control_labels`;
the two were split when the scanner crossed GATE-11's default cap, and the seam
is the right one -- walking the tree and deciding an exit code are two jobs.

The classification, per control construction, taken in **source order within the
enclosing function**:

* ``labelled``   -- a ``wx.StaticText`` is built at an earlier position in the
  same function and no other in-scope control is built between the two. That
  adjacency *is* the z-order association.
* ``named-only`` -- ``SetName`` and/or ``SetHelpText`` is written for it and no
  static text precedes it. **This is the bug.**
* ``unlabelled`` -- neither. Announces as a bare role.

(``reviewed`` is a fourth state, applied by the gate from its snapshot rather
than decided here: the scanner reports what the source says and a human overrides
it with a reason.)

Buttons, check boxes, radio buttons and static boxes are out of scope: they
carry their own label, so the preceding-static-text rule does not apply to them.

A **call to a label helper counts as the label it builds** -- see
:func:`label_helpers_in`. Two shapes in this tree are already correct through a
helper (``StudioPage.add_label`` then a field; a local ``row(label, make_ctrl)``
factory), several with a comment citing the z-order contract by name. Following
them took the first run from 239 offenders to 165, and the 74 it dropped were
all correct code. That matters more than tidiness: the report's job is to hand
somebody the ten files worth opening, and a list padded with already-correct
files is a list nobody opens twice.

Known precision limits, each a false *positive* rather than a miss, and each
answerable with a ``reviewed`` entry in the gate's snapshot:

* The scope is the enclosing function, not the parent window. A form that builds
  its labels in ``_build_form`` and its fields in a ``_make_field`` helper that
  constructs the control itself reads as unlabelled here even though the runtime
  z-order is fine. Function scope is the conservative choice: widening it to the
  module would let a label in one dialog vouch for a field in another.
* Naming detection is textual within the enclosing function, exactly as
  ``accessible_name_audit`` does it, so a variable rebound to a second control
  lends its ``SetName`` to both sites.
* A control whose label is a ``wx.StaticBox`` heading, or which is genuinely
  self-describing (a single-column list whose column header is its name), is a
  ``reviewed`` entry and not a code change.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from quill.tools.source_cache import parsed, scope

REPO_ROOT = Path(__file__).resolve().parents[2]

#: Where the windows live. ``quill/ui`` is the editor shell and its dialogs;
#: ``quill/apps`` is every QuillVille app. Nothing else builds a window that a
#: listener reaches -- ``standalone/`` is a packaging shell by house rule.
SCAN_GLOBS: tuple[str, ...] = ("quill/ui/**/*.py", "quill/apps/**/*.py")

#: The controls that need a name and cannot supply one themselves. A
#: ``wx.Button``, ``wx.CheckBox``, ``wx.RadioButton`` and ``wx.StaticBox`` are
#: deliberately absent: their own label *is* their accessible name, so the
#: preceding-static-text rule has nothing to say about them.
CONTROL_CLASSES: frozenset[str] = frozenset({
    "TextCtrl",
    "Choice",
    "ComboBox",
    "ListBox",
    "CheckListBox",
    "SpinCtrl",
    "SpinCtrlDouble",
    "Slider",
    "ListCtrl",
    "TreeCtrl",
    "SearchCtrl",
    "DatePickerCtrl",
    "FilePickerCtrl",
    "DirPickerCtrl",
})

#: What counts as a label. Only a real static text: this is the widget wxMSW
#: actually hands to the accessibility bridge.
LABEL_CLASSES: frozenset[str] = frozenset({"StaticText"})

#: The pseudo-kind recorded for a call to a label helper. Not a wx class, so it
#: can never be mistaken for a control site in a report.
_HELPER_LABEL = "<label helper>"

#: A name written for the control. Both spellings count, because both are the
#: evidence that somebody *meant* to name it -- which is what makes a
#: ``named-only`` site a reported bug rather than an oversight.
NAMING_METHODS: frozenset[str] = frozenset({"SetName", "SetHelpText", "set_accessible_name"})

#: Naming helpers called as ``helper(control, "name")`` rather than as a method.
#: Beacon wraps ``SetName`` in a module-level ``_name`` in four of its modules,
#: and without this every one of its controls read as ``unlabelled`` rather than
#: ``named-only`` -- the same offence, but the wrong story about it. The
#: distinction is the whole value of the report: ``named-only`` means somebody
#: already wrote the sentence and only needs it moved into a label.
NAMING_HELPERS: frozenset[str] = frozenset({"_name", "set_accessible_name", "name_control"})

LABELLED = "labelled"
NAMED_ONLY = "named-only"
UNLABELLED = "unlabelled"
REVIEWED = "reviewed"

#: The two that fail a build. Kept as a set so the gate and the report cannot
#: disagree about what an "offender" is.
OFFENDING = frozenset({NAMED_ONLY, UNLABELLED})


@dataclass(frozen=True, order=True)
class ControlSite:
    """One construction of a control that needs a name it may not carry."""

    path: str
    line: int
    kind: str
    status: str
    qualname: str
    #: Only set for ``reviewed``; the human's stated reason.
    reason: str = ""

    @property
    def key(self) -> str:
        """``path:line: wx.Class`` -- clickable in a terminal, which is the point.

        A key that a reader cannot paste into an editor is a key that gets
        ignored, and this gate's whole job is to hand somebody a list of places
        to go.
        """
        return f"{self.path}:{self.line}: {self.kind}"

    @property
    def group(self) -> tuple[str, str]:
        """The line-independent identity: which file, which control class.

        The grandfathered ratchet matches on this and a count, not on the line
        number. A snapshot keyed only on lines goes red the moment somebody adds
        an import above the dialog, and a gate that cries wolf after an
        unrelated edit is one people learn to regenerate without reading.
        """
        return (self.path, self.kind)


def wx_class(func: ast.expr) -> str | None:
    """Return ``wx.<Class>`` for a ``wx.X`` or ``wx.adv.X`` call target.

    ``wx.adv`` is accepted because ``DatePickerCtrl`` lives there and a listener
    cannot tell which submodule a silent control came from.
    """
    if not isinstance(func, ast.Attribute):
        return None
    base = func.value
    if isinstance(base, ast.Name) and base.id == "wx":
        return f"wx.{func.attr}"
    if (
        isinstance(base, ast.Attribute)
        and isinstance(base.value, ast.Name)
        and base.value.id == "wx"
    ):
        return f"wx.{func.attr}"
    return None


def label_helpers_in(tree: ast.Module) -> set[str]:
    """Functions whose whole effect on z-order is "a static text was added".

    Two shapes in this tree do the right thing through a helper, and a rule that
    only looked at adjacent statements would call both of them broken::

        self.add_label("&Source folder:")          # pages_base builds the label
        self.source = wx.ComboBox(self, ...)       # and this is the next child

        def row(label_text, make_ctrl):            # the local row factory
            grid.Add(wx.StaticText(self.dialog, label=label_text), ...)
            return make_ctrl()                     # the control is built HERE
        self.host = row("Host or IP address", lambda: wx.TextCtrl(self.dialog))

    In both, the label really is created before the field, and several of these
    call sites carry a comment saying so. Treating a call to such a helper as a
    label event in the adjacency chain handles both at once -- in the second
    case the helper call sorts before the lambda's construction, which is also
    the true evaluation order.

    The qualifying condition is deliberately strict: the function must construct
    a ``wx.StaticText`` **and no in-scope control of its own**. A function that
    builds both -- a whole settings page, or ``pages_base.add_ms_spin``, which
    builds a label and the spin that belongs to it -- is disqualified, because
    the last child it created is then not the label, and vouching for the *next*
    control would be a lie. Dunders are excluded for the same reason: every
    dialog's ``__init__`` builds static texts.

    A false negative is the price of a name-keyed rule (two functions may share
    a name, and one of them may qualify). It is the right direction to fail: a
    missed offender is filed as a bug the next time somebody listens to the
    window, whereas a false positive here would send a fixer to a file that is
    already correct.
    """
    found: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        if node.name.startswith("__"):
            continue
        builds_label = False
        builds_control = False
        for inner in ast.walk(node):
            if not isinstance(inner, ast.Call):
                continue
            kind = wx_class(inner.func)
            if kind is None:
                continue
            bare = kind.split(".", 1)[1]
            if bare in LABEL_CLASSES:
                builds_label = True
            elif bare in CONTROL_CLASSES:
                builds_control = True
        if builds_label and not builds_control:
            found.add(node.name)
    return found


def _assignment_targets(tree: ast.Module) -> dict[int, str]:
    """Map ``id(call node)`` -> the expression it was assigned to.

    Needed so ``self._url_ctrl = wx.TextCtrl(...)`` can be paired with the
    ``self._url_ctrl.SetName(...)`` three lines below it.
    """
    targets: dict[int, str] = {}
    for node in ast.walk(tree):
        value: ast.expr | None = None
        names: list[ast.expr] = []
        if isinstance(node, ast.Assign):
            value, names = node.value, list(node.targets)
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            value, names = node.value, [node.target]
        if value is None or not isinstance(value, ast.Call) or not names:
            continue
        try:
            targets[id(value)] = ast.unparse(names[0])
        except Exception:  # pragma: no cover - unparse is total in practice
            continue
    return targets


class _ControlVisitor(ast.NodeVisitor):
    """Collect label and control constructions, per function scope, in order."""

    def __init__(self, targets: dict[int, str], helpers: frozenset[str]) -> None:
        self._targets = targets
        self._helpers = helpers
        self._scope: list[str] = []
        #: scope -> list of (line, col, kind, assigned-expression-or-"")
        self.events: dict[str, list[tuple[int, int, str, str]]] = {}
        #: scope -> the expressions something wrote a name for
        self.named: dict[str, set[str]] = {}

    @property
    def _key(self) -> str:
        return ".".join(self._scope) if self._scope else "<module>"

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._scope.append(node.name)
        self.generic_visit(node)
        self._scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._scope.append(node.name)
        self.generic_visit(node)
        self._scope.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._scope.append(node.name)
        self.generic_visit(node)
        self._scope.pop()

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        kind = wx_class(func)
        if kind is not None:
            bare = kind.split(".", 1)[1]
            if bare in LABEL_CLASSES or bare in CONTROL_CLASSES:
                assigned = self._targets.get(id(node), "")
                self.events.setdefault(self._key, []).append((
                    node.lineno,
                    node.col_offset,
                    kind,
                    assigned,
                ))
                # A constructor ``name=`` is a written name just as much as a
                # later SetName, and it is just as invisible to wxMSW.
                if assigned and any(kw.arg == "name" for kw in node.keywords):
                    self.named.setdefault(self._key, set()).add(assigned)
        elif isinstance(func, ast.Attribute) and func.attr in NAMING_METHODS:
            self._record_named(func.value)
        elif isinstance(func, ast.Name) and func.id in NAMING_HELPERS and node.args:
            self._record_named(node.args[0])
        called = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
        if kind is None and called in self._helpers:
            # A call to a label helper *is* a label in the z-order chain. It is
            # recorded at the call's own position, which is before the lambda
            # argument that builds the control -- the same order the interpreter
            # evaluates them in, and therefore the same order wx creates them.
            self.events.setdefault(self._key, []).append((
                node.lineno,
                node.col_offset,
                _HELPER_LABEL,
                "",
            ))
        self.generic_visit(node)

    def _record_named(self, target: ast.expr) -> None:
        try:
            self.named.setdefault(self._key, set()).add(ast.unparse(target))
        except Exception:  # pragma: no cover - unparse is total in practice
            pass


def _is_label(kind: str) -> bool:
    return kind == _HELPER_LABEL or kind.split(".", 1)[-1] in LABEL_CLASSES


def _classify_scope(
    path: str,
    qualname: str,
    events: list[tuple[int, int, str, str]],
    named: set[str],
) -> Iterator[ControlSite]:
    """Walk one function's constructions in source order and classify each.

    Source order is ``(line, column)``, which is evaluation order and therefore
    creation order and therefore z-order. A label only labels the control that
    comes next: once a second control is created, the label belongs to the
    first, and the second is on its own -- which is why the two edit fields in
    ``add_podcast_dialog.py`` could not borrow the combo box's label.
    """
    previous_was_label = False
    for line, _col, kind, assigned in sorted(events):
        if _is_label(kind):
            previous_was_label = True
            continue
        if previous_was_label:
            status = LABELLED
        elif assigned and assigned in named:
            status = NAMED_ONLY
        else:
            status = UNLABELLED
        # The label is spent. A single static text cannot name two controls,
        # and pretending otherwise would hide every second field in a form.
        previous_was_label = False
        yield ControlSite(path=path, line=line, kind=kind, status=status, qualname=qualname)


def classify_tree(tree: ast.Module, path: str, helpers: frozenset[str]) -> list[ControlSite]:
    """Classify every in-scope control construction in one parsed module."""
    visitor = _ControlVisitor(_assignment_targets(tree), helpers)
    visitor.visit(tree)
    sites: list[ControlSite] = []
    for qualname, events in visitor.events.items():
        sites.extend(_classify_scope(path, qualname, events, visitor.named.get(qualname, set())))
    return sites


def classify_source(source: str, path: str = "<memory>") -> list[ControlSite]:
    """Classify a source snippet. The gate's own tests use this.

    A gate that detects nothing passes silently, so the detector needs tests of
    its own against the exact shapes it was written for.
    """
    tree = ast.parse(source)
    return sorted(classify_tree(tree, path, frozenset(label_helpers_in(tree))))


def safe_parse(path: Path) -> ast.Module | None:
    """The module's AST, or ``None`` when the file cannot be read as Python.

    A whole-tree scanner must not die on one bad file. This is not a theoretical
    worry: the first run of this gate crashed on a module another process was
    halfway through writing, which on Windows meant a file full of NUL bytes and
    a ``SyntaxError`` from ``compile``. A gate that aborts on that reports
    nothing about the other 1,300 files, which is worse than reporting nothing
    about one.

    Callers pass a list to :func:`scan_control_sites` to collect what was
    skipped, because a file the scanner could not read is a file it cannot vouch
    for, and silence about it would be the same mistake this gate is about.
    """
    try:
        return parsed(path)
    except (OSError, SyntaxError, ValueError):
        return None


def scan_module(
    path: Path, helpers: frozenset[str] = frozenset(), root: Path = REPO_ROOT
) -> list[ControlSite]:
    """Every in-scope control construction in one module, classified.

    *root* is what the reported path is made relative to. It is a parameter and
    not the constant because the scan's own tests point it at a temporary tree,
    and a hard-coded repository root made that raise rather than report.
    """
    tree = safe_parse(path)
    if tree is None:
        return []
    relative = path.relative_to(root).as_posix()
    return classify_tree(tree, relative, helpers | frozenset(label_helpers_in(tree)))


def scanned_paths(root: Path = REPO_ROOT) -> list[Path]:
    found: list[Path] = []
    for pattern in SCAN_GLOBS:
        found.extend(path for path in sorted(root.glob(pattern)) if "__pycache__" not in path.parts)
    return found


def scan_control_sites(
    root: Path = REPO_ROOT, skipped: list[str] | None = None
) -> list[ControlSite]:
    """Every in-scope control construction under :data:`SCAN_GLOBS`.

    Two passes. Label helpers are collected across the whole scan first, because
    the commonest one -- ``StudioPage.add_label`` -- lives in a base class two
    modules away from the pages that call it, and a per-module pass would report
    eighteen already-correct fields in ``pages_documents.py`` alone.

    Pass a list as *skipped* to be told which files would not parse; see
    :func:`safe_parse`.
    """
    with scope():
        paths = scanned_paths(root)
        helpers: set[str] = set()
        readable: list[Path] = []
        for path in paths:
            tree = safe_parse(path)
            if tree is None:
                if skipped is not None:
                    skipped.append(path.relative_to(root).as_posix())
                continue
            readable.append(path)
            helpers |= label_helpers_in(tree)
        frozen = frozenset(helpers)
        sites: list[ControlSite] = []
        for path in readable:
            sites.extend(scan_module(path, frozen, root))
        return sorted(sites)
