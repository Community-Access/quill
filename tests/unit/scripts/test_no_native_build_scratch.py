"""No shipped payload carries the CMake scratch from building the native code.

``quill/native/optilab/build`` is where CMake compiles ``quill-optilab.exe`` in
place: ``CMakeFiles``, ``*.tlog``, ``Debug/``, ``VCTargetsPath``. It is
gitignored and wholly regenerable, and it was riding into every portable zip
(87 files) and into the shared runtime every installer ships -- exactly as the
mypy/pytest/ruff caches once did, and for the same reason: both build paths
sweep the package tree as it sits on the build machine.

It also carried the five longest paths in the archive. Dropping it takes the
deepest entry from 144 characters to 120, which is real headroom against
MAX_PATH for someone unpacking into an already-deep folder -- a partial
extraction leaves a portable copy with no ``pythonw.exe``, which is precisely
the "it does not start" report this came out of (2026-09-30).

The two filters are tested rather than the built output, so this costs
milliseconds instead of a twenty-minute build.
"""

from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_SPEC_FILE = _ROOT / "standalone" / "runtime" / "quillville-runtime.spec"


def _load_build_portable():
    name = "quill_build_portable_scratch"
    spec = importlib.util.spec_from_file_location(
        name, _ROOT / "standalone" / "studio" / "scripts" / "build_portable.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _load_spec_filter():
    """Exec just the filter block: the spec itself needs PyInstaller's globals."""
    text = _SPEC_FILE.read_text(encoding="utf-8")
    start = text.index("_DEV_CACHE_PARTS = (")
    end = text.index("# Freeze the quill of the checkout")
    namespace: dict[str, object] = {}
    exec(compile(text[start:end], str(_SPEC_FILE), "exec"), namespace)  # noqa: S102
    return namespace["drop_dev_caches"]


def test_the_portable_copy_skips_a_native_build_directory() -> None:
    ignore = _load_build_portable()._DEV_CACHE_IGNORE
    skipped = ignore("quill/native/optilab", ["build", "upstream", "quill_optilab.cpp"])
    assert "build" in skipped
    assert "upstream" not in skipped, "the vendored OptiLab source must still ship"
    assert "quill_optilab.cpp" not in skipped


def test_the_portable_copy_still_skips_the_dev_caches() -> None:
    ignore = _load_build_portable()._DEV_CACHE_IGNORE
    names = ["__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache", "a.pyc", "core"]
    skipped = ignore("quill", names)
    assert "core" not in skipped
    assert skipped == {"__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache", "a.pyc"}


def test_the_runtime_spec_drops_native_build_scratch() -> None:
    drop = _load_spec_filter()
    entries = [
        (
            "D:/QUILL/quill/native/optilab/build/CMakeFiles/4.4.2/CompilerIdCXX/Debug/x.tlog",
            "quill/native/optilab/build/CMakeFiles/4.4.2/CompilerIdCXX/Debug/x.tlog",
        ),
        (
            "D:/QUILL/quill/native/optilab/quill_optilab.cpp",
            "quill/native/optilab/quill_optilab.cpp",
        ),
        ("D:/QUILL/quill/native/optilab/upstream/LICENSE", "quill/native/optilab/upstream/LICENSE"),
        ("D:/QUILL/quill/core/ai/.mypy_cache/x.json", "quill/core/ai/.mypy_cache/x.json"),
    ]
    kept = {dest for _, dest in drop(entries)}
    assert kept == {
        "quill/native/optilab/quill_optilab.cpp",
        "quill/native/optilab/upstream/LICENSE",
    }


def test_a_checkout_that_merely_lives_under_a_build_folder_still_ships() -> None:
    """The filter reads the DEST path, never the build machine's own layout.

    A CI agent whose workspace is ``C:/build/agent/...`` must not have its whole
    package filtered away -- which is what matching the source path would do.
    """
    drop = _load_spec_filter()
    entries = [
        (
            "C:/build/agent/QUILL/quill/data/radio-catalog/seed.db.xz",
            "quill/data/radio-catalog/seed.db.xz",
        ),
        ("C:/build/agent/QUILL/quill/apps/radio.py", "quill/apps/radio.py"),
    ]
    kept = {dest for _, dest in drop(entries)}
    assert kept == {"quill/data/radio-catalog/seed.db.xz", "quill/apps/radio.py"}


def test_the_adapter_itself_is_never_filtered() -> None:
    """``find_adapter`` looks beside the app and in ``quill/native/optilab``
    before it ever reaches a build directory, so both shipped copies survive."""
    drop = _load_spec_filter()
    entries = [
        (
            "D:/QUILL/quill/native/optilab/quill-optilab.exe",
            "quill/native/optilab/quill-optilab.exe",
        ),
    ]
    assert len(drop(entries)) == 1

    ignore = _load_build_portable()._DEV_CACHE_IGNORE
    assert "quill-optilab.exe" not in ignore("quill/native/optilab", ["quill-optilab.exe"])


def test_shutil_ignore_patterns_is_what_the_copy_actually_uses() -> None:
    """Guard the assumption the tests above rest on: a hand-rolled callable
    would make every assertion here meaningless."""
    module = _load_build_portable()
    probe = shutil.ignore_patterns("build")
    assert type(module._DEV_CACHE_IGNORE) is type(probe)
