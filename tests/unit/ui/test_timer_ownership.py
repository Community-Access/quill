"""Every ``wx.Timer`` an app or window keeps has somewhere that stops it (qc.md F-12).

A timer nobody stops fires into a window that has gone: QUILL Lite's status
timer did exactly that on exit (2026-10-01, ``RuntimeError: wrapped C/C++
object of type Panel has been deleted``), and the first run of this gate found
Quill Player's resume and status timers and Quill Converter's IPC timer with no
stop at all -- the Player also lost up to fifteen seconds of a listener's place
on every close, because the save only ran on its timer.

The rule, static and by AST: a ``self.<name> = wx.Timer(...)`` in ``quill/apps``
or ``quill/ui`` needs a ``<name>.Stop()`` -- directly, or as ``timer.Stop()``
on a value fetched by that attribute name -- somewhere in the package. That is
a necessary condition, not a proof the stop runs at the right moment; the
behavioural tests of each close path are the proof. A timer genuinely meant to
die with its process goes in :data:`ALLOWED` with the reason.
"""

from __future__ import annotations

import ast
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_SCOPES = ("quill/apps", "quill/ui")

#: "path::attribute" -> why no explicit stop is needed. Empty is the goal.
ALLOWED: dict[str, str] = {}


def _timers(path: Path) -> list[tuple[str, int]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        value = None
        target = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            value, target = node.value, node.targets[0]
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            value, target = node.value, node.target
        if not isinstance(value, ast.Call) or not isinstance(target, ast.Attribute):
            continue
        func = value.func
        name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
        if name == "Timer":
            found.append((target.attr, node.lineno))
    return found


def _stopped_names(sources: list[str]) -> set[str]:
    """Attribute names something stops, in any of the three shapes in use.

    ``self._x.Stop()``; ``timer = getattr(self, "_x", None)`` then
    ``timer.Stop()`` (or ``timer.Stop`` handed on as a callable); and a loop over
    a tuple of attribute names whose body stops what it fetches. Resolved per
    function, because a local called ``timer`` means a different timer in each.
    """
    stopped: set[str] = set()
    for source in sources:
        tree = ast.parse(source)
        scopes = [
            n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        for scope in scopes or [tree]:
            fetched: dict[str, str] = {}
            for node in ast.walk(scope):
                if isinstance(node, ast.Assign) and len(node.targets) == 1:
                    target, value = node.targets[0], node.value
                    if isinstance(target, ast.Name):
                        if isinstance(value, ast.Attribute):
                            fetched[target.id] = value.attr
                        elif (
                            isinstance(value, ast.Call)
                            and getattr(value.func, "id", "") == "getattr"
                            and len(value.args) >= 2
                            and isinstance(value.args[1], ast.Constant)
                        ):
                            fetched[target.id] = str(value.args[1].value)
                if isinstance(node, ast.For) and isinstance(node.iter, ast.Tuple):
                    if "Stop" in ast.unparse(node):
                        for element in node.iter.elts:
                            if isinstance(element, ast.Constant) and isinstance(element.value, str):
                                stopped.add(element.value)
            for node in ast.walk(scope):
                if isinstance(node, ast.Attribute) and node.attr == "Stop":
                    owner = node.value
                    if isinstance(owner, ast.Attribute):
                        stopped.add(owner.attr)
                    elif isinstance(owner, ast.Name):
                        stopped.add(fetched.get(owner.id, owner.id))
    return stopped


def _scan() -> list[str]:
    files = [p for scope in _SCOPES for p in sorted((_ROOT / scope).rglob("*.py"))]
    sources = [p.read_text(encoding="utf-8") for p in files]
    stopped = _stopped_names(sources)
    offenders = []
    for path in files:
        rel = path.relative_to(_ROOT).as_posix()
        for attr, line in _timers(path):
            if attr in stopped or f"{rel}::{attr}" in ALLOWED:
                continue
            offenders.append(f"{rel}:{line} self.{attr}")
    return offenders


def test_the_detector_sees_an_unstopped_timer_and_both_stop_shapes() -> None:
    unstopped = "import wx\nclass A:\n    def b(self):\n        self._tick = wx.Timer(self)\n"
    assert _stopped_names([unstopped]) == set()
    direct = "def s(self):\n    self._tick.Stop()\n"
    fetched = "def s(self):\n    timer = getattr(self, '_tick', None)\n    timer.Stop()\n"
    looped = (
        "def s(self):\n    for name in ('_tick', '_tock'):\n        getattr(self, name).Stop()\n"
    )
    assert "_tick" in _stopped_names([direct])
    assert "_tick" in _stopped_names([fetched])
    assert {"_tick", "_tock"} <= _stopped_names([looped])


def test_every_kept_timer_has_somewhere_that_stops_it() -> None:
    offenders = _scan()
    assert offenders == [], (
        "a wx.Timer with no Stop anywhere fires into a window that has gone: "
        + ", ".join(offenders)
    )


def test_the_player_saves_its_place_and_stops_its_clocks_on_close() -> None:
    """The behaviour the Player was missing, not only the shape."""
    from types import SimpleNamespace

    from quill.apps.player_close import on_player_close

    calls: list[str] = []

    class _Timer:
        def __init__(self, name: str) -> None:
            self.name = name

        def Stop(self) -> None:  # noqa: N802 - wx API shape
            calls.append(f"stop {self.name}")

    app = SimpleNamespace(
        _save_resume=lambda: calls.append("save"),
        _resume_timer=_Timer("resume"),
        _sleep_timer=_Timer("sleep"),
        _status_timer=_Timer("status"),
        _listen_timer=None,
    )
    skipped: list[bool] = []
    on_player_close(app, SimpleNamespace(Skip=lambda: skipped.append(True)))
    assert calls[0] == "save"
    assert {"stop resume", "stop sleep", "stop status"} <= set(calls)
    assert skipped == [True]
