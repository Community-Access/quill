"""Access-key uniqueness gate (GATE-14): one letter, one control, per window.

EdSharp's ``checkAccessKeysUnique`` imported (2026-08-27): within one window,
every ampersand mnemonic must be claimed by at most one control. Two controls
sharing a letter means Alt+letter reaches one of them unreliably -- on
Windows a duplicated mnemonic cycles focus instead of pressing, so the
button the user expected to fire silently does not -- and nothing announces
the loss. The first sweep found 128 collisions across 76 windows
('&Cancel' beside '&Clear Finished', '&Save' beside '&Secret:'), every one
invisible until a keyboard user pays for it.

Scoping, and why it is shaped this way:

* A ``wx.Dialog`` / ``wx.Frame`` subclass is treated as **one window**, all
  methods together -- the overwhelming convention is one class, one window,
  and builder helpers split across methods still target the same window.
* Any other class (a mixin, ``MainFrame``) is scoped **per method** -- such
  classes build many windows, one per method, and class-wide grouping would
  invent collisions between controls that never share a screen.
* Labels are read from ``label="..."`` keywords and the positional label
  argument of ``Button``, ``ToggleButton``, ``CheckBox``, ``RadioButton``
  and ``StaticText`` constructions, **including** a label wrapped in a
  translation call -- ``label=_("&Save")`` and ``label=str(_("&Save"))``
  count exactly as ``label="&Save"`` does. ``&&`` is a literal ampersand,
  not a mnemonic. Dynamic labels are invisible here, as everywhere
  source-level.

  The translation unwrap arrived on 2026-09-21 and it was not a refinement:
  without it a module that translates its labels was invisible control by
  control, so whole windows reported clean while carrying duplicates. Nine
  collisions surfaced the moment it landed, five of them in one window.

* Still invisible, and worth knowing before trusting a clean run: a label
  handed to a **helper** (``self._tag_field(grid, _("&Genre:"), ...)``) or
  read from a **tuple table** the constructor loops over. Those are not
  ``wx.<Control>(...)`` calls, so no amount of unwrapping reaches them, and
  the Chapter Workbench builds most of its window that way. Attributing them
  needs the gate to learn which argument of which helper is a label -- a
  different design, not a bigger regex.

* Also invisible: a **wizard page and the wizard's own chrome** share one
  top-level window, so a page control and the ``&Next >`` button really do
  compete, while the gate scopes them to different classes. That is not
  theoretical -- the Audio Studio's Voices page claimed ``N`` for "Remove
  language", Alt+N cycled instead of pressing Next, and the wizard could not
  be advanced past step 3 from the keyboard at all. It is why that label is
  now ``R&emove language`` and ``&Engine:`` is ``Eng&ine:``. Both pages_documents.py
  and chapter_workbench.py sit exactly on their GATE-11 budgets, so neither
  could carry the comment; this is where it lives.

The EdSharp companion rule is worth honouring while fixing: **OK, Cancel and
Close need no access key at all** -- Enter and Escape already serve them
(the dialog contract binds both), and every letter they give up resolves a
collision somewhere else in the window.

And when a window genuinely runs out, the loser gets **no** mnemonic rather
than a duplicate: a duplicate advertises a key that cycles instead of pressing
and nothing announces the loss, while silence is merely silent and Tab still
arrives. One control is in that state today and it is the only one --
``chapter_workbench.py``'s **Split at playhead**, in a window with
twenty-two mnemonic-bearing controls where every letter of that label is
claimed by a better claim (S by Save, P by Publish, A by Save As, L by
"Propose AI titles", H by the chapter list, and D/E/T by the controls that
moved to resolve their own collisions). Its label carries a one-line comment
pointing here; the file sits exactly on its GATE-11 budget, which is why the
reasoning lives in this docstring instead of at the site.

Run directly::

    python -m quill.tools.check_access_keys

or via pytest (``tests/unit/tools/test_access_keys.py``). Exit code is
non-zero when any collision is found.
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]

_SCAN_DIRS = ("quill/ui", "quill/apps", "quill/devtools")

#: Constructions whose label plants a live mnemonic in the window.
_LABELED_CONTROLS = frozenset({"Button", "ToggleButton", "CheckBox", "RadioButton", "StaticText"})

#: Reviewed exceptions: ``"<path>::<scope>"`` -> reason. A scope is
#: ``ClassName`` for window classes and ``ClassName.method`` for builder
#: methods. Use only when two same-letter controls genuinely never share a
#: window and the scoping above cannot see it.
_ALLOWLIST: dict[str, str] = {}


@dataclass(frozen=True)
class Collision:
    path: str
    scope: str
    line: int
    label: str
    other_label: str
    other_line: int
    letter: str

    def __str__(self) -> str:
        return (
            f"{self.path}::{self.scope}:{self.line}: {self.label!r} and "
            f"{self.other_label!r} (line {self.other_line}) both claim "
            f"Alt+{self.letter}"
        )


def mnemonic_of(label: str) -> str:
    """The Alt letter *label* claims, or "" (``&&`` escapes a literal &)."""
    index = label.find("&")
    while label[index : index + 2] == "&&":
        index = label.find("&", index + 2)
    if index == -1 or index + 1 >= len(label):
        return ""
    char = label[index + 1]
    return char.upper() if char.isalnum() else ""


def _string_within(node: ast.AST) -> str | None:
    """The string literal *node* is, or the one a translation call wraps.

    Labels are written three ways in this tree and all three plant the same
    mnemonic in the same window::

        wx.Button(self, label="&Save")
        wx.Button(self, label=_("&Save"))
        wx.Button(self, label=str(_("&Save")))

    Only the first used to count. That is not a small gap: the modules that
    translate their labels are whole windows, and the gate reported them as
    clean because it could not read a single control in them. The Chapter
    Workbench had five duplicated letters and passed.

    Recursing through the call's arguments handles ``_``, ``str(_(...))``,
    ``lazy_gettext`` and anything else shaped like a wrapper, without the gate
    needing to know their names.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Call):
        for argument in node.args:
            found = _string_within(argument)
            if found is not None:
                return found
    return None


