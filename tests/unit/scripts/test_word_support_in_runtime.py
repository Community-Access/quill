"""Word documents work in every built QUILL and QUILL Lite (2026-10-17).

The shared QuillVille runtime excluded ``lxml`` for months. python-docx is pure
Python, so it froze in and ``find_spec`` found it -- and then raised the moment
it imported lxml. Installed copies of QUILL and QUILL Lite opened Word files as
plain text, could not save a real ``.docx``, and the GLOW Word, PDF and
PowerPoint audits failed. Every build exited 0.

A built runtime cannot be made in a unit test, but its *excludes* can be
simulated exactly: every package ``quillville-runtime.spec`` excludes is
blocked in a fresh interpreter, and the Word stack must still import and
round-trip a real document there. Excluding lxml (or docx, or anything they
need) again fails this test on the pull request, long before a release.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[3]
_SPEC_FILE = _ROOT / "standalone" / "runtime" / "quillville-runtime.spec"


def _load(name: str, path: Path):  # type: ignore[no-untyped-def]
    unique = f"_word_support_{name}"
    spec = importlib.util.spec_from_file_location(unique, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    # A dataclass looks its module up in sys.modules while the class is built.
    sys.modules[unique] = module
    spec.loader.exec_module(module)
    return module


gate = _load("check_runtime_imports", _ROOT / "scripts" / "check_runtime_imports.py")
inventory_gate = _load("check_runtime_inventory", _ROOT / "scripts" / "check_runtime_inventory.py")
bp = _load("build_portable", _ROOT / "standalone" / "studio" / "scripts" / "build_portable.py")


def spec_excludes() -> list[str]:
    """The literal ``excludes=[...]`` list of the runtime spec's Analysis call."""
    tree = ast.parse(_SPEC_FILE.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "Analysis":
            for keyword in node.keywords:
                if keyword.arg == "excludes":
                    return [ast.literal_eval(item) for item in keyword.value.elts]  # type: ignore[attr-defined]
    raise AssertionError("no Analysis(excludes=[...]) in the runtime spec")


_SIMULATION = textwrap.dedent(
    """
    import importlib, importlib.abc, json, sys

    BLOCKED = tuple(json.loads(sys.argv[1]))
    MODULES = json.loads(sys.argv[2])

    class _Excluded(importlib.abc.MetaPathFinder):
        # What a PyInstaller exclude leaves behind: the module is not there.
        def find_spec(self, name, path=None, target=None):
            if any(name == b or name.startswith(b + ".") for b in BLOCKED):
                raise ModuleNotFoundError(f"No module named {name!r} (excluded)", name=name)
            return None

    sys.meta_path.insert(0, _Excluded())
    failures = {}
    for name in MODULES:
        try:
            importlib.import_module(name)
        except Exception as error:
            failures[name] = f"{type(error).__name__}: {error}"
    from quill.io.word_selfcheck import word_round_trip_problem
    print(json.dumps({"failures": failures, "round_trip": word_round_trip_problem()}))
    """
)


def _installed(name: str) -> bool:
    try:
        return importlib.util.find_spec(name.split(".")[0]) is not None
    except (ImportError, ValueError):
        return False


def test_the_spec_no_longer_excludes_anything_word_needs() -> None:
    excludes = set(spec_excludes())
    for name in ("lxml", "docx", "pptx", "openpyxl", "acb_large_print", "quill_glow_core"):
        assert name not in excludes, f"{name} is excluded from the shared runtime again"


def test_word_imports_and_round_trips_with_every_spec_exclude_blocked() -> None:
    """The simulated built runtime: excludes blocked, Word must still work."""
    modules = [name for name in gate.WORD_MUST_IMPORT if _installed(name)]
    # python-docx and lxml are base dependencies, so they are always here; the
    # GLOW engine is skipped only on a machine that has not installed [glow].
    for required in ("lxml.etree", "docx", "quill.core.docx_open", "quill.io.word_selfcheck"):
        assert required in modules, required
    env = dict(os.environ, PYTHONPATH=str(_ROOT))
    completed = subprocess.run(  # noqa: S603 - fixed argv
        [sys.executable, "-c", _SIMULATION, json.dumps(spec_excludes()), json.dumps(modules)],
        capture_output=True,
        text=True,
        cwd=_ROOT,
        env=env,
        timeout=300,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout.strip().splitlines()[-1])
    assert report["failures"] == {}, report["failures"]
    assert report["round_trip"] is None, report["round_trip"]


def test_the_round_trip_names_lxml_when_it_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """The safety net still says what broke, so a build fails with a reason."""
    from quill.io import word_selfcheck

    monkeypatch.setitem(sys.modules, "lxml.etree", None)
    problem = word_selfcheck.word_round_trip_problem()
    assert problem is not None and "lxml.etree" in problem
    with pytest.raises(RuntimeError, match="python-docx needs lxml"):
        word_selfcheck.assert_word_round_trip()


def test_the_round_trip_passes_in_the_development_interpreter() -> None:
    from quill.io.word_selfcheck import word_round_trip_problem

    assert word_round_trip_problem() is None


def test_the_runtime_gate_runs_the_word_round_trip() -> None:
    assert set(gate.WORD_MUST_IMPORT) <= set(gate.MUST_IMPORT)
    assert gate.WORD_ROUND_TRIP == "quill.io.word_selfcheck"
    assert "word_round_trip_problem" in gate._PROBE_SOURCE
    for name in ("acb_large_print.auditor", "acb_large_print.pdf_auditor", "lxml.etree"):
        assert name in gate.WORD_MUST_IMPORT


def test_a_word_failure_in_the_gate_says_what_it_means(capsys: pytest.CaptureFixture[str]) -> None:
    result = {
        "absent_violations": [],
        "import_failures": [
            {"module": "docx", "error": "ModuleNotFoundError: No module named 'lxml'"}
        ],
        "checked": 40,
    }
    assert gate.report(result) == 1
    out = capsys.readouterr().out
    assert "python-docx needs lxml" in out and "quillville-runtime.spec" in out


def test_the_inventory_lists_lxml_and_the_swept_packages_stay_out() -> None:
    """Rebaselined 2026-10-24: lxml is part of the runtime, so the gate no longer
    explains it, and the five packages that build swept from the machine through
    optional imports are excluded rather than baselined."""
    import json

    listed = json.loads(
        (_ROOT / "standalone" / "runtime" / "runtime-inventory.json").read_text(encoding="utf-8")
    )
    internal = listed["_internal"]
    assert "lxml" in internal
    assert inventory_gate.explain("lxml") == ""
    spec = (_ROOT / "standalone" / "runtime" / "quillville-runtime.spec").read_text(
        encoding="utf-8"
    )
    for swept in ("orjson", "bcrypt", "h2", "clr_loader", "pythonnet"):
        assert swept not in internal, swept
        assert f'"{swept}",' in spec, swept
    script = (_ROOT / "standalone" / "runtime" / "build_runtime.ps1").read_text(encoding="utf-8")
    assert '"h2-*.dist-info"' in script


def test_every_word_capable_portable_round_trips_a_document() -> None:
    from quill.io.word_selfcheck import WORD_SUPPORT_MODULES

    assert bp.WORD_SUPPORT_MODULES == WORD_SUPPORT_MODULES
    for key in ("quilllite", "quill"):
        product = bp.PRODUCTS[key]
        assert product.check_word, key
        assert "docx" in product.dep_groups and "office-text" in product.dep_groups, key
        probe = bp.import_check_source(product)
        assert "import lxml.etree;" in probe
        assert "word_check.assert_word_round_trip()" in probe


def test_the_quill_distribution_checks_word_too() -> None:
    bwd = _load("build_windows_distribution", _ROOT / "scripts" / "build_windows_distribution.py")
    assert "assert_word_round_trip" in bwd.WORD_SUPPORT_CHECK
