"""The runtime's frozen quill package must match the source it was built from.

``Assert-QuillRuntimeHasModule`` asks whether a module is *present* in the
frozen tree. On 2026-09-08 that was not enough: a runtime reused with
``-SkipSharedRuntime`` contained ``quill/apps/lite.py`` -- an older copy of it,
28 files behind, with two QuillLite modules missing entirely -- and the
assertion passed. The installer would have shipped an app three weeks older
than its own installer, with every check green.

These tests pin the gate that answers the question the assertion could not:
a module that is present but differs is stale, a source module absent from the
frozen tree is missing, a frozen module whose source is gone is an orphan, and
a tree that matches passes. The caches and the machine-written token are
excluded, because each would otherwise fail every run for a reason that is not
staleness.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "check_runtime_freshness.py"
_spec = importlib.util.spec_from_file_location("check_runtime_freshness", _SCRIPT)
assert _spec is not None and _spec.loader is not None
freshness = importlib.util.module_from_spec(_spec)
# Registered before exec: @dataclass resolves its own class's __module__ through
# sys.modules, and a file-loaded module that is not there raises AttributeError
# from inside dataclasses rather than anywhere that names the cause.
sys.modules[_spec.name] = freshness
_spec.loader.exec_module(freshness)


def _tree(root: Path, files: dict[str, str]) -> None:
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def _build(tmp_path: Path, *, source: dict[str, str], frozen: dict[str, str]) -> tuple[Path, Path]:
    """A fake source root and runtime dist carrying the given quill trees."""
    source_root = tmp_path / "checkout"
    _tree(source_root / "quill", source)
    dist = tmp_path / "dist" / "QuillVilleRuntime"
    dist.mkdir(parents=True)
    (dist / "QuillVilleRuntime.exe").write_bytes(b"MZ")
    _tree(dist / "_internal" / "quill", frozen)
    return source_root, dist


def test_a_matching_tree_reports_nothing(tmp_path: Path) -> None:
    same = {"apps/lite.py": "print('hi')\n", "core/lite/paths.py": "X = 1\n"}
    source_root, dist = _build(tmp_path, source=same, frozen=dict(same))
    assert freshness.compare(dist, source_root) == []


def test_a_module_present_but_different_is_stale(tmp_path: Path) -> None:
    """The 2026-09-08 case: present, so the old assertion passed."""
    source_root, dist = _build(
        tmp_path,
        source={"apps/lite.py": "VERSION = 2\n"},
        frozen={"apps/lite.py": "VERSION = 1\n"},
    )
    findings = freshness.compare(dist, source_root)
    assert [(f.kind, f.relative) for f in findings] == [("stale", "apps/lite.py")]


def test_a_source_module_absent_from_the_frozen_tree_is_missing(tmp_path: Path) -> None:
    """``lite_check.py`` and ``lite_window_selection.py`` were exactly this."""
    source_root, dist = _build(
        tmp_path,
        source={"apps/lite.py": "A = 1\n", "apps/lite_check.py": "B = 1\n"},
        frozen={"apps/lite.py": "A = 1\n"},
    )
    findings = freshness.compare(dist, source_root)
    assert [(f.kind, f.relative) for f in findings] == [("missing", "apps/lite_check.py")]


def test_a_frozen_module_whose_source_is_gone_is_an_orphan(tmp_path: Path) -> None:
    source_root, dist = _build(
        tmp_path,
        source={"apps/lite.py": "A = 1\n"},
        frozen={"apps/lite.py": "A = 1\n", "apps/removed.py": "old\n"},
    )
    findings = freshness.compare(dist, source_root)
    assert [(f.kind, f.relative) for f in findings] == [("orphan", "apps/removed.py")]


def test_caches_and_the_generated_token_are_not_staleness(tmp_path: Path) -> None:
    """Each of these differs for a reason that is not "the runtime is old"."""
    source_root, dist = _build(
        tmp_path,
        source={
            "apps/lite.py": "A = 1\n",
            "apps/__pycache__/lite.cpython-313.pyc": "compiled\n",
            "tools/.mypy_cache/x.py": "cached\n",
            "_feedback_token.py": "TOKEN = 'new'\n",
            "native/launcher/build/gen.py": "generated\n",
        },
        frozen={"apps/lite.py": "A = 1\n", "_feedback_token.py": "TOKEN = 'old'\n"},
    )
    assert freshness.compare(dist, source_root) == []


def test_only_python_sources_are_compared(tmp_path: Path) -> None:
    """Data files churn for reasons of their own; the gate is about code."""
    source_root, dist = _build(
        tmp_path,
        source={"apps/lite.py": "A = 1\n", "core/help/topics.json": '{"a": 2}\n'},
        frozen={"apps/lite.py": "A = 1\n", "core/help/topics.json": '{"a": 1}\n'},
    )
    assert freshness.compare(dist, source_root) == []


def test_a_dist_without_the_runtime_exe_is_rejected(tmp_path: Path) -> None:
    """Pointing the gate at the wrong directory must not read as 'fresh'."""
    source_root = tmp_path / "checkout"
    (source_root / "quill").mkdir(parents=True)
    not_a_dist = tmp_path / "nowhere"
    not_a_dist.mkdir()
    assert freshness.main([str(not_a_dist), "--source-root", str(source_root)]) == 2


def test_the_exit_code_names_the_failure(tmp_path: Path) -> None:
    source_root, dist = _build(
        tmp_path,
        source={"apps/lite.py": "VERSION = 2\n"},
        frozen={"apps/lite.py": "VERSION = 1\n"},
    )
    assert freshness.main([str(dist), "--source-root", str(source_root)]) == 1


def test_a_fresh_tree_exits_zero(tmp_path: Path) -> None:
    same = {"apps/lite.py": "A = 1\n"}
    source_root, dist = _build(tmp_path, source=same, frozen=dict(same))
    assert freshness.main([str(dist), "--source-root", str(source_root)]) == 0
