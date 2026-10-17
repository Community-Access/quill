"""Gate: one ``wx.App`` per test process, and ``wx.CallAfter`` patched one way.

Two flake sources, both process-wide, both found by the 2026-10 P3 review:

* **Test files building their own ``wx.App``** (230 of them, until 2026-10-17).
  wx supports one App per process; files that made and destroyed their own
  left the next file in the same xdist worker holding an App whose C++ half
  was gone, decided by which files happened to share a worker. Use the
  ``wx_session_app`` fixture or ``tests.wx_session.shared_wx_app()``.
* **Test files replacing ``wx.CallAfter`` by hand** (33 files). The attribute
  is the wx module's, so the replacement is global; written as
  ``monkeypatch.setattr(some_module.wx, "CallAfter", ...)`` it does not look
  global. Use the ``wx_call_after`` fixture or
  ``tests.wx_session.patch_call_after(monkeypatch, ...)``, which is always
  test-scoped and records every call.

The scan is an AST walk, not a grep: a ``wx.App()`` inside a string (a
generated probe file, a docstring) is not a call and is not flagged. Only a
call on a name bound to the wx module counts, including
``wx = pytest.importorskip("wx")``.

``ALLOWED`` names the files that may still do it, each with its reason. It may
only shrink.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

TESTS = Path(__file__).resolve().parents[1]

#: path (relative to tests/, forward slashes) -> why it may build an App or
#: patch CallAfter itself.
ALLOWED: dict[str, str] = {
    "wx_session.py": "the one sanctioned home of both",
    "ui_live/conftest.py": "drives a real, visible app session; never run by unit CI",
    "integration/test_cast_native_storage_budget.py": (
        "integration test against real windows; not run under the overnight "
        "no-real-desktop rule, so left unmigrated rather than changed blind"
    ),
    "integration/test_cast_native_transport.py": (
        "integration test that plays through a real native window; same reason"
    ),
}

#: Only files that mention one of these can offend, so only they are parsed.
_NEEDLES = (".App(", "PySimpleApp", "CallAfter")


def _wx_names(tree: ast.Module) -> set[str]:
    names = {"wx"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.asname or a.name for a in node.names if a.name == "wx")
        elif isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            func = node.value.func
            args = node.value.args
            if (
                isinstance(func, ast.Attribute)
                and func.attr == "importorskip"
                and args
                and isinstance(args[0], ast.Constant)
                and args[0].value == "wx"
            ):
                names.update(t.id for t in node.targets if isinstance(t, ast.Name))
    return names


def _is_wx(node: ast.AST, names: set[str]) -> bool:
    if isinstance(node, ast.Name):
        return node.id in names
    return isinstance(node, ast.Attribute) and node.attr == "wx"


def offences(source: str) -> list[str]:
    """Each place *source* builds a wx.App or patches wx.CallAfter by hand."""
    tree = ast.parse(source)
    names = _wx_names(tree)
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if (
                isinstance(func, ast.Attribute)
                and func.attr in {"App", "PySimpleApp"}
                and isinstance(func.value, ast.Name)
                and func.value.id in names
            ):
                found.append(f"line {node.lineno}: builds its own wx.{func.attr}")
            if (
                isinstance(func, ast.Attribute)
                and func.attr == "setattr"
                and len(node.args) >= 2
                and isinstance(node.args[1], ast.Constant)
                and node.args[1].value == "CallAfter"
                and _is_wx(node.args[0], names)
            ):
                found.append(f"line {node.lineno}: patches wx.CallAfter by hand")
            if (
                isinstance(func, ast.Attribute)
                and func.attr in {"patch", "object"}
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and node.args[0].value == "wx.CallAfter"
            ):
                found.append(f"line {node.lineno}: patches wx.CallAfter by hand")
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Attribute)
                    and target.attr == "CallAfter"
                    and isinstance(target.value, ast.Name)
                    and target.value.id in names
                ):
                    found.append(f"line {node.lineno}: assigns wx.CallAfter")
    return found


# Reading ~2,300 files is I/O, and on a busy machine it took 11 s of the
# suite's 30 s per-test ceiling; the parse itself is a fraction of a second.
@pytest.mark.timeout(120)
def test_no_test_file_builds_its_own_app_or_patches_call_after() -> None:
    problems: list[str] = []
    for path in sorted(TESTS.rglob("*.py")):
        relative = path.relative_to(TESTS).as_posix()
        if relative in ALLOWED:
            continue
        try:
            source = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if not any(needle in source for needle in _NEEDLES):
            continue
        problems.extend(f"tests/{relative} {issue}" for issue in offences(source))
    assert not problems, (
        "Use the wx_session_app / wx_call_after fixtures (tests/wx_session.py) "
        "instead:\n" + "\n".join(problems)
    )


def test_the_allowlist_has_no_stale_rows() -> None:
    """A row for a file that no longer offends (or no longer exists) must go."""
    stale = [
        name
        for name in ALLOWED
        if name != "wx_session.py"
        and (
            not (TESTS / name).exists() or not offences((TESTS / name).read_text(encoding="utf-8"))
        )
    ]
    assert not stale, f"remove from ALLOWED: {stale}"


def test_the_scan_sees_each_shape_and_ignores_strings() -> None:
    assert offences("import wx\napp = wx.App()\n")
    assert offences("import wx as w\napp = w.App(False)\n")
    assert offences('import pytest\nwx = pytest.importorskip("wx")\nwx.App()\n')
    assert offences(
        'import mod\ndef t(monkeypatch):\n    monkeypatch.setattr(mod.wx, "CallAfter", f)\n'
    )
    assert offences('from unittest import mock\nmock.patch("wx.CallAfter")\n')
    assert offences("import wx\nwx.CallAfter = print\n")
    assert not offences('PROBE = "app = wx.App()"\n')
    assert not offences("fake = object()\nfake.CallAfter = print\n")


def test_the_shared_app_survives_a_test_destroying_it() -> None:
    from tests.wx_session import shared_wx_app

    app = shared_wx_app()
    if type(app).__name__ != "_SessionApp":
        pytest.skip("another test's own App class is the live one in this worker")
    app.Destroy()
    assert shared_wx_app() is app
    assert app.GetAppName() is not None


def test_patch_call_after_is_test_scoped_and_records(monkeypatch) -> None:
    import wx

    from tests.wx_session import patch_call_after

    original = wx.CallAfter
    ran: list[int] = []
    capture = patch_call_after(monkeypatch, None)
    wx.CallAfter(ran.append, 1)
    assert ran == [1]
    assert len(capture) == 1
    monkeypatch.undo()
    assert wx.CallAfter is original
