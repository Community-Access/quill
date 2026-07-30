"""Tests for the runtime resolver algorithm.

The actual resolver is C code in ``quill/native/launcher/runtime_resolve.c``;
this test module reimplements the same algorithm in Python so we can
exercise the *contract* (path-walk, fallback order, marker validation) in
isolation, without spinning up a Windows build.

The Python implementation here MUST stay byte-for-byte aligned with the C
one. If you change one, change the other -- there is a comment in
``runtime_resolve.c`` ("The function never crashes.") that is the contract
this test file enforces.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

# ----------------------------------------------------------------------
# Python mirror of runtime_resolve.c. MUST stay in sync.
# ----------------------------------------------------------------------

PATH_SEP = "\\" if sys.platform == "win32" else "/"
EXE_EXT = ".exe" if sys.platform == "win32" else ""

# The shared runtime is a PyInstaller onedir. The boot loader exe
# (QuillVilleRuntime.exe on Windows, QuillVilleRuntime on POSIX) is the
# onedir root's only executable and IS the entry point the per-app C
# launchers spawn. Phase 4 (see docs/design/native-launcher-2026-07-24.md §7)
# drops PyInstaller in favour of a real CPython at the same path -- when that
# lands, change the probe back to "python.exe" / "bin/python3". MUST match
# the C code in runtime_resolve.c::try_shared_runtime.
SHARED_RUNTIME_EXE = "QuillVilleRuntime.exe" if sys.platform == "win32" else "QuillVilleRuntime"


@dataclass
class QlRuntime:
    python: str = ""
    install_root: str = ""
    data_dir: str = ""


def _path_join(a: str, b: str) -> str:
    if not a:
        return b
    if a[-1] in ("/", "\\"):
        return a + b
    return a + PATH_SEP + b


def _path_is_file(p: str) -> bool:
    return Path(p).is_file()


def _path_exists(p: str) -> bool:
    return Path(p).exists()


def _dirname(p: str) -> str:
    return str(Path(p).parent)


def _read_python_version_from_marker(path: str) -> str | None:
    p = Path(path)
    if not p.is_file():
        return None
    try:
        data = json.loads(p.read_text("utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    py = data.get("python") if isinstance(data, dict) else None
    return py if isinstance(py, str) else None


def _python_version_compatible(marker_python: str) -> bool:
    """Match the C version of this function: '3.13' baseline, prefix compare."""
    baseline = "3.13"
    if not marker_python.startswith(baseline):
        return False
    next_char = marker_python[len(baseline) :]
    return not next_char or next_char.startswith(".")


def try_shared_runtime(local_appdata: str | None) -> QlRuntime | None:
    """Probe the shared QuillVille runtime.

    Mirrors try_shared_runtime() in runtime_resolve.c.
    """
    if not local_appdata:
        return None
    base = _path_join(local_appdata, _path_join("QuillVille", "Runtime"))
    if not _path_exists(base):
        return None
    runtime_dir = _path_join(base, "3.13")
    if not _path_exists(runtime_dir):
        return None
    marker = _path_join(runtime_dir, "quillville-runtime.json")
    if not _path_is_file(marker):
        return None
    py = _read_python_version_from_marker(marker)
    if not py or not _python_version_compatible(py):
        return None
    python = _path_join(runtime_dir, SHARED_RUNTIME_EXE)
    if not _path_is_file(python):
        return None
    return QlRuntime(python=python, install_root=runtime_dir)


def try_private_runtime(self_dir: str) -> QlRuntime | None:
    """Probe the launcher's own directory for an embedded runtime.

    Mirrors try_private_runtime() in runtime_resolve.c.
    """
    candidates = [
        _path_join(self_dir, _path_join("_internal", f"python{EXE_EXT}")),
        _path_join(self_dir, f"python{EXE_EXT}"),
        _path_join(self_dir, f"pythonw{EXE_EXT}"),
    ]
    for candidate in candidates:
        if _path_is_file(candidate):
            return QlRuntime(python=candidate, install_root=self_dir, data_dir=self_dir)
    return None


def ql_resolve_runtime(self_path: str, local_appdata: str | None = None) -> QlRuntime:
    """Python mirror of ql_resolve_runtime(self_path) from runtime_resolve.c.

    Note: the C function reads LOCALAPPDATA from getenv; the Python mirror
    accepts it as a parameter so the test can drive the env without an
    actual environment variable (fixture-controlled, deterministic).
    """
    if local_appdata is None:
        local_appdata = (
            os.environ.get("LOCALAPPDATA")
            if sys.platform == "win32"
            else os.environ.get("XDG_DATA_HOME")
        )

    shared = try_shared_runtime(local_appdata)
    if shared is not None:
        return shared

    self_dir = _dirname(self_path)
    private = try_private_runtime(self_dir)
    if private is not None:
        return private

    return QlRuntime()  # python == "" signals "not found"


# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------


@pytest.fixture
def fake_local_appdata(tmp_path: Path) -> Path:
    """A scratch directory standing in for %LOCALAPPDATA%."""
    return tmp_path / "localappdata"


@pytest.fixture
def shared_runtime(fake_local_appdata: Path) -> Path:
    """A real shared runtime layout under fake_local_appdata/QuillVille/Runtime/3.13/."""
    runtime = fake_local_appdata / "QuillVille" / "Runtime" / "3.13"
    runtime.mkdir(parents=True)
    (runtime / SHARED_RUNTIME_EXE).write_bytes(b"MZ" + b"\x00" * 100)  # fake PE header
    (runtime / "quillville-runtime.json").write_text(
        json.dumps({"python": "3.13.14", "build": "2026-07-24"}),
        encoding="utf-8",
    )
    return runtime


def test_shared_runtime_resolves_when_marker_matches(
    fake_local_appdata: Path, shared_runtime: Path
) -> None:
    """The shared runtime is preferred when its marker is present and valid."""
    self_path = str(shared_runtime.parent / "QuillRadio.exe")  # somewhere unrelated
    result = ql_resolve_runtime(self_path, local_appdata=str(fake_local_appdata))
    assert result.python == str(shared_runtime / SHARED_RUNTIME_EXE)
    assert result.install_root == str(shared_runtime)


def test_shared_runtime_ignored_when_marker_missing(
    fake_local_appdata: Path, tmp_path: Path
) -> None:
    """Without a marker, the resolver falls through to the private runtime."""
    runtime = fake_local_appdata / "QuillVille" / "Runtime" / "3.13"
    runtime.mkdir(parents=True)
    (runtime / SHARED_RUNTIME_EXE).write_bytes(b"MZ")  # shared exe present, marker absent
    self_dir = tmp_path / "QuillRadio"
    self_dir.mkdir()
    (self_dir / "QuillRadio.exe").write_bytes(b"MZ")
    (self_dir / "python.exe").write_bytes(b"MZ")
    (self_dir / "data").mkdir()  # portable evidence

    result = ql_resolve_runtime(
        str(self_dir / "QuillRadio.exe"), local_appdata=str(fake_local_appdata)
    )
    assert result.python == str(self_dir / "python.exe")
    assert result.data_dir == str(self_dir)


def test_shared_runtime_ignored_when_marker_wrong_version(fake_local_appdata: Path) -> None:
    """A 3.12 marker must not be selected by a 3.13-baselined launcher."""
    runtime = fake_local_appdata / "QuillVille" / "Runtime" / "3.13"
    runtime.mkdir(parents=True)
    (runtime / SHARED_RUNTIME_EXE).write_bytes(b"MZ")
    (runtime / "quillville-runtime.json").write_text(
        json.dumps({"python": "3.12.5", "build": "2026-01-01"}),
        encoding="utf-8",
    )

    self_dir = fake_local_appdata / "fallback"
    self_dir.mkdir()
    (self_dir / "python.exe").write_bytes(b"MZ")

    result = ql_resolve_runtime(str(self_dir / "python.exe"), local_appdata=str(fake_local_appdata))
    assert result.python == str(self_dir / "python.exe")


def test_private_runtime_pyinstaller_layout(tmp_path: Path) -> None:
    """The PyInstaller onedir layout puts python at _internal/python.exe."""
    self_dir = tmp_path / "QuillRadio"
    self_dir.mkdir()
    internal = self_dir / "_internal"
    internal.mkdir()
    (internal / "python.exe").write_bytes(b"MZ")
    (self_dir / "QuillRadio.exe").write_bytes(b"MZ")

    result = ql_resolve_runtime(str(self_dir / "QuillRadio.exe"))
    assert result.python == str(internal / "python.exe")
    assert result.data_dir == str(self_dir)


def test_private_runtime_flat_layout(tmp_path: Path) -> None:
    """The main QUILL build uses a flat layout: python.exe beside quill.exe."""
    self_dir = tmp_path / "QUILL"
    self_dir.mkdir()
    (self_dir / "python.exe").write_bytes(b"MZ")
    (self_dir / "quill.exe").write_bytes(b"MZ")

    result = ql_resolve_runtime(str(self_dir / "quill.exe"))
    assert result.python == str(self_dir / "python.exe")


def test_private_runtime_pythonw_legacy_fallback(tmp_path: Path) -> None:
    """During the transition, a pythonw.exe beside the launcher still works."""
    self_dir = tmp_path / "QUILL"
    self_dir.mkdir()
    (self_dir / "pythonw.exe").write_bytes(b"MZ")
    (self_dir / "quill.exe").write_bytes(b"MZ")

    result = ql_resolve_runtime(str(self_dir / "quill.exe"))
    assert result.python == str(self_dir / "pythonw.exe")


def test_no_runtime_found_returns_empty(tmp_path: Path) -> None:
    """When nothing is found, .python == '' -- never a crash."""
    self_dir = tmp_path / "QUILL"
    self_dir.mkdir()
    (self_dir / "quill.exe").write_bytes(b"MZ")
    # No python, no pythonw, no _internal, no shared runtime.
    result = ql_resolve_runtime(str(self_dir / "quill.exe"), local_appdata="")
    assert result.python == ""


def test_marker_with_garbage_json_is_rejected(tmp_path: Path, fake_local_appdata: Path) -> None:
    """A malformed marker must not crash the resolver -- it's a no-op fallback."""
    runtime = fake_local_appdata / "QuillVille" / "Runtime" / "3.13"
    runtime.mkdir(parents=True)
    (runtime / SHARED_RUNTIME_EXE).write_bytes(b"MZ")
    (runtime / "quillville-runtime.json").write_text("not json at all", encoding="utf-8")
    self_dir = tmp_path / "fallback"
    self_dir.mkdir()
    (self_dir / "python.exe").write_bytes(b"MZ")
    result = ql_resolve_runtime(str(self_dir / "python.exe"), local_appdata=str(fake_local_appdata))
    assert result.python == str(self_dir / "python.exe")


