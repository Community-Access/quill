"""The copyleft source collector: an exact manifest, offline, from a build folder.

Every GPL/AGPL/LGPL component a release ships owes its Corresponding Source.
These tests pin the manifest half of the collector without the network: that
it lists copyleft components and nothing else, reads exact versions from the
build folder when it can (dist-info, pillow-heif's bundled list, the GCC
stamp in libstdc++) and says so, leaves build-only tools out, and never
downloads unless asked.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import urllib.request
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "collect_copyleft_sources.py"
_spec = importlib.util.spec_from_file_location("collect_copyleft_sources", _SCRIPT)
assert _spec is not None and _spec.loader is not None
collector = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = collector  # dataclasses resolve their module by name
_spec.loader.exec_module(collector)


@pytest.fixture
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("the collector touched the network")

    monkeypatch.setattr(urllib.request, "urlretrieve", refuse)
    monkeypatch.setattr(urllib.request, "urlopen", refuse)


@pytest.fixture
def build_dir(tmp_path: Path) -> Path:
    """A runtime build folder shaped like PyInstaller's, with exact versions in it."""
    internal = tmp_path / "QuillVilleRuntime" / "_internal"
    (internal / "mutagen-1.48.9.dist-info").mkdir(parents=True)
    heif = internal / "pillow_heif-1.8.1.dist-info" / "licenses"
    heif.mkdir(parents=True)
    (heif / "LICENSES_bundled.txt").write_text(
        "Name: libheif\n"
        "  Source code: https://github.com/strukturag/libheif/tree/v1.99.0\n"
        "Name: x265\n"
        "  Source code: https://github.com/Multicorewareinc/x265/tree/9.9\n",
        encoding="utf-8",
    )
    (internal / "libstdc++-6.dll").write_bytes(
        b"MZ\0\0junk GCC: (Rev3, Built by MSYS2 project) 15.1.0\0more"
    )
    return tmp_path / "QuillVilleRuntime"


def _by_id(entries: list) -> dict:
    return {entry.id: entry for entry in entries}


def test_lists_copyleft_components_only(no_network: None) -> None:
    catalogue = collector.load_catalogue()
    entries = _by_id(collector.collect(catalogue, "radio"))

    assert {"mutagen", "pillow-heif", "libmpv", "mingw-runtime"} <= set(entries)
    for entry in entries.values():
        assert set(entry.licences) & collector.COPYLEFT, entry.id
    assert "pyinstaller" not in entries, "build-only tools are not distributed"
    assert "pandoc-docs" not in entries


def test_exact_versions_come_from_the_build_folder(no_network: None, build_dir: Path) -> None:
    entries = _by_id(collector.collect(collector.load_catalogue(), "radio", build_dir))

    mutagen = entries["mutagen"]
    assert mutagen.version == "1.48.9" and mutagen.version_from == "build"
    assert "mutagen==1.48.9" in mutagen.sources[0].command

    heif = {s.label.split(" ", 1)[0]: s for s in entries["pillow-heif"].sources}
    assert heif["libheif"].url.endswith("/archive/refs/tags/v1.99.0.tar.gz")
    assert heif["libheif"].version_from == "build"
    assert heif["x265"].version == "9.9"
    assert heif["libde265"].version_from == "catalogue", "not in the bundled list here"

    gcc = [s.version for s in entries["mingw-runtime"].sources]
    assert gcc == ["15.1.0"]


def test_without_a_build_folder_versions_are_marked_catalogue(no_network: None) -> None:
    entries = _by_id(collector.collect(collector.load_catalogue(), "radio"))

    assert entries["mutagen"].version_from == "catalogue"
    assert all(s.version_from == "catalogue" for s in entries["mutagen"].sources)


def test_pymupdf_keeps_its_pinned_sdist_and_checksum(no_network: None) -> None:
    catalogue = collector.load_catalogue()
    entry = _by_id(collector.collect(catalogue, "quill"))["pymupdf"]
    pinned = next(item for item in catalogue.components if item.id == "pymupdf")

    assert entry.sources[0].url == pinned.source_url
    assert entry.sources[0].sha256 == pinned.source_sha256


def test_main_writes_the_manifest_and_never_downloads_by_default(
    no_network: None, build_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def no_download(*_args: object, **_kwargs: object) -> int:
        raise AssertionError("downloaded without --download")

    monkeypatch.setattr(collector, "download", no_download)
    out = tmp_path / "out"

    code = collector.main([
        "--product",
        "radio",
        "--build-dir",
        str(build_dir),
        "--out",
        str(out),
        "--commit",
        "abc123",
    ])

    assert code == 0
    data = json.loads((out / collector.MANIFEST_JSON).read_text(encoding="utf-8"))
    assert data["product"] == "radio"
    assert data["quill_commit"] == "abc123"
    assert "git archive" in data["quill_source"]["command"]
    ids = {component["id"] for component in data["components"]}
    assert "mutagen" in ids
    text = (out / collector.MANIFEST_TXT).read_text(encoding="utf-8")
    assert "mutagen 1.48.9 (build)" in text
    assert "QUILL itself:" in text


def test_an_unknown_product_is_refused(no_network: None, tmp_path: Path) -> None:
    assert collector.main(["--product", "nope", "--out", str(tmp_path)]) == 2
