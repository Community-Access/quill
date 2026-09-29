"""The build gate that keeps the retired bug-report credential out of every build.

Owner decision 2026-09-26: feedback is email-only, and no QuillVille build may
ship ``quill/_feedback_token.py`` (a GitHub token) or the ``feedback_hub``
package again. These pin what the gate catches and that every freezer runs it.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from scripts.check_no_credentials import (
    assert_toc_clean,
    find_forbidden,
    is_forbidden_module,
    main,
)

_ROOT = Path(__file__).resolve().parents[3]


def _write(path: Path, text: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_clean_tree_passes(tmp_path: Path) -> None:
    _write(tmp_path / "Lib" / "site-packages" / "quill" / "__init__.py")
    _write(tmp_path / "Lib" / "site-packages" / "quill" / "core" / "feedback_email.py")
    assert find_forbidden(tmp_path) == []
    assert main([str(tmp_path)]) == 0


@pytest.mark.parametrize(
    "relative",
    [
        "Lib/site-packages/quill/_feedback_token.py",
        "_internal/quill/_feedback_token.pyc",
        "quill/__pycache__/_feedback_token.cpython-313.pyc",
    ],
)
def test_the_token_module_in_any_form_fails(tmp_path: Path, relative: str) -> None:
    _write(tmp_path / relative, 'BUNDLED_TOKEN = "x"\n')
    assert find_forbidden(tmp_path) == [relative]
    assert main([str(tmp_path)]) == 1


def test_feedback_hub_package_and_metadata_fail_and_are_reported_once(tmp_path: Path) -> None:
    site = tmp_path / "Lib" / "site-packages"
    _write(site / "feedback_hub" / "__init__.py")
    _write(site / "feedback_hub" / "dialog.py")
    _write(site / "feedback_hub-1.1.0.dist-info" / "METADATA")
    assert find_forbidden(tmp_path) == [
        "Lib/site-packages/feedback_hub",
        "Lib/site-packages/feedback_hub-1.1.0.dist-info",
    ]


def test_inside_a_py2app_zip(tmp_path: Path) -> None:
    lib = tmp_path / "Quill.app" / "Contents" / "Resources" / "lib"
    lib.mkdir(parents=True)
    with zipfile.ZipFile(lib / "python313.zip", "w") as zf:
        zf.writestr("quill/__init__.py", "")
        zf.writestr("quill/_feedback_token.pyc", b"\x00")
    assert find_forbidden(tmp_path) == [
        "Quill.app/Contents/Resources/lib/python313.zip!quill/_feedback_token.pyc"
    ]


def test_missing_directory_is_not_an_offender(tmp_path: Path) -> None:
    assert find_forbidden(tmp_path / "nope") == []


def test_module_names() -> None:
    assert is_forbidden_module("quill._feedback_token")
    assert is_forbidden_module("feedback_hub")
    assert is_forbidden_module("feedback_hub.dialog")
    assert not is_forbidden_module("quill.core.feedback_token_notes")
    assert not is_forbidden_module("feedback_hubs")


def test_pyinstaller_toc_gate() -> None:
    assert_toc_clean([("quill", "x", "PYMODULE"), ("quill.core", "y", "PYMODULE")])
    with pytest.raises(SystemExit, match="quill._feedback_token"):
        assert_toc_clean([("quill._feedback_token", "z", "PYMODULE")])


def test_every_pyinstaller_spec_excludes_and_gates_the_token() -> None:
    specs = sorted((_ROOT / "standalone").glob("*/*.spec"))
    assert specs
    for spec in specs:
        text = spec.read_text(encoding="utf-8")
        assert '"quill._feedback_token",' in text, spec.name
        assert "assert_toc_clean(a.pure)" in text, spec.name
        assert "feedback_hub" in text, spec.name  # excluded


def test_every_build_path_runs_the_gate() -> None:
    windows = (_ROOT / "scripts" / "build_windows_distribution.py").read_text(encoding="utf-8")
    assert "_assert_no_retired_credential(portable_dir)" in windows
    mac = (_ROOT / "scripts" / "build_macos.sh").read_text(encoding="utf-8")
    assert "scripts/check_no_credentials.py" in mac
    runtime = (_ROOT / "standalone" / "runtime" / "build_runtime.ps1").read_text(encoding="utf-8")
    assert "check_no_credentials.py" in runtime