def test_marker_missing_python_key_is_rejected(tmp_path: Path, fake_local_appdata: Path) -> None:
    """A JSON marker without a 'python' key is treated as absent."""
    runtime = fake_local_appdata / "QuillVille" / "Runtime" / "3.13"
    runtime.mkdir(parents=True)
    (runtime / SHARED_RUNTIME_EXE).write_bytes(b"MZ")
    (runtime / "quillville-runtime.json").write_text(
        json.dumps({"build": "2026-07-24"}), encoding="utf-8"
    )
    self_dir = tmp_path / "fallback"
    self_dir.mkdir()
    (self_dir / "python.exe").write_bytes(b"MZ")
    result = ql_resolve_runtime(str(self_dir / "python.exe"), local_appdata=str(fake_local_appdata))
    assert result.python == str(self_dir / "python.exe")


def test_python_version_compatible_accepts_patch(tmp_path: Path) -> None:
    """A 3.13.14 marker is compatible with a 3.13 launcher."""
    assert _python_version_compatible("3.13.14")


def test_python_version_compatible_rejects_minor_mismatch() -> None:
    """A 3.12 marker is not compatible with a 3.13 launcher."""
    assert not _python_version_compatible("3.12.5")
    assert not _python_version_compatible("3.14.0")
    assert not _python_version_compatible("4.0.0")


