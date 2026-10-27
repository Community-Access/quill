"""The portable build's import check must not dirty its package inventory."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_BUILDER_PATH = _ROOT / "standalone" / "studio" / "scripts" / "build_portable.py"
_SPEC = importlib.util.spec_from_file_location("quill_build_portable_runtime_check", _BUILDER_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_BUILDER = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _BUILDER
_SPEC.loader.exec_module(_BUILDER)


def test_sanity_import_disables_bytecode_writes() -> None:
    product = _BUILDER.PRODUCTS["quilllite"]
    python_exe = Path("bundle") / "python.exe"

    assert _BUILDER.import_check_command(python_exe, product) == [
        str(python_exe),
        "-B",
        "-c",
        _BUILDER.import_check_source(product),
    ]
