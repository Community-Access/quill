"""Layer 2 of IntelliSense: names from the rest of the project
(quill.core.project_names), over a small project built in tmp_path."""

from __future__ import annotations

import threading
from pathlib import Path

from quill.core import project_names
from quill.core.project_names import (
    build_project_index,
    imported_modules,
    project_root_for,
)


def _project(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    (root / ".git").mkdir(parents=True)
    (root / "pkg").mkdir()
    (root / "pkg" / "shapes.py").write_text(
        "class Rectangle:\n    pass\n\ndef rectangle_area(r):\n    return r\n", encoding="utf-8"
    )
    (root / "pkg" / "colours.py").write_text(
        "RECT_COLOUR = 'red'\nrecolour = 1\n", encoding="utf-8"
    )
    (root / "notes.md").write_text("rectangle rectangles everywhere\n", encoding="utf-8")
    (root / "node_modules").mkdir()
    (root / "node_modules" / "dep.js").write_text(
        "function rectDependency() {}\n", encoding="utf-8"
    )
    (root / "main.py").write_text("from pkg.shapes import Rectangle\nrec\n", encoding="utf-8")
    return root


def test_the_project_root_is_the_marked_folder(tmp_path: Path) -> None:
    root = _project(tmp_path)
    assert project_root_for(root / "pkg" / "shapes.py") == root.resolve()
    loose = tmp_path / "loose" / "a.py"
    loose.parent.mkdir()
    assert project_root_for(loose) == loose.parent.resolve()
    assert project_root_for(None) is None


def test_the_walk_reads_code_and_skips_prose_and_dependencies(tmp_path: Path) -> None:
    index = build_project_index(_project(tmp_path))
    assert "rectangle_area" in index.files_for
    assert "rectDependency" not in index.files_for, "node_modules is skipped"
    assert "everywhere" not in index.files_for, "Markdown is prose, not code"
    assert index.kinds["Rectangle"] == "class"
    assert index.kinds["rectangle_area"] == "function"


def test_imported_files_and_definitions_come_first(tmp_path: Path) -> None:
    index = build_project_index(_project(tmp_path))
    names = index.complete("rec", exclude=set(), imports={"shapes"}, own_stem="main")
    assert [n.name for n in names][:2] == ["rectangle_area", "recolour"]
    assert ("Rectangle", "class") in [(n.name, n.kind) for n in names]


def test_names_only_in_this_file_and_excluded_names_are_left_to_layer_1(tmp_path: Path) -> None:
    root = _project(tmp_path)
    (root / "solo.py").write_text("record_only_here = 1\n", encoding="utf-8")
    index = build_project_index(root)
    names = index.complete("rec", exclude={"recolour"}, imports=set(), own_stem="solo")
    labels = [n.name for n in names]
    assert "record_only_here" not in labels
    assert "recolour" not in labels


def test_the_caps_stop_the_walk_and_say_so(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(project_names, "MAX_FILES", 1)
    index = build_project_index(_project(tmp_path))
    assert index.files_read == 1 and index.truncated


def test_a_cancelled_walk_stops(tmp_path: Path) -> None:
    cancel = threading.Event()
    cancel.set()
    index = build_project_index(_project(tmp_path), cancel=cancel)
    assert index.files_read == 0 and index.truncated


def test_imports_in_several_languages() -> None:
    text = (
        "from quill.core.code_names import x\nimport os\n"
        "const u = require('./lib/util')\nimport { a } from './widgets.js'\n"
        '#include "point.h"\nuse std::io;\n'
    )
    assert imported_modules(text) >= {"code_names", "os", "util", "widgets", "point", "io"}


def test_a_loose_file_has_no_marked_project_and_is_never_indexed(tmp_path: Path) -> None:
    """Review 2026-11-09, QUILL Lite 12: a file on the Desktop must not index the Desktop."""
    from quill.core.project_names import marked_project_root

    loose = tmp_path / "desk" / "note.py"
    loose.parent.mkdir()
    loose.write_text("x = 1\n", encoding="utf-8")
    assert marked_project_root(loose) is None
    assert project_root_for(loose) == loose.parent.resolve(), "a server still gets a folder"
    (tmp_path / "desk" / "pyproject.toml").write_text("", encoding="utf-8")
    assert marked_project_root(loose) == loose.parent.resolve()
