"""Detect ``sys.platform`` guard branches so gate scanners can tag Mac-only sites.

The QUILL dev box is Windows, so a dialog or network-egress call site that sits
inside a ``if sys.platform == "darwin":`` branch can never be exercised locally.
The dialog-inventory and network-egress gates use these helpers to record a
``platform`` tag on each discovered site -- ``"darwin"`` for a Mac-only branch,
``""`` otherwise -- so a reviewer can see at a glance which sites only show their
real effect on a Mac.

Detection is deliberately conservative and purely AST-driven (deterministic, no
execution): only a literal ``sys.platform`` comparison is recognised, and only
branches that are unambiguously Mac-only are tagged ``"darwin"``. Anything this
heuristic cannot model (an ``is_darwin`` alias, a ``platform.system()`` call, a
combined ``or`` test, ...) is left ``""`` -- the tag is a *lower bound*, so it is
never wrong, only sometimes silent. That is the right trade-off for a gate: a
false ``"darwin"`` tag would mislead a reviewer, while a missed one merely hides
a site that is still caught by the rest of the review.

Recognised guards (``sys.platform`` on the left, a string literal on the right):

    == "darwin"   body  -> darwin        (orelse is not Mac-only)
    != "darwin"   orelse -> darwin       (body is not Mac-only)
    == "win32"    orelse -> darwin       (body is Windows-only)
    != "win32"    body  -> darwin        (orelse is Windows-only)
"""

from __future__ import annotations

import ast

#: The only platform tag this module ever emits. ``""`` means "cross-platform or
#: Windows-default" -- the untagged majority. Keeping the set to one non-empty
#: value keeps the gate output and its tests trivial to reason about.
DARWIN = "darwin"


def _platform_compare(
    test: ast.expr,
) -> tuple[str | None, str | None] | None:
    """Classify a single ``sys.platform ==/!= "..."`` comparison.

    Returns ``(body_platform, orelse_platform)`` where each is ``"darwin"`` when
    that branch runs only on macOS, or ``None`` when it does not. Returns
    ``None`` when ``test`` is not a recognised literal ``sys.platform`` compare.
    """
    if not isinstance(test, ast.Compare):
        return None
    if len(test.ops) != 1 or len(test.comparators) != 1:
        return None
    left, op, right = test.left, test.ops[0], test.comparators[0]
    if not (
        isinstance(left, ast.Attribute)
        and isinstance(left.value, ast.Name)
        and left.value.id == "sys"
        and left.attr == "platform"
    ):
        return None
    if not isinstance(right, ast.Constant) or not isinstance(right.value, str):
        return None
    is_eq = isinstance(op, ast.Eq)
    is_ne = isinstance(op, ast.NotEq)
    if not (is_eq or is_ne):
        return None
    value = right.value
    if value == "darwin":
        # `== "darwin"`: body is Mac-only. `!= "darwin"`: orelse is Mac-only.
        return (DARWIN, None) if is_eq else (None, DARWIN)
    if value == "win32":
        # `== "win32"`: body is Windows-only, orelse is the non-Windows (Mac)
        # branch. `!= "win32"`: body is the non-Windows (Mac) branch.
        return (None, DARWIN) if is_eq else (DARWIN, None)
    return None


def branch_platform(test: ast.expr) -> tuple[str | None, str | None]:
    """Return ``(body_platform, orelse_platform)`` for an ``if`` test node.

    Each element is ``"darwin"`` when that branch is Mac-only, else ``None``.
    Unrecognised tests (BoolOp, ``platform.system()``, aliases, ...) return
    ``(None, None)`` so the caller leaves the site untagged rather than guessing.
    """
    classified = _platform_compare(test)
    if classified is not None:
        return classified
    # A combined `and` whose operands include a darwin-body compare still makes
    # the body Mac-only (`sys.platform == "darwin" and self._voice`). An `or` is
    # ambiguous (it could also run on Linux, which QUILL does not target), so we
    # leave it untagged rather than over-claim.
    if isinstance(test, ast.BoolOp) and isinstance(test.op, ast.And):
        for operand in test.values:
            body_pl, _ = _platform_compare(operand)
            if body_pl == DARWIN:
                return (DARWIN, None)
    return (None, None)


def build_parent_map(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    """Return ``{child: parent}`` for every node in ``tree``.

    AST nodes carry no parent pointer; the guard resolver walks up from a call
    site to its enclosing ``if``, so a parent map is built once per module.
    """
    parents: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent
    return parents


def platform_for_node(parents: dict[ast.AST, ast.AST], node: ast.AST) -> str:
    """Return ``"darwin"`` if ``node`` sits in a Mac-only branch, else ``""``.

    The *innermost* recognised ``sys.platform`` guard determines the tag: a node
    in that guard's Mac-only branch is ``"darwin"``, and a node in its other
    branch is ``""`` (that branch overrides any outer guard for this node). A
    node in the guard's ``test`` expression is not branch-bound, so the walk
    continues past it to the next enclosing guard.
    """
    current: ast.AST = node
    while current in parents:
        parent = parents[current]
        if isinstance(parent, ast.If):
            body_pl, orelse_pl = branch_platform(parent.test)
            if body_pl is not None or orelse_pl is not None:
                if current is parent.test:
                    pass  # In the test expression, not a branch; keep climbing.
                elif current in parent.body:
                    return body_pl or ""
                elif current in parent.orelse:
                    return orelse_pl or ""
                else:  # Defensive: direct child not in body/orelse/test.
                    break
        current = parent
    return ""
