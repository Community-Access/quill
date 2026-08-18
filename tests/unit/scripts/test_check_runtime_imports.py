"""The runtime import gate: what it declares, and what it says when it fails.

The gate itself has to run a built runtime, so the end-to-end path belongs to
the build. What is testable here -- and what actually rotted in practice -- is
the *declaration*: a module named as engine-pack-owned must also be excluded
from the PyInstaller spec, or the gate reports a failure the build cannot fix.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SPEC_FILE = Path("standalone/runtime/quillville-runtime.spec")


def _load_gate():
    path = Path("scripts/check_runtime_imports.py")
    spec = importlib.util.spec_from_file_location("check_runtime_imports", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate = _load_gate()


@pytest.mark.parametrize("name", gate.ENGINE_PACK_OWNED)
def test_engine_pack_modules_are_excluded_from_the_spec(name: str) -> None:
    """Naming a module here without excluding it makes the build unfixable.

    The gate fails when an engine-pack-owned module is frozen in; the only fix
    is a spec exclude. If the two lists drift apart, the build fails with an
    instruction that has already been followed.
    """
    spec_text = _SPEC_FILE.read_text(encoding="utf-8")
    assert f'"{name}"' in spec_text, (
        f"{name} is declared engine-pack-owned but is not in the excludes list of "
        f"{_SPEC_FILE}, so every build would fail the import gate"
    )


def test_the_engine_pack_list_covers_the_engines_that_shipped_broken() -> None:
    """The 2026-08-17 regression, kept as a named case rather than a memory."""
    for name in ("vosk", "faster_whisper", "kokoro_onnx"):
        assert name in gate.ENGINE_PACK_OWNED


def test_clean_report_succeeds() -> None:
    result = {"absent_violations": [], "import_failures": [], "checked": 12}
    assert gate.report(result) == 0


def test_a_frozen_engine_pack_module_fails(capsys: pytest.CaptureFixture[str]) -> None:
    result = {
        "absent_violations": [{"module": "vosk", "origin": r"C:\x\_internal\vosk\__init__.py"}],
        "import_failures": [],
        "checked": 12,
    }
    assert gate.report(result) == 1
    out = capsys.readouterr().out
    assert "vosk" in out
    assert "excludes" in out, "the failure must say how to fix it"


def test_a_broken_import_fails(capsys: pytest.CaptureFixture[str]) -> None:
    result = {
        "absent_violations": [],
        "import_failures": [{"module": "enchant", "error": "ImportError: no libenchant"}],
        "checked": 12,
    }
    assert gate.report(result) == 1
    out = capsys.readouterr().out
    assert "enchant" in out and "no libenchant" in out


def test_both_kinds_are_reported_together(capsys: pytest.CaptureFixture[str]) -> None:
    """One build should not have to be run twice to see both classes of problem."""
    result = {
        "absent_violations": [{"module": "vosk", "origin": ""}],
        "import_failures": [{"module": "wx", "error": "ImportError: DLL load failed"}],
        "checked": 12,
    }
    assert gate.report(result) == 1
    out = capsys.readouterr().out
    assert "vosk" in out and "wx" in out


def test_missing_runtime_is_a_clear_error(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as caught:
        gate.run_probe(tmp_path)
    assert "QuillVilleRuntime.exe" in str(caught.value)
