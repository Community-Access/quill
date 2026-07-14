"""Tests for the portable-distribution ZIP builder (scratch exclusion)."""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

from scripts.build_portable_zip import main


def _build(tmp_path: Path) -> list[str]:
    src = tmp_path / "portable"
    # Shipped payload.
    (src / "python").mkdir(parents=True)
    (src / "python" / "python.exe").write_bytes(b"exe")
    (src / "tools" / "pandoc").mkdir(parents=True)
    (src / "tools" / "pandoc" / "pandoc.exe").write_bytes(b"pandoc")
    (src / "run-quill.cmd").write_text("run")
    # Build-only scratch that must be excluded.
    (src / "_tool-download" / "piper" / "stage").mkdir(parents=True)
    (src / "_tool-download" / "piper" / "stage" / "piper.exe").write_bytes(b"dup")
    (src / "quill" / "__pycache__").mkdir(parents=True)
    (src / "quill" / "__pycache__" / "x.pyc").write_bytes(b"cache")

    out = tmp_path / "Quill-Portable.zip"
    argv = sys.argv
    sys.argv = ["build_portable_zip.py", "--source-dir", str(src), "--output", str(out)]
    try:
        assert main() == 0
    finally:
        sys.argv = argv
    with zipfile.ZipFile(out) as zf:
        return zf.namelist()


def test_scratch_is_excluded_from_the_zip(tmp_path: Path) -> None:
    names = _build(tmp_path)
    joined = "\n".join(names)
    assert "_tool-download" not in joined  # the ~376 MB staging duplicate
    assert "__pycache__" not in joined  # Python bytecode caches


def test_shipped_payload_is_present(tmp_path: Path) -> None:
    names = _build(tmp_path)
    joined = "\n".join(names).replace("\\", "/")
    assert any(n.endswith("python/python.exe") for n in [x.replace("\\", "/") for x in names])
    assert "portable/run-quill.cmd" in joined
    assert any("tools/pandoc/pandoc.exe" in n.replace("\\", "/") for n in names)