def _label_of(node: ast.Call) -> str | None:
    for keyword in node.keywords:
        if keyword.arg == "label":
            return _string_within(keyword.value)
    # wx.Button(parent, id, "label") / wx.StaticText(parent, id, "label")
    if len(node.args) >= 3:
        return _string_within(node.args[2])
    return None


def _is_window_class(cls: ast.ClassDef) -> bool:
    """True when *cls* subclasses a Dialog/Frame (one class, one window)."""
    for base in cls.bases:
        name = base.attr if isinstance(base, ast.Attribute) else getattr(base, "id", "")
        if isinstance(name, str) and ("Dialog" in name or "Frame" in name):
            return True
    return False


def _labeled_constructions(scope: ast.AST) -> list[tuple[int, str, str]]:
    """``(line, label, letter)`` for every mnemonic-bearing control in *scope*."""
    out: list[tuple[int, str, str]] = []
    for node in ast.walk(scope):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
        if name not in _LABELED_CONTROLS:
            continue
        label = _label_of(node)
        if not label:
            continue
        letter = mnemonic_of(label)
        if letter:
            out.append((node.lineno, label, letter))
    return out


def _collisions_in_scope(
    rel: str, scope_name: str, sites: list[tuple[int, str, str]]
) -> list[Collision]:
    first_claim: dict[str, tuple[int, str]] = {}
    collisions: list[Collision] = []
    for line, label, letter in sites:
        if letter in first_claim:
            other_line, other_label = first_claim[letter]
            if other_label != label:  # identical repeated labels: one control, re-created
                collisions.append(
                    Collision(rel, scope_name, line, label, other_label, other_line, letter)
                )
        else:
            first_claim[letter] = (line, label)
    return collisions


def _check_file(path: Path) -> list[Collision]:
    rel = path.relative_to(_REPO_ROOT).as_posix()
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return []
    collisions: list[Collision] = []
    for cls in ast.walk(tree):
        if not isinstance(cls, ast.ClassDef):
            continue
        if _is_window_class(cls):
            scope_name = cls.name
            if f"{rel}::{scope_name}" in _ALLOWLIST:
                continue
            collisions.extend(_collisions_in_scope(rel, scope_name, _labeled_constructions(cls)))
        else:
            for method in cls.body:
                if not isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                scope_name = f"{cls.name}.{method.name}"
                if f"{rel}::{scope_name}" in _ALLOWLIST:
                    continue
                collisions.extend(
                    _collisions_in_scope(rel, scope_name, _labeled_constructions(method))
                )
    return collisions


def scan() -> list[Collision]:
    collisions: list[Collision] = []
    for rel_dir in _SCAN_DIRS:
        root = _REPO_ROOT / rel_dir
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.py")):
            collisions.extend(_check_file(path))
    return collisions


def main() -> int:
    collisions = scan()
    if collisions:
        print("Access-key gate (GATE-14) collisions:")
        for collision in collisions:
            print(f"  {collision}")
        print(
            f"\n{len(collisions)} collision(s). Give each control in a window "
            "its own Alt letter; OK, Cancel and Close need none at all "
            "(Enter and Escape already serve them)."
        )
        return 1
    print("GATE-14: every window's access keys are unique.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
