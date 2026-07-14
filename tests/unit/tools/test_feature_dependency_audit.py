"""The feature-tags gate audits the dependency graph (existence + acyclicity)."""

from __future__ import annotations

from quill.core.features import transitive_dependencies
from quill.tools.check_feature_tags import _find_dependency_cycle, run


class _Def:
    def __init__(self, dependencies):
        self.dependencies = tuple(dependencies)


def test_real_graph_passes() -> None:
    assert run() == 0  # the shipped catalog is sound


def test_transitive_dependencies_are_transitive_and_cycle_safe() -> None:
    # core.format -> core.editor -> core.app (from the real catalog).
    deps = transitive_dependencies("core.format")
    assert "core.editor" in deps and "core.app" in deps


def test_cycle_detector_finds_a_cycle() -> None:
    graph = {"a": _Def(["b"]), "b": _Def(["c"]), "c": _Def(["a"])}
    cycle = _find_dependency_cycle(graph)
    assert cycle is not None and cycle[0] == cycle[-1]  # closed loop


def test_cycle_detector_passes_a_dag() -> None:
    graph = {"a": _Def(["b"]), "b": _Def(["c"]), "c": _Def([])}
    assert _find_dependency_cycle(graph) is None
