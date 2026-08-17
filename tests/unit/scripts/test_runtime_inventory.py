"""The runtime inventory gate: swept-content drift fails the build, named.

The 2026-08-15 installers shipped 81.8 MB of undeclared payload (pymupdf, a
second OpenBLAS, pydantic, curl_cffi...) because PyInstaller's Analysis sweeps
whatever the build interpreter can import, and nothing compared the result to a
declared expectation. These tests pin the comparison: an extra package fails,
a vanished one fails, a version bump does not, and a package present at two
versions at once is caught even though the name-set cannot see it.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "check_runtime_inventory.py"
_spec = importlib.util.spec_from_file_location("check_runtime_inventory", _SCRIPT)
assert _spec is not None and _spec.loader is not None
inv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(inv)


def _make_dist(root: Path, internal: list[str], tools: list[str] = ("ffmpeg", "mpv")) -> Path:
    dist = root / "QuillVilleRuntime"
    (dist / "_internal").mkdir(parents=True)
    (dist / "QuillVilleRuntime.exe").write_bytes(b"MZ")
    (dist / "quillville-runtime.json").write_text("{}", encoding="utf-8")
    for name in internal:
        if name.endswith((".pyd", ".dll")):
            (dist / "_internal" / name).write_bytes(b"")
        elif name.endswith(".dist-info"):
            (dist / "_internal" / name).mkdir()
        else:
            (dist / "_internal" / name).mkdir()
    for name in tools:
        (dist / "tools" / name).mkdir(parents=True)
    return dist


def _run(argv: list[str]) -> int:
    old = sys.argv
    sys.argv = ["check_runtime_inventory.py", *argv]
    try:
        return inv.main()
    finally:
        sys.argv = old


# -- normalization ------------------------------------------------------------


def test_dist_info_normalizes_to_a_version_free_name() -> None:
    assert inv.normalize("numpy-2.5.2.dist-info") == "numpy"
    assert inv.normalize("yt_dlp-2026.7.4.dist-info") == "yt-dlp"


def test_interpreter_tags_are_stripped_so_a_python_bump_is_not_drift() -> None:
    assert inv.normalize("_brotli.cp313-win_amd64.pyd") == "_brotli"
    assert inv.normalize("_brotli.cp314-win_amd64.pyd") == "_brotli"


def test_plain_names_pass_through_casefolded() -> None:
    assert inv.normalize("Pythonwin") == "pythonwin"
    assert inv.normalize("python313.dll") == "python313.dll"


# -- the gate -----------------------------------------------------------------


def test_matching_dist_passes(tmp_path: Path) -> None:
    dist = _make_dist(tmp_path, ["wx", "numpy", "numpy-2.5.2.dist-info"])
    manifest = tmp_path / "inventory.json"
    assert _run([str(dist), "--manifest", str(manifest), "--write"]) == 0
    assert _run([str(dist), "--manifest", str(manifest)]) == 0


def test_an_undeclared_swept_package_fails_named(tmp_path: Path, capsys) -> None:
    dist = _make_dist(tmp_path, ["wx"])
    manifest = tmp_path / "inventory.json"
    assert _run([str(dist), "--manifest", str(manifest), "--write"]) == 0
    (dist / "_internal" / "pymupdf").mkdir()
    assert _run([str(dist), "--manifest", str(manifest)]) == 1
    assert "unexpected in _internal: pymupdf" in capsys.readouterr().out


def test_a_vanished_package_fails_named(tmp_path: Path, capsys) -> None:
    """The 2026-08-09 winrt OCR regression: shipped once, silently absent next."""
    dist = _make_dist(tmp_path, ["wx", "winrt"])
    manifest = tmp_path / "inventory.json"
    assert _run([str(dist), "--manifest", str(manifest), "--write"]) == 0
    import shutil

    shutil.rmtree(dist / "_internal" / "winrt")
    assert _run([str(dist), "--manifest", str(manifest)]) == 1
    assert "missing from _internal: winrt" in capsys.readouterr().out


def test_a_version_bump_is_not_drift(tmp_path: Path) -> None:
    dist = _make_dist(tmp_path, ["numpy", "numpy-2.5.2.dist-info"])
    manifest = tmp_path / "inventory.json"
    assert _run([str(dist), "--manifest", str(manifest), "--write"]) == 0
    (dist / "_internal" / "numpy-2.5.2.dist-info").rename(
        dist / "_internal" / "numpy-2.6.0.dist-info"
    )
    assert _run([str(dist), "--manifest", str(manifest)]) == 0


def test_a_package_at_two_versions_at_once_fails(tmp_path: Path, capsys) -> None:
    """The doubled-OpenBLAS shape: two dist-infos, one name, twice the DLLs."""
    dist = _make_dist(tmp_path, ["numpy", "numpy-2.5.1.dist-info", "numpy-2.5.2.dist-info"])
    manifest = tmp_path / "inventory.json"
    (dist / "_internal" / "numpy-2.5.1.dist-info").rename(dist / "_internal" / "hold")
    assert _run([str(dist), "--manifest", str(manifest), "--write"]) == 0
    (dist / "_internal" / "hold").rename(dist / "_internal" / "numpy-2.5.1.dist-info")
    assert _run([str(dist), "--manifest", str(manifest)]) == 1
    assert "duplicated: numpy" in capsys.readouterr().out


def test_optional_entries_may_be_absent_or_present(tmp_path: Path) -> None:
    """OptiLab is best-effort: staged only when a C++ toolchain exists."""
    dist = _make_dist(tmp_path, ["wx"])
    manifest = tmp_path / "inventory.json"
    assert _run([str(dist), "--manifest", str(manifest), "--write"]) == 0
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["optional"] = ["quill-optilab.exe"]
    manifest.write_text(json.dumps(data), encoding="utf-8")
    assert _run([str(dist), "--manifest", str(manifest)]) == 0  # absent: fine
    (dist / "quill-optilab.exe").write_bytes(b"MZ")
    assert _run([str(dist), "--manifest", str(manifest)]) == 0  # present: fine


def test_rebaseline_preserves_the_optional_list(tmp_path: Path) -> None:
    dist = _make_dist(tmp_path, ["wx"])
    manifest = tmp_path / "inventory.json"
    assert _run([str(dist), "--manifest", str(manifest), "--write"]) == 0
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["optional"] = ["quill-optilab.exe"]
    manifest.write_text(json.dumps(data), encoding="utf-8")
    (dist / "quill-optilab.exe").write_bytes(b"MZ")
    assert _run([str(dist), "--manifest", str(manifest), "--write"]) == 0
    rewritten = json.loads(manifest.read_text(encoding="utf-8"))
    assert rewritten["optional"] == ["quill-optilab.exe"]
    assert "quill-optilab.exe" not in rewritten["root"]


def test_a_non_dist_directory_is_refused(tmp_path: Path) -> None:
    assert _run([str(tmp_path), "--manifest", str(tmp_path / "m.json")]) == 2


def test_missing_manifest_says_how_to_create_one(tmp_path: Path, capsys) -> None:
    dist = _make_dist(tmp_path, ["wx"])
    assert _run([str(dist), "--manifest", str(tmp_path / "none.json")]) == 2
    assert "--write" in capsys.readouterr().err
