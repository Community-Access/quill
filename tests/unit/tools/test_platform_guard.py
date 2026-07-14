"""Unit tests for the ``sys.platform`` guard detector (GATE platform field, #3/#13).

These build tiny AST trees by ``ast.parse``-ing source snippets so the detector
is exercised on real Python syntax rather than hand-constructed nodes. The
detector is conservative by design: every assertion below pins one of the
recognised guards, and the "unrecognised" cases assert ``""`` (never a false
``"darwin"``).
"""

from __future__ import annotations

import ast

from quill.tools.platform_guard import (
    DARWIN,
    branch_platform,
    build_parent_map,
    platform_for_node,
)


def _if_test(source: str) -> ast.expr:
    """Parse `if <test>: ...` and return the test expression."""
    tree = ast.parse(source)
    assert isinstance(tree, ast.Module) and isinstance(tree.body[0], ast.If)
    return tree.body[0].test


def _node_in_body(source: str) -> tuple[dict[ast.AST, ast.AST], ast.AST]:
    """Parse `if ...: <stmt>` and return (parent map, the body call node)."""
    tree = ast.parse(source)
    parents = build_parent_map(tree)
    if_node = tree.body[0]
    assert isinstance(if_node, ast.If)
    # The body is an `urlopen(...)` expression statement.
    call = if_node.body[0]
    assert isinstance(call, ast.Expr) and isinstance(call.value, ast.Call)
    return parents, call.value


def _node_in_orelse(source: str) -> tuple[dict[ast.AST, ast.AST], ast.AST]:
    tree = ast.parse(source)
    parents = build_parent_map(tree)
    if_node = tree.body[0]
    assert isinstance(if_node, ast.If)
    call = if_node.orelse[0]
    assert isinstance(call, ast.Expr) and isinstance(call.value, ast.Call)
    return parents, call.value


# -- branch_platform --------------------------------------------------------


def test_eq_darwin_tags_body() -> None:
    body_pl, orelse_pl = branch_platform(_if_test('if sys.platform == "darwin":\n  pass'))
    assert body_pl == DARWIN
    assert orelse_pl is None


def test_ne_darwin_tags_orelse() -> None:
    body_pl, orelse_pl = branch_platform(_if_test('if sys.platform != "darwin":\n  pass'))
    assert body_pl is None
    assert orelse_pl == DARWIN


def test_eq_win32_tags_orelse() -> None:
    body_pl, orelse_pl = branch_platform(_if_test('if sys.platform == "win32":\n  pass'))
    assert body_pl is None
    assert orelse_pl == DARWIN


def test_ne_win32_tags_body() -> None:
    body_pl, orelse_pl = branch_platform(_if_test('if sys.platform != "win32":\n  pass'))
    assert body_pl == DARWIN
    assert orelse_pl is None


def test_and_with_darwin_operand_tags_body() -> None:
    body_pl, _ = branch_platform(_if_test('if sys.platform == "darwin" and self._enabled:\n  pass'))
    assert body_pl == DARWIN


def test_unrecognised_test_is_not_tagged() -> None:
    # An alias / platform.system() / an `or` combo are all left untagged.
    for src in (
        "if is_darwin:\n  pass",
        'if platform.system() == "Darwin":\n  pass',
        'if sys.platform == "darwin" or sys.platform == "linux":\n  pass',
        'if some_other == "darwin":\n  pass',
    ):
        assert branch_platform(_if_test(src)) == (None, None), src


# -- platform_for_node ------------------------------------------------------


def test_call_inside_darwin_body_is_darwin() -> None:
    parents, call = _node_in_body('if sys.platform == "darwin":\n  urlopen("x")')
    assert platform_for_node(parents, call) == DARWIN


def test_call_inside_win32_body_is_empty() -> None:
    parents, call = _node_in_body('if sys.platform == "win32":\n  urlopen("x")')
    assert platform_for_node(parents, call) == ""


def test_call_inside_eq_win32_orelse_is_darwin() -> None:
    parents, call = _node_in_orelse('if sys.platform == "win32":\n  pass\nelse:\n  urlopen("x")')
    assert platform_for_node(parents, call) == DARWIN


def test_call_outside_any_guard_is_empty() -> None:
    tree = ast.parse('urlopen("x")')
    parents = build_parent_map(tree)
    call = tree.body[0].value
    assert isinstance(call, ast.Call)
    assert platform_for_node(parents, call) == ""


def test_innermost_guard_wins() -> None:
    # A win32 guard nested inside a darwin guard: the node is in the win32 body,
    # so it is NOT Mac-only even though an outer darwin guard exists.
    source = 'if sys.platform == "darwin":\n  if sys.platform == "win32":\n    urlopen("x")\n'
    tree = ast.parse(source)
    parents = build_parent_map(tree)
    # Walk to the innermost call.
    outer = tree.body[0]
    inner = outer.body[0]
    call = inner.body[0].value
    assert isinstance(call, ast.Call)
    assert platform_for_node(parents, call) == ""


def test_call_in_test_expression_is_not_branch_bound() -> None:
    # `if urlopen(x) is not None:` -- the call is the test, not a branch body.
    source = 'if urlopen("x") is not None:\n  pass'
    tree = ast.parse(source)
    parents = build_parent_map(tree)
    if_node = tree.body[0]
    assert isinstance(if_node, ast.If)
    call = if_node.test.left
    assert isinstance(call, ast.Call)
    assert platform_for_node(parents, call) == ""
