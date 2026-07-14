from __future__ import annotations

from pathlib import Path

from scripts.footprint_report import (
    Component,
    build_report,
    dir_size,
    human_bytes,
    render_markdown,
    sort_desc,
    total_bytes,
)


def test_human_bytes_scales_units() -> None:
    assert human_bytes(500) == "0.5 KB"
    assert human_bytes(5 * 1024 * 1024) == "5.0 MB"
    assert human_bytes(2 * 1024 * 1024 * 1024) == "2.00 GB"


def test_sort_desc_is_biggest_first_stable_on_ties() -> None:
    comps = [
        Component("b", "x", 10, "/b"),
        Component("a", "x", 10, "/a"),
        Component("c", "x", 99, "/c"),
    ]
    ordered = [c.name for c in sort_desc(comps)]
    assert ordered == ["c", "a", "b"]


def test_total_bytes_sums() -> None:
    comps = [Component("a", "x", 3, "/a"), Component("b", "x", 4, "/b")]
    assert total_bytes(comps) == 7


def test_dir_size_walks_files(tmp_path: Path) -> None:
    (tmp_path / "one.bin").write_bytes(b"x" * 100)
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "two.bin").write_bytes(b"y" * 50)
    assert dir_size(tmp_path) == 150
    assert dir_size(tmp_path / "one.bin") == 100


def test_dir_size_missing_path_is_zero(tmp_path: Path) -> None:
    assert dir_size(tmp_path / "nope") == 0


def test_build_report_is_read_only_and_populated(tmp_path: Path) -> None:
    # Point --root at an empty tree: the walk must not create anything and must
    # still return a well-formed report (degrades, never crashes).
    before = list(tmp_path.iterdir())
    report = build_report(tmp_path)
    assert list(tmp_path.iterdir()) == before
    assert report.python
    assert report.platform
    # Rendering must not raise on an empty component set.
    md = render_markdown(report, top=10)
    assert "footprint baseline" in md.lower()