def test_shared_runtime_preferred_over_private(fake_local_appdata: Path, tmp_path: Path) -> None:
    """When BOTH the shared runtime and a private one are valid, the shared wins.

    This is the Phase 2 behavior: the resolver prefers the shared runtime
    once it is installed, and the per-app private runtime becomes the
    fallback for portable mode.
    """
    shared = fake_local_appdata / "QuillVille" / "Runtime" / "3.13"
    shared.mkdir(parents=True)
    (shared / SHARED_RUNTIME_EXE).write_bytes(b"MZ")
    (shared / "quillville-runtime.json").write_text(
        json.dumps({"python": "3.13.14", "build": "2026-07-24"}),
        encoding="utf-8",
    )

    private = tmp_path / "QuillRadio"
    private.mkdir()
    internal = private / "_internal"
    internal.mkdir()
    (internal / "python.exe").write_bytes(b"MZ")
    (private / "QuillRadio.exe").write_bytes(b"MZ")

    result = ql_resolve_runtime(
        str(private / "QuillRadio.exe"), local_appdata=str(fake_local_appdata)
    )
    assert result.python == str(shared / SHARED_RUNTIME_EXE), (
        "shared runtime must be preferred over per-app private runtime"
    )


def test_shared_runtime_finds_quillville_runtime_exe_not_python(fake_local_appdata: Path) -> None:
    """The shared runtime's entry point is QuillVilleRuntime.exe, not python.exe.

    PyInstaller's COLLECT places the boot loader exe (QuillVilleRuntime.exe) at
    the onedir root. The shared runtime layout has NO real python.exe at that
    path -- PyInstaller unpacks the interpreter from a bundled archive at
    runtime. A regression that probed for python.exe at the shared location
    would fail every install of every per-app product. This test guards the
    contract: a runtime with both files present must select the bootloader
    (Phase 2 today), and a runtime with ONLY python.exe (no bootloader) must
    not be selected (the file the resolver actually checks for is gone).

    Phase 4 (see docs/design/native-launcher-2026-07-24.md §7) drops the
    PyInstaller bootloader in favour of a real CPython at the same path; this
    test will be updated to assert the new probe name at that time.
    """
    runtime = fake_local_appdata / "QuillVille" / "Runtime" / "3.13"
    runtime.mkdir(parents=True)
    # BOTH files present: bootloader wins, python.exe is ignored.
    (runtime / "python.exe").write_bytes(b"MZ")
    (runtime / SHARED_RUNTIME_EXE).write_bytes(b"MZ")
    (runtime / "quillville-runtime.json").write_text(
        json.dumps({"python": "3.13.14", "build": "2026-07-24"}),
        encoding="utf-8",
    )
    self_dir = fake_local_appdata / "fallback"
    self_dir.mkdir()
    (self_dir / "python.exe").write_bytes(b"MZ")
    (self_dir / "quill.exe").write_bytes(b"MZ")

    result = ql_resolve_runtime(str(self_dir / "quill.exe"), local_appdata=str(fake_local_appdata))
    assert result.python == str(runtime / SHARED_RUNTIME_EXE), (
        "shared runtime must select the PyInstaller bootloader, not python.exe"
    )

    # ONLY python.exe present (no bootloader): the resolver must NOT select
    # this as the shared runtime. The resolver's contract is "the entry point
    # is QuillVilleRuntime.exe; if it isn't there, fall through to private."
    (runtime / SHARED_RUNTIME_EXE).unlink()
    result2 = ql_resolve_runtime(str(self_dir / "quill.exe"), local_appdata=str(fake_local_appdata))
    assert result2.python == str(self_dir / "python.exe"), (
        "without QuillVilleRuntime.exe, shared runtime is not selected"
    )
